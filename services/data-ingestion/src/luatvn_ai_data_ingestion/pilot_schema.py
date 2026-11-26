"""Shared schema, rights guards, atomic staging, and cutoff rules for the G1 SRC-01/SRC-03 pilot."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sqlite3
import ssl
import time
import unicodedata
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from .source_rights import ACTIONS, Authorization, RightsDenied, SourceOperation, SourceRegistry

VN_TZ = timezone(timedelta(hours=7))
WINDOW_START_DATE = date(2020, 1, 1)
PILOT_DOMAINS = ("CIV", "CRI", "ADM", "LAB", "LND", "BUS", "TRA", "EDU", "ENV")
ALL_DOMAIN_LABELS = (*PILOT_DOMAINS, "UNMAPPED")

RELATION_ROLES = frozenset(
    {
        "catalog_entry",
        "signed_original",
        "gazette_publication",
        "consolidated",
        "appendix",
        "corrigendum",
        "amending",
        "pre_2020_reference",
    }
)

MIME_MAGIC_PREFIXES: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF-",),
    "application/msword": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (b"PK\x03\x04",),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (b"PK\x03\x04",),
    "text/html": (b"<!doctype", b"<html", b"<div", b"<table", b"<?xml"),
    "text/plain": (),
}

CATALOG_RECORD_FIELDS = (
    "source_id",
    "source_record_id",
    "partition_id",
    "data_origin",
    "page_url",
    "year",
    "quarter",
    "observed_at",
    "gazette_issue",
    "gazette_page",
    "continuation_issues",
    "issuer",
    "document_type",
    "document_number",
    "title",
    "issued_date",
    "gazette_published_date",
    "observed_effective_date",
    "version",
    "relation_role",
    "related_to_document_number",
    "domain_candidate",
    "rights_ref",
    "status",
    "date_reconciliation_flag",
    "is_pre_2020_reference",
    "eligible_for_pilot_denominator",
    "legal_status_verified",
    "error",
    "cutoff_utc",
    "cutoff_vn",
)

ARTIFACT_RECORD_FIELDS = (
    "source_id",
    "source_record_id",
    "partition_id",
    "data_origin",
    "parent_id",
    "attachment_id",
    "page_url",
    "file_url",
    "year",
    "quarter",
    "observed_at",
    "gazette_issue",
    "gazette_page",
    "document_number",
    "version",
    "relation_role",
    "file_type",
    "declared_mime",
    "detected_mime",
    "size_bytes",
    "sha256",
    "stored_blob_path",
    "rights_ref",
    "status",
    "quarantine_reason",
    "error",
    "cutoff_utc",
    "cutoff_vn",
)


@dataclass(frozen=True)
class RunCutoff:
    run_id: str
    cutoff_utc: str
    cutoff_vn: str
    window_start_date: str = "2020-01-01"

    @property
    def cutoff_datetime_vn(self) -> datetime:
        parsed = datetime.fromisoformat(self.cutoff_vn)
        if parsed.utcoffset() is None:
            raise ValueError("cutoff_vn must include timezone offset")
        return parsed.astimezone(VN_TZ)

    @property
    def cutoff_date_vn(self) -> date:
        return self.cutoff_datetime_vn.date()

    @property
    def window_start(self) -> date:
        return date.fromisoformat(self.window_start_date)


@dataclass(frozen=True)
class CatalogRecord:
    source_id: str
    source_record_id: str
    partition_id: str
    data_origin: str
    page_url: str
    year: int | str
    quarter: str
    observed_at: str
    gazette_issue: str
    gazette_page: str
    continuation_issues: list[str]
    issuer: str
    document_type: str
    document_number: str
    title: str
    issued_date: str
    gazette_published_date: str
    observed_effective_date: str
    version: str
    relation_role: str
    related_to_document_number: str
    domain_candidate: str
    rights_ref: str
    status: str
    date_reconciliation_flag: str
    is_pre_2020_reference: bool
    eligible_for_pilot_denominator: bool
    legal_status_verified: bool
    error: str
    cutoff_utc: str
    cutoff_vn: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArtifactRecord:
    source_id: str
    source_record_id: str
    partition_id: str
    data_origin: str
    parent_id: str
    attachment_id: str
    page_url: str
    file_url: str
    year: int | str
    quarter: str
    observed_at: str
    gazette_issue: str
    gazette_page: str
    document_number: str
    version: str
    relation_role: str
    file_type: str
    declared_mime: str
    detected_mime: str
    size_bytes: int | None
    sha256: str
    stored_blob_path: str
    rights_ref: str
    status: str
    quarantine_reason: str
    error: str
    cutoff_utc: str
    cutoff_vn: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PartitionCheckpoint:
    source_id: str
    partition_id: str
    year: int
    quarter: str
    owner_worker: str
    status: str
    last_completed_cursor: int
    completed_record_ids: list[str] = field(default_factory=list)
    failed_record_ids: list[str] = field(default_factory=list)
    quarantined_attachment_ids: list[str] = field(default_factory=list)
    rights_status: str = "PENDING_RIGHTS"
    rights_ref: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NetworkPolicyStop(RuntimeError):
    """Raised when a partition must stop due to 403, CAPTCHA, TLS, or exhausted 429/retry budget."""

    def __init__(self, code: str, message: str, *, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.code = code
        self.retry_after_seconds = retry_after_seconds


class SharedRateLimiter:
    """Enforces per-source and shared infrastructure request limits (e.g., chinhphu.vn).

    When ``state_path`` is supplied, timestamps are persisted in a SQLite database using
    ``BEGIN IMMEDIATE`` transactions so independent CLI worker processes share the exact
    same per-source and shared infrastructure buckets.
    """

    def __init__(
        self,
        *,
        per_source_max_per_minute: int = 20,
        shared_infra_max_per_minute: int = 30,
        clock: Callable[[], float] | None = None,
        state_path: Path | str | None = None,
    ):
        if per_source_max_per_minute <= 0 or shared_infra_max_per_minute <= 0:
            raise ValueError("rate limits must be positive integers")
        self.per_source_max_per_minute = per_source_max_per_minute
        self.shared_infra_max_per_minute = shared_infra_max_per_minute
        self.state_path = Path(state_path) if state_path is not None else None
        if clock is not None:
            self._clock = clock
        else:
            self._clock = time.time if self.state_path is not None else time.monotonic
        self._source_hits: dict[str, list[float]] = {}
        self._infra_hits: dict[str, list[float]] = {}
        if self.state_path is not None:
            self._init_state_db()

    def _connect(self) -> sqlite3.Connection:
        assert self.state_path is not None
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.state_path), timeout=30.0, isolation_level=None)
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def _init_state_db(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_hits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    source_id TEXT NOT NULL,
                    infra_group TEXT NOT NULL,
                    pid INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rate_hits_source_ts ON rate_hits (source_id, ts)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rate_hits_infra_ts ON rate_hits (infra_group, ts)"
            )
            conn.execute("COMMIT")

    def acquire(
        self,
        source_id: str,
        infra_group: str = "chinhphu.vn",
        *,
        per_source_limit: int | None = None,
    ) -> None:
        effective_source_cap = self.per_source_max_per_minute
        if per_source_limit is not None:
            if per_source_limit <= 0:
                raise ValueError("per_source_limit must be positive")
            effective_source_cap = min(effective_source_cap, per_source_limit)
        now = float(self._clock())
        cutoff = now - 60.0
        if self.state_path is not None:
            with closing(self._connect()) as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    conn.execute("DELETE FROM rate_hits WHERE ts <= ?", (cutoff,))
                    source_count = conn.execute(
                        "SELECT COUNT(*) FROM rate_hits WHERE source_id = ? AND ts > ?",
                        (source_id, cutoff),
                    ).fetchone()[0]
                    if source_count >= effective_source_cap:
                        conn.execute("ROLLBACK")
                        raise NetworkPolicyStop(
                            "SOURCE_RATE_LIMIT",
                            f"Source {source_id} exceeded {effective_source_cap}/min",
                        )
                    infra_count = conn.execute(
                        "SELECT COUNT(*) FROM rate_hits WHERE infra_group = ? AND ts > ?",
                        (infra_group, cutoff),
                    ).fetchone()[0]
                    if infra_count >= self.shared_infra_max_per_minute:
                        conn.execute("ROLLBACK")
                        raise NetworkPolicyStop(
                            "SHARED_INFRA_RATE_LIMIT",
                            f"Infrastructure group {infra_group} exceeded {self.shared_infra_max_per_minute}/min",
                        )
                    conn.execute(
                        "INSERT INTO rate_hits (ts, source_id, infra_group, pid) VALUES (?, ?, ?, ?)",
                        (now, source_id, infra_group, os.getpid()),
                    )
                    conn.execute("COMMIT")
                except Exception:
                    if conn.in_transaction:
                        conn.execute("ROLLBACK")
                    raise
            return

        s_hits = [ts for ts in self._source_hits.get(source_id, []) if ts > cutoff]
        i_hits = [ts for ts in self._infra_hits.get(infra_group, []) if ts > cutoff]
        if len(s_hits) >= effective_source_cap:
            raise NetworkPolicyStop(
                "SOURCE_RATE_LIMIT",
                f"Source {source_id} exceeded {effective_source_cap}/min",
            )
        if len(i_hits) >= self.shared_infra_max_per_minute:
            raise NetworkPolicyStop(
                "SHARED_INFRA_RATE_LIMIT",
                f"Infrastructure group {infra_group} exceeded {self.shared_infra_max_per_minute}/min",
            )
        s_hits.append(now)
        i_hits.append(now)
        self._source_hits[source_id] = s_hits
        self._infra_hits[infra_group] = i_hits

    def snapshot_counts(self, *, now: float | None = None) -> dict[str, dict[str, int]]:
        """Return active 60-second hit counts grouped by source and infra group."""
        current = float(self._clock() if now is None else now)
        cutoff = current - 60.0
        if self.state_path is not None:
            with closing(self._connect()) as conn:
                by_source = {
                    row[0]: int(row[1])
                    for row in conn.execute(
                        "SELECT source_id, COUNT(*) FROM rate_hits WHERE ts > ? GROUP BY source_id",
                        (cutoff,),
                    ).fetchall()
                }
                by_infra = {
                    row[0]: int(row[1])
                    for row in conn.execute(
                        "SELECT infra_group, COUNT(*) FROM rate_hits WHERE ts > ? GROUP BY infra_group",
                        (cutoff,),
                    ).fetchall()
                }
            return {"by_source": by_source, "by_infra": by_infra}
        return {
            "by_source": {
                key: len([ts for ts in vals if ts > cutoff])
                for key, vals in self._source_hits.items()
                if any(ts > cutoff for ts in vals)
            },
            "by_infra": {
                key: len([ts for ts in vals if ts > cutoff])
                for key, vals in self._infra_hits.items()
                if any(ts > cutoff for ts in vals)
            },
        }


def classify_http_stop(
    *,
    status_code: int | None,
    body_snippet: str = "",
    retry_after: str | None = None,
    tls_error: str | None = None,
    retries_used: int = 0,
    max_transient_retries: int = 2,
) -> tuple[str, int | None]:
    """Return ('PROCEED'|'RETRY'|'STOP_*', wait_seconds) according to G1 network stop rules."""
    if tls_error:
        return ("STOP_TLS_ERROR", None)
    if status_code == 403:
        return ("STOP_HTTP_403", None)
    low = body_snippet.casefold()
    if any(token in low for token in ("captcha", "verify you are human", "cloudflare", "mã xác thực robot")):
        return ("STOP_CAPTCHA", None)
    if status_code == 429:
        wait = int(retry_after) if retry_after and retry_after.isdigit() else None
        if retries_used < max_transient_retries and wait is not None and wait <= 60:
            return ("RETRY", wait)
        return ("STOP_HTTP_429", wait)
    if status_code is not None and 500 <= status_code < 600:
        if retries_used < max_transient_retries:
            return ("RETRY", 2 ** retries_used)
        return ("STOP_RETRY_BUDGET_EXHAUSTED", None)
    if status_code is None:
        if retries_used < max_transient_retries:
            return ("RETRY", 2 ** retries_used)
        return ("STOP_NETWORK_ERROR", None)
    if status_code == 200:
        return ("PROCEED", None)
    return (f"STOP_HTTP_{status_code}", None)


def parse_vn_date(raw_value: str | None) -> date | None:
    """Parse common Vietnamese portal dates (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD)."""
    if not raw_value:
        return None
    cleaned = raw_value.strip()
    for pattern, order in (
        (r"^(\d{4})-(\d{2})-(\d{2})$", "ymd"),
        (r"^(\d{1,2})/(\d{1,2})/(\d{4})$", "dmy"),
        (r"^(\d{1,2})-(\d{1,2})-(\d{4})$", "dmy"),
    ):
        match = re.match(pattern, cleaned)
        if match:
            a, b, c = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            try:
                return date(a, b, c) if order == "ymd" else date(c, b, a)
            except ValueError:
                return None
    return None


def date_quarter(d: date | None) -> str:
    if d is None:
        return "UNKNOWN"
    return f"Q{((d.month - 1) // 3) + 1}"


def evaluate_date_window(
    issued_date_str: str | None,
    cutoff: RunCutoff,
    *,
    gazette_published_date_str: str | None = None,
    observed_effective_date_str: str | None = None,
) -> dict[str, Any]:
    """Classify a record against [2020-01-01, cutoff_date_vn] and flag date anomalies."""
    issued = parse_vn_date(issued_date_str)
    gazette = parse_vn_date(gazette_published_date_str)
    effective = parse_vn_date(observed_effective_date_str)

    flags: list[str] = []
    if issued_date_str and issued is None:
        flags.append("UNPARSEABLE_ISSUED_DATE")
    if not issued_date_str:
        flags.append("MISSING_ISSUED_DATE")
    if gazette_published_date_str and gazette is None:
        flags.append("UNPARSEABLE_GAZETTE_DATE")
    if observed_effective_date_str and effective is None:
        flags.append("UNPARSEABLE_EFFECTIVE_DATE")
    if issued is not None and gazette is not None and gazette < issued:
        flags.append("GAZETTE_BEFORE_ISSUED_DATE")
    if issued is not None and effective is not None and effective < issued:
        flags.append("EFFECTIVE_BEFORE_ISSUED_DATE")

    is_pre_2020 = issued is not None and issued < cutoff.window_start
    is_post_cutoff = issued is not None and issued > cutoff.cutoff_date_vn
    if is_post_cutoff:
        flags.append("POST_CUTOFF_ISSUED_DATE")

    eligible = (
        issued is not None
        and not is_pre_2020
        and not is_post_cutoff
        and "UNPARSEABLE_ISSUED_DATE" not in flags
    )
    return {
        "issued_iso": issued.isoformat() if issued else "",
        "gazette_iso": gazette.isoformat() if gazette else "",
        "effective_iso": effective.isoformat() if effective else "",
        "year": issued.year if issued else "UNKNOWN",
        "quarter": date_quarter(issued),
        "is_pre_2020_reference": is_pre_2020,
        "is_post_cutoff": is_post_cutoff,
        "eligible_for_pilot_denominator": eligible,
        "date_reconciliation_flag": ";".join(flags),
    }


def normalize_text_nfc(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(unicodedata.normalize("NFC", value).strip().split())


def normalize_document_number(value: str | None) -> str:
    """Normalize Vietnamese legal document numbers for canonical grouping without losing accents."""
    cleaned = normalize_text_nfc(value)
    if not cleaned:
        return ""
    cleaned = re.sub(r"\s*/\s*", "/", cleaned)
    cleaned = re.sub(r"\s*-\s*", "-", cleaned)
    return cleaned.upper()


def normalize_issuer(value: str | None) -> str:
    return normalize_text_nfc(value).casefold()


def normalize_document_type(value: str | None) -> str:
    return normalize_text_nfc(value).casefold()


def detect_mime_from_bytes(payload: bytes, declared_mime: str = "") -> str:
    if not payload:
        return "application/x-empty"
    if payload.startswith(b"%PDF-"):
        return "application/pdf"
    if payload.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "application/msword"
    if payload.startswith(b"PK\x03\x04"):
        if b"xl/" in payload[:4096]:
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    head = payload[:512].lstrip().lower()
    if head.startswith((b"<!doctype html", b"<html", b"<div", b"<table", b"<?xml")):
        return "text/html"
    try:
        payload.decode("utf-8")
        if b"\x00" not in payload:
            return "text/plain"
    except UnicodeDecodeError:
        pass
    return "application/octet-stream"


def validate_blob_integrity(
    payload: bytes,
    *,
    declared_mime: str,
    expected_sha256: str | None = None,
) -> tuple[str, str, str]:
    """Return (sha256_hex, detected_mime, quarantine_reason_or_empty)."""
    digest = hashlib.sha256(payload).hexdigest()
    detected = detect_mime_from_bytes(payload, declared_mime)
    if not payload:
        return (digest, detected, "EMPTY_CORRUPT_ARTIFACT")
    if expected_sha256 and digest != expected_sha256.lower():
        return (digest, detected, "CHECKSUM_MISMATCH")
    if declared_mime and detected != declared_mime:
        # Allow text/html declared when sniffing plain utf-8 only if HTML tags exist; otherwise flag mismatch
        return (digest, detected, f"MIME_MISMATCH:declared={declared_mime},detected={detected}")
    if detected == "application/pdf" and b"%%EOF" not in payload[-2048:]:
        return (digest, detected, "TRUNCATED_OR_CORRUPT_PDF")
    return (digest, detected, "")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def atomic_write_bytes(path: Path, payload: bytes) -> str:
    """Atomically write bytes after computing checksum and verifying the written temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    expected = sha256_bytes(payload)
    if path.exists():
        existing = sha256_bytes(path.read_bytes())
        if existing != expected:
            raise ValueError(f"Immutable file conflict at {path}: existing={existing} new={expected}")
        return expected
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_bytes(payload)
    actual = sha256_bytes(tmp.read_bytes())
    if actual != expected:
        tmp.unlink(missing_ok=True)
        raise IOError(f"Checksum verification failed for {path}")
    os.replace(tmp, path)
    return expected


def atomic_write_text(path: Path, text: str, *, allow_overwrite: bool = True) -> str:
    """Atomically write UTF-8 text (without BOM, LF line endings) and return SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.replace("\r\n", "\n")
    payload = normalized.encode("utf-8")
    expected = sha256_bytes(payload)
    if not allow_overwrite and path.exists():
        existing = sha256_bytes(path.read_bytes())
        if existing != expected:
            raise ValueError(f"Immutable text file conflict at {path}")
        return expected
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_bytes(payload)
    actual = sha256_bytes(tmp.read_bytes())
    if actual != expected:
        tmp.unlink(missing_ok=True)
        raise IOError(f"Checksum verification failed for {path}")
    os.replace(tmp, path)
    return expected


def write_jsonl_atomic(path: Path, rows: Iterable[dict[str, Any]]) -> str:
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    content = ("\n".join(lines) + "\n") if lines else ""
    return atomic_write_text(path, content, allow_overwrite=True)


def write_csv_atomic(path: Path, fieldnames: Iterable[str], rows: Iterable[dict[str, Any]]) -> str:
    fields = list(fieldnames)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            serialized = {}
            for key in fields:
                val = row.get(key, "")
                if isinstance(val, (list, dict)):
                    serialized[key] = json.dumps(val, ensure_ascii=False, sort_keys=True)
                elif val is None:
                    serialized[key] = ""
                else:
                    serialized[key] = val
            writer.writerow(serialized)
    digest = sha256_bytes(tmp.read_bytes())
    os.replace(tmp, path)
    return digest


def check_source_actions(
    registry: SourceRegistry,
    *,
    source_id: str,
    actions: Iterable[str],
    purpose: str,
    data_class: str,
    region: str,
    document_type: str,
    url: str,
    document_date: date,
    size_bytes: int,
    at: datetime,
) -> tuple[bool, dict[str, str]]:
    """Verify every requested action against SourceRegistry (fail-closed)."""
    statuses: dict[str, str] = {}
    all_ok = True
    for action in actions:
        if action not in ACTIONS:
            statuses[action] = "INVALID_ACTION"
            all_ok = False
            continue
        op = SourceOperation(
            source_id=source_id,
            action=action,
            purpose=purpose,
            data_class=data_class,
            region=region,
            document_type=document_type,
            url=url,
            document_date=document_date,
            size_bytes=size_bytes,
        )
        try:
            auth = registry.authorize(op, at=at)
            statuses[action] = f"APPROVED:{auth.registry_revision}:{auth.evidence_ref}"
        except RightsDenied as err:
            statuses[action] = f"BLOCKED_RIGHTS:{err}"
            all_ok = False
    return (all_ok, statuses)


def authorize_actions(
    registry: SourceRegistry,
    *,
    source_id: str,
    actions: Iterable[str],
    purpose: str,
    data_class: str,
    region: str,
    document_type: str,
    url: str,
    document_date: date,
    size_bytes: int,
    at: datetime,
    redirect_urls: Iterable[str] = (),
    final_url: str = "",
) -> dict[str, Authorization]:
    """Authorize exact operation URL (plus every redirect hop/final URL), date, time, and size."""
    urls_to_check: list[str] = []
    for candidate in (url, *redirect_urls, final_url):
        cleaned = (candidate or "").strip()
        if cleaned and cleaned not in urls_to_check:
            urls_to_check.append(cleaned)
    if not urls_to_check:
        raise RightsDenied("MISSING_URL")

    authorizations: dict[str, Authorization] = {}
    for action in actions:
        if action not in ACTIONS:
            raise RightsDenied(f"INVALID_ACTION:{action}")
        last_auth: Authorization | None = None
        for target_url in urls_to_check:
            op = SourceOperation(
                source_id=source_id,
                action=action,
                purpose=purpose,
                data_class=data_class,
                region=region,
                document_type=document_type,
                url=target_url,
                document_date=document_date,
                size_bytes=size_bytes,
            )
            last_auth = registry.authorize(op, at=at)
        assert last_auth is not None
        authorizations[action] = last_auth
    return authorizations


def canonical_partition_status(status: str) -> str:
    """Normalize partition status labels (legacy 'COMPLETE' -> 'COMPLETED')."""
    normalized = (status or "").strip().upper()
    if normalized == "COMPLETE":
        return "COMPLETED"
    return normalized or "UNKNOWN"


class _GuardedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, on_redirect: Callable[[str], None] | None = None) -> None:
        super().__init__()
        self._on_redirect = on_redirect
        self.chain: list[str] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        resolved = urljoin(req.full_url, newurl)
        self.chain.append(resolved)
        if self._on_redirect is not None:
            self._on_redirect(resolved)
        return super().redirect_request(req, fp, code, msg, headers, resolved)


@dataclass(frozen=True)
class HttpTransportResponse:
    url: str
    final_url: str
    redirect_urls: tuple[str, ...]
    status_code: int | None
    body: bytes = b""
    headers: Mapping[str, str] = field(default_factory=dict)
    retry_after: str | None = None
    tls_error: str | None = None
    message: str = ""


def build_authorized_https_fetcher(
    *,
    timeout_seconds: float = 15.0,
    max_bytes: int = 32 * 1024 * 1024,
    user_agent: str = "LuatVN-AI-G1-AuthorizedClient/0.1",
    on_redirect: Callable[[str], None] | None = None,
) -> Callable[[str], HttpTransportResponse]:
    """Build a strict-TLS HTTPS fetcher with pre-redirect authorization and size cap."""
    ssl_ctx = ssl.create_default_context()

    def fetch(url: str) -> HttpTransportResponse:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise RightsDenied(f"NON_HTTPS_URL:{url}")
        redirect_handler = _GuardedRedirectHandler(on_redirect=on_redirect)
        opener = build_opener(redirect_handler, HTTPSHandler(context=ssl_ctx))
        request = Request(url, headers={"User-Agent": user_agent})
        try:
            with opener.open(request, timeout=timeout_seconds) as response:
                raw = response.read(max_bytes + 1)
                headers = {key.casefold(): value for key, value in response.headers.items()}
                return HttpTransportResponse(
                    url=url,
                    final_url=response.geturl(),
                    redirect_urls=tuple(redirect_handler.chain),
                    status_code=response.status,
                    body=raw,
                    headers=headers,
                    retry_after=headers.get("retry-after"),
                )
        except RightsDenied:
            raise
        except HTTPError as err:
            headers = {key.casefold(): value for key, value in (err.headers.items() if err.headers else ())}
            body = b""
            try:
                body = err.read(4096)
            except Exception:
                pass
            return HttpTransportResponse(
                url=url,
                final_url=getattr(err, "url", url) or url,
                redirect_urls=tuple(redirect_handler.chain),
                status_code=err.code,
                body=body,
                headers=headers,
                retry_after=headers.get("retry-after"),
                message=str(err),
            )
        except URLError as err:
            reason = str(err.reason)
            is_tls = isinstance(err.reason, ssl.SSLError) or "ssl" in reason.lower() or "cert" in reason.lower()
            return HttpTransportResponse(
                url=url,
                final_url=url,
                redirect_urls=tuple(redirect_handler.chain),
                status_code=None,
                tls_error=reason if is_tls else None,
                message=f"URLError: {reason}",
            )

    return fetch


def resolve_safe_local_path(root: Path, relative_or_child: str) -> Path:
    """Resolve a manifest-declared local path strictly inside ``root`` (blocks traversal)."""
    root_resolved = Path(root).resolve()
    candidate = (root_resolved / relative_or_child).resolve()
    if not candidate.is_relative_to(root_resolved):
        raise ValueError(f"path escapes intake root: {relative_or_child}")
    return candidate


_SENSITIVE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(authorization\s*:\s*(?:bearer|basic)\s+)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)((?:api[_-]?key|token|secret|password)\s*[=:]\s*)[^\s\"'&;]+"), r"\1[REDACTED]"),
    (re.compile(r"\b(?:ghp_[A-Za-z0-9]{36}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|sk-[A-Za-z0-9_-]{16,})\b"), "[REDACTED]"),
    (re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|PRIVATE) KEY-----[\s\S]*?-----END (?:RSA|EC|OPENSSH|PRIVATE) KEY-----"), "[REDACTED_PRIVATE_KEY]"),
)


def redact_sensitive_text(text: str) -> str:
    """Redact credentials, API keys, and auth headers before persisting execution logs."""
    cleaned = text
    for pattern, replacement in _SENSITIVE_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


def record_execution_log(
    log_dir: Path,
    *,
    step_name: str,
    command: list[str] | str,
    started_at_utc: str,
    finished_at_utc: str,
    exit_code: int,
    stdout: str = "",
    stderr: str = "",
    metadata: Mapping[str, Any] | None = None,
    output_digests: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Write a redacted stdout/stderr log and structured JSON audit record with SHA-256 digests."""
    safe_step = re.sub(r"[^A-Za-z0-9._-]+", "_", step_name).strip("_") or "step"
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    redacted_out = redact_sensitive_text(stdout)
    redacted_err = redact_sensitive_text(stderr)
    combined_log = (
        f"# step: {safe_step}\n"
        f"# command: {command if isinstance(command, str) else ' '.join(command)}\n"
        f"# started_at_utc: {started_at_utc}\n"
        f"# finished_at_utc: {finished_at_utc}\n"
        f"# exit_code: {exit_code}\n"
        "--- STDOUT (filtered) ---\n"
        f"{redacted_out}\n"
        "--- STDERR (filtered) ---\n"
        f"{redacted_err}\n"
    )
    log_path = log_dir / f"{safe_step}.log"
    log_sha256 = atomic_write_text(log_path, combined_log, allow_overwrite=True)
    record = {
        "step_name": safe_step,
        "command": list(command) if isinstance(command, list) else command,
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc,
        "exit_code": exit_code,
        "log_file": log_path.name,
        "log_sha256": log_sha256,
        "stdout_bytes": len(redacted_out.encode("utf-8")),
        "stderr_bytes": len(redacted_err.encode("utf-8")),
        "output_digests": dict(sorted((output_digests or {}).items())),
        "metadata": dict(metadata or {}),
    }
    json_path = log_dir / f"{safe_step}.json"
    record_sha256 = atomic_write_text(
        json_path,
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        allow_overwrite=True,
    )
    return {**record, "record_file": json_path.name, "record_sha256": record_sha256}


def load_checkpoint(path: Path) -> PartitionCheckpoint | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return PartitionCheckpoint(**data)


def save_checkpoint(path: Path, checkpoint: PartitionCheckpoint) -> str:
    return atomic_write_text(
        path,
        json.dumps(checkpoint.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        allow_overwrite=True,
    )
