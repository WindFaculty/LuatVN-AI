"""Deny-by-default authorization for source operations in the G1 pilot."""

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit


ACTIONS = frozenset({"manual_download", "automated_access", "store", "index", "cite", "redistribute"})
SELECTORS = ("purpose", "data_class", "region", "document_type", "url")


class RightsDenied(PermissionError):
    pass


@dataclass(frozen=True)
class SourceOperation:
    source_id: str
    action: str
    purpose: str
    data_class: str
    region: str
    document_type: str
    url: str
    document_date: date
    size_bytes: int


@dataclass(frozen=True)
class Authorization:
    registry_revision: str
    source_id: str
    action: str
    evidence_ref: str
    max_actions_per_minute: int


def _required_text(record: dict, field: str) -> None:
    value = record[field]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing {field}")


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("policy timestamp requires timezone")
    return parsed


def _https(value: str) -> None:
    url = urlsplit(value)
    if (url.scheme != "https" or not url.hostname or url.username is not None or url.fragment
            or "*" in value or any(c.isspace() for c in value)):
        raise ValueError("expected exact HTTPS URL")


def _unique_keys(pairs: list[tuple]) -> dict:
    keys = Counter(key for key, _ in pairs)
    if any(count > 1 for count in keys.values()):
        raise ValueError("duplicate registry key")
    return dict(pairs)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def authorization_clock(
    source_id: str,
    cutoff: datetime,
    *,
    at: datetime | None = None,
    at_fn: Callable[[], datetime] | None = None,
) -> Callable[[], datetime]:
    """Resolve the clock for source rights; fixture replay may use a fixed time."""
    if at_fn is not None:
        return at_fn
    if at is not None or source_id.startswith("FIXTURE-"):
        fixed_time = at if at is not None else cutoff
        return lambda: fixed_time
    return _utc_now


class SourceRegistry:
    def __init__(self, path: Path):
        self._path = path.resolve()
        self._contents = self._path.read_bytes()
        record = json.loads(self._contents.decode("utf-8"), object_pairs_hook=_unique_keys)
        _required_text(record, "revision")
        self.revision = record["revision"]
        self._sources = record["sources"]
        for source_id, source in self._sources.items():
            _required_text(source, "name")
            if source.get("url"):
                _https(source["url"])
            for action, policy in source["actions"].items():
                if action not in ACTIONS or policy["status"] not in {
                    "PENDING_RIGHTS", "APPROVED", "DENIED", "EXPIRED"
                }:
                    raise ValueError(f"invalid action/status for {source_id}")
                if policy["status"] == "APPROVED":
                    self._validate_approval(source, policy)

    @staticmethod
    def _validate_approval(source: dict, policy: dict) -> None:
        for field in ("owner", "contact", "url"):
            _required_text(source, field)
        for field in ("evidence_ref", "approved_by", "policy_url", "policy_version", "revocation_procedure"):
            _required_text(policy, field)
        _https(policy["policy_url"])
        date.fromisoformat(policy["policy_date"])
        if _timestamp(policy["approved_at"]) >= _timestamp(policy["expires_at"]):
            raise ValueError("invalid approval interval")
        scope = policy["scope"]
        if date.fromisoformat(scope["document_from"]) > date.fromisoformat(scope["document_through"]):
            raise ValueError("invalid document date interval")
        for field in SELECTORS:
            values = scope[field]
            if not isinstance(values, list) or not values or any(
                not isinstance(value, str) or not value.strip() or "*" in value for value in values
            ):
                raise ValueError(f"expected explicit {field} values")
        for url in scope["url"]:
            _https(url)
        for field in ("max_bytes_per_item", "max_actions_per_minute"):
            if type(policy[field]) is not int or policy[field] <= 0:
                raise ValueError(f"invalid {field}")

    def authorize(self, operation: SourceOperation, *, at: datetime) -> Authorization:
        if at.utcoffset() is None:
            raise ValueError("authorization timestamp requires timezone")
        source = self._sources.get(operation.source_id)
        if source is None or operation.action not in ACTIONS:
            raise RightsDenied("UNKNOWN_SOURCE_OR_ACTION")
        policy = source["actions"].get(operation.action, {"status": "PENDING_RIGHTS"})
        if policy["status"] != "APPROVED":
            raise RightsDenied(policy["status"])
        if not operation.source_id.startswith("FIXTURE-"):
            try:
                current_contents = self._path.read_bytes()
            except OSError as error:
                raise RightsDenied("REGISTRY_UNAVAILABLE") from error
            if current_contents != self._contents:
                raise RightsDenied("REGISTRY_CHANGED")
        if not _timestamp(policy["approved_at"]) <= at < _timestamp(policy["expires_at"]):
            raise RightsDenied("OUTSIDE_APPROVAL_PERIOD")
        scope = policy["scope"]
        if (any(getattr(operation, field) not in scope[field] for field in SELECTORS)
                or not date.fromisoformat(scope["document_from"]) <= operation.document_date
                <= date.fromisoformat(scope["document_through"])
                or type(operation.size_bytes) is not int
                or not 0 <= operation.size_bytes <= policy["max_bytes_per_item"]):
            raise RightsDenied("OUTSIDE_APPROVED_SCOPE")
        return Authorization(self.revision, operation.source_id, operation.action, policy["evidence_ref"],
                             policy["max_actions_per_minute"])
