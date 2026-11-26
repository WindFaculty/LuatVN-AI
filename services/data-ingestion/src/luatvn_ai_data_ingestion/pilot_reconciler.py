"""Cross-source reconciliation, canonical grouping, G1-D02 sampling, and QA replay.

The reconciler keeps four entity layers strictly apart:

* ``document_families`` - the canonical act (normalized number, issuer, type, date).
* ``document_versions`` - a family revision scoped by ``version`` and ``relation_role``.
* ``source_records`` - every observed catalog row, with its own URL/partition/provenance.
* ``artifacts`` - unique binary blobs keyed by SHA-256, plus ``artifact_occurrences`` that
  retain every source URL, parent, attachment id, and relation role.

Portal metadata never proves legal validity: every emitted canonical row is forced to
``legal_status_verified=False`` and ``portal_effective_date_unverified=True``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .pilot_schema import (
    ALL_DOMAIN_LABELS,
    PILOT_DOMAINS,
    RunCutoff,
    atomic_write_text,
    canonical_partition_status,
    evaluate_date_window,
    normalize_document_number,
    normalize_document_type,
    normalize_issuer,
    normalize_text_nfc,
    parse_vn_date,
    sha256_bytes,
    write_csv_atomic,
    write_jsonl_atomic,
)
from .source_rights import ACTIONS, SourceRegistry

DEFAULT_RUN_ID = "G1-PILOT-SRC01-SRC03-20261126-01"
FIXTURE_SOURCE_PREFIX = "FIXTURE-"
REQUIRED_REAL_ACTIONS = ("automated_access", "store", "index")
if not set(REQUIRED_REAL_ACTIONS) <= ACTIONS:  # fail closed if the shared action set drifts
    raise RuntimeError("pilot_reconciler requires automated_access/store/index in ACTIONS")

G1_D02_TARGETS = {
    "pilot_catalog_families": 45,
    "extraction_artifacts": 36,
    "graph_families": 18,
    "review_candidate_cases": 27,
}
G1_D02_PER_DOMAIN = {
    "pilot_catalog_families": 5,
    "graph_families": 2,
    "review_candidate_cases": 3,
}
EXTRACTION_FORMAT_TARGETS = {
    "pdf_text": 6,
    "pdf_scan": 6,
    "html": 4,
    "doc_docx": 4,
    "spreadsheet": 4,
}
FORMAT_ORDER = ("pdf_text", "pdf_scan", "html", "doc_docx", "spreadsheet", "other")
REVIEW_CASE_KINDS = ("LOOKUP", "VALIDITY", "RISK_MISSING_EVIDENCE")
CHILD_RELATION_ROLES = frozenset({"appendix", "child", "attachment", "supplement"})
SRC01_SOURCE_IDS = frozenset({"SRC-01", "FIXTURE-SRC-01"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

SOURCE_CATALOG_FIELDS = (
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
    "document_family_id",
    "document_version_id",
    "issued_iso",
    "classification",
    "portal_effective_date_unverified",
    "artifact_ids",
)
ARTIFACT_MANIFEST_FIELDS = (
    "artifact_id",
    "sha256",
    "occurrence_count",
    "status",
    "quarantined_count",
    "source_ids",
    "partition_ids",
    "file_type",
    "file_types",
    "format_groups",
    "format_group",
    "detected_mimes",
    "declared_mimes",
    "size_bytes",
    "document_family_ids",
    "document_version_ids",
    "domain_primaries",
    "domain_primary",
    "data_origin",
    "data_origins",
    "rights_ref",
    "rights_refs",
    "eligible_for_extraction",
    "eligible_for_pilot_denominator",
    "legal_status_verified",
    "portal_effective_date_unverified",
    "cutoff_utc",
    "cutoff_vn",
    "occurrences",
)
CANONICAL_FIELDS = (
    "document_family_id",
    "document_version_id",
    "document_number",
    "document_number_normalized",
    "issuer",
    "issuer_normalized",
    "document_type",
    "document_type_normalized",
    "title",
    "issued_date",
    "year",
    "quarter",
    "domain_primary",
    "domain_candidates",
    "version",
    "relation_role",
    "related_to_document_number",
    "related_to_document_numbers",
    "source_ids",
    "source_record_ids",
    "source_urls",
    "partition_ids",
    "rights_ref",
    "rights_refs",
    "data_origin",
    "data_origins",
    "gazette_issues",
    "gazette_pages",
    "observed_effective_dates",
    "gazette_published_dates",
    "artifact_ids",
    "cross_source_overlap",
    "eligible_for_pilot_denominator",
    "is_pre_2020_reference",
    "is_post_cutoff",
    "legal_status_verified",
    "portal_effective_date_unverified",
    "cutoff_utc",
    "cutoff_vn",
)
CONFLICT_FIELDS = (
    "conflict_id",
    "conflict_type",
    "conflict_code",
    "document_family_id",
    "document_family_ids",
    "document_number",
    "document_year",
    "document_type",
    "domain_candidate",
    "data_origin",
    "file_type",
    "source_ids",
    "source_urls",
    "partition_ids",
    "record_ids",
    "details",
    "review_status",
    "legal_status_verified",
    "cutoff_utc",
    "cutoff_vn",
)
PILOT_SAMPLE_FIELDS = (
    "sample_id",
    "sample_kind",
    "document_family_id",
    "document_family_ids",
    "document_version_ids",
    "artifact_id",
    "case_id",
    "case_kind",
    "sha256",
    "file_type",
    "format_group",
    "domain_primary",
    "rights_ref",
    "data_origin",
    "in_pilot_catalog",
    "in_extraction_gold",
    "in_graph_gold",
    "in_review_candidates",
    "review_case_ids",
    "legal_status_verified",
    "portal_effective_date_unverified",
    "cutoff_utc",
    "cutoff_vn",
)
RIGHTS_MATRIX_FIELDS = (
    "source_id",
    "action",
    "status",
    "rights_ref",
    "approved_at",
    "expires_at",
    "policy_url",
    "evidence_ref",
    "registry_revision",
    "data_origin",
    "action_valid",
)
PARTITION_LEDGER_FIELDS = (
    "source_id",
    "partition_id",
    "status",
    "rights_status",
    "rights_ref",
    "owner_worker",
    "requests_attempted",
    "records_observed",
    "records_eligible",
    "artifacts_downloaded",
    "blobs_written",
    "quarantined",
    "errors",
    "catalog_enumeration_complete",
    "checkpoint_sha256",
    "manifest_sha256",
    "updated_at",
    "notes",
)
_METRIC_KEYS = (
    "observed",
    "eligible",
    "downloaded",
    "hash_verified",
    "unique_families",
    "unique_versions",
    "unique_blobs",
    "cross_source_overlap",
    "missing_or_shortfall",
    "suspected_duplicates",
    "quarantined",
    "errors",
    "pre_2020_references_excluded",
    "post_cutoff_excluded",
    "raw_bytes",
    "normalized_bytes_or_NOT_RUN",
)


def _s(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [_s(item) for item in value]
    text = _s(value)
    return [text] if text else []


def _distinct_sorted(values: Iterable[Any]) -> list[str]:
    return sorted({_s(value) for value in values if _s(value)})


def _is_real_source(source_id: str) -> bool:
    return bool(source_id) and not source_id.upper().startswith(FIXTURE_SOURCE_PREFIX)


def _origin_is_synthetic(origin: Any, source_id: str) -> bool:
    if source_id and not _is_real_source(source_id):
        return True
    label = _s(origin).upper()
    if label == "SYNTHETIC_FIXTURE" or label.startswith("SYNTHETIC"):
        return True
    if label == "REAL":
        return False
    return not _is_real_source(source_id)


def _record_is_synthetic(row: dict[str, Any]) -> bool:
    return _origin_is_synthetic(row.get("data_origin"), _s(row.get("source_id")))


def _origin_lane(row: dict[str, Any]) -> str:
    return "SYNTHETIC_FIXTURE" if _record_is_synthetic(row) else "REAL"


def _rights_ref_is_valid_real(rights_ref: Any) -> bool:
    ref = _s(rights_ref)
    if not ref:
        return False
    upper = ref.upper()
    forbidden = ("BLOCKED_RIGHTS", "PENDING_RIGHTS", "DENIED", "EXPIRED", "SYNTHETIC")
    return not any(token in upper for token in forbidden)


def _source_real_rights_valid(
    source_id: str, rights_index: dict[str, dict[str, set[str]]]
) -> bool:
    if not _is_real_source(source_id):
        return False
    if source_id not in rights_index:
        return True
    actions = rights_index[source_id]
    store_ok = bool(actions.get("store")) and set(actions.get("store", set())) == {"APPROVED"}
    access_ok = any(
        bool(actions.get(action)) and set(actions.get(action, set())) == {"APPROVED"}
        for action in ("automated_access", "manual_download")
    )
    return store_ok and access_ok


def _record_has_valid_real_provenance(
    row: dict[str, Any], rights_index: dict[str, dict[str, set[str]]]
) -> bool:
    source_id = _s(row.get("source_id"))
    if _origin_is_synthetic(row.get("data_origin"), source_id):
        return False
    if _s(row.get("data_origin")).upper() != "REAL":
        return False
    if not _is_real_source(source_id):
        return False
    if not _rights_ref_is_valid_real(row.get("rights_ref")):
        return False
    return _source_real_rights_valid(source_id, rights_index)


def _family_is_synthetic(family: dict[str, Any]) -> bool:
    source_ids = [s for s in family.get("source_ids", []) if s]
    if source_ids and all(not _is_real_source(s) for s in source_ids):
        return True
    origins = [origin for origin in family.get("data_origins", []) if origin]
    if not origins:
        origins = [origin for origin in [family.get("data_origin")] if origin]
    return all(_origin_is_synthetic(origin, "") for origin in origins) if origins else True


def _normalize_domain(value: Any) -> str:
    label = _s(value).upper()
    return label if label in ALL_DOMAIN_LABELS else "UNMAPPED"


def _domain_rank(label: str) -> int:
    if label in PILOT_DOMAINS:
        return PILOT_DOMAINS.index(label)
    if label == "UNMAPPED":
        return len(PILOT_DOMAINS)
    return len(PILOT_DOMAINS) + 1


def _family_key(record: dict[str, Any]) -> tuple[str, str, str, str, str]:
    issued = parse_vn_date(_s(record.get("issued_date")))
    disambiguation = _text_or_empty(
        record.get("disambiguation") or record.get("identity_disambiguation")
    )
    return (
        normalize_document_number(_s(record.get("document_number"))),
        normalize_issuer(_s(record.get("issuer"))),
        normalize_document_type(_s(record.get("document_type"))),
        issued.isoformat() if issued else "",
        disambiguation,
    )


def _text_or_empty(value: Any) -> str:
    return normalize_text_nfc(_s(value))


def _family_id_from_key(
    key: tuple[str, str, str, str, str],
    *,
    origin_lane: str = "REAL",
) -> str:
    payload = list(key) if origin_lane == "REAL" else [origin_lane, *key]
    basis = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return "fam_" + sha256_bytes(basis.encode("utf-8"))[:16]


def document_family_id(record: dict[str, Any]) -> str:
    return _family_id_from_key(_family_key(record), origin_lane=_origin_lane(record))


def document_version_id(record: dict[str, Any]) -> str:
    family_id = document_family_id(record)
    role = _text_or_empty(record.get("relation_role")).casefold()
    version = _text_or_empty(record.get("version"))
    basis = json.dumps([family_id, version, role], ensure_ascii=False, separators=(",", ":"))
    return "ver_" + sha256_bytes(basis.encode("utf-8"))[:16]


def _valid_sha(value: Any) -> str:
    sha = _s(value).lower()
    return sha if SHA256_RE.match(sha) else ""


def _artifact_blob_id(sha256: str, fallback: str, *, origin_lane: str = "REAL") -> str:
    if origin_lane != "REAL":
        basis = f"{origin_lane}|{sha256 or fallback}"
        return "blb_" + sha256_bytes(basis.encode("utf-8"))[:16]
    if sha256:
        return "blb_" + sha256[:16]
    return "blb_" + sha256_bytes(fallback.encode("utf-8"))[:16]


def _format_group(
    file_type: Any,
    detected_mime: Any,
    declared_mime: Any,
    record: dict[str, Any],
) -> str:
    kind = _s(file_type).casefold()
    mime = (_s(detected_mime) or _s(declared_mime)).casefold()
    combined = f"{kind} {mime}"
    if "spreadsheet" in mime or kind in {"xls", "xlsx", "csv", "sheet", "spreadsheet"}:
        return "spreadsheet"
    if "wordprocessing" in mime or kind in {"doc", "docx", "word", "doc_docx"}:
        return "doc_docx"
    if kind in {"html", "htm"} or "text/html" in mime:
        return "html"
    if "pdf" in kind or mime == "application/pdf":
        file_url_lower = _s(record.get("file_url")).casefold()
        scan_hint = (
            "scan" in kind
            or "scan" in combined
            or bool(re.search(r"(^|[/_-])scan([._-]|$)", file_url_lower))
            or bool(_s(record.get("scan_condition")))
            or record.get("is_scanned") is True
        )
        return "pdf_scan" if scan_hint else "pdf_text"
    return "other"


def _year_text(record: dict[str, Any], issued_iso: str = "") -> str:
    if issued_iso:
        return issued_iso[:4]
    raw_year = record.get("year")
    if isinstance(raw_year, bool):
        return "UNKNOWN"
    if isinstance(raw_year, int):
        return str(raw_year)
    text = _s(raw_year)
    return text if text.isdigit() else "UNKNOWN"


def _primary_domain(rows: Iterable[dict[str, Any]]) -> str:
    counts = Counter(
        _normalize_domain(
            row.get("domain_candidate_normalized") or row.get("domain_candidate")
        )
        for row in rows
    )
    if not counts:
        return "UNMAPPED"
    return min(counts, key=lambda label: (-counts[label], _domain_rank(label), label))


def _origin_summary(rows: Iterable[dict[str, Any]]) -> tuple[str, list[str]]:
    origins = _distinct_sorted(row.get("data_origin") for row in rows)
    if not origins:
        return "UNKNOWN", []
    return (origins[0] if len(origins) == 1 else "MIXED"), origins


def _prepare_catalog(
    catalog_records: list[dict[str, Any]],
    cutoff: RunCutoff,
    rights_index: dict[str, dict[str, set[str]]] | None = None,
) -> list[dict[str, Any]]:
    resolved_rights = rights_index or {}
    prepared: list[dict[str, Any]] = []
    for record in catalog_records:
        row = dict(record)
        source_id = _s(row.get("source_id"))
        raw_origin = _s(row.get("data_origin")) or "UNKNOWN"
        lane = "SYNTHETIC_FIXTURE" if _origin_is_synthetic(raw_origin, source_id) else "REAL"
        effective_origin = "SYNTHETIC_FIXTURE" if lane == "SYNTHETIC_FIXTURE" else "REAL"
        window = evaluate_date_window(
            _s(row.get("issued_date")),
            cutoff,
            gazette_published_date_str=_s(row.get("gazette_published_date")),
            observed_effective_date_str=_s(row.get("observed_effective_date")),
        )
        issued = parse_vn_date(_s(row.get("issued_date")))
        explicit_pre_2020 = bool(row.get("is_pre_2020_reference"))
        flags = set(filter(None, _s(window["date_reconciliation_flag"]).split(";")))
        if explicit_pre_2020 or (issued is not None and issued < cutoff.window_start):
            classification = "PRE_2020_REFERENCE"
        elif issued is None or "UNPARSEABLE_ISSUED_DATE" in flags:
            classification = "MISSING_OR_INVALID_ISSUED_DATE"
        elif issued > cutoff.cutoff_date_vn:
            classification = "POST_CUTOFF"
        else:
            classification = "ELIGIBLE"
        eligible = classification == "ELIGIBLE"
        row["source_id"] = source_id
        row["data_origin"] = effective_origin
        valid_real = _record_has_valid_real_provenance(row, resolved_rights)
        row.update(
            {
                "source_id": source_id,
                "source_record_id": _s(row.get("source_record_id")),
                "partition_id": _s(row.get("partition_id")),
                "data_origin": effective_origin,
                "origin_lane": lane,
                "valid_real_provenance": valid_real,
                "page_url": _s(row.get("page_url")),
                "issuer": _text_or_empty(row.get("issuer")),
                "document_type": _text_or_empty(row.get("document_type")),
                "document_number": _text_or_empty(row.get("document_number")),
                "title": _text_or_empty(row.get("title")),
                "issued_date": _s(row.get("issued_date")),
                "issued_iso": _s(window["issued_iso"]),
                "gazette_iso": _s(window["gazette_iso"]),
                "effective_iso": _s(window["effective_iso"]),
                "year": _year_text(row, _s(window["issued_iso"])),
                "quarter": _s(window["quarter"]) if issued else (_s(row.get("quarter")) or "UNKNOWN"),
                "domain_candidate_normalized": _normalize_domain(row.get("domain_candidate")),
                "document_family_id": document_family_id(row),
                "document_version_id": document_version_id(row),
                "classification": classification,
                "eligible_for_pilot_denominator": eligible,
                "is_pre_2020_reference": classification == "PRE_2020_REFERENCE",
                "is_post_cutoff": classification == "POST_CUTOFF",
                "date_reconciliation_flag": _s(window["date_reconciliation_flag"]),
                "legal_status_verified": False,
                "portal_effective_date_unverified": True,
                "cutoff_utc": _s(row.get("cutoff_utc")) or cutoff.cutoff_utc,
                "cutoff_vn": _s(row.get("cutoff_vn")) or cutoff.cutoff_vn,
                "artifact_ids": [],
            }
        )
        prepared.append(row)
    prepared.sort(key=_source_record_sort_key)
    return prepared


def _source_record_sort_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        _s(row.get("origin_lane")) or _origin_lane(row),
        _s(row.get("source_id")),
        _s(row.get("partition_id")),
        _s(row.get("source_record_id")),
        _s(row.get("relation_role")),
        _s(row.get("version")),
        _s(row.get("page_url")),
    )


def _prepare_occurrences(
    artifact_records: list[dict[str, Any]],
    prepared_catalog: list[dict[str, Any]],
    cutoff: RunCutoff,
    rights_index: dict[str, dict[str, set[str]]] | None = None,
) -> list[dict[str, Any]]:
    resolved_rights = rights_index or {}
    by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    by_number: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in prepared_catalog:
        lane = _s(record.get("origin_lane")) or _origin_lane(record)
        by_key[(lane, _s(record["source_id"]), _s(record["source_record_id"]))].append(record)
        by_number[
            (lane, _s(record["source_id"]), normalize_document_number(record["document_number"]))
        ].append(record)

    occurrences: list[dict[str, Any]] = []
    for artifact in artifact_records:
        row = dict(artifact)
        source_id = _s(row.get("source_id"))
        raw_origin = _s(row.get("data_origin")) or "UNKNOWN"
        lane = "SYNTHETIC_FIXTURE" if _origin_is_synthetic(raw_origin, source_id) else "REAL"
        effective_origin = "SYNTHETIC_FIXTURE" if lane == "SYNTHETIC_FIXTURE" else "REAL"
        row["source_id"] = source_id
        row["data_origin"] = effective_origin
        parent_id = _s(row.get("parent_id"))
        relation_role = _s(row.get("relation_role"))
        is_child = relation_role.casefold() in CHILD_RELATION_ROLES
        parent: dict[str, Any] | None = None
        if parent_id:
            candidates = by_key.get((lane, source_id, parent_id), [])
            if candidates:
                parent = sorted(candidates, key=_source_record_sort_key)[0]
        if parent is None and not is_child:
            rec_id = _s(row.get("source_record_id"))
            candidates = by_key.get((lane, source_id, rec_id), []) if rec_id else []
            if not candidates:
                number = normalize_document_number(_s(row.get("document_number")))
                candidates = by_number.get((lane, source_id, number), []) if number else []
            if candidates:
                parent = sorted(candidates, key=_source_record_sort_key)[0]
        sha = _valid_sha(row.get("sha256"))
        fallback = "|".join(
            (
                lane,
                source_id,
                _s(row.get("source_record_id")),
                parent_id,
                _s(row.get("attachment_id")),
                _s(row.get("file_url")),
                sha,
            )
        )
        parent_eligible = bool(parent and parent["eligible_for_pilot_denominator"])
        status = _s(row.get("status"))
        quarantine_reason = _s(row.get("quarantine_reason"))
        quarantined = status.upper() == "QUARANTINED" or bool(quarantine_reason)
        size_bytes = row.get("size_bytes")
        if isinstance(size_bytes, str) and size_bytes.isdigit():
            size_bytes = int(size_bytes)
        valid_real = _record_has_valid_real_provenance(row, resolved_rights) and (
            parent is None or bool(parent.get("valid_real_provenance"))
        )
        row.update(
            {
                "source_id": source_id,
                "source_record_id": _s(row.get("source_record_id")),
                "partition_id": _s(row.get("partition_id")),
                "data_origin": effective_origin,
                "origin_lane": lane,
                "valid_real_provenance": valid_real,
                "parent_id": parent_id,
                "attachment_id": _s(row.get("attachment_id")),
                "page_url": _s(row.get("page_url")),
                "file_url": _s(row.get("file_url")),
                "sha256": sha,
                "file_type": _s(row.get("file_type")),
                "declared_mime": _s(row.get("declared_mime")),
                "detected_mime": _s(row.get("detected_mime")),
                "size_bytes": size_bytes,
                "status": status,
                "quarantine_reason": quarantine_reason,
                "quarantined": quarantined,
                "document_number": _text_or_empty(row.get("document_number")),
                "version": _text_or_empty(row.get("version")),
                "relation_role": relation_role,
                "artifact_id": _artifact_blob_id(sha, fallback, origin_lane=lane),
                "format_group": _format_group(
                    row.get("file_type"),
                    row.get("detected_mime"),
                    row.get("declared_mime"),
                    row,
                ),
                "is_child": is_child,
                "parent_matched": parent is not None,
                "parent_source_id": _s(parent["source_id"]) if parent else "",
                "parent_source_record_id": _s(parent["source_record_id"]) if parent else "",
                "document_family_id": _s(parent["document_family_id"]) if parent else "",
                "document_version_id": _s(parent["document_version_id"]) if parent else "",
                "classification": _s(parent["classification"]) if parent else "UNRESOLVED_PARENT",
                "eligible_for_pilot_denominator": parent_eligible,
                "domain_candidate_normalized": (
                    _s(parent["domain_candidate_normalized"]) if parent else "UNMAPPED"
                ),
                "document_type_normalized": (
                    normalize_document_type(_s(parent.get("document_type"))) if parent else ""
                ),
                "year": _year_text(row, _s(parent["issued_iso"]) if parent and parent["issued_iso"] else ""),
                "quarter": _s(parent.get("quarter")) if parent else (_s(row.get("quarter")) or "UNKNOWN"),
                "eligible_for_extraction": bool(
                    parent_eligible and not quarantined and bool(sha)
                ),
                "legal_status_verified": False,
                "portal_effective_date_unverified": True,
                "cutoff_utc": _s(row.get("cutoff_utc")) or cutoff.cutoff_utc,
                "cutoff_vn": _s(row.get("cutoff_vn")) or cutoff.cutoff_vn,
            }
        )
        occurrences.append(row)
    occurrences.sort(key=_occurrence_sort_key)
    return occurrences


def _occurrence_sort_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        _s(row.get("source_id")),
        _s(row.get("partition_id")),
        _s(row.get("parent_id")),
        _s(row.get("source_record_id")),
        _s(row.get("relation_role")),
        _s(row.get("attachment_id")),
        _s(row.get("file_url")),
        _s(row.get("sha256")),
    )


def _build_artifacts(occurrences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for occurrence in occurrences:
        groups[occurrence["artifact_id"]].append(occurrence)
    artifacts: list[dict[str, Any]] = []
    for artifact_id in sorted(groups):
        rows = sorted(groups[artifact_id], key=_occurrence_sort_key)
        sha = next((row["sha256"] for row in rows if row["sha256"]), "")
        sizes = [
            row.get("size_bytes")
            for row in rows
            if isinstance(row.get("size_bytes"), int) and not isinstance(row.get("size_bytes"), bool)
        ]
        formats = Counter(row["format_group"] for row in rows)
        format_group = min(
            formats,
            key=lambda item: (-formats[item], FORMAT_ORDER.index(item) if item in FORMAT_ORDER else 99, item),
        )
        quarantined_count = sum(1 for row in rows if row["quarantined"])
        if quarantined_count == len(rows):
            status = "QUARANTINED"
        elif quarantined_count:
            status = "MIXED"
        else:
            status = "VALID"
        family_ids = _distinct_sorted(row["document_family_id"] for row in rows)
        version_ids = _distinct_sorted(row["document_version_id"] for row in rows)
        domains = _distinct_sorted(row["domain_candidate_normalized"] for row in rows)
        domain_primary = _primary_domain(rows)
        origins = _distinct_sorted(row["data_origin"] for row in rows)
        rights_refs = _distinct_sorted(row.get("rights_ref") for row in rows)
        file_types = _distinct_sorted(row.get("file_type") for row in rows)
        artifact = {
            "artifact_id": artifact_id,
            "sha256": sha,
            "occurrence_count": len(rows),
            "status": status,
            "quarantined_count": quarantined_count,
            "source_ids": _distinct_sorted(row["source_id"] for row in rows),
            "partition_ids": _distinct_sorted(row["partition_id"] for row in rows),
            "file_type": file_types[0] if file_types else "",
            "file_types": file_types,
            "format_groups": sorted(formats),
            "format_group": format_group,
            "detected_mimes": _distinct_sorted(row.get("detected_mime") for row in rows),
            "declared_mimes": _distinct_sorted(row.get("declared_mime") for row in rows),
            "size_bytes": max(sizes) if sizes else None,
            "document_family_ids": family_ids,
            "document_version_ids": version_ids,
            "domain_primaries": domains,
            "domain_primary": domain_primary,
            "data_origin": origins[0] if len(origins) == 1 else ("MIXED" if origins else "UNKNOWN"),
            "data_origins": origins,
            "valid_real_provenance": bool(rows) and all(row.get("valid_real_provenance", False) for row in rows),
            "rights_ref": rights_refs[0] if len(rights_refs) == 1 else ("MULTIPLE" if rights_refs else ""),
            "rights_refs": rights_refs,
            "eligible_for_extraction": any(row["eligible_for_extraction"] for row in rows),
            "eligible_for_pilot_denominator": any(
                row["eligible_for_pilot_denominator"] for row in rows
            ),
            "legal_status_verified": False,
            "portal_effective_date_unverified": True,
            "cutoff_utc": rows[0]["cutoff_utc"],
            "cutoff_vn": rows[0]["cutoff_vn"],
            "occurrences": rows,
        }
        artifacts.append(artifact)
    artifacts.sort(key=lambda row: (row["sha256"] or "", row["artifact_id"]))
    return artifacts


def _build_families_and_versions(
    prepared_catalog: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    cutoff: RunCutoff,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in prepared_catalog:
        if row["eligible_for_pilot_denominator"]:
            grouped[row["document_family_id"]].append(row)
    family_rows: list[dict[str, Any]] = []
    version_rows: list[dict[str, Any]] = []
    for family_id in sorted(grouped):
        rows = sorted(grouped[family_id], key=_source_record_sort_key)
        primary = rows[0]
        domain = _primary_domain(rows)
        source_ids = _distinct_sorted(row["source_id"] for row in rows)
        version_ids = _distinct_sorted(row["document_version_id"] for row in rows)
        origin, origins = _origin_summary(rows)
        rights_refs = _distinct_sorted(row.get("rights_ref") for row in rows)
        family = {
            "document_family_id": family_id,
            "document_number": _s(primary.get("document_number")),
            "document_number_normalized": normalize_document_number(primary.get("document_number")),
            "issuer": _s(primary.get("issuer")),
            "issuer_normalized": normalize_issuer(primary.get("issuer")),
            "document_type": _s(primary.get("document_type")),
            "document_type_normalized": normalize_document_type(primary.get("document_type")),
            "title": _s(primary.get("title")),
            "issued_date": _s(primary.get("issued_iso")),
            "year": _s(primary.get("year")),
            "quarter": _s(primary.get("quarter")),
            "domain_primary": domain,
            "domain_candidates": _distinct_sorted(
                row["domain_candidate_normalized"] for row in rows
            ),
            "version_ids": version_ids,
            "source_ids": source_ids,
            "source_record_ids": _distinct_sorted(row["source_record_id"] for row in rows),
            "source_urls": _distinct_sorted(row["page_url"] for row in rows),
            "partition_ids": _distinct_sorted(row["partition_id"] for row in rows),
            "rights_ref": rights_refs[0] if len(rights_refs) == 1 else ("MULTIPLE" if rights_refs else ""),
            "rights_refs": rights_refs,
            "data_origin": origin,
            "data_origins": origins,
            "valid_real_provenance": bool(rows) and all(row.get("valid_real_provenance", False) for row in rows),
            "gazette_issues": _distinct_sorted(row.get("gazette_issue") for row in rows),
            "gazette_pages": _distinct_sorted(row.get("gazette_page") for row in rows),
            "observed_effective_dates": _distinct_sorted(
                row.get("observed_effective_date") for row in rows
            ),
            "gazette_published_dates": _distinct_sorted(
                row.get("gazette_published_date") for row in rows
            ),
            "artifact_ids": [],
            "cross_source_overlap": len(source_ids) > 1,
            "eligible_for_pilot_denominator": True,
            "is_pre_2020_reference": False,
            "is_post_cutoff": False,
            "legal_status_verified": False,
            "portal_effective_date_unverified": True,
            "cutoff_utc": cutoff.cutoff_utc,
            "cutoff_vn": cutoff.cutoff_vn,
        }
        family_rows.append(family)

        version_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            version_groups[row["document_version_id"]].append(row)
        for version_id in sorted(version_groups):
            version_source_rows = sorted(version_groups[version_id], key=_source_record_sort_key)
            version_primary = version_source_rows[0]
            version_source_ids = _distinct_sorted(
                row["source_id"] for row in version_source_rows
            )
            version_origin, version_origins = _origin_summary(version_source_rows)
            version_rights = _distinct_sorted(
                row.get("rights_ref") for row in version_source_rows
            )
            version_rows.append(
                {
                    **family,
                    "document_version_id": version_id,
                    "version": _s(version_primary.get("version")),
                    "relation_role": _s(version_primary.get("relation_role")),
                    "related_to_document_number": _s(
                        version_primary.get("related_to_document_number")
                    ),
                    "related_to_document_numbers": _distinct_sorted(
                        row.get("related_to_document_number") for row in version_source_rows
                    ),
                    "source_ids": version_source_ids,
                    "source_record_ids": _distinct_sorted(
                        row["source_record_id"] for row in version_source_rows
                    ),
                    "source_urls": _distinct_sorted(
                        row["page_url"] for row in version_source_rows
                    ),
                    "partition_ids": _distinct_sorted(
                        row["partition_id"] for row in version_source_rows
                    ),
                    "rights_ref": (
                        version_rights[0]
                        if len(version_rights) == 1
                        else ("MULTIPLE" if version_rights else "")
                    ),
                    "rights_refs": version_rights,
                    "data_origin": version_origin,
                    "data_origins": version_origins,
                    "gazette_issues": _distinct_sorted(
                        row.get("gazette_issue") for row in version_source_rows
                    ),
                    "gazette_pages": _distinct_sorted(
                        row.get("gazette_page") for row in version_source_rows
                    ),
                    "observed_effective_dates": _distinct_sorted(
                        row.get("observed_effective_date") for row in version_source_rows
                    ),
                    "gazette_published_dates": _distinct_sorted(
                        row.get("gazette_published_date") for row in version_source_rows
                    ),
                    "cross_source_overlap": len(version_source_ids) > 1,
                    "artifact_ids": [],
                }
            )
    family_rows.sort(key=lambda row: (_domain_rank(row["domain_primary"]), row["document_family_id"]))
    version_rows.sort(
        key=lambda row: (
            _domain_rank(row["domain_primary"]),
            row["document_family_id"],
            row["relation_role"],
            row["version"],
            row["document_version_id"],
        )
    )
    family_by_id = {row["document_family_id"]: row for row in family_rows}
    version_by_id = {row["document_version_id"]: row for row in version_rows}
    for artifact in artifacts:
        for family_id in artifact["document_family_ids"]:
            if family_id in family_by_id:
                family_by_id[family_id]["artifact_ids"].append(artifact["artifact_id"])
        for version_id in artifact["document_version_ids"]:
            if version_id in version_by_id:
                version_by_id[version_id]["artifact_ids"].append(artifact["artifact_id"])
    for row in family_rows:
        row["artifact_ids"] = sorted(set(row["artifact_ids"]))
    for row in version_rows:
        row["artifact_ids"] = sorted(set(row["artifact_ids"]))
    return family_rows, version_rows


def _conflict_row(
    *,
    conflict_type: str,
    conflict_code: str,
    rows: Iterable[dict[str, Any]],
    cutoff: RunCutoff,
    details: dict[str, Any],
    artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_rows = list(rows)
    if artifact is not None:
        source_ids = {artifact["source_id"]}
        source_urls = {
            _s(artifact.get("page_url")),
            _s(artifact.get("file_url")),
        }
        partition_ids = {artifact["partition_id"]}
        family_ids = {artifact["document_family_id"]} if artifact["document_family_id"] else set()
        primary = source_rows[0] if source_rows else {}
        document_number = (
            _s(primary.get("document_number"))
            or _s(artifact.get("document_number"))
        )
        document_year = _s(artifact.get("year"))
        document_type = normalize_document_type(
            _s(artifact.get("document_type_normalized")) or _s(primary.get("document_type"))
        )
        domain = _s(artifact.get("domain_candidate_normalized")) or "UNMAPPED"
        origin = _s(artifact.get("data_origin")) or "UNKNOWN"
        file_type = _s(artifact.get("file_type"))
        record_ids = {
            f"{artifact['source_id']}:{artifact['source_record_id']}:{artifact['attachment_id']}"
        }
    else:
        source_ids = {_s(row.get("source_id")) for row in source_rows}
        source_urls = {_s(row.get("page_url")) for row in source_rows}
        partition_ids = {_s(row.get("partition_id")) for row in source_rows}
        family_ids = {_s(row.get("document_family_id")) for row in source_rows}
        primary = source_rows[0] if source_rows else {}
        document_number = _s(primary.get("document_number"))
        document_year = _s(primary.get("year"))
        document_type = normalize_document_type(_s(primary.get("document_type")))
        domain = _s(primary.get("domain_candidate_normalized")) or "UNMAPPED"
        origin = _s(primary.get("data_origin")) or "UNKNOWN"
        file_type = ""
        record_ids = {f"{row['source_id']}:{row['source_record_id']}" for row in source_rows}
    source_ids.discard("")
    source_urls.discard("")
    partition_ids.discard("")
    family_ids.discard("")
    sorted_sources = sorted(source_ids)
    sorted_urls = sorted(source_urls)
    sorted_partitions = sorted(partition_ids)
    sorted_families = sorted(family_ids)
    sorted_records = sorted(record_ids)
    basis = json.dumps(
        [
            conflict_type,
            conflict_code,
            sorted_families,
            document_number,
            sorted_sources,
            sorted_records,
            details,
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "conflict_id": "cf_" + sha256_bytes(basis.encode("utf-8"))[:16],
        "conflict_type": conflict_type,
        "conflict_code": conflict_code,
        "document_family_id": sorted_families[0] if sorted_families else "",
        "document_family_ids": sorted_families,
        "document_number": document_number,
        "document_year": document_year,
        "document_type": document_type,
        "domain_candidate": domain,
        "data_origin": origin,
        "file_type": file_type,
        "source_ids": sorted_sources,
        "source_urls": sorted_urls,
        "partition_ids": sorted_partitions,
        "record_ids": sorted_records,
        "details": details,
        "review_status": "PENDING_REVIEW",
        "legal_status_verified": False,
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
    }


def _detect_conflicts_prepared(
    prepared_catalog: list[dict[str, Any]],
    occurrences: list[dict[str, Any]],
    cutoff: RunCutoff,
) -> list[dict[str, Any]]:
    conflicts: dict[str, dict[str, Any]] = {}

    def add(conflict: dict[str, Any]) -> None:
        conflicts.setdefault(conflict["conflict_id"], conflict)

    # Cross-source metadata disagreement keyed by origin lane + normalized number + issued date.
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in prepared_catalog:
        if row["issued_iso"]:
            lane = _s(row.get("origin_lane")) or _origin_lane(row)
            grouped[
                (lane, normalize_document_number(row["document_number"]), row["issued_iso"])
            ].append(row)
    for key in sorted(grouped):
        rows = sorted(grouped[key], key=_source_record_sort_key)
        sources = _distinct_sorted(row["source_id"] for row in rows)
        if len(sources) < 2:
            continue
        for field, normalizer, code in (
            ("issuer", normalize_issuer, "CROSS_SOURCE_ISSUER_MISMATCH"),
            ("document_type", normalize_document_type, "CROSS_SOURCE_DOCUMENT_TYPE_MISMATCH"),
            (
                "title",
                lambda value: normalize_text_nfc(_s(value)).casefold(),
                "CROSS_SOURCE_TITLE_MISMATCH",
            ),
        ):
            values_by_source = {
                source: sorted(
                    {
                        normalizer(row.get(field))
                        for row in rows
                        if row["source_id"] == source and normalizer(row.get(field))
                    }
                )
                for source in sources
            }
            distinct_values = sorted(
                {value for values in values_by_source.values() for value in values}
            )
            if len(distinct_values) > 1:
                add(
                    _conflict_row(
                        conflict_type="METADATA_MISMATCH",
                        conflict_code=code,
                        rows=rows,
                        cutoff=cutoff,
                        details={
                            "field": field,
                            "values_by_source": values_by_source,
                            "distinct_values": distinct_values,
                        },
                    )
                )
        effective_by_source = {
            source: sorted(
                {
                    parse_vn_date(_s(row.get("observed_effective_date"))).isoformat()
                    if parse_vn_date(_s(row.get("observed_effective_date")))
                    else _s(row.get("observed_effective_date"))
                    for row in rows
                    if row["source_id"] == source and _s(row.get("observed_effective_date"))
                }
            )
            for source in sources
        }
        distinct_effective = sorted(
            {
                value
                for values in effective_by_source.values()
                for value in values
            }
        )
        if len(distinct_effective) > 1:
            add(
                _conflict_row(
                    conflict_type="METADATA_MISMATCH",
                    conflict_code="CROSS_SOURCE_EFFECTIVE_DATE_MISMATCH",
                    rows=rows,
                    cutoff=cutoff,
                    details={
                        "field": "observed_effective_date",
                        "values_by_source": effective_by_source,
                        "distinct_values": distinct_effective,
                    },
                )
            )

    # Same number + issued date but different issuer/type is a suspected duplicate.
    for key in sorted(grouped):
        rows = sorted(grouped[key], key=_source_record_sort_key)
        issuers = _distinct_sorted(normalize_issuer(row["issuer"]) for row in rows)
        types = _distinct_sorted(normalize_document_type(row["document_type"]) for row in rows)
        if len(issuers) > 1 or len(types) > 1:
            add(
                _conflict_row(
                    conflict_type="SUSPECTED_DUPLICATE",
                    conflict_code="SAME_NUMBER_DATE_DIFFERENT_IDENTITY",
                    rows=rows,
                    cutoff=cutoff,
                    details={
                        "normalized_issuers": issuers,
                        "normalized_document_types": types,
                        "source_ids": _distinct_sorted(row["source_id"] for row in rows),
                    },
                )
            )

    # Per-record date anomalies.
    for row in prepared_catalog:
        flags = set(filter(None, _s(row["date_reconciliation_flag"]).split(";")))
        details_base = {
            "issued_date": _s(row.get("issued_date")),
            "issued_iso": row["issued_iso"],
            "gazette_published_date": _s(row.get("gazette_published_date")),
            "gazette_iso": row["gazette_iso"],
            "observed_effective_date": _s(row.get("observed_effective_date")),
            "effective_iso": row["effective_iso"],
            "date_reconciliation_flag": row["date_reconciliation_flag"],
        }
        codes: list[tuple[str, str]] = []
        if "MISSING_ISSUED_DATE" in flags or "UNPARSEABLE_ISSUED_DATE" in flags:
            codes.append(("MISSING_OR_INVALID_ISSUED_DATE", "issued_date"))
        if "GAZETTE_BEFORE_ISSUED_DATE" in flags:
            codes.append(("GAZETTE_BEFORE_ISSUED_DATE", "gazette_published_date"))
        if "EFFECTIVE_BEFORE_ISSUED_DATE" in flags:
            codes.append(("EFFECTIVE_BEFORE_ISSUED_DATE", "observed_effective_date"))
        if "UNPARSEABLE_GAZETTE_DATE" in flags or "UNPARSEABLE_EFFECTIVE_DATE" in flags:
            codes.append(("UNPARSEABLE_DATE", "gazette_or_effective_date"))
        for code, field in codes:
            add(
                _conflict_row(
                    conflict_type="DATE_ANOMALY",
                    conflict_code=code,
                    rows=[row],
                    cutoff=cutoff,
                    details={**details_base, "field": field},
                )
            )

    # SRC-01 gazette completeness.
    for row in prepared_catalog:
        if _s(row["source_id"]).upper() not in SRC01_SOURCE_IDS:
            continue
        reasons: list[str] = []
        if not _s(row.get("gazette_page")):
            reasons.append("MISSING_GAZETTE_PAGE")
        if row.get("continuation_gap") is True or row.get("declared_continuation_gap") is True:
            reasons.append("DECLARED_CONTINUATION_GAP")
        if _s(row.get("gazette_issue")).endswith("+"):
            reasons.append("CONTINUATION_GAP")
        for entry in _as_list(row.get("continuation_issues")):
            token = entry.upper()
            if not token or token in {"GAP", "MISSING"} or token.startswith("MISSING"):
                reasons.append("CONTINUATION_GAP")
                break
        if reasons:
            add(
                _conflict_row(
                    conflict_type="MISSING_GAZETTE_PAGE_OR_CONTINUATION",
                    conflict_code="+".join(sorted(set(reasons))),
                    rows=[row],
                    cutoff=cutoff,
                    details={
                        "reasons": sorted(set(reasons)),
                        "gazette_issue": _s(row.get("gazette_issue")),
                        "gazette_page": _s(row.get("gazette_page")),
                        "continuation_issues": _as_list(row.get("continuation_issues")),
                    },
                )
            )

    # Quarantined and orphaned attachments.
    for occurrence in occurrences:
        if occurrence["quarantined"]:
            add(
                _conflict_row(
                    conflict_type="QUARANTINED_ARTIFACT",
                    conflict_code=_s(occurrence.get("quarantine_reason"))
                    or "QUARANTINED_ARTIFACT",
                    rows=[],
                    cutoff=cutoff,
                    artifact=occurrence,
                    details={
                        "source_record_id": occurrence["source_record_id"],
                        "attachment_id": occurrence["attachment_id"],
                        "relation_role": occurrence["relation_role"],
                        "file_url": occurrence["file_url"],
                        "sha256": occurrence["sha256"],
                        "status": occurrence["status"],
                        "quarantine_reason": occurrence["quarantine_reason"],
                    },
                )
            )
        if occurrence["is_child"] and not occurrence["parent_matched"]:
            add(
                _conflict_row(
                    conflict_type="MISSING_PARENT_ATTACHMENT",
                    conflict_code="APPENDIX_PARENT_NOT_FOUND",
                    rows=[],
                    cutoff=cutoff,
                    artifact=occurrence,
                    details={
                        "attachment_id": occurrence["attachment_id"],
                        "parent_id": occurrence["parent_id"],
                        "file_url": occurrence["file_url"],
                        "relation_role": occurrence["relation_role"],
                    },
                )
            )
    return sorted(
        conflicts.values(),
        key=lambda row: (
            row["conflict_type"],
            row["document_number"],
            row["conflict_id"],
        ),
    )


def detect_conflicts(
    catalog_records: list[dict[str, Any]],
    artifact_records: list[dict[str, Any]],
    cutoff: RunCutoff,
) -> list[dict[str, Any]]:
    """Return the structured cross-source review queue."""
    prepared = _prepare_catalog(catalog_records, cutoff)
    occurrences = _prepare_occurrences(artifact_records, prepared, cutoff)
    return _detect_conflicts_prepared(prepared, occurrences, cutoff)


def _stratum_entry(target: int, selected: int) -> dict[str, Any]:
    shortfall = max(target - selected, 0)
    return {
        "target": target,
        "selected": selected,
        "shortfall": shortfall,
        "status": "MET" if shortfall == 0 else "SHORTFALL",
    }


def _item_origin_for_selection(row: dict[str, Any]) -> str:
    origin = _s(row.get("data_origin")).upper()
    origins = [_s(item).upper() for item in (row.get("data_origins") or []) if _s(item)]
    if origin == "MIXED" or len(set(origins)) > 1:
        return "MIXED"
    source_ids = [_s(item) for item in (row.get("source_ids") or []) if _s(item)]
    if not source_ids and _s(row.get("source_id")):
        source_ids = [_s(row.get("source_id"))]
    if source_ids and any(not _is_real_source(s) for s in source_ids):
        if any(_is_real_source(s) for s in source_ids) or origin == "REAL":
            return "MIXED"
        return "SYNTHETIC_FIXTURE"
    if origin == "REAL":
        return "REAL"
    if origin == "SYNTHETIC_FIXTURE" or origin.startswith("SYNTHETIC"):
        return "SYNTHETIC_FIXTURE"
    return "UNKNOWN"


def _item_passes_origin_selection(
    row: dict[str, Any],
    *,
    selected_origin: str,
    require_valid_real_provenance: bool,
) -> bool:
    item_origin = _item_origin_for_selection(row)
    if item_origin != selected_origin:
        return False
    if selected_origin == "REAL" and require_valid_real_provenance:
        if "valid_real_provenance" in row:
            return bool(row["valid_real_provenance"])
        return _rights_ref_is_valid_real(row.get("rights_ref"))
    return True


def select_g1_d02_pilot_samples(
    families: list[dict[str, Any]] | dict[str, Any],
    artifacts: list[dict[str, Any]] | None = None,
    *,
    origin_filter: str | None = None,
    require_valid_real_provenance: bool = False,
) -> dict[str, Any]:
    """Select the approved G1-D02 layers strictly within one data_origin lane.

    ``REAL`` and ``SYNTHETIC_FIXTURE`` are never mixed: when ``origin_filter`` is omitted
    and any ``REAL`` row is present, selection uses ``REAL`` rows only and excludes all
    ``SYNTHETIC_FIXTURE`` and ``MIXED`` rows. Targets (45/36/18/27) are never lowered.
    """
    if artifacts is None and isinstance(families, dict):
        reconciliation = families
        artifacts = list(reconciliation.get("artifacts", []))
        families = list(reconciliation.get("document_families", []))
    raw_artifacts = list(artifacts or [])
    raw_families = list(families)

    if origin_filter is not None:
        selected_origin = origin_filter.upper()
    else:
        has_real = any(
            _item_origin_for_selection(row) == "REAL" for row in (*raw_families, *raw_artifacts)
        )
        selected_origin = "REAL" if has_real else "SYNTHETIC_FIXTURE"

    artifacts = [
        {**row, "domain_primary": _normalize_domain(row.get("domain_primary"))}
        for row in raw_artifacts
        if _item_passes_origin_selection(
            row,
            selected_origin=selected_origin,
            require_valid_real_provenance=require_valid_real_provenance,
        )
    ]
    families = [
        {**row, "domain_primary": _normalize_domain(row.get("domain_primary"))}
        for row in raw_families
        if row.get("eligible_for_pilot_denominator", True)
        and _item_passes_origin_selection(
            row,
            selected_origin=selected_origin,
            require_valid_real_provenance=require_valid_real_provenance,
        )
    ]
    families = [row for row in families if row["domain_primary"] in PILOT_DOMAINS]
    families.sort(key=lambda row: (_domain_rank(row["domain_primary"]), row["document_family_id"]))
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for family in families:
        by_domain[family["domain_primary"]].append(family)

    catalog_selected: list[dict[str, Any]] = []
    for domain in PILOT_DOMAINS:
        catalog_selected.extend(
            sorted(by_domain.get(domain, []), key=lambda row: row["document_family_id"])[
                : G1_D02_PER_DOMAIN["pilot_catalog_families"]
            ]
        )
    catalog_ids = {row["document_family_id"] for row in catalog_selected}

    graph_selected: list[dict[str, Any]] = []
    for domain in PILOT_DOMAINS:
        domain_rows = [
            row for row in catalog_selected if row["domain_primary"] == domain
        ]
        graph_selected.extend(
            sorted(domain_rows, key=lambda row: row["document_family_id"])[
                : G1_D02_PER_DOMAIN["graph_families"]
            ]
        )
    graph_ids = {row["document_family_id"] for row in graph_selected}

    review_cases: list[dict[str, Any]] = []
    for domain in PILOT_DOMAINS:
        domain_rows = sorted(
            [row for row in catalog_selected if row["domain_primary"] == domain],
            key=lambda row: row["document_family_id"],
        )
        for index in range(G1_D02_PER_DOMAIN["review_candidate_cases"]):
            if not domain_rows:
                break
            family = domain_rows[index % len(domain_rows)]
            review_cases.append(
                {
                    "case_id": f"rc_{domain.lower()}_{index + 1}",
                    "case_kind": REVIEW_CASE_KINDS[index % len(REVIEW_CASE_KINDS)],
                    "document_family_id": family["document_family_id"],
                    "domain_primary": domain,
                    "rights_ref": _s(family.get("rights_ref")),
                    "data_origin": _s(family.get("data_origin")) or "UNKNOWN",
                    "cutoff_utc": _s(family.get("cutoff_utc")),
                    "cutoff_vn": _s(family.get("cutoff_vn")),
                }
            )
    review_ids = {row["document_family_id"] for row in review_cases}

    candidates = [
        row
        for row in artifacts
        if row.get("eligible_for_extraction")
        and _s(row.get("domain_primary")) in PILOT_DOMAINS
        and row.get("artifact_id")
    ]
    candidates.sort(
        key=lambda row: (
            FORMAT_ORDER.index(row["format_group"]) if row["format_group"] in FORMAT_ORDER else 99,
            _domain_rank(row["domain_primary"]),
            row["artifact_id"],
        )
    )
    selected_artifacts: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for format_name, target in EXTRACTION_FORMAT_TARGETS.items():
        format_rows = [
            row for row in candidates if row["format_group"] == format_name
        ]
        for row in format_rows:
            if len([item for item in selected_artifacts if item["format_group"] == format_name]) >= target:
                break
            if row["artifact_id"] not in selected_ids:
                selected_artifacts.append(row)
                selected_ids.add(row["artifact_id"])
    remaining = [
        row for row in candidates if row["artifact_id"] not in selected_ids
    ]
    if len(selected_artifacts) < G1_D02_TARGETS["extraction_artifacts"]:
        for row in remaining:
            if len(selected_artifacts) >= G1_D02_TARGETS["extraction_artifacts"]:
                break
            selected_artifacts.append(row)
            selected_ids.add(row["artifact_id"])
    extraction_length = len(selected_artifacts)
    selected_artifacts = selected_artifacts[: G1_D02_TARGETS["extraction_artifacts"]]
    extraction_ids = {row["artifact_id"] for row in selected_artifacts}

    extraction_family_ids = {
        family_id
        for artifact in selected_artifacts
        for family_id in artifact.get("document_family_ids", [])
    }
    all_family_ids = sorted(catalog_ids | graph_ids | review_ids | extraction_family_ids)
    family_by_id = {row["document_family_id"]: row for row in families}
    rows: list[dict[str, Any]] = []
    for family_id in all_family_ids:
        family = family_by_id.get(family_id)
        if family is None:
            continue
        rows.append(
            _pilot_family_row(
                family,
                in_catalog=family_id in catalog_ids,
                in_extraction=family_id in extraction_family_ids,
                in_graph=family_id in graph_ids,
                in_review=family_id in review_ids,
                review_case_ids=[
                    case["case_id"] for case in review_cases if case["document_family_id"] == family_id
                ],
            )
        )
    for artifact in sorted(selected_artifacts, key=lambda row: row["artifact_id"]):
        rows.append(_pilot_artifact_row(artifact))
    for case in sorted(
        review_cases, key=lambda row: (_domain_rank(row["domain_primary"]), row["case_id"])
    ):
        rows.append(_pilot_review_row(case))
    rows.sort(key=_pilot_sample_sort_key)

    catalog_by_domain = {
        domain: {
            "target": G1_D02_PER_DOMAIN["pilot_catalog_families"],
            "selected": len([row for row in catalog_selected if row["domain_primary"] == domain]),
        }
        for domain in PILOT_DOMAINS
    }
    graph_by_domain = {
        domain: {
            "target": G1_D02_PER_DOMAIN["graph_families"],
            "selected": len([row for row in graph_selected if row["domain_primary"] == domain]),
        }
        for domain in PILOT_DOMAINS
    }
    review_by_domain = {
        domain: {
            "target": G1_D02_PER_DOMAIN["review_candidate_cases"],
            "selected": len(
                [row for row in review_cases if row["domain_primary"] == domain]
            ),
        }
        for domain in PILOT_DOMAINS
    }
    extraction_by_format = {
        format_name: {
            "target": target,
            "selected": len(
                [row for row in selected_artifacts if row["format_group"] == format_name]
            ),
        }
        for format_name, target in EXTRACTION_FORMAT_TARGETS.items()
    }
    shortfalls = {
        "pilot_catalog_families": {
            **_stratum_entry(
                G1_D02_TARGETS["pilot_catalog_families"], len(catalog_selected)
            ),
            "by_domain": {
                domain: _stratum_entry(entry["target"], entry["selected"])
                for domain, entry in catalog_by_domain.items()
            },
        },
        "extraction_artifacts": {
            **_stratum_entry(G1_D02_TARGETS["extraction_artifacts"], extraction_length),
            "by_format": {
                format_name: _stratum_entry(entry["target"], entry["selected"])
                for format_name, entry in extraction_by_format.items()
            },
        },
        "graph_families": {
            **_stratum_entry(G1_D02_TARGETS["graph_families"], len(graph_selected)),
            "by_domain": {
                domain: _stratum_entry(entry["target"], entry["selected"])
                for domain, entry in graph_by_domain.items()
            },
        },
        "review_candidate_cases": {
            **_stratum_entry(
                G1_D02_TARGETS["review_candidate_cases"], len(review_cases)
            ),
            "by_domain": {
                domain: _stratum_entry(entry["target"], entry["selected"])
                for domain, entry in review_by_domain.items()
            },
        },
    }
    format_shortfall = any(
        entry["status"] == "SHORTFALL"
        for entry in shortfalls["extraction_artifacts"]["by_format"].values()
    )
    if shortfalls["extraction_artifacts"]["status"] == "MET" and format_shortfall:
        shortfalls["extraction_artifacts"]["status"] = "SHORTFALL"
        shortfalls["extraction_artifacts"]["reasons"] = [
            f"format minimum not met: {format_name}"
            for format_name, entry in shortfalls["extraction_artifacts"]["by_format"].items()
            if entry["status"] == "SHORTFALL"
        ]
    counts = {
        "pilot_catalog_families": len(catalog_selected),
        "extraction_artifacts": len(selected_artifacts),
        "graph_families": len(graph_selected),
        "review_candidate_cases": len(review_cases),
        "unique_families_total": len({row["document_family_id"] for row in rows if row["document_family_id"]}),
        "unique_artifacts_total": len(extraction_ids),
        "unique_review_cases_total": len(review_cases),
    }
    targets = dict(G1_D02_TARGETS)
    return {
        "selection_origin": selected_origin,
        "targets": targets,
        "counts": counts,
        "rows": rows,
        "shortfalls": shortfalls,
        "selections": {
            "pilot_catalog_family_ids": sorted(catalog_ids),
            "graph_family_ids": sorted(graph_ids),
            "review_case_ids": sorted(case["case_id"] for case in review_cases),
            "extraction_artifact_ids": sorted(extraction_ids),
        },
    }


def _pilot_sample_id(kind: str, key: str) -> str:
    return "ps_" + sha256_bytes(f"{kind}|{key}".encode("utf-8"))[:16]


def _pilot_family_row(
    family: dict[str, Any],
    *,
    in_catalog: bool,
    in_extraction: bool,
    in_graph: bool,
    in_review: bool,
    review_case_ids: list[str],
) -> dict[str, Any]:
    return {
        "sample_id": _pilot_sample_id("document_family", family["document_family_id"]),
        "sample_kind": "document_family",
        "document_family_id": family["document_family_id"],
        "document_family_ids": [family["document_family_id"]],
        "document_version_ids": sorted(family.get("version_ids", [])),
        "artifact_id": "",
        "case_id": "",
        "case_kind": "",
        "sha256": "",
        "file_type": "",
        "format_group": "",
        "domain_primary": family.get("domain_primary", "UNMAPPED"),
        "rights_ref": _s(family.get("rights_ref")),
        "data_origin": _s(family.get("data_origin")) or "UNKNOWN",
        "in_pilot_catalog": in_catalog,
        "in_extraction_gold": in_extraction,
        "in_graph_gold": in_graph,
        "in_review_candidates": in_review,
        "review_case_ids": sorted(review_case_ids),
        "legal_status_verified": False,
        "portal_effective_date_unverified": True,
        "cutoff_utc": _s(family.get("cutoff_utc")),
        "cutoff_vn": _s(family.get("cutoff_vn")),
    }


def _pilot_artifact_row(artifact: dict[str, Any]) -> dict[str, Any]:
    family_ids = sorted(artifact.get("document_family_ids", []))
    return {
        "sample_id": _pilot_sample_id("artifact", artifact["artifact_id"]),
        "sample_kind": "artifact",
        "document_family_id": family_ids[0] if family_ids else "",
        "document_family_ids": family_ids,
        "document_version_ids": sorted(artifact.get("document_version_ids", [])),
        "artifact_id": artifact["artifact_id"],
        "case_id": "",
        "case_kind": "",
        "sha256": _s(artifact.get("sha256")),
        "file_type": _s(artifact.get("file_type"))
        or ((artifact.get("file_types") or [""])[0]),
        "format_group": artifact.get("format_group", "other"),
        "domain_primary": artifact.get("domain_primary", "UNMAPPED"),
        "rights_ref": _s(artifact.get("rights_ref")),
        "data_origin": _s(artifact.get("data_origin")) or "UNKNOWN",
        "in_pilot_catalog": False,
        "in_extraction_gold": True,
        "in_graph_gold": False,
        "in_review_candidates": False,
        "review_case_ids": [],
        "legal_status_verified": False,
        "portal_effective_date_unverified": True,
        "cutoff_utc": _s(artifact.get("cutoff_utc")),
        "cutoff_vn": _s(artifact.get("cutoff_vn")),
    }


def _pilot_review_row(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": _pilot_sample_id("review_case", case["case_id"]),
        "sample_kind": "review_case",
        "document_family_id": case["document_family_id"],
        "document_family_ids": [case["document_family_id"]],
        "document_version_ids": [],
        "artifact_id": "",
        "case_id": case["case_id"],
        "case_kind": case["case_kind"],
        "sha256": "",
        "file_type": "",
        "format_group": "",
        "domain_primary": case["domain_primary"],
        "rights_ref": _s(case.get("rights_ref")),
        "data_origin": _s(case.get("data_origin")) or "UNKNOWN",
        "in_pilot_catalog": False,
        "in_extraction_gold": False,
        "in_graph_gold": False,
        "in_review_candidates": True,
        "review_case_ids": [case["case_id"]],
        "legal_status_verified": False,
        "portal_effective_date_unverified": True,
        "cutoff_utc": _s(case.get("cutoff_utc")),
        "cutoff_vn": _s(case.get("cutoff_vn")),
    }


def _pilot_sample_sort_key(row: dict[str, Any]) -> tuple[str, int, str, str]:
    kind_order = {"document_family": 0, "artifact": 1, "review_case": 2}
    return (
        str(kind_order.get(row["sample_kind"], 9)),
        _domain_rank(row["domain_primary"]),
        row["document_family_id"],
        row["artifact_id"] or row["case_id"],
    )


def _new_metric() -> dict[str, Any]:
    metric: dict[str, Any] = {key: 0 for key in _METRIC_KEYS}
    metric["unique_families"] = set()
    metric["unique_versions"] = set()
    metric["unique_blobs"] = set()
    metric["normalized_bytes_or_NOT_RUN"] = "NOT_RUN"
    metric["_blob_sizes"] = {}
    metric["_suspected_duplicates"] = set()
    metric["_missing"] = set()
    return metric


def _apply_catalog_metric(metric: dict[str, Any], row: dict[str, Any]) -> None:
    metric["observed"] += 1
    if row["eligible_for_pilot_denominator"]:
        metric["eligible"] += 1
        metric["unique_families"].add(row["document_family_id"])
        metric["unique_versions"].add(row["document_version_id"])
    if row["classification"] == "PRE_2020_REFERENCE":
        metric["pre_2020_references_excluded"] += 1
    elif row["classification"] == "POST_CUTOFF":
        metric["post_cutoff_excluded"] += 1
    if _s(row.get("error")):
        metric["errors"] += 1


def _apply_occurrence_metric(metric: dict[str, Any], occurrence: dict[str, Any]) -> None:
    metric["downloaded"] += 1
    if occurrence["sha256"] and not occurrence["quarantined"]:
        metric["hash_verified"] += 1
    if occurrence["quarantined"]:
        metric["quarantined"] += 1
    if _s(occurrence.get("error")):
        metric["errors"] += 1
    size = occurrence.get("size_bytes")
    if isinstance(size, int) and not isinstance(size, bool) and size >= 0:
        metric["raw_bytes"] += size
        metric["_blob_sizes"][occurrence["artifact_id"]] = max(
            metric["_blob_sizes"].get(occurrence["artifact_id"], 0), size
        )
    metric["unique_blobs"].add(occurrence["artifact_id"])


def _apply_conflict_metric(metric: dict[str, Any], conflict: dict[str, Any]) -> None:
    if conflict["conflict_type"] == "SUSPECTED_DUPLICATE":
        metric["_suspected_duplicates"].add(conflict["conflict_id"])
    if conflict["conflict_type"] in {
        "MISSING_GAZETTE_PAGE_OR_CONTINUATION",
        "MISSING_PARENT_ATTACHMENT",
    }:
        metric["_missing"].add(conflict["conflict_id"])


def _finalize_metric(metric: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in _METRIC_KEYS:
        value = metric[key]
        out[key] = len(value) if isinstance(value, set) else value
    out["unique_blob_bytes"] = sum(metric["_blob_sizes"].values())
    out["missing_or_shortfall"] = len(metric["_missing"])
    out["suspected_duplicates"] = len(metric["_suspected_duplicates"])
    return out


def _status_metric(status: str) -> dict[str, Any]:
    out = {key: status for key in _METRIC_KEYS}
    out["unique_blob_bytes"] = status
    # Normalization has not run in this phase, even when catalog measurement is blocked.
    out["normalized_bytes_or_NOT_RUN"] = "NOT_RUN"
    return out


def _record_contexts(row: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("data_origin", _s(row.get("data_origin")) or "UNKNOWN"),
        ("source_id", _s(row.get("source_id")) or "UNKNOWN"),
        ("year", _s(row.get("year")) or "UNKNOWN"),
        (
            "document_type",
            normalize_document_type(_s(row.get("document_type"))) or "UNKNOWN",
        ),
        ("domain_candidate", _s(row.get("domain_candidate_normalized")) or "UNMAPPED"),
    ]


def _occurrence_contexts(occurrence: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("data_origin", _s(occurrence.get("data_origin")) or "UNKNOWN"),
        ("source_id", _s(occurrence.get("source_id")) or "UNKNOWN"),
        ("year", _s(occurrence.get("year")) or "UNKNOWN"),
        (
            "document_type",
            normalize_document_type(_s(occurrence.get("document_type_normalized")))
            or "UNKNOWN",
        ),
        ("file_type", _s(occurrence.get("file_type")) or "UNKNOWN"),
        ("domain_candidate", _s(occurrence.get("domain_candidate_normalized")) or "UNMAPPED"),
    ]


def _conflict_contexts(conflict: dict[str, Any]) -> list[tuple[str, str]]:
    contexts = [
        ("data_origin", _s(conflict.get("data_origin")) or "UNKNOWN"),
        (
            "year",
            _s(conflict.get("document_year")) or "UNKNOWN",
        ),
        (
            "document_type",
            normalize_document_type(_s(conflict.get("document_type"))) or "UNKNOWN",
        ),
        ("domain_candidate", _s(conflict.get("domain_candidate")) or "UNMAPPED"),
    ]
    contexts.extend(("source_id", source) for source in conflict["source_ids"])
    if _s(conflict.get("file_type")):
        contexts.append(("file_type", _s(conflict["file_type"])))
    return contexts


def _finalize_buckets(
    buckets: dict[str, dict[str, dict[str, Any]]],
    *,
    always_include: dict[str, Iterable[str]] | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    finalized: dict[str, dict[str, dict[str, Any]]] = {}
    for dimension in sorted(buckets):
        keys = set(buckets[dimension])
        if always_include and dimension in always_include:
            keys.update(always_include[dimension])
        finalized[dimension] = {
            key: _finalize_metric(buckets[dimension].get(key) or _new_metric())
            for key in sorted(keys)
        }
    return finalized


def _build_denominators(
    prepared_catalog: list[dict[str, Any]],
    occurrences: list[dict[str, Any]],
    families: list[dict[str, Any]],
    versions: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    rights_matrix: list[dict[str, Any]],
    partition_ledger: list[dict[str, Any]],
    *,
    required_partitions_by_source: dict[str, Iterable[str]] | None = None,
) -> dict[str, Any]:
    rights_index = _rights_index(rights_matrix)
    rights_rows = _flatten_rights_matrix(rights_matrix)
    normalized_ledger = _normalize_ledger(partition_ledger)
    required_map = {
        source_id: set(part_ids)
        for source_id, part_ids in (required_partitions_by_source or {}).items()
    }
    real_sources: set[str] = set(required_map.keys())
    synthetic_sources: set[str] = set()

    def classify_source(row: dict[str, Any]) -> None:
        source_id = _s(row.get("source_id"))
        if not source_id:
            return
        if _record_is_synthetic(row):
            synthetic_sources.add(source_id)
        else:
            real_sources.add(source_id)

    for row in prepared_catalog:
        classify_source(row)
    for occurrence in occurrences:
        classify_source(occurrence)
    for row in normalized_ledger:
        classify_source(row)
    for row in rights_rows:
        classify_source(row)

    def conflict_is_synthetic(conflict: dict[str, Any]) -> bool:
        return _origin_is_synthetic(
            conflict.get("data_origin"),
            conflict["source_ids"][0] if conflict["source_ids"] else "",
        )

    def source_accessible(source_id: str) -> bool:
        actions = rights_index.get(source_id, {})
        return all(
            bool(actions.get(action)) and set(actions.get(action, set())) == {"APPROVED"}
            for action in REQUIRED_REAL_ACTIONS
        )

    def source_manual_authorized(source_id: str) -> bool:
        actions = rights_index.get(source_id, {})
        return all(
            bool(actions.get(action)) and set(actions.get(action, set())) == {"APPROVED"}
            for action in ("manual_download", "store")
        )

    def metrics_for_source(
        source_id: str,
        synthetic: bool,
        *,
        valid_real_only: bool = False,
    ) -> dict[str, Any]:
        metric = _new_metric()
        for row in prepared_catalog:
            if row["source_id"] != source_id or _record_is_synthetic(row) != synthetic:
                continue
            if valid_real_only and not row.get("valid_real_provenance", False):
                continue
            _apply_catalog_metric(metric, row)
        for occurrence in occurrences:
            if (
                occurrence["source_id"] != source_id
                or _record_is_synthetic(occurrence) != synthetic
            ):
                continue
            if valid_real_only and not occurrence.get("valid_real_provenance", False):
                continue
            _apply_occurrence_metric(metric, occurrence)
        metric["cross_source_overlap"] = len(
            [
                family
                for family in families
                if family.get("cross_source_overlap")
                and source_id in family["source_ids"]
                and _family_is_synthetic(family) == synthetic
                and (not valid_real_only or family.get("valid_real_provenance", False))
            ]
        )
        for conflict in conflicts:
            if (
                source_id in conflict["source_ids"]
                and conflict_is_synthetic(conflict) == synthetic
            ):
                _apply_conflict_metric(metric, conflict)
        return _finalize_metric(metric)

    real_detail: dict[str, Any] = {}
    for source_id in sorted(real_sources):
        accessible = source_accessible(source_id)
        manual_ok = source_manual_authorized(source_id)
        source_ledger = [
            row
            for row in normalized_ledger
            if row["source_id"] == source_id and not _record_is_synthetic(row)
        ]
        required_ids = set(required_map.get(source_id, ())) | {
            row["partition_id"] for row in source_ledger if row["partition_id"]
        }
        completed_ids = {
            row["partition_id"]
            for row in source_ledger
            if row["status"] == "COMPLETED" and row["rights_status"] == "APPROVED"
        }
        enumerated_complete_ids = {
            row["partition_id"]
            for row in source_ledger
            if row["status"] == "COMPLETED"
            and row["rights_status"] == "APPROVED"
            and row.get("catalog_enumeration_complete") is True
        }
        incomplete_partition_ids = sorted(required_ids - enumerated_complete_ids)
        has_real_rows = any(
            row["source_id"] == source_id and not _record_is_synthetic(row)
            for row in prepared_catalog
        ) or any(
            occ["source_id"] == source_id and not _record_is_synthetic(occ)
            for occ in occurrences
        )
        has_started_partition = any(
            row["status"] not in {"BLOCKED_RIGHTS", "PENDING_RIGHTS", "NOT_RUN", "PENDING", ""}
            for row in source_ledger
        )
        progress_metrics = metrics_for_source(source_id, synthetic=False, valid_real_only=True)
        progress_block = {
            **progress_metrics,
            "partitions_total": len(required_ids),
            "partitions_completed": len(completed_ids),
            "partitions_enumerated_complete": len(enumerated_complete_ids),
            "incomplete_partition_ids": incomplete_partition_ids,
        }
        fully_enumerated = (
            bool(source_ledger)
            and bool(required_ids)
            and not incomplete_partition_ids
        )

        if not accessible:
            real_detail[source_id] = {
                "real_catalog_accessible": False,
                "manual_intake_authorized": manual_ok,
                "denominator_locked": False,
                "measurement_status": "UNKNOWN",
                "rights_status": "MANUAL_ONLY_PARTIAL" if manual_ok else "BLOCKED_OR_MISSING_APPROVAL",
                "progress": progress_block,
                **_status_metric("UNKNOWN"),
            }
        elif not has_real_rows and not has_started_partition:
            real_detail[source_id] = {
                "real_catalog_accessible": True,
                "manual_intake_authorized": manual_ok,
                "denominator_locked": False,
                "measurement_status": "NOT_RUN",
                "rights_status": "APPROVED",
                "progress": progress_block,
                **_status_metric("NOT_RUN"),
            }
        elif not fully_enumerated:
            real_detail[source_id] = {
                "real_catalog_accessible": True,
                "manual_intake_authorized": manual_ok,
                "denominator_locked": False,
                "measurement_status": "PARTIAL",
                "rights_status": "APPROVED",
                "progress": progress_block,
                **_status_metric("UNKNOWN"),
            }
        else:
            real_detail[source_id] = {
                "real_catalog_accessible": True,
                "manual_intake_authorized": manual_ok,
                "denominator_locked": True,
                "measurement_status": "MEASURED",
                "rights_status": "APPROVED",
                "progress": progress_block,
                **progress_metrics,
            }

    real_progress_metric = _new_metric()
    for row in prepared_catalog:
        if row.get("valid_real_provenance", False):
            _apply_catalog_metric(real_progress_metric, row)
    for occurrence in occurrences:
        if occurrence.get("valid_real_provenance", False):
            _apply_occurrence_metric(real_progress_metric, occurrence)
    real_progress_metric["cross_source_overlap"] = len(
        [
            family
            for family in families
            if family.get("cross_source_overlap")
            and family.get("valid_real_provenance", False)
        ]
    )
    for conflict in conflicts:
        if not conflict_is_synthetic(conflict):
            _apply_conflict_metric(real_progress_metric, conflict)
    real_progress_final = _finalize_metric(real_progress_metric)

    real_aggregate: dict[str, Any]
    if not real_sources:
        real_aggregate = {
            "real_catalog_accessible": False,
            "denominator_locked": False,
            "measurement_status": "UNKNOWN",
            "progress": real_progress_final,
            **_status_metric("UNKNOWN"),
        }
    elif any(not entry["real_catalog_accessible"] for entry in real_detail.values()):
        real_aggregate = {
            "real_catalog_accessible": False,
            "denominator_locked": False,
            "measurement_status": "UNKNOWN",
            "progress": real_progress_final,
            **_status_metric("UNKNOWN"),
        }
    elif all(entry["measurement_status"] == "NOT_RUN" for entry in real_detail.values()):
        real_aggregate = {
            "real_catalog_accessible": True,
            "denominator_locked": False,
            "measurement_status": "NOT_RUN",
            "progress": real_progress_final,
            **_status_metric("NOT_RUN"),
        }
    elif all(entry["measurement_status"] == "MEASURED" for entry in real_detail.values()):
        real_aggregate = {
            "real_catalog_accessible": True,
            "denominator_locked": True,
            "measurement_status": "MEASURED",
            "progress": real_progress_final,
            **real_progress_final,
        }
    else:
        incomplete_sources = sorted(
            sid
            for sid, entry in real_detail.items()
            if entry["measurement_status"] != "MEASURED"
        )
        real_aggregate = {
            "real_catalog_accessible": True,
            "denominator_locked": False,
            "measurement_status": "PARTIAL",
            "incomplete_sources": incomplete_sources,
            "progress": real_progress_final,
            **_status_metric("UNKNOWN"),
        }

    synthetic_detail: dict[str, Any] = {}
    for source_id in sorted(synthetic_sources):
        synthetic_detail[source_id] = {
            "real_catalog_accessible": False,
            "measurement_status": "SYNTHETIC_FIXTURE",
            **metrics_for_source(source_id, synthetic=True),
        }
    synthetic_metric = _new_metric()
    for row in prepared_catalog:
        if _record_is_synthetic(row):
            _apply_catalog_metric(synthetic_metric, row)
    for occurrence in occurrences:
        if _record_is_synthetic(occurrence):
            _apply_occurrence_metric(synthetic_metric, occurrence)
    synthetic_metric["cross_source_overlap"] = len(
        [
            family
            for family in families
            if family.get("cross_source_overlap") and _family_is_synthetic(family)
        ]
    )
    for conflict in conflicts:
        if conflict_is_synthetic(conflict):
            _apply_conflict_metric(synthetic_metric, conflict)
    pilot_origins = _distinct_sorted(family.get("data_origin") for family in families)
    return {
        "real": real_aggregate,
        "real_sources": real_detail,
        "synthetic": {
            "real_catalog_accessible": False,
            "measurement_status": "SYNTHETIC_FIXTURE",
            **_finalize_metric(synthetic_metric),
        },
        "synthetic_sources": synthetic_detail,
        "pilot": {
            "eligible_unique_families": len(families),
            "eligible_unique_versions": len(versions),
            "eligible_source_records": len(
                [row for row in prepared_catalog if row["eligible_for_pilot_denominator"]]
            ),
            "data_origins": pilot_origins,
            "normalized_bytes_or_NOT_RUN": "NOT_RUN",
        },
        "normalized_bytes_or_NOT_RUN": "NOT_RUN",
    }


def _rights_index(rights_matrix: list[dict[str, Any]]) -> dict[str, dict[str, set[str]]]:
    flattened = _flatten_rights_matrix(rights_matrix)
    index: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in flattened:
        source_id = _s(row.get("source_id"))
        action = _s(row.get("action"))
        if not source_id or not action:
            continue
        index[source_id][action].add(_s(row.get("status")) or "PENDING_RIGHTS")
    return {source: dict(actions) for source, actions in index.items()}


def _flatten_rights_matrix(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for row in rows:
        actions = row.get("actions")
        if isinstance(actions, dict):
            base = {key: value for key, value in row.items() if key != "actions"}
            for action in sorted(actions):
                policy = actions[action]
                if isinstance(policy, dict):
                    flat.append(
                        {
                            **base,
                            "action": action,
                            "status": _s(policy.get("status")) or "PENDING_RIGHTS",
                            "rights_ref": _s(policy.get("evidence_ref"))
                            or _s(row.get("rights_ref")),
                            "evidence_ref": _s(policy.get("evidence_ref")),
                            "approved_at": _s(policy.get("approved_at")),
                            "expires_at": _s(policy.get("expires_at")),
                            "policy_url": _s(policy.get("policy_url")),
                        }
                    )
                else:
                    flat.append(
                        {
                            **base,
                            "action": action,
                            "status": _s(policy) or "PENDING_RIGHTS",
                        }
                    )
        else:
            flat.append(dict(row))
    normalized: list[dict[str, Any]] = []
    for row in flat:
        action = _s(row.get("action"))
        normalized.append(
            {
                **row,
                "source_id": _s(row.get("source_id")),
                "action": action,
                "status": _s(row.get("status")) or "PENDING_RIGHTS",
                "rights_ref": _s(row.get("rights_ref")) or _s(row.get("evidence_ref")),
                "approved_at": _s(row.get("approved_at")),
                "expires_at": _s(row.get("expires_at")),
                "policy_url": _s(row.get("policy_url")),
                "evidence_ref": _s(row.get("evidence_ref")) or _s(row.get("rights_ref")),
                "registry_revision": _s(row.get("registry_revision")),
                "data_origin": _s(row.get("data_origin")),
                "action_valid": action in ACTIONS,
                "legal_status_verified": False,
            }
        )
    normalized.sort(
        key=lambda row: (
            row["source_id"],
            row["action"],
            row["status"],
            row["rights_ref"],
        )
    )
    return normalized


def _normalize_ledger(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        requests_attempted = row.get("requests_attempted", 0)
        blobs_written = row.get("blobs_written", 0)
        normalized.append(
            {
                **row,
                "source_id": _s(row.get("source_id")),
                "partition_id": _s(row.get("partition_id"))
                or _s(row.get("partition"))
                or f"{_s(row.get('source_id'))}__{_s(row.get('year'))}",
                "status": canonical_partition_status(_s(row.get("status"))),
                "rights_status": _s(row.get("rights_status")) or "UNKNOWN",
                "requests_attempted": int(requests_attempted) if isinstance(requests_attempted, int) and not isinstance(requests_attempted, bool) else 0,
                "blobs_written": int(blobs_written) if isinstance(blobs_written, int) and not isinstance(blobs_written, bool) else 0,
                "catalog_enumeration_complete": bool(row.get("catalog_enumeration_complete", False)),
                "legal_status_verified": False,
            }
        )
    normalized.sort(key=lambda row: (row["source_id"], row["partition_id"], row["status"]))
    return normalized


def _selection_summary_block(selection: dict[str, Any]) -> dict[str, Any]:
    shortfall_summary = {
        "total_shortfall": sum(
            entry["shortfall"] for entry in selection["shortfalls"].values()
        ),
        **selection["shortfalls"],
    }
    return {
        "selection_origin": selection.get("selection_origin", "UNKNOWN"),
        "targets": selection["targets"],
        "counts": selection["counts"],
        "shortfalls": shortfall_summary,
    }


def _build_summary(
    cutoff: RunCutoff,
    prepared_catalog: list[dict[str, Any]],
    families: list[dict[str, Any]],
    versions: list[dict[str, Any]],
    occurrences: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    rights_matrix: list[dict[str, Any]],
    partition_ledger: list[dict[str, Any]],
    selection: dict[str, Any],
    *,
    real_selection: dict[str, Any] | None = None,
    synthetic_selection: dict[str, Any] | None = None,
    required_partitions_by_source: dict[str, Iterable[str]] | None = None,
) -> dict[str, Any]:
    totals = _new_metric()
    buckets: dict[str, dict[str, dict[str, Any]]] = {
        "by_data_origin": {},
        "by_source_id": {},
        "by_year": {},
        "by_document_type": {},
        "by_file_type": {},
        "by_domain_candidate": {},
    }

    def bucket(dimension: str, key: str) -> dict[str, Any]:
        return buckets[f"by_{dimension}"].setdefault(key, _new_metric())

    for row in prepared_catalog:
        _apply_catalog_metric(totals, row)
        for dimension, key in _record_contexts(row):
            _apply_catalog_metric(bucket(dimension, key), row)
    for occurrence in occurrences:
        _apply_occurrence_metric(totals, occurrence)
        for dimension, key in _occurrence_contexts(occurrence):
            _apply_occurrence_metric(bucket(dimension, key), occurrence)
    for family in families:
        if family.get("cross_source_overlap"):
            totals["cross_source_overlap"] += 1
        contexts = [
            ("data_origin", _s(family.get("data_origin")) or "UNKNOWN"),
            ("year", _s(family.get("year")) or "UNKNOWN"),
            (
                "document_type",
                normalize_document_type(_s(family.get("document_type_normalized")))
                or "UNKNOWN",
            ),
            ("domain_candidate", _s(family.get("domain_primary")) or "UNMAPPED"),
        ]
        if family.get("cross_source_overlap"):
            for dimension, key in contexts:
                bucket(dimension, key)["cross_source_overlap"] += 1
            for source in family["source_ids"]:
                bucket("source_id", source)["cross_source_overlap"] += 1
    for conflict in conflicts:
        _apply_conflict_metric(totals, conflict)
        for dimension, key in _conflict_contexts(conflict):
            _apply_conflict_metric(bucket(dimension, key), conflict)

    finalized_buckets = _finalize_buckets(
        buckets,
        always_include={
            "by_data_origin": ("REAL", "SYNTHETIC_FIXTURE"),
            "by_domain_candidate": (*PILOT_DOMAINS, "UNMAPPED"),
        },
    )
    conflict_counts = Counter(conflict["conflict_type"] for conflict in conflicts)
    shortfall_summary = {
        "total_shortfall": sum(
            entry["shortfall"] for entry in selection["shortfalls"].values()
        ),
        **selection["shortfalls"],
    }
    denominators = _build_denominators(
        prepared_catalog,
        occurrences,
        families,
        versions,
        conflicts,
        rights_matrix,
        partition_ledger,
        required_partitions_by_source=required_partitions_by_source,
    )
    real_status = denominators["real"]["measurement_status"]
    if real_status == "MEASURED":
        finalized_buckets["by_data_origin"]["REAL"] = {
            "real_catalog_accessible": True,
            "denominator_locked": True,
            "measurement_status": "MEASURED",
            **{
                key: denominators["real"][key]
                for key in (*_METRIC_KEYS, "unique_blob_bytes")
            },
        }
    else:
        metric_token = "NOT_RUN" if real_status == "NOT_RUN" else "UNKNOWN"
        finalized_buckets["by_data_origin"]["REAL"] = {
            "real_catalog_accessible": denominators["real"]["real_catalog_accessible"],
            "denominator_locked": False,
            "measurement_status": real_status,
            "progress": denominators["real"].get("progress", {}),
            **_status_metric(metric_token),
        }
    for source_id, entry in sorted(denominators["real_sources"].items()):
        if entry["measurement_status"] == "MEASURED":
            finalized_buckets.setdefault("by_source_id", {})[source_id] = {
                "real_catalog_accessible": True,
                "denominator_locked": True,
                "measurement_status": "MEASURED",
                "rights_status": entry.get("rights_status", "APPROVED"),
                **{key: entry[key] for key in (*_METRIC_KEYS, "unique_blob_bytes")},
            }
            continue
        metric_token = "NOT_RUN" if entry["measurement_status"] == "NOT_RUN" else "UNKNOWN"
        finalized_buckets.setdefault("by_source_id", {})[source_id] = {
            "real_catalog_accessible": entry["real_catalog_accessible"],
            "denominator_locked": False,
            "measurement_status": entry["measurement_status"],
            "rights_status": entry.get("rights_status", ""),
            "progress": entry.get("progress", {}),
            **_status_metric(metric_token),
        }
    finalized_buckets["by_source_id"] = {
        key: finalized_buckets["by_source_id"][key]
        for key in sorted(finalized_buckets["by_source_id"])
    }
    g1_d02_by_origin: dict[str, Any] = {}
    if real_selection is not None:
        g1_d02_by_origin["REAL"] = _selection_summary_block(real_selection)
    if synthetic_selection is not None:
        g1_d02_by_origin["SYNTHETIC_FIXTURE"] = _selection_summary_block(synthetic_selection)

    return {
        "run_id": cutoff.run_id,
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
        "window_start_date": cutoff.window_start_date,
        "generated_by": "luatvn_ai_data_ingestion.pilot_reconciler",
        "totals": _finalize_metric(totals),
        **finalized_buckets,
        "denominators": denominators,
        "real_source_denominators": real_status,
        "measurement_status": {
            "real_catalog": real_status,
            "real_denominator_locked": bool(denominators["real"].get("denominator_locked", False)),
            "normalized_bytes": "NOT_RUN",
        },
        "conflicts": {
            "total": len(conflicts),
            "by_type": {key: conflict_counts[key] for key in sorted(conflict_counts)},
        },
        "unique_blob_count": len(artifacts),
        "artifact_dedup": {
            "unique_blobs": len(artifacts),
            "unique_blob_count": len(artifacts),
            "total_occurrences": len(occurrences),
            "deduplicated_occurrences": max(len(occurrences) - len(artifacts), 0),
        },
        "g1_d02": {
            "selection_origin": selection.get("selection_origin", "UNKNOWN"),
            "targets": selection["targets"],
            "counts": selection["counts"],
            "shortfalls": shortfall_summary,
            "by_data_origin": g1_d02_by_origin,
        },
        "legal_status_verified": False,
        "portal_effective_date_unverified": True,
        "normalized_bytes_or_NOT_RUN": "NOT_RUN",
    }


def reconcile_pilot_data(
    catalog_records: list[dict[str, Any]],
    artifact_records: list[dict[str, Any]],
    cutoff: RunCutoff,
    rights_matrix: list[dict[str, Any]] | None = None,
    partition_ledger: list[dict[str, Any]] | None = None,
    *,
    required_partitions_by_source: dict[str, Iterable[str]] | None = None,
) -> dict[str, Any]:
    """Reconcile catalog/artifact observations into canonical entities and QA queues."""
    rights_matrix = list(rights_matrix or [])
    partition_ledger = list(partition_ledger or [])
    rights_index = _rights_index(rights_matrix)
    prepared_catalog = _prepare_catalog(list(catalog_records), cutoff, rights_index=rights_index)
    occurrences = _prepare_occurrences(
        list(artifact_records), prepared_catalog, cutoff, rights_index=rights_index
    )
    artifacts = _build_artifacts(occurrences)
    families, versions = _build_families_and_versions(prepared_catalog, artifacts, cutoff)
    conflicts = _detect_conflicts_prepared(prepared_catalog, occurrences, cutoff)

    artifact_ids_by_parent: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for occurrence in occurrences:
        if occurrence["parent_matched"]:
            artifact_ids_by_parent[
                (
                    occurrence["origin_lane"],
                    occurrence["parent_source_id"],
                    occurrence["parent_source_record_id"],
                )
            ].append(occurrence["artifact_id"])
    for row in prepared_catalog:
        row["artifact_ids"] = sorted(
            set(
                artifact_ids_by_parent.get(
                    (row["origin_lane"], row["source_id"], row["source_record_id"]), []
                )
            )
        )

    real_selection = select_g1_d02_pilot_samples(
        families,
        artifacts,
        origin_filter="REAL",
        require_valid_real_provenance=True,
    )
    synthetic_selection = select_g1_d02_pilot_samples(
        families,
        artifacts,
        origin_filter="SYNTHETIC_FIXTURE",
    )
    has_real_observations = any(
        not _record_is_synthetic(row) for row in prepared_catalog
    ) or any(not _record_is_synthetic(occ) for occ in occurrences)
    selection = real_selection if has_real_observations else synthetic_selection

    summary = _build_summary(
        cutoff,
        prepared_catalog,
        families,
        versions,
        occurrences,
        artifacts,
        conflicts,
        rights_matrix,
        partition_ledger,
        selection,
        real_selection=real_selection,
        synthetic_selection=synthetic_selection,
        required_partitions_by_source=required_partitions_by_source,
    )
    return {
        "run_id": cutoff.run_id,
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
        "rights_matrix": _flatten_rights_matrix(rights_matrix),
        "partition_ledger": _normalize_ledger(partition_ledger),
        "source_records": prepared_catalog,
        "document_families": families,
        "document_versions": versions,
        "artifacts": artifacts,
        "unique_blob_count": len(artifacts),
        "artifact_occurrences": occurrences,
        "pre_2020_references": [
            row for row in prepared_catalog if row["classification"] == "PRE_2020_REFERENCE"
        ],
        "out_of_window_excluded": [
            row for row in prepared_catalog if row["classification"] == "POST_CUTOFF"
        ],
        "missing_or_invalid_date_records": [
            row
            for row in prepared_catalog
            if row["classification"] == "MISSING_OR_INVALID_ISSUED_DATE"
        ],
        "conflicts": conflicts,
        "pilot_samples": selection["rows"],
        "pilot_selection": selection,
        "pilot_selection_by_origin": {
            "REAL": real_selection,
            "SYNTHETIC_FIXTURE": synthetic_selection,
        },
        "shortfalls": selection["shortfalls"],
        "denominators": summary["denominators"],
        "summary": summary,
        "legal_status_verified": False,
        "portal_effective_date_unverified": True,
    }


def write_reconciliation_bundle(
    reconciliation: dict[str, Any],
    output_dir: Path | str,
) -> dict[str, Any]:
    """Write the seven JSONL/CSV artifacts plus ``summary-metrics.json`` atomically."""
    if isinstance(reconciliation, (str, Path)) and isinstance(output_dir, dict):
        reconciliation, output_dir = output_dir, reconciliation
    destination = Path(output_dir)
    specs = (
        ("rights-matrix", RIGHTS_MATRIX_FIELDS, reconciliation["rights_matrix"]),
        ("partition-ledger", PARTITION_LEDGER_FIELDS, reconciliation["partition_ledger"]),
        ("source-catalog", SOURCE_CATALOG_FIELDS, reconciliation["source_records"]),
        ("artifact-manifest", ARTIFACT_MANIFEST_FIELDS, reconciliation["artifacts"]),
        ("canonical-catalog", CANONICAL_FIELDS, reconciliation["document_versions"]),
        ("conflicts", CONFLICT_FIELDS, reconciliation["conflicts"]),
        ("pilot-samples", PILOT_SAMPLE_FIELDS, reconciliation["pilot_samples"]),
    )
    digests: dict[str, str] = {}
    for name, fields, rows in specs:
        jsonl_path = destination / f"{name}.jsonl"
        csv_path = destination / f"{name}.csv"
        digests[jsonl_path.name] = write_jsonl_atomic(jsonl_path, rows)
        digests[csv_path.name] = write_csv_atomic(csv_path, fields, rows)
    summary_text = (
        json.dumps(
            reconciliation["summary"],
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )
    summary_path = destination / "summary-metrics.json"
    digests[summary_path.name] = atomic_write_text(summary_path, summary_text)
    return {
        "output_dir": str(destination),
        "files": digests,
        "bundle_sha256": sha256_bytes(
            json.dumps(digests, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ),
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"expected JSON object rows in {path}")
            rows.append(value)
    return rows


def _catalog_signature(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        _s(row.get("source_id")),
        _s(row.get("source_record_id")),
        _s(row.get("partition_id")),
        _s(row.get("page_url")),
        _s(row.get("rights_ref")),
        _s(row.get("relation_role")),
        _s(row.get("version")),
        normalize_document_number(_s(row.get("document_number"))),
        _s(row.get("issued_date")),
    )


def _occurrence_signature(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        _s(row.get("source_id")),
        _s(row.get("source_record_id")),
        _s(row.get("partition_id")),
        _s(row.get("parent_id")),
        _s(row.get("attachment_id")),
        _s(row.get("relation_role")),
        _s(row.get("version")),
        _s(row.get("file_url")),
        _s(row.get("page_url")),
        _valid_sha(row.get("sha256")),
        _s(row.get("status")),
        _s(row.get("quarantine_reason")),
    )


def _is_child_occurrence(row: dict[str, Any]) -> bool:
    return _s(row.get("relation_role")).casefold() in CHILD_RELATION_ROLES


def _walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk_json(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json(item)


def verify_reconciliation_invariants(
    catalog_records: list[dict[str, Any]],
    artifact_records: list[dict[str, Any]],
    cutoff: RunCutoff,
    rights_matrix: list[dict[str, Any]] | None,
    partition_ledger: list[dict[str, Any]] | None,
    *,
    run_a_dir: Path | str,
    run_b_dir: Path | str,
) -> dict[str, Any]:
    """Reconcile twice and assert deterministic digests, full provenance, and boundaries."""
    first = reconcile_pilot_data(
        catalog_records, artifact_records, cutoff, rights_matrix, partition_ledger
    )
    second = reconcile_pilot_data(
        catalog_records, artifact_records, cutoff, rights_matrix, partition_ledger
    )
    bundle_a = write_reconciliation_bundle(first, run_a_dir)
    bundle_b = write_reconciliation_bundle(second, run_b_dir)
    destination_a = Path(run_a_dir)
    destination_b = Path(run_b_dir)

    expected_files = sorted(
        [f"{name}.jsonl" for name in (
            "rights-matrix",
            "partition-ledger",
            "source-catalog",
            "artifact-manifest",
            "canonical-catalog",
            "conflicts",
            "pilot-samples",
        )]
        + [f"{name}.csv" for name in (
            "rights-matrix",
            "partition-ledger",
            "source-catalog",
            "artifact-manifest",
            "canonical-catalog",
            "conflicts",
            "pilot-samples",
        )]
        + ["summary-metrics.json"]
    )
    deterministic = bundle_a["files"] == bundle_b["files"] and all(
        name in bundle_a["files"] for name in expected_files
    )
    checks: list[dict[str, Any]] = [
        {
            "name": "deterministic_output_digests",
            "passed": deterministic,
            "details": {
                "bundle_sha256": bundle_a["bundle_sha256"],
                "mismatched_files": sorted(
                    name
                    for name in set(bundle_a["files"]) | set(bundle_b["files"])
                    if bundle_a["files"].get(name) != bundle_b["files"].get(name)
                ),
            },
        }
    ]

    source_catalog = _read_jsonl(destination_a / "source-catalog.jsonl")
    artifact_manifest = _read_jsonl(destination_a / "artifact-manifest.jsonl")
    canonical_catalog = _read_jsonl(destination_a / "canonical-catalog.jsonl")
    conflict_rows = _read_jsonl(destination_a / "conflicts.jsonl")
    summary = json.loads((destination_a / "summary-metrics.json").read_text(encoding="utf-8"))

    input_page_urls = Counter(
        _s(row.get("page_url")) for row in catalog_records if _s(row.get("page_url"))
    )
    input_file_urls = Counter(
        _s(row.get("file_url")) for row in artifact_records if _s(row.get("file_url"))
    )
    output_page_urls = Counter(
        _s(row.get("page_url")) for row in source_catalog if _s(row.get("page_url"))
    )
    output_file_urls: Counter[str] = Counter()
    for artifact in artifact_manifest:
        for occurrence in artifact.get("occurrences", []):
            if _s(occurrence.get("page_url")):
                output_page_urls[_s(occurrence["page_url"])] += 1
            if _s(occurrence.get("file_url")):
                output_file_urls[_s(occurrence["file_url"])] += 1
    lost_page_urls = sorted(
        url for url, count in input_page_urls.items() if output_page_urls[url] < count
    )
    lost_file_urls = sorted(
        url for url, count in input_file_urls.items() if output_file_urls[url] < count
    )
    input_catalog_rows = Counter(_catalog_signature(row) for row in catalog_records)
    output_catalog_rows = Counter(_catalog_signature(row) for row in source_catalog)
    dropped_catalog_rows = sum(
        max(count - output_catalog_rows[signature], 0)
        for signature, count in input_catalog_rows.items()
    )
    checks.append(
        {
            "name": "zero_lost_source_or_file_urls",
            "passed": not lost_page_urls and not lost_file_urls and dropped_catalog_rows == 0,
            "details": {
                "lost_page_urls": lost_page_urls,
                "lost_file_urls": lost_file_urls,
                "dropped_catalog_rows": dropped_catalog_rows,
            },
        }
    )

    output_occurrence_counts = Counter(
        _occurrence_signature(occurrence)
        for artifact in artifact_manifest
        for occurrence in artifact.get("occurrences", [])
    )
    input_occurrence_counts = Counter(_occurrence_signature(row) for row in artifact_records)
    appendix_counts = Counter(
        _occurrence_signature(row) for row in artifact_records if _is_child_occurrence(row)
    )
    appendix_output_counts = Counter(
        signature
        for signature in output_occurrence_counts
        if signature[5].casefold() in CHILD_RELATION_ROLES
    )
    quarantined_inputs = {
        (
            _s(row.get("source_id")),
            _s(row.get("source_record_id")),
            _s(row.get("attachment_id")),
            _s(row.get("file_url")),
            _valid_sha(row.get("sha256")),
            _s(row.get("quarantine_reason")),
        )
        for row in artifact_records
        if _s(row.get("status")).upper() == "QUARANTINED"
        or _s(row.get("quarantine_reason"))
    }
    quarantine_conflicts = {
        (
            row["source_ids"][0] if row["source_ids"] else "",
            _s(row["details"].get("source_record_id")),
            _s(row["details"].get("attachment_id")),
            _s(row["details"].get("file_url")),
            _valid_sha(row["details"].get("sha256")),
            _s(row["details"].get("quarantine_reason")),
        )
        for row in conflict_rows
        if row["conflict_type"] == "QUARANTINED_ARTIFACT"
    }
    missing_parent_conflicts = [
        row for row in conflict_rows if row["conflict_type"] == "MISSING_PARENT_ATTACHMENT"
    ]
    expected_missing_parents = {
        (
            _s(row.get("source_id")),
            _s(row.get("parent_id")),
            _s(row.get("attachment_id")),
            _s(row.get("file_url")),
        )
        for row in artifact_records
        if _is_child_occurrence(row)
        and not any(
            _s(catalog.get("source_id")) == _s(row.get("source_id"))
            and _s(catalog.get("source_record_id")) == _s(row.get("parent_id"))
            for catalog in catalog_records
        )
    }
    reported_missing_parents = {
        (
            row["source_ids"][0] if row["source_ids"] else "",
            _s(row["details"].get("parent_id")),
            _s(row["details"].get("attachment_id")),
            _s(row["details"].get("file_url")),
        )
        for row in missing_parent_conflicts
    }
    checks.append(
        {
            "name": "every_occurrence_appendix_and_quarantine_reported",
            "passed": (
                input_occurrence_counts == output_occurrence_counts
                and appendix_counts == appendix_output_counts
                and quarantined_inputs <= quarantine_conflicts
                and expected_missing_parents == reported_missing_parents
                and all(
                    row["review_status"] == "PENDING_REVIEW" for row in conflict_rows
                )
            ),
            "details": {
                "input_occurrences": len(artifact_records),
                "output_occurrences": sum(
                    len(artifact.get("occurrences", []))
                    for artifact in artifact_manifest
                ),
                "input_appendices": sum(appendix_counts.values()),
                "output_appendices": sum(appendix_output_counts.values()),
                "quarantined_inputs": len(quarantined_inputs),
                "missing_parent_conflicts": len(missing_parent_conflicts),
                "quarantine_conflicts": len(quarantine_conflicts),
            },
        }
    )

    boundary_leaks: list[str] = []
    for row in canonical_catalog:
        issued = _s(row.get("issued_date"))
        if not issued or issued < cutoff.window_start_date or issued > cutoff.cutoff_date_vn.isoformat():
            boundary_leaks.append(f"canonical date outside window: {row.get('document_version_id')}")
        if row.get("eligible_for_pilot_denominator") is not True:
            boundary_leaks.append(f"canonical row not eligible: {row.get('document_version_id')}")
        if row.get("is_pre_2020_reference") is not False or row.get("is_post_cutoff") is not False:
            boundary_leaks.append(f"canonical row carries excluded flag: {row.get('document_version_id')}")
    for row in source_catalog:
        if row.get("classification") in {
            "PRE_2020_REFERENCE",
            "POST_CUTOFF",
            "MISSING_OR_INVALID_ISSUED_DATE",
        } and row.get("eligible_for_pilot_denominator") is not False:
            boundary_leaks.append(
                f"excluded source record eligible: {row.get('source_id')}:{row.get('source_record_id')}"
            )
    if summary["totals"]["pre_2020_references_excluded"] != len(
        [row for row in source_catalog if row.get("classification") == "PRE_2020_REFERENCE"]
    ):
        boundary_leaks.append("pre-2020 exclusion total mismatch")
    if summary["totals"]["post_cutoff_excluded"] != len(
        [row for row in source_catalog if row.get("classification") == "POST_CUTOFF"]
    ):
        boundary_leaks.append("post-cutoff exclusion total mismatch")
    checks.append(
        {
            "name": "boundary_exclusions_hold",
            "passed": not boundary_leaks,
            "details": {
                "leaks": boundary_leaks,
                "pre_2020_excluded": summary["totals"]["pre_2020_references_excluded"],
                "post_cutoff_excluded": summary["totals"]["post_cutoff_excluded"],
            },
        }
    )

    legal_violations: list[str] = []
    canonical_missing_unverified = 0
    for name in (
        "rights-matrix.jsonl",
        "partition-ledger.jsonl",
        "source-catalog.jsonl",
        "artifact-manifest.jsonl",
        "canonical-catalog.jsonl",
        "conflicts.jsonl",
        "pilot-samples.jsonl",
    ):
        for row in _read_jsonl(destination_a / name):
            for nested in _walk_json(row):
                if nested.get("legal_status_verified") is not False and "legal_status_verified" in nested:
                    legal_violations.append(f"{name}: legal_status_verified is not False")
    for row in canonical_catalog:
        if row.get("portal_effective_date_unverified") is not True:
            canonical_missing_unverified += 1
    if summary.get("legal_status_verified") is not False:
        legal_violations.append("summary legal_status_verified is not False")
    checks.append(
        {
            "name": "portal_metadata_never_affirms_legal_status",
            "passed": not legal_violations and canonical_missing_unverified == 0,
            "details": {
                "violations": legal_violations,
                "canonical_missing_unverified": canonical_missing_unverified,
            },
        }
    )

    passed = all(check["passed"] for check in checks)
    jsonl_sha256 = {
        name: digest
        for name, digest in sorted(bundle_a["files"].items())
        if name.endswith(".jsonl")
    }
    csv_sha256 = {
        name: digest
        for name, digest in sorted(bundle_a["files"].items())
        if name.endswith(".csv")
    }
    return {
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "checks": checks,
        "run_a_dir": str(destination_a),
        "run_b_dir": str(destination_b),
        "file_sha256": bundle_a["files"],
        "jsonl_sha256": jsonl_sha256,
        "csv_sha256": csv_sha256,
        "bundle_sha256": bundle_a["bundle_sha256"],
        "counts": {
            "catalog_records": len(catalog_records),
            "artifact_records": len(artifact_records),
            "document_families": len(first["document_families"]),
            "document_versions": len(first["document_versions"]),
            "unique_blobs": len(first["artifacts"]),
            "artifact_occurrences": len(first["artifact_occurrences"]),
            "conflicts": len(first["conflicts"]),
            "pilot_samples": len(first["pilot_samples"]),
        },
        "denominators": first["denominators"],
        "summary": first["summary"],
        "targets": first["pilot_selection"]["targets"],
        "selected": first["pilot_selection"]["counts"],
        "shortfalls": first["shortfalls"],
    }


# ---------------------------------------------------------------------------
# Self-contained QA fixture (synthetic only; no network or source-staging reads)
# ---------------------------------------------------------------------------

_SHARED_PDF = b"%PDF-1.4\n%SYNTH-SHARED-78-2025-ND-CP-V1\n%%EOF\n"


def _fixture_bytes(label: str, kind: str) -> bytes:
    if kind == "pdf":
        return f"%PDF-1.4\n%SYNTH-{label}\n%%EOF\n".encode("utf-8")
    if kind == "scan":
        return f"%PDF-1.4\n%SYNTH-SCAN-{label}\n%%EOF\n".encode("utf-8")
    if kind == "doc":
        return f"SYNTH-DOC {label}\n".encode("utf-8")
    if kind == "docx":
        return b"PK\x03\x04" + f"SYNTH-DOCX-{label}".encode("utf-8")
    if kind == "xlsx":
        return b"PK\x03\x04xl/" + f"SYNTH-XLSX-{label}".encode("utf-8")
    return f"<html><body><h1>{label}</h1></body></html>".encode("utf-8")


def _fixture_sha(label: str, kind: str) -> str:
    return sha256_bytes(_fixture_bytes(label, kind))


def _fixture_catalog(
    *,
    cutoff: RunCutoff,
    source_id: str,
    source_record_id: str,
    issuer: str,
    document_type: str,
    document_number: str,
    title: str,
    issued_date: str,
    domain: str,
    gazette_published_date: str = "",
    observed_effective_date: str = "",
    gazette_issue: str = "",
    gazette_page: str = "",
    continuation_issues: list[str] | None = None,
    version: str = "1",
    relation_role: str = "signed_original",
    related_to_document_number: str = "",
    is_pre_2020_reference: bool = False,
    page_url: str = "",
    status: str = "CATALOGUED",
) -> dict[str, Any]:
    issued = parse_vn_date(issued_date)
    year = str(issued.year) if issued else "UNKNOWN"
    quarter = f"Q{((issued.month - 1) // 3) + 1}" if issued else "UNKNOWN"
    return {
        "source_id": source_id,
        "source_record_id": source_record_id,
        "partition_id": f"{source_id}__{year}",
        "data_origin": "SYNTHETIC_FIXTURE",
        "page_url": page_url or f"https://fixture.local/{source_id.lower()}/{source_record_id}.htm",
        "year": year,
        "quarter": quarter,
        "observed_at": cutoff.cutoff_utc,
        "gazette_issue": gazette_issue,
        "gazette_page": gazette_page,
        "continuation_issues": list(continuation_issues or []),
        "issuer": issuer,
        "document_type": document_type,
        "document_number": document_number,
        "title": title,
        "issued_date": issued_date,
        "gazette_published_date": gazette_published_date,
        "observed_effective_date": observed_effective_date,
        "version": version,
        "relation_role": relation_role,
        "related_to_document_number": related_to_document_number,
        "domain_candidate": domain,
        "rights_ref": "QA-FIXTURE-RIGHTS-v1",
        "status": status,
        "date_reconciliation_flag": "",
        "is_pre_2020_reference": is_pre_2020_reference,
        "eligible_for_pilot_denominator": False,
        "legal_status_verified": False,
        "error": "",
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
    }


def _fixture_artifact(
    *,
    cutoff: RunCutoff,
    source_id: str,
    source_record_id: str,
    parent_id: str,
    attachment_id: str,
    document_number: str,
    file_type: str,
    kind: str,
    label: str,
    relation_role: str,
    domain: str,
    year: str,
    file_url: str = "",
    version: str = "1",
    status: str = "STORED",
    quarantine_reason: str = "",
    sha256: str | None = None,
    size_bytes: int | None = None,
    declared_mime: str = "",
    detected_mime: str = "",
    error: str = "",
) -> dict[str, Any]:
    payload = _fixture_bytes(label, kind)
    mime_by_kind = {
        "pdf": "application/pdf",
        "scan": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "html": "text/html",
    }
    return {
        "source_id": source_id,
        "source_record_id": source_record_id,
        "partition_id": f"{source_id}__{year}",
        "data_origin": "SYNTHETIC_FIXTURE",
        "parent_id": parent_id,
        "attachment_id": attachment_id,
        "page_url": f"https://fixture.local/{source_id.lower()}/{parent_id}.htm",
        "file_url": file_url
        or f"https://fixture.local/{source_id.lower()}/files/{attachment_id}.{kind}",
        "year": year,
        "quarter": "UNKNOWN",
        "observed_at": cutoff.cutoff_utc,
        "gazette_issue": "",
        "gazette_page": "",
        "document_number": document_number,
        "version": version,
        "relation_role": relation_role,
        "file_type": file_type,
        "declared_mime": declared_mime or mime_by_kind.get(kind, "application/octet-stream"),
        "detected_mime": detected_mime or mime_by_kind.get(kind, "application/octet-stream"),
        "size_bytes": len(payload) if size_bytes is None else size_bytes,
        "sha256": sha256 or sha256_bytes(payload),
        "stored_blob_path": "",
        "rights_ref": "QA-FIXTURE-RIGHTS-v1",
        "status": status,
        "quarantine_reason": quarantine_reason,
        "error": error,
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
    }


def build_qa_fixture(cutoff: RunCutoff | None = None) -> dict[str, Any]:
    """Build deterministic synthetic inputs that exercise every reconciler rule."""
    cutoff = cutoff or RunCutoff(
        run_id=DEFAULT_RUN_ID,
        cutoff_utc="2026-11-26T12:58:39Z",
        cutoff_vn="2026-11-26T19:58:39+07:00",
    )
    s1 = "FIXTURE-SRC-01"
    s3 = "FIXTURE-SRC-03"
    catalog: list[dict[str, Any]] = []

    def cat(**kwargs: Any) -> None:
        catalog.append(_fixture_catalog(cutoff=cutoff, **kwargs))

    # SRC-01 side.
    cat(
        source_id=s1,
        source_record_id="src01-78-2025",
        issuer="CHÍNH PHỦ",
        document_type="Nghị định",
        document_number="78/2025/NĐ-CP",
        title="Nghị định quy định chi tiết thi hành Luật Tổ chức Chính phủ",
        issued_date="01/04/2025",
        gazette_published_date="03/04/2025",
        observed_effective_date="01/06/2025",
        gazette_issue="649+650",
        gazette_page="1-52",
        continuation_issues=[
            "https://fixture.local/fixture-src-01/issues/651-652.htm",
            "https://fixture.local/fixture-src-01/issues/653-654.htm",
        ],
        domain="ADM",
    )
    cat(
        source_id=s1,
        source_record_id="src01-99-2025",
        issuer="BỘ TÀI NGUYÊN VÀ MÔI TRƯỜNG",
        document_type="Thông tư",
        document_number="99/2025/TT-BTNMT",
        title="Thông tư quy định về bảo vệ môi trường",
        issued_date="15/07/2025",
        gazette_published_date="20/07/2025",
        observed_effective_date="01/09/2025",
        gazette_issue="700/2025",
        gazette_page="",
        domain="ENV",
    )
    cat(
        source_id=s1,
        source_record_id="src01-61-2025",
        issuer="THỦ TƯỚNG CHÍNH PHỦ",
        document_type="Quyết định",
        document_number="61/2025/QĐ-TTg",
        title="Quyết định về một số cơ chế đặc thù",
        issued_date="10/09/2025",
        gazette_published_date="05/09/2025",
        observed_effective_date="01/09/2025",
        gazette_issue="720/2025",
        gazette_page="1-6",
        domain="TRA",
    )
    cat(
        source_id=s1,
        source_record_id="src01-101-2025",
        issuer="THỦ TƯỚNG CHÍNH PHỦ",
        document_type="Quyết định",
        document_number="101/2025/QĐ-TTg",
        title="Quyết định về phân cấp quản lý đầu tư",
        issued_date="20/10/2025",
        gazette_published_date="22/10/2025",
        observed_effective_date="01/12/2025",
        gazette_issue="760/2025",
        gazette_page="5",
        domain="TRA",
    )
    cat(
        source_id=s1,
        source_record_id="src01-45-2019",
        issuer="QUỐC HỘI",
        document_type="Luật",
        document_number="45/2019/QH14",
        title="Bộ luật Lao động",
        issued_date="20/11/2019",
        gazette_published_date="25/11/2019",
        observed_effective_date="01/01/2021",
        gazette_issue="2019/2019",
        gazette_page="1-120",
        relation_role="pre_2020_reference",
        is_pre_2020_reference=True,
        domain="LAB",
    )
    cat(
        source_id=s1,
        source_record_id="src01-59-2020",
        issuer="QUỐC HỘI",
        document_type="Luật",
        document_number="59/2020/QH14",
        title="Luật Doanh nghiệp",
        issued_date="17/06/2020",
        gazette_published_date="25/06/2020",
        observed_effective_date="01/01/2021",
        gazette_issue="800/2020",
        gazette_page="1-30",
        domain="BUS",
    )
    cat(
        source_id=s1,
        source_record_id="src01-01-2020",
        issuer="QUỐC HỘI",
        document_type="Luật",
        document_number="01/2020/QH14",
        title="Luật sửa đổi một số điều của Luật Đầu tư",
        issued_date="20/05/2020",
        gazette_published_date="01/06/2020",
        observed_effective_date="01/01/2021",
        gazette_issue="700/2020",
        gazette_page="1-10",
        domain="CIV",
    )
    cat(
        source_id=s1,
        source_record_id="src01-90-2020",
        issuer="QUỐC HỘI",
        document_type="Luật",
        document_number="90/2020/QH14",
        title="Luật Cư trú",
        issued_date="10/11/2020",
        gazette_published_date="20/11/2020",
        observed_effective_date="01/07/2021",
        gazette_issue="950/2020",
        gazette_page="1-12",
        domain="LAB",
    )
    cat(
        source_id=s1,
        source_record_id="src01-88-2020",
        issuer="QUỐC HỘI",
        document_type="Luật",
        document_number="88/2020/QH14",
        title="Luật Hòa giải, đối thoại tại Tòa án",
        issued_date="01/07/2020",
        gazette_published_date="10/07/2020",
        observed_effective_date="01/01/2021",
        gazette_issue="820/2020",
        gazette_page="1-15",
        domain="CRI",
    )
    cat(
        source_id=s1,
        source_record_id="src01-15-2025",
        issuer="BỘ GIÁO DỤC VÀ ĐÀO TẠO",
        document_type="Thông tư",
        document_number="15/2025/TT-BGDĐT",
        title="Thông tư quy định về tuyển sinh đại học",
        issued_date="05/03/2025",
        gazette_published_date="15/03/2025",
        observed_effective_date="01/05/2025",
        gazette_issue="600/2025",
        gazette_page="10-20",
        domain="EDU",
    )
    cat(
        source_id=s1,
        source_record_id="src01-205-2025",
        issuer="BỘ Y TẾ",
        document_type="Thông tư",
        document_number="205/2025/TT-BYT",
        title="Thông tư quy định về khám bệnh, chữa bệnh",
        issued_date="",
        gazette_issue="",
        gazette_page="1",
        domain="EDU",
    )
    cat(
        source_id=s1,
        source_record_id="src01-999-2026",
        issuer="CHÍNH PHỦ",
        document_type="Nghị định",
        document_number="999/2026/NĐ-CP",
        title="Nghị định phát hành sau cutoff",
        issued_date="28/11/2026",
        gazette_published_date="28/11/2026",
        observed_effective_date="01/01/2027",
        gazette_issue="999/2026",
        gazette_page="1",
        domain="LND",
    )
    cat(
        source_id=s1,
        source_record_id="src01-413-2026",
        issuer="CHÍNH PHỦ",
        document_type="Nghị định",
        document_number="413/2026/NĐ-CP",
        title="Nghị định sửa đổi, bổ sung một số điều của Nghị định 104/2025/NĐ-CP",
        issued_date="16/11/2026",
        gazette_published_date="26/11/2026",
        observed_effective_date="16/11/2026",
        gazette_issue="588/2026",
        gazette_page="1-8",
        relation_role="amending",
        related_to_document_number="104/2025/NĐ-CP",
        domain="LND",
    )
    cat(
        source_id=s1,
        source_record_id="src01-31-2024",
        issuer="QUỐC HỘI",
        document_type="Luật",
        document_number="31/2024/QH15",
        title="Luật Đất đai",
        issued_date="18/01/2024",
        gazette_published_date="30/01/2024",
        observed_effective_date="01/08/2024",
        gazette_issue="100/2024",
        gazette_page="1-40",
        domain="LND",
    )
    cat(
        source_id=s1,
        source_record_id="src01-36-2024",
        issuer="QUỐC HỘI",
        document_type="Luật",
        document_number="36/2024/QH15",
        title="Luật Trật tự, an toàn giao thông đường bộ",
        issued_date="27/06/2024",
        gazette_published_date="10/07/2024",
        observed_effective_date="01/01/2025",
        gazette_issue="400/2024",
        gazette_page="1-25",
        domain="TRA",
    )

    # SRC-03 side (overlaps the same canonical families).
    cat(
        source_id=s3,
        source_record_id="docid-213310",
        issuer="Chính phủ",
        document_type="Nghị định",
        document_number="78/2025/NĐ-CP",
        title="Nghị định quy định chi tiết thi hành Luật Tổ chức Chính phủ",
        issued_date="01-04-2025",
        observed_effective_date="01/06/2025",
        gazette_page="",
        domain="ADM",
        page_url="https://fixture.local/fixture-src-03/docid-213310.htm",
    )
    cat(
        source_id=s3,
        source_record_id="docid-413-2026",
        issuer="Chính phủ",
        document_type="Nghị định",
        document_number="413/2026/NĐ-CP",
        title="Nghị định sửa đổi và bổ sung một số điều của Nghị định số 104/2025/NĐ-CP",
        issued_date="16-11-2026",
        gazette_published_date="26/11/2026",
        observed_effective_date="01/12/2026",
        gazette_issue="588/2026",
        gazette_page="1-8",
        relation_role="amending",
        related_to_document_number="104/2025/NĐ-CP",
        domain="LND",
        page_url="https://fixture.local/fixture-src-03/docid-413-2026.htm",
    )
    cat(
        source_id=s3,
        source_record_id="docid-116-2026",
        issuer="Bộ Nông nghiệp và Môi trường",
        document_type="Văn bản hợp nhất",
        document_number="116/VBHN-BNNMT",
        title="Văn bản hợp nhất Nghị định quy định chi tiết thi hành Luật Tổ chức Chính phủ",
        issued_date="20/11/2026",
        observed_effective_date="20/11/2026",
        gazette_issue="590/2026",
        gazette_page="1-15",
        relation_role="consolidated",
        related_to_document_number="78/2025/NĐ-CP",
        domain="ENV",
        page_url="https://fixture.local/fixture-src-03/docid-116-2026.htm",
    )
    cat(
        source_id=s3,
        source_record_id="docid-12-2025",
        issuer="Thủ tướng Chính phủ",
        document_type="Quyết định",
        document_number="12/QĐ-TTg-ĐC",
        title="Quyết định đính chính Nghị định 78/2025/NĐ-CP",
        issued_date="10/05/2025",
        observed_effective_date="10/05/2025",
        gazette_issue="670/2025",
        gazette_page="1",
        relation_role="corrigendum",
        related_to_document_number="78/2025/NĐ-CP",
        domain="ADM",
        page_url="https://fixture.local/fixture-src-03/docid-12-2025.htm",
    )
    cat(
        source_id=s3,
        source_record_id="docid-101-2025",
        issuer="BỘ TƯ PHÁP",
        document_type="Quyết định",
        document_number="101/2025/QĐ-TTg",
        title="Quyết định về phân cấp quản lý đầu tư",
        issued_date="20/10/2025",
        gazette_published_date="22/10/2025",
        observed_effective_date="01/12/2025",
        gazette_issue="760/2025",
        gazette_page="5",
        domain="CRI",
        page_url="https://fixture.local/fixture-src-03/docid-101-2025.htm",
    )
    cat(
        source_id=s3,
        source_record_id="docid-59-2020",
        issuer="Quốc hội",
        document_type="Luật",
        document_number="59/2020/QH14",
        title="Luật Doanh nghiệp",
        issued_date="17-06-2020",
        observed_effective_date="01/01/2021",
        gazette_issue="800/2020",
        gazette_page="1-30",
        domain="BUS",
        page_url="https://fixture.local/fixture-src-03/docid-59-2020.htm",
    )
    cat(
        source_id=s3,
        source_record_id="docid-31-2024",
        issuer="Quốc hội",
        document_type="Luật",
        document_number="31/2024/QH15",
        title="Luật Đất đai",
        issued_date="18-01-2024",
        observed_effective_date="01/08/2024",
        gazette_issue="100/2024",
        gazette_page="1-40",
        domain="LND",
        page_url="https://fixture.local/fixture-src-03/docid-31-2024.htm",
    )
    cat(
        source_id=s3,
        source_record_id="docid-36-2024",
        issuer="Quốc hội",
        document_type="Luật",
        document_number="36/2024/QH15",
        title="Luật Trật tự, an toàn giao thông đường bộ",
        issued_date="27-06-2024",
        observed_effective_date="01/01/2025",
        gazette_issue="400/2024",
        gazette_page="1-25",
        domain="TRA",
        page_url="https://fixture.local/fixture-src-03/docid-36-2024.htm",
    )
    cat(
        source_id=s3,
        source_record_id="docid-45-2019",
        issuer="Quốc hội",
        document_type="Luật",
        document_number="45/2019/QH14",
        title="Bộ luật Lao động",
        issued_date="20-11-2019",
        relation_role="pre_2020_reference",
        is_pre_2020_reference=True,
        domain="LAB",
        page_url="https://fixture.local/fixture-src-03/docid-45-2019.htm",
    )

    artifacts: list[dict[str, Any]] = []
    shared_sha = sha256_bytes(_SHARED_PDF)

    def art(**kwargs: Any) -> None:
        artifacts.append(_fixture_artifact(cutoff=cutoff, **kwargs))

    # SRC-01: shared signed original, three continuation PDFs+DOCs, quarantines, orphan, formats.
    art(
        source_id=s1,
        source_record_id="src01-78-2025:1",
        parent_id="src01-78-2025",
        attachment_id="a01-78-signed",
        document_number="78/2025/NĐ-CP",
        file_type="pdf_text",
        kind="pdf",
        label="SRC01-78-SIGNED",
        relation_role="signed_original",
        domain="ADM",
        year="2025",
        sha256=shared_sha,
        file_url="https://fixture.local/fixture-src-01/files/78-2025-nd-cp.signed.pdf",
    )
    for index in range(1, 4):
        art(
            source_id=s1,
            source_record_id=f"src01-78-2025:c{index}",
            parent_id="src01-78-2025",
            attachment_id=f"a01-78-cont-pdf-{index}",
            document_number="78/2025/NĐ-CP",
            file_type="pdf_text",
            kind="pdf",
            label=f"SRC01-78-CONT-PDF-{index}",
            relation_role="gazette_publication",
            domain="ADM",
            year="2025",
        )
    for index in range(1, 4):
        art(
            source_id=s1,
            source_record_id=f"src01-78-2025:d{index}",
            parent_id="src01-78-2025",
            attachment_id=f"a01-78-cont-doc-{index}",
            document_number="78/2025/NĐ-CP",
            file_type="doc",
            kind="doc",
            label=f"SRC01-78-CONT-DOC-{index}",
            relation_role="gazette_publication",
            domain="ADM",
            year="2025",
        )
    art(
        source_id=s1,
        source_record_id="src01-78-2025:q1",
        parent_id="src01-78-2025",
        attachment_id="a01-78-truncated",
        document_number="78/2025/NĐ-CP",
        file_type="pdf_text",
        kind="pdf",
        label="SRC01-78-TRUNCATED",
        relation_role="signed_original",
        domain="ADM",
        year="2025",
        status="QUARANTINED",
        quarantine_reason="TRUNCATED_OR_CORRUPT_PDF",
        sha256=sha256_bytes(b"%PDF-1.4\n%TRUNCATED-WITHOUT-EOF"),
        size_bytes=31,
    )
    art(
        source_id=s1,
        source_record_id="src01-99-2025:q1",
        parent_id="src01-99-2025",
        attachment_id="a01-99-mime-mismatch",
        document_number="99/2025/TT-BTNMT",
        file_type="pdf_text",
        kind="pdf",
        label="SRC01-99-MIME-MISMATCH",
        relation_role="signed_original",
        domain="ENV",
        year="2025",
        status="QUARANTINED",
        quarantine_reason="MIME_MISMATCH:declared=application/pdf,detected=text/plain",
        sha256=sha256_bytes(b"plain text, not a pdf"),
        size_bytes=20,
        declared_mime="application/pdf",
        detected_mime="text/plain",
    )
    art(
        source_id=s1,
        source_record_id="src01-orphan:1",
        parent_id="MISSING-PARENT-999",
        attachment_id="a01-orphan-appendix",
        document_number="78/2025/NĐ-CP",
        file_type="pdf_text",
        kind="pdf",
        label="SRC01-ORPHAN-APPENDIX",
        relation_role="appendix",
        domain="ADM",
        year="2025",
    )
    art(
        source_id=s1,
        source_record_id="src01-61-2025:1",
        parent_id="src01-61-2025",
        attachment_id="a01-61-scan",
        document_number="61/2025/QĐ-TTg",
        file_type="pdf_scan",
        kind="scan",
        label="SRC01-61-SCAN",
        relation_role="signed_original",
        domain="TRA",
        year="2025",
    )
    art(
        source_id=s1,
        source_record_id="src01-59-2020:1",
        parent_id="src01-59-2020",
        attachment_id="a01-59-signed",
        document_number="59/2020/QH14",
        file_type="pdf_text",
        kind="pdf",
        label="SRC01-59-SIGNED",
        relation_role="signed_original",
        domain="BUS",
        year="2020",
    )
    art(
        source_id=s1,
        source_record_id="src01-90-2020:1",
        parent_id="src01-90-2020",
        attachment_id="a01-90-docx",
        document_number="90/2020/QH14",
        file_type="docx",
        kind="docx",
        label="SRC01-90-DOCX",
        relation_role="signed_original",
        domain="LAB",
        year="2020",
    )
    art(
        source_id=s1,
        source_record_id="src01-15-2025:1",
        parent_id="src01-15-2025",
        attachment_id="a01-15-html",
        document_number="15/2025/TT-BGDĐT",
        file_type="html",
        kind="html",
        label="SRC01-15-HTML",
        relation_role="signed_original",
        domain="EDU",
        year="2025",
    )
    art(
        source_id=s1,
        source_record_id="src01-88-2020:1",
        parent_id="src01-88-2020",
        attachment_id="a01-88-xlsx",
        document_number="88/2020/QH14",
        file_type="xlsx",
        kind="xlsx",
        label="SRC01-88-XLSX",
        relation_role="appendix",
        domain="CRI",
        year="2020",
    )

    # SRC-03: same shared signed blob under a different URL, four appendices, distinct relations.
    art(
        source_id=s3,
        source_record_id="docid-213310:1",
        parent_id="docid-213310",
        attachment_id="a03-78-signed",
        document_number="78/2025/NĐ-CP",
        file_type="pdf_text",
        kind="pdf",
        label="SRC03-78-SIGNED",
        relation_role="signed_original",
        domain="ADM",
        year="2025",
        sha256=shared_sha,
        file_url="https://fixture.local/fixture-src-03/files/78ndcp-1.signed.pdf",
    )
    for index in range(1, 5):
        art(
            source_id=s3,
            source_record_id=f"docid-213310:pl{index}",
            parent_id="docid-213310",
            attachment_id=f"a03-78-pl{index}",
            document_number="78/2025/NĐ-CP",
            file_type="pdf_text",
            kind="pdf",
            label=f"SRC03-78-APPENDIX-{index}",
            relation_role="appendix",
            domain="ADM",
            year="2025",
        )
    art(
        source_id=s3,
        source_record_id="docid-413-2026:1",
        parent_id="docid-413-2026",
        attachment_id="a03-413-signed",
        document_number="413/2026/NĐ-CP",
        file_type="pdf_text",
        kind="pdf",
        label="SRC03-413-SIGNED",
        relation_role="amending",
        domain="LND",
        year="2026",
    )
    art(
        source_id=s3,
        source_record_id="docid-116-2026:1",
        parent_id="docid-116-2026",
        attachment_id="a03-116-consolidated",
        document_number="116/VBHN-BNNMT",
        file_type="pdf_text",
        kind="pdf",
        label="SRC03-116-CONSOLIDATED",
        relation_role="consolidated",
        domain="ENV",
        year="2026",
    )
    art(
        source_id=s3,
        source_record_id="docid-12-2025:1",
        parent_id="docid-12-2025",
        attachment_id="a03-12-corrigendum",
        document_number="12/QĐ-TTg-ĐC",
        file_type="docx",
        kind="docx",
        label="SRC03-12-CORRIGENDUM",
        relation_role="corrigendum",
        domain="ADM",
        year="2025",
    )
    art(
        source_id=s3,
        source_record_id="docid-31-2024:1",
        parent_id="docid-31-2024",
        attachment_id="a03-31-xlsx",
        document_number="31/2024/QH15",
        file_type="xlsx",
        kind="xlsx",
        label="SRC03-31-XLSX",
        relation_role="appendix",
        domain="LND",
        year="2024",
    )
    art(
        source_id=s3,
        source_record_id="docid-31-2024:2",
        parent_id="docid-31-2024",
        attachment_id="a03-31-signed",
        document_number="31/2024/QH15",
        file_type="pdf_text",
        kind="pdf",
        label="SRC03-31-SIGNED",
        relation_role="signed_original",
        domain="LND",
        year="2024",
    )
    art(
        source_id=s3,
        source_record_id="docid-36-2024:1",
        parent_id="docid-36-2024",
        attachment_id="a03-36-html",
        document_number="36/2024/QH15",
        file_type="html",
        kind="html",
        label="SRC03-36-HTML",
        relation_role="signed_original",
        domain="TRA",
        year="2024",
    )
    art(
        source_id=s3,
        source_record_id="docid-36-2024:2",
        parent_id="docid-36-2024",
        attachment_id="a03-36-scan",
        document_number="36/2024/QH15",
        file_type="pdf_scan",
        kind="scan",
        label="SRC03-36-SCAN",
        relation_role="signed_original",
        domain="TRA",
        year="2024",
    )
    art(
        source_id=s3,
        source_record_id="docid-59-2020:1",
        parent_id="docid-59-2020",
        attachment_id="a03-59-signed",
        document_number="59/2020/QH14",
        file_type="pdf_text",
        kind="pdf",
        label="SRC03-59-SIGNED",
        relation_role="signed_original",
        domain="BUS",
        year="2020",
    )

    rights_matrix: list[dict[str, Any]] = []
    for source_id, status, origin, rights_ref in (
        ("SRC-01", "PENDING_RIGHTS", "REAL", "g1-rights-pending-v1"),
        ("SRC-03", "PENDING_RIGHTS", "REAL", "g1-rights-pending-v1"),
        (s1, "APPROVED", "SYNTHETIC_FIXTURE", "QA-FIXTURE-RIGHTS-v1"),
        (s3, "APPROVED", "SYNTHETIC_FIXTURE", "QA-FIXTURE-RIGHTS-v1"),
    ):
        for action in sorted(ACTIONS):
            rights_matrix.append(
                {
                    "source_id": source_id,
                    "action": action,
                    "status": status,
                    "rights_ref": rights_ref,
                    "registry_revision": (
                        "g1-rights-pending-v1" if origin == "REAL" else "qa-fixture-v1"
                    ),
                    "data_origin": origin,
                }
            )

    partition_ledger: list[dict[str, Any]] = []
    for source_id in ("SRC-01", "SRC-03"):
        for year in range(2020, 2027):
            partition_ledger.append(
                {
                    "source_id": source_id,
                    "partition_id": f"{source_id}__{year}",
                    "status": "BLOCKED_RIGHTS",
                    "rights_status": "PENDING_RIGHTS",
                    "rights_ref": "g1-rights-pending-v1",
                    "owner_worker": (
                        "worker-src01" if source_id == "SRC-01" else "worker-src03"
                    ),
                    "requests_attempted": 0,
                    "records_observed": 0,
                    "records_eligible": 0,
                    "artifacts_downloaded": 0,
                    "blobs_written": 0,
                    "quarantined": 0,
                    "errors": 0,
                    "catalog_enumeration_complete": False,
                    "notes": "fail-closed before any fetch",
                }
            )
    partitions: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in catalog:
        partitions[(row["source_id"], row["partition_id"])].append(row["source_record_id"])
    for (source_id, partition_id), record_ids in sorted(partitions.items()):
        part_arts = [row for row in artifacts if row["partition_id"] == partition_id]
        part_stored_blobs = len({row["sha256"] for row in part_arts if row["status"] == "STORED"})
        partition_ledger.append(
            {
                "source_id": source_id,
                "partition_id": partition_id,
                "status": "COMPLETED",
                "rights_status": "APPROVED",
                "rights_ref": "QA-FIXTURE-RIGHTS-v1",
                "owner_worker": "worker-qa",
                "requests_attempted": 0,
                "records_observed": len(record_ids),
                "records_eligible": len(record_ids),
                "artifacts_downloaded": len(part_arts),
                "blobs_written": part_stored_blobs,
                "quarantined": len(
                    [row for row in part_arts if row["status"] == "QUARANTINED"]
                ),
                "errors": 0,
                "catalog_enumeration_complete": False,
                "notes": "synthetic QA fixture only",
            }
        )
    return {
        "run_id": cutoff.run_id,
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
        "catalog_records": catalog,
        "artifact_records": artifacts,
        "rights_matrix": _flatten_rights_matrix(rights_matrix),
        "partition_ledger": _normalize_ledger(partition_ledger),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        return _read_jsonl(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = (
            data.get("rows")
            or data.get("rights_matrix")
            or data.get("rights-matrix")
            or data.get("matrix")
            or data.get("records")
        )
        if rows is None and data.get("sources") and isinstance(data["sources"], dict):
            rows = [
                {"source_id": source_id, "actions": source.get("actions", {})}
                for source_id, source in sorted(data["sources"].items())
            ]
        if rows is None:
            raise ValueError(f"no row list found in {path}")
    else:
        raise ValueError(f"expected a list or object in {path}")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"expected object rows in {path}")
    return rows


def _discover_files(directories: Iterable[Path], name: str) -> list[Path]:
    found: set[Path] = set()
    for directory in directories:
        if directory.is_file():
            if directory.name == name:
                found.add(directory.resolve())
            continue
        for path in directory.rglob(name):
            if path.is_file():
                found.add(path.resolve())
    return sorted(found)


def _load_registry_rights(path: Path) -> list[dict[str, Any]]:
    registry = SourceRegistry(path)  # validates fail-closed registry structure
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for source_id, source in sorted(payload.get("sources", {}).items()):
        declared_actions = source.get("actions", {})
        all_actions = sorted(set(ACTIONS) | set(declared_actions.keys()))
        for action in all_actions:
            policy = declared_actions.get(action, {"status": "PENDING_RIGHTS"})
            status = policy.get("status", "PENDING_RIGHTS") if isinstance(policy, dict) else str(policy)
            evidence_ref = policy.get("evidence_ref", "") if isinstance(policy, dict) else ""
            rights_ref = (
                f"{registry.revision}:{evidence_ref}"
                if evidence_ref
                else f"BLOCKED_RIGHTS:{registry.revision}:{status}"
            )
            rows.append(
                {
                    "source_id": source_id,
                    "action": action,
                    "status": status,
                    "rights_ref": rights_ref,
                    "approved_at": policy.get("approved_at", "") if isinstance(policy, dict) else "",
                    "expires_at": policy.get("expires_at", "") if isinstance(policy, dict) else "",
                    "policy_url": policy.get("policy_url", "") if isinstance(policy, dict) else "",
                    "evidence_ref": evidence_ref,
                    "registry_revision": registry.revision,
                    "data_origin": "REAL",
                }
            )
    return rows


def _derive_ledger_from_manifests(directories: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in _discover_files(directories, "partition-manifest.json"):
        raw_bytes = path.read_bytes()
        payload = json.loads(raw_bytes.decode("utf-8"))
        if not isinstance(payload, dict):
            continue
        source_id = _s(payload.get("source_id"))
        partition_id = _s(payload.get("partition_id"))
        if not source_id or not partition_id:
            continue
        counts = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
        network = payload.get("network") if isinstance(payload.get("network"), dict) else {}
        files_map = payload.get("files") if isinstance(payload.get("files"), dict) else {}
        outputs_map = payload.get("outputs") if isinstance(payload.get("outputs"), dict) else {}
        checkpoint_path = path.parent / "checkpoint.json"
        checkpoint_data = (
            json.loads(checkpoint_path.read_text(encoding="utf-8"))
            if checkpoint_path.exists()
            else {}
        )
        rights_ref = _s(payload.get("rights_ref")) or _s(checkpoint_data.get("rights_ref"))
        if not rights_ref and isinstance(payload.get("blocked_actions"), dict):
            rights_ref = ";".join(
                f"{act}={val}" for act, val in sorted(payload["blocked_actions"].items())
            )
        owner_worker = _s(payload.get("owner_worker")) or _s(checkpoint_data.get("owner_worker"))
        if not owner_worker:
            owner_worker = "worker-src01" if "SRC-01" in source_id else ("worker-src03" if "SRC-03" in source_id else "")
        requests_attempted = network.get("requests_attempted", payload.get("fetch_attempts", 0))
        blobs_written = counts.get(
            "blobs_unique",
            counts.get(
                "unique_blobs",
                counts.get("stored_blobs", counts.get("artifacts_stored", 0)),
            ),
        )
        row = {
            "source_id": source_id,
            "partition_id": partition_id,
            "status": canonical_partition_status(_s(payload.get("status"))),
            "rights_status": _s(payload.get("rights_status")),
            "rights_ref": rights_ref,
            "owner_worker": owner_worker,
            "requests_attempted": int(requests_attempted) if isinstance(requests_attempted, int) and not isinstance(requests_attempted, bool) else 0,
            "records_observed": counts.get("records_observed", counts.get("documents_observed", 0)),
            "records_eligible": counts.get("records_eligible", counts.get("eligible_for_pilot_denominator", 0)),
            "artifacts_downloaded": counts.get("artifacts_total", 0),
            "blobs_written": int(blobs_written) if isinstance(blobs_written, int) and not isinstance(blobs_written, bool) else 0,
            "quarantined": counts.get("artifacts_quarantined", counts.get("quarantined_artifacts", 0)),
            "errors": counts.get("errors", 0),
            "catalog_enumeration_complete": bool(payload.get("catalog_enumeration_complete", False)),
            "checkpoint_sha256": _s(files_map.get("checkpoint.json") or outputs_map.get("checkpoint.json")),
            "manifest_sha256": sha256_bytes(raw_bytes),
            "updated_at": _s(checkpoint_data.get("updated_at")) or _s(payload.get("observed_at")),
            "notes": _s(payload.get("data_origin")),
        }
        rows.append(row)
    return rows


def _load_merge_inputs(
    staging_dirs: list[Path],
    *,
    rights_matrix_path: Path | None,
    partition_ledger_path: Path | None,
    source_rights_path: Path | None,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    catalog_paths = _discover_files(staging_dirs, "catalog.jsonl")
    artifact_paths = _discover_files(staging_dirs, "artifacts.jsonl")
    if not catalog_paths:
        raise ValueError("no catalog.jsonl found in the supplied staging directories")
    catalog_records: list[dict[str, Any]] = []
    artifact_records: list[dict[str, Any]] = []
    for path in catalog_paths:
        catalog_records.extend(_read_jsonl(path))
    for path in artifact_paths:
        artifact_records.extend(_read_jsonl(path))

    rights_rows: list[dict[str, Any]] = []
    if source_rights_path is not None:
        rights_rows.extend(_load_registry_rights(source_rights_path))
    if rights_matrix_path is not None:
        rights_rows.extend(_load_rows(rights_matrix_path))
    for filename in ("rights-matrix.jsonl", "rights-matrix.json", "rights_matrix.jsonl", "rights_matrix.json"):
        for path in _discover_files(staging_dirs, filename):
            rights_rows.extend(_load_rows(path))

    ledger_rows: list[dict[str, Any]] = []
    if partition_ledger_path is not None:
        ledger_rows.extend(_load_rows(partition_ledger_path))
    for filename in ("partition-ledger.jsonl", "partition-ledger.json", "partition_ledger.jsonl", "partition_ledger.json"):
        for path in _discover_files(staging_dirs, filename):
            ledger_rows.extend(_load_rows(path))
    if not ledger_rows:
        ledger_rows.extend(_derive_ledger_from_manifests(staging_dirs))
    return catalog_records, artifact_records, rights_rows, ledger_rows


def _write_json_file(path: Path, payload: dict[str, Any]) -> str:
    return atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )


def _run_qa_fixture(qa_dir: Path, cutoff: RunCutoff) -> dict[str, Any]:
    qa_dir.mkdir(parents=True, exist_ok=True)
    inputs = build_qa_fixture(cutoff)
    inputs_text = (
        json.dumps(inputs, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )
    inputs_digest = atomic_write_text(qa_dir / "qa-fixture-inputs.json", inputs_text)
    verification = verify_reconciliation_invariants(
        inputs["catalog_records"],
        inputs["artifact_records"],
        cutoff,
        inputs["rights_matrix"],
        inputs["partition_ledger"],
        run_a_dir=qa_dir / "replay-a",
        run_b_dir=qa_dir / "replay-b",
    )
    manifest = {
        "run_id": cutoff.run_id,
        "role": "worker-qa",
        "plan": "worker-qa-plan.md",
        "status": verification["status"],
        "passed": verification["passed"],
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
        "qa_fixture_dir": str(qa_dir),
        "qa_fixture_inputs_sha256": inputs_digest,
        "bundle_sha256": verification["bundle_sha256"],
        "digests": verification["file_sha256"],
        "deterministic": all(
            check["passed"]
            for check in verification["checks"]
            if check["name"] == "deterministic_output_digests"
        ),
        "replay": {
            "directories": ["replay-a", "replay-b"],
            "deterministic": all(
                check["passed"]
                for check in verification["checks"]
                if check["name"] == "deterministic_output_digests"
            ),
            "file_sha256": verification["file_sha256"],
            "jsonl_sha256": verification["jsonl_sha256"],
            "csv_sha256": verification["csv_sha256"],
            "bundle_sha256": verification["bundle_sha256"],
        },
        "checks": verification["checks"],
        "invariants": {
            check["name"]: check["passed"] for check in verification["checks"]
        },
        "counts": verification["counts"],
        "denominators": verification["denominators"],
        "g1_d02": {
            "targets": verification["targets"],
            "selected": verification["selected"],
            "shortfalls": verification["shortfalls"],
        },
        "real_source_denominators": verification["denominators"]["real"]["measurement_status"],
        "normalized_bytes_or_NOT_RUN": "NOT_RUN",
        "legal_status_verified": False,
        "portal_effective_date_unverified": True,
    }
    _write_json_file(qa_dir / "worker-manifest.json", manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m luatvn_ai_data_ingestion.pilot_reconciler",
        description="Cross-source reconciliation, blob dedup, G1-D02 sampling, and QA replay.",
    )
    parser.add_argument("--qa-fixture-dir", type=Path, help="run the self-contained QA fixture here")
    parser.add_argument(
        "--merge-staging-dirs",
        nargs="+",
        type=Path,
        help="staging directories to merge (recursively reads catalog.jsonl/artifacts.jsonl)",
    )
    parser.add_argument("--output-dir", type=Path, help="bundle output directory for merge mode")
    parser.add_argument("--cutoff-vn", required=True, help="locked cutoff in Asia/Ho_Chi_Minh")
    parser.add_argument("--cutoff-utc", required=True, help="locked cutoff in UTC")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--rights-matrix", type=Path, help="extra rights matrix JSON/JSONL")
    parser.add_argument("--partition-ledger", type=Path, help="extra partition ledger JSON/JSONL")
    parser.add_argument(
        "--source-rights",
        type=Path,
        help="source-rights registry JSON used to derive the rights matrix",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cutoff = RunCutoff(
        run_id=args.run_id,
        cutoff_utc=args.cutoff_utc,
        cutoff_vn=args.cutoff_vn,
    )
    if args.qa_fixture_dir and args.merge_staging_dirs:
        parser.error("--qa-fixture-dir and --merge-staging-dirs are mutually exclusive")
    try:
        if args.qa_fixture_dir:
            manifest = _run_qa_fixture(args.qa_fixture_dir, cutoff)
            print(
                json.dumps(
                    {
                        "status": manifest["status"],
                        "worker_manifest": str(args.qa_fixture_dir / "worker-manifest.json"),
                        "bundle_sha256": manifest["replay"]["bundle_sha256"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0 if manifest["passed"] else 1
        if args.merge_staging_dirs:
            if args.output_dir is None:
                parser.error("--output-dir is required with --merge-staging-dirs")
            catalog, artifacts, rights, ledger = _load_merge_inputs(
                args.merge_staging_dirs,
                rights_matrix_path=args.rights_matrix,
                partition_ledger_path=args.partition_ledger,
                source_rights_path=args.source_rights,
            )
            reconciliation = reconcile_pilot_data(catalog, artifacts, cutoff, rights, ledger)
            bundle = write_reconciliation_bundle(reconciliation, args.output_dir)
            print(
                json.dumps(
                    {
                        "status": "OK",
                        "output_dir": bundle["output_dir"],
                        "bundle_sha256": bundle["bundle_sha256"],
                        "families": len(reconciliation["document_families"]),
                        "versions": len(reconciliation["document_versions"]),
                        "unique_blobs": len(reconciliation["artifacts"]),
                        "conflicts": len(reconciliation["conflicts"]),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0
        parser.error("choose --qa-fixture-dir or --merge-staging-dirs")
    except Exception as error:  # fail closed with a concise message
        print(f"pilot_reconciler: error: {error}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
