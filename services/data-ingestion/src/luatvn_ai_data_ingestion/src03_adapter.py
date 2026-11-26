"""SRC-03 (Hệ thống văn bản Chính phủ) adapter, rights-gated staging, and synthetic pilot.

Real SRC-03 partitions are PENDING_RIGHTS and must fail closed before any network access.
The full parse -> fetch -> quarantine -> checkpoint pipeline is exercised only on the
deterministic synthetic fixtures built by ``build_src03_synthetic_fixtures``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

from .pilot_schema import (
    ARTIFACT_RECORD_FIELDS,
    CATALOG_RECORD_FIELDS,
    HttpTransportResponse,
    NetworkPolicyStop,
    PartitionCheckpoint,
    RunCutoff,
    SharedRateLimiter,
    atomic_write_bytes,
    atomic_write_text,
    authorize_actions,
    build_authorized_https_fetcher,
    canonical_partition_status,
    check_source_actions,
    classify_http_stop,
    evaluate_date_window,
    load_checkpoint,
    normalize_document_number,
    normalize_text_nfc,
    parse_vn_date,
    resolve_safe_local_path,
    save_checkpoint,
    sha256_bytes,
    validate_blob_integrity,
    write_csv_atomic,
    write_jsonl_atomic,
)
from .source_rights import RightsDenied, SourceRegistry, authorization_clock

RUN_ID = "G1-PILOT-SRC01-SRC03-20261126-01"
OWNER_WORKER = "worker-src03"
SRC03_SOURCE_ID = "SRC-03"
SRC03_PORTAL_URL = "https://vanban.chinhphu.vn/"
SRC03_FILE_HOST = "datafiles.chinhphu.vn"
FIXTURE_SOURCE_ID = "FIXTURE-SRC-03"
FIXTURE_BASE_URL = "https://fixture-src03.test/"
SHARED_SYNTHETIC_PDF = b"%PDF-1.4\n%SYNTH-SHARED-78-2025-ND-CP-V1\n%%EOF\n"
DEFAULT_OBSERVED_AT = "2026-11-26T19:58:39+07:00"
WINDOW_START = date(2020, 1, 1)

MIME_BY_EXTENSION = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "html": "text/html",
    "htm": "text/html",
}

SIGNED_ROLES = frozenset({"signed_original", "consolidated", "corrigendum", "amending"})

METADATA_LABELS = {
    "document_number": ("số ký hiệu",),
    "issued_date": ("ngày ban hành",),
    "observed_effective_date": ("ngày có hiệu lực", "ngày hiệu lực"),
    "document_type": ("loại văn bản",),
    "issuer": ("cơ quan ban hành",),
    "title": ("trích yếu",),
}


# --------------------------------------------------------------------------------------
# Parsed page model
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Src03AttachmentLink:
    file_url: str
    file_name: str
    file_type: str
    declared_mime: str
    relation_role: str
    parent_id: str
    attachment_id: str


@dataclass(frozen=True)
class Src03DocumentPage:
    source_record_id: str
    page_url: str
    document_number: str
    document_type: str
    issuer: str
    issued_date: str
    observed_effective_date: str
    title: str
    relation_role: str
    related_to_document_number: str
    attachments: tuple[Src03AttachmentLink, ...]


@dataclass(frozen=True)
class FetchResult:
    """Result of a pluggable fetch. Synthetic fixtures return these directly."""

    url: str = ""
    status_code: int | None = 200
    body: bytes = b""
    headers: Mapping[str, str] = field(default_factory=dict)
    declared_mime: str = ""
    expected_sha256: str = ""
    body_snippet: str = ""
    tls_error: str = ""
    final_url: str = ""
    redirect_urls: tuple[str, ...] = ()


@dataclass(frozen=True)
class PartitionRecordSpec:
    page_url: str
    source_record_id: str = ""
    domain_candidate: str = "UNMAPPED"
    issued_date_hint: str = ""
    expected_html_sha256: str = ""


def file_name_from_url(url: str) -> str:
    return unquote(urlsplit(url).path).rsplit("/", 1)[-1]


def file_type_from_name(file_name: str) -> str:
    name = file_name.casefold()
    return name.rsplit(".", 1)[-1] if "." in name else ""


def declared_mime_for_name(file_name: str) -> str:
    return MIME_BY_EXTENSION.get(file_type_from_name(file_name), "")


def docid_from_url(url: str) -> str:
    query = parse_qs(urlsplit(url).query)
    for key in ("docid", "DocID", "docId"):
        for value in query.get(key, ()):
            if value.isdigit():
                return value
    return ""


def _clean(value: str | None) -> str:
    return normalize_text_nfc(value)


def _normalized_casefold(value: str | None) -> str:
    return normalize_text_nfc(value).casefold()


def _is_appendix_file(file_name: str, link_text: str) -> bool:
    name = _normalized_casefold(file_name)
    if "phụ lục" in _normalized_casefold(link_text):
        return True
    if "-kem" in name or "phu-luc" in name:
        return True
    return re.search(r"(?:^|[-_])pl(?:\d+|[-_.]|$)", name) is not None


def extract_related_document_number(text: str, *, exclude_document_number: str = "") -> str:
    """Return the first referenced act number that is not the act itself."""
    excluded = normalize_document_number(exclude_document_number)
    pattern = re.compile(
        r"(?:Nghị định|Thông tư|Quyết định|Luật|Pháp lệnh|Nghị quyết|Bộ luật)\s+số\s+"
        r"(\d{1,4}/\d{4}/[A-Za-zĐđ][A-Za-zĐđ0-9\-]*)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text or ""):
        candidate = _clean(match.group(1))
        if normalize_document_number(candidate) != excluded:
            return candidate
    return ""


def classify_document_relation_role(
    document_number: str,
    document_type: str,
    title: str,
    *,
    issued_date: str = "",
) -> str:
    number = normalize_document_number(document_number)
    text = _normalized_casefold(f"{document_type} {title}")
    if "VBHN" in number or "văn bản hợp nhất" in text:
        return "consolidated"
    if number.endswith("-DC") or "đính chính" in text or "dinh-chinh" in text:
        return "corrigendum"
    if "sửa đổi, bổ sung" in text or "sua-doi" in text:
        return "amending"
    issued = parse_vn_date(issued_date)
    if issued is not None and issued < WINDOW_START:
        return "pre_2020_reference"
    return "catalog_entry"


def classify_attachment_relation_role(
    file_name: str,
    link_text: str = "",
    *,
    document_number: str = "",
    document_type: str = "",
    title: str = "",
    issued_date: str = "",
) -> str:
    """Classify one attachment without collapsing signed, consolidated, appendix, corrigendum."""
    if _is_appendix_file(file_name, link_text):
        return "appendix"
    name = _normalized_casefold(file_name)
    if "vbhn" in name:
        return "consolidated"
    if "dinh-chinh" in name or "đính-chính" in name or "đính chính" in _normalized_casefold(link_text):
        return "corrigendum"
    document_role = classify_document_relation_role(
        document_number, document_type, title, issued_date=issued_date
    )
    if document_role in ("consolidated", "corrigendum", "amending"):
        return document_role
    return "signed_original"


class _Src03HtmlCollector(HTMLParser):
    """Small tolerant collector for table rows, links, and headings (stdlib only)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.links: list[dict[str, str]] = []
        self.text_parts: list[str] = []
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None
        self._link: dict[str, str] | None = None
        self._link_text: list[str] = []
        self._in_title = False
        self._in_h1 = 0
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag in ("script", "style"):
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = True
            self.title_parts = []
        elif tag == "h1":
            self._in_h1 += 1
            self.h1_parts = []
        elif tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell_parts = []
        elif tag == "a":
            self._link = {"href": attributes.get("href", "")}
            self._link_text = []
        elif tag == "br":
            self.text_parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = max(0, self._in_h1 - 1)
        elif tag in ("td", "th") and self._row is not None and self._cell_parts is not None:
            self._row.append(_clean("".join(self._cell_parts)))
            self._cell_parts = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None
        elif tag == "a" and self._link is not None:
            self._link["text"] = _clean("".join(self._link_text))
            self.links.append(self._link)
            self._link = None
            self._link_text = []
        if tag in ("div", "p", "li", "tr", "table", "h1", "h2", "h3", "section", "ul"):
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self.text_parts.append(data)
        if self._in_title:
            self.title_parts.append(data)
        if self._in_h1:
            self.h1_parts.append(data)
        if self._cell_parts is not None:
            self._cell_parts.append(data)
        if self._link is not None:
            self._link_text.append(data)


def _row_value(rows: Iterable[list[str]], labels: tuple[str, ...]) -> str:
    wanted = {normalize_text_nfc(label).casefold() for label in labels}
    for row in rows:
        cells = [_clean(cell) for cell in row]
        for index, cell in enumerate(cells[:-1]):
            if cell.casefold().rstrip(": ").strip() in wanted:
                for candidate in cells[index + 1 :]:
                    if candidate:
                        return candidate
                break
    return ""


def _text_label_value(
    text: str, labels: tuple[str, ...], value_pattern: str, *, compact: bool = True
) -> str:
    for label in labels:
        match = re.search(
            rf"{re.escape(label)}\s*[:\-]?\s*({value_pattern})",
            text,
            re.IGNORECASE,
        )
        if match:
            value = _clean(match.group(1))
            return re.sub(r"\s+", "", value) if compact else value
    return ""


def _page_title(collector: _Src03HtmlCollector) -> str:
    title = _clean("".join(collector.h1_parts)) or _clean("".join(collector.title_parts))
    if ":" in title:
        prefix, rest = title.split(":", 1)
        if rest.strip() and re.search(r"(số\s+\S+|của\s+)", prefix, re.IGNORECASE):
            title = _clean(rest)
    return title


def parse_src03_document_html(html: str, page_url: str) -> Src03DocumentPage:
    """Parse a Hệ thống văn bản Chính phủ document page into catalog + attachment links.

    Table rows are authoritative. A text-label fallback covers minor DOM variants;
    shortcut: no archived live DOM is available while rights are pending, so extend the
    fallback once an approved HTML snapshot exists.
    """
    collector = _Src03HtmlCollector()
    collector.feed(html)
    collector.close()

    text = "".join(collector.text_parts)
    source_record_id = docid_from_url(page_url)
    if not source_record_id:
        hidden = re.search(r"""name=["']docid["'][^>]*value=["'](\d+)["']""", html, re.IGNORECASE)
        source_record_id = hidden.group(1) if hidden else ""

    document_number = _row_value(collector.rows, METADATA_LABELS["document_number"])
    if not document_number:
        document_number = _text_label_value(
            text, METADATA_LABELS["document_number"], r"\d{1,4}\s*/\s*\d{4}\s*/\s*[A-Za-zĐđ0-9\-]+"
        )
    issued_date = _row_value(collector.rows, METADATA_LABELS["issued_date"])
    if not issued_date:
        issued_date = _text_label_value(
            text, METADATA_LABELS["issued_date"], r"\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{4}"
        )
    effective_date = _row_value(collector.rows, METADATA_LABELS["observed_effective_date"])
    if not effective_date:
        effective_date = _text_label_value(
            text,
            METADATA_LABELS["observed_effective_date"],
            r"\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{4}",
        )
    document_type = _row_value(collector.rows, METADATA_LABELS["document_type"])
    if not document_type:
        document_type = _text_label_value(
            text, METADATA_LABELS["document_type"], r"[^\n]{1,80}", compact=False
        )
    issuer = _row_value(collector.rows, METADATA_LABELS["issuer"])
    if not issuer:
        issuer = _text_label_value(
            text, METADATA_LABELS["issuer"], r"[^\n]{1,120}", compact=False
        )
    title = _row_value(collector.rows, METADATA_LABELS["title"]) or _page_title(collector)

    relation_role = classify_document_relation_role(
        document_number, document_type, title, issued_date=issued_date
    )
    related_number = extract_related_document_number(
        title, exclude_document_number=document_number
    )

    attachments: list[Src03AttachmentLink] = []
    seen_urls: set[str] = set()
    for link in collector.links:
        href = _clean(link.get("href", ""))
        if not href.startswith("https://"):
            continue
        split = urlsplit(href)
        if (split.hostname or "").casefold() != SRC03_FILE_HOST:
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)
        file_name = file_name_from_url(href)
        attachment_role = classify_attachment_relation_role(
            file_name,
            link.get("text", ""),
            document_number=document_number,
            document_type=document_type,
            title=title,
            issued_date=issued_date,
        )
        attachment_id = "att_" + hashlib.sha256(
            f"{source_record_id or page_url}|{href}".encode("utf-8")
        ).hexdigest()[:16]
        attachments.append(
            Src03AttachmentLink(
                file_url=href,
                file_name=file_name,
                file_type=file_type_from_name(file_name),
                declared_mime=declared_mime_for_name(file_name),
                relation_role=attachment_role,
                parent_id=source_record_id,
                attachment_id=attachment_id,
            )
        )

    return Src03DocumentPage(
        source_record_id=source_record_id,
        page_url=page_url,
        document_number=document_number,
        document_type=document_type,
        issuer=issuer,
        issued_date=issued_date,
        observed_effective_date=effective_date,
        title=title,
        relation_role=relation_role,
        related_to_document_number=related_number,
        attachments=tuple(attachments),
    )


def parse_src03_listing_html(html: str, *, base_url: str = SRC03_PORTAL_URL) -> dict[str, Any]:
    """Parse a vanban.chinhphu.vn listing page into document specs and optional next_page_url."""
    collector = _Src03HtmlCollector()
    collector.feed(html)
    collector.close()
    document_urls: list[str] = []
    seen_docs: set[str] = set()
    next_page_url = ""
    for link in collector.links:
        raw_href = _clean(link.get("href", ""))
        if not raw_href or raw_href.casefold().startswith("javascript:"):
            continue
        href = urljoin(base_url, raw_href)
        split = urlsplit(href)
        host = (split.hostname or "").casefold()
        if host != "vanban.chinhphu.vn":
            continue
        text_low = _normalized_casefold(link.get("text", ""))
        if not next_page_url and text_low in {"tiếp", "trang sau", "next", ">"}:
            next_page_url = href
            continue
        if docid_from_url(href):
            if href not in seen_docs:
                seen_docs.add(href)
                document_urls.append(href)
    return {"document_urls": document_urls, "next_page_url": next_page_url}


# --------------------------------------------------------------------------------------
# Network policy gate
# --------------------------------------------------------------------------------------


class _NetworkControl:
    """Per-operation rights, rate-limit, redirect, and stop-policy gate around a fetcher."""

    def __init__(
        self,
        fetcher: Callable[[str], Any],
        limiter: SharedRateLimiter,
        *,
        registry: SourceRegistry,
        source_id: str,
        access_action: str = "automated_access",
        purpose: str = "g1-pilot",
        data_class: str = "public",
        region: str = "VN",
        document_type: str = "regulation",
        authorization_time_fn: Callable[[], datetime],
        infra_group: str = "chinhphu.vn",
        allow_network: bool = True,
        sleep_func: Callable[[float], None] | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._limiter = limiter
        self._registry = registry
        self._source_id = source_id
        self._access_action = access_action
        self._purpose = purpose
        self._data_class = data_class
        self._region = region
        self._document_type = document_type
        self._authorization_time_fn = authorization_time_fn
        self._infra_group = infra_group
        self._allow_network = allow_network
        self._sleep_func = sleep_func
        self.requests_attempted = 0

    def authorize(
        self,
        *,
        actions: Iterable[str],
        url: str,
        document_date: date,
        size_bytes: int,
        redirect_urls: Iterable[str] = (),
        final_url: str = "",
    ) -> dict[str, Any]:
        return authorize_actions(
            self._registry,
            source_id=self._source_id,
            actions=actions,
            purpose=self._purpose,
            data_class=self._data_class,
            region=self._region,
            document_type=self._document_type,
            url=url,
            document_date=document_date,
            size_bytes=size_bytes,
            at=self._authorization_time_fn(),
            redirect_urls=redirect_urls,
            final_url=final_url,
        )

    def fetch(self, url: str, *, document_date: date) -> FetchResult:
        retries_used = 0
        while True:
            auths = self.authorize(
                actions=(self._access_action,),
                url=url,
                document_date=document_date,
                size_bytes=0,
            )
            if self._allow_network:
                self._limiter.acquire(
                    self._source_id,
                    self._infra_group,
                    per_source_limit=auths[self._access_action].max_actions_per_minute,
                )
                self.requests_attempted += 1
            raw_result = self._fetcher(url)
            if isinstance(raw_result, HttpTransportResponse):
                result = FetchResult(
                    url=raw_result.url or url,
                    status_code=raw_result.status_code,
                    body=raw_result.body,
                    headers=raw_result.headers,
                    tls_error=raw_result.tls_error or "",
                    final_url=raw_result.final_url or url,
                    redirect_urls=raw_result.redirect_urls,
                )
            elif isinstance(raw_result, FetchResult):
                result = raw_result
            else:
                raise TypeError("fetcher must return FetchResult or HttpTransportResponse")
            headers = {str(key).casefold(): str(value) for key, value in (result.headers or {}).items()}
            snippet = result.body_snippet
            if not snippet and result.body:
                snippet = result.body[:2048].decode("utf-8", errors="replace")
            code, wait = classify_http_stop(
                status_code=result.status_code,
                body_snippet=snippet,
                retry_after=headers.get("retry-after"),
                tls_error=result.tls_error or None,
                retries_used=retries_used,
            )
            if code == "PROCEED":
                final_url = result.final_url or result.url or url
                self.authorize(
                    actions=(self._access_action,),
                    url=url,
                    document_date=document_date,
                    size_bytes=len(result.body),
                    redirect_urls=result.redirect_urls,
                    final_url=final_url,
                )
                return result
            if code == "RETRY":
                retries_used += 1
                if wait and self._sleep_func is not None:
                    self._sleep_func(wait)
                continue
            raise NetworkPolicyStop(
                code,
                f"{code} while fetching {url}",
                retry_after_seconds=wait,
            )


# --------------------------------------------------------------------------------------
# Staging outputs
# --------------------------------------------------------------------------------------


def _safe_record_id(record_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", record_id)


def _state_path(partition_dir: Path, record_id: str) -> Path:
    return partition_dir / ".state" / f"{_safe_record_id(record_id)}.json"


def _load_record_state(partition_dir: Path, record_id: str) -> dict[str, Any] | None:
    path = _state_path(partition_dir, record_id)
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(state, dict) or "catalog" not in state or "artifacts" not in state:
        return None
    return state


def _write_record_state(
    partition_dir: Path, record_id: str, catalog_row: dict[str, Any], artifacts: list[dict[str, Any]]
) -> None:
    atomic_write_text(
        _state_path(partition_dir, record_id),
        json.dumps(
            {"catalog": catalog_row, "artifacts": artifacts},
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
    )


def _error_row(
    *,
    cutoff: RunCutoff,
    source_id: str,
    partition_id: str,
    error_type: str,
    message: str,
    url: str = "",
    source_record_id: str = "",
    observed_at: str = "",
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "partition_id": partition_id,
        "error_type": error_type,
        "message": message,
        "url": url,
        "source_record_id": source_record_id,
        "observed_at": observed_at,
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
    }


def _write_partition_outputs(
    partition_dir: Path,
    checkpoint: PartitionCheckpoint,
    cutoff: RunCutoff,
    *,
    catalog_rows: list[dict[str, Any]],
    artifact_rows: list[dict[str, Any]],
    error_rows: list[dict[str, Any]],
    data_origin: str,
    observed_at: str,
    requests_attempted: int,
    stop_reason: str,
    access_action: str = "automated_access",
    catalog_enumeration_complete: bool = False,
) -> dict[str, Any]:
    checkpoint.status = canonical_partition_status(checkpoint.status)
    catalog_rows = sorted(catalog_rows, key=lambda row: (row["source_record_id"], row["page_url"]))
    artifact_rows = sorted(
        artifact_rows, key=lambda row: (row["source_record_id"], row["file_url"], row["attachment_id"])
    )
    error_rows = sorted(
        error_rows,
        key=lambda row: (row.get("source_record_id", ""), row.get("error_type", ""), row.get("url", "")),
    )

    catalog_jsonl = write_jsonl_atomic(partition_dir / "catalog.jsonl", catalog_rows)
    catalog_csv = write_csv_atomic(
        partition_dir / "catalog.csv", CATALOG_RECORD_FIELDS, catalog_rows
    )
    artifacts_jsonl = write_jsonl_atomic(partition_dir / "artifacts.jsonl", artifact_rows)
    artifacts_csv = write_csv_atomic(
        partition_dir / "artifacts.csv", ARTIFACT_RECORD_FIELDS, artifact_rows
    )
    errors_jsonl = write_jsonl_atomic(partition_dir / "errors.jsonl", error_rows)
    checkpoint_digest = save_checkpoint(partition_dir / "checkpoint.json", checkpoint)

    stored = [row for row in artifact_rows if row["status"] == "STORED"]
    quarantined = [row for row in artifact_rows if row["status"] == "QUARANTINED"]
    pre_2020 = [row for row in catalog_rows if row["is_pre_2020_reference"]]
    post_cutoff = [
        row for row in catalog_rows if "POST_CUTOFF_ISSUED_DATE" in row["date_reconciliation_flag"]
    ]
    missing_date = [
        row for row in catalog_rows if "MISSING_ISSUED_DATE" in row["date_reconciliation_flag"]
    ]
    eligible = [row for row in catalog_rows if row["eligible_for_pilot_denominator"]]

    counts = {
        "records_observed": len(catalog_rows),
        "records_eligible": len(eligible),
        "records_pre_2020_reference": len(pre_2020),
        "records_post_cutoff_excluded": len(post_cutoff),
        "records_missing_issued_date": len(missing_date),
        "artifacts_total": len(artifact_rows),
        "artifacts_stored": len(stored),
        "artifacts_quarantined": len(quarantined),
        "blobs_unique": len({row["sha256"] for row in stored}),
        "quarantine_unique": len({row["sha256"] for row in quarantined}),
        "errors": len(error_rows),
    }

    enumeration_complete = bool(
        catalog_enumeration_complete
        and checkpoint.status == "COMPLETED"
        and checkpoint.rights_status == "APPROVED"
    )
    manifest = {
        "schema_version": "1.0",
        "run_id": cutoff.run_id,
        "source_id": checkpoint.source_id,
        "partition_id": checkpoint.partition_id,
        "year": checkpoint.year,
        "quarter": checkpoint.quarter,
        "owner_worker": checkpoint.owner_worker,
        "data_origin": data_origin,
        "access_action": access_action,
        "status": checkpoint.status,
        "rights_status": checkpoint.rights_status,
        "rights_ref": checkpoint.rights_ref,
        "catalog_enumeration_complete": enumeration_complete,
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
        "window_start_date": cutoff.window_start_date,
        "observed_at": observed_at,
        "counts": counts,
        "network": {
            "requests_attempted": requests_attempted,
            "stop_reason": stop_reason,
        },
        "outputs": {
            "catalog.jsonl": catalog_jsonl,
            "catalog.csv": catalog_csv,
            "artifacts.jsonl": artifacts_jsonl,
            "artifacts.csv": artifacts_csv,
            "errors.jsonl": errors_jsonl,
            "checkpoint.json": checkpoint_digest,
        },
    }
    atomic_write_text(
        partition_dir / "partition-manifest.json",
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )
    return manifest


# --------------------------------------------------------------------------------------
# Rights-gated partition runner
# --------------------------------------------------------------------------------------


def _normalize_specs(specs: Iterable[PartitionRecordSpec | str]) -> tuple[PartitionRecordSpec, ...]:
    normalized: list[PartitionRecordSpec] = []
    for spec in specs:
        normalized.append(PartitionRecordSpec(page_url=spec) if isinstance(spec, str) else spec)
    return tuple(normalized)


def run_src03_partition(
    *,
    staging_root: Path,
    registry: SourceRegistry,
    cutoff: RunCutoff,
    partition_id: str,
    year: int,
    source_id: str = SRC03_SOURCE_ID,
    quarter: str = "",
    document_specs: Iterable[PartitionRecordSpec | str] = (),
    fetcher: Callable[[str], Any] | None = None,
    rate_limiter: SharedRateLimiter | None = None,
    owner_worker: str = OWNER_WORKER,
    data_origin: str = "",
    observed_at: str = "",
    infra_group: str = "chinhphu.vn",
    access_action: str = "automated_access",
    purpose: str = "g1-pilot",
    data_class: str = "",
    region: str = "VN",
    document_type: str = "regulation",
    probe_url: str = "",
    probe_document_date: date | None = None,
    at: datetime | None = None,
    at_fn: Callable[[], datetime] | None = None,
    sleep_func: Callable[[float], None] | None = None,
    catalog_enumeration_complete: bool = False,
) -> dict[str, Any]:
    """Run one SRC-03 (or FIXTURE-SRC-03) partition with per-operation rights, stop, and checkpoint guards."""
    if "/" in partition_id or "\\" in partition_id:
        raise ValueError("partition_id must not contain path separators")
    specs = _normalize_specs(document_specs)
    origin = data_origin or ("SYNTHETIC_FIXTURE" if source_id.startswith("FIXTURE-") else "REAL")
    observation_time = observed_at or cutoff.cutoff_vn
    partition_dir = staging_root / partition_id
    partition_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = partition_dir / "checkpoint.json"
    checkpoint = load_checkpoint(checkpoint_path) or PartitionCheckpoint(
        source_id=source_id,
        partition_id=partition_id,
        year=year,
        quarter=quarter,
        owner_worker=owner_worker,
        status="PENDING",
        last_completed_cursor=0,
        rights_status="PENDING_RIGHTS",
        rights_ref="",
        updated_at=observation_time,
    )
    checkpoint.source_id = source_id
    checkpoint.partition_id = partition_id
    checkpoint.year = year
    checkpoint.quarter = quarter
    checkpoint.owner_worker = owner_worker
    checkpoint.updated_at = observation_time

    fixture_source = source_id.startswith("FIXTURE-")
    if not fixture_source and source_id != SRC03_SOURCE_ID:
        raise ValueError(f"unsupported SRC-03 source_id: {source_id}")
    effective_data_class = data_class or ("synthetic-fixture" if fixture_source else "public")
    preflight_url = (
        probe_url
        or (specs[0].page_url if specs else (FIXTURE_BASE_URL if fixture_source else SRC03_PORTAL_URL))
    )
    preflight_date = probe_document_date or (
        parse_vn_date(specs[0].issued_date_hint) if specs and specs[0].issued_date_hint else None
    ) or date(year, 1, 1)
    auth_time_fn = authorization_clock(source_id, cutoff.cutoff_datetime_vn, at=at, at_fn=at_fn)

    approved, rights_statuses = check_source_actions(
        registry,
        source_id=source_id,
        actions=(access_action, "store"),
        purpose=purpose,
        data_class=effective_data_class,
        region=region,
        document_type=document_type,
        url=preflight_url,
        document_date=preflight_date,
        size_bytes=0,
        at=auth_time_fn(),
    )
    if not approved:
        checkpoint.status = "BLOCKED_RIGHTS"
        checkpoint.rights_status = "BLOCKED_RIGHTS"
        checkpoint.rights_ref = ";".join(
            f"{action}={status}" for action, status in sorted(rights_statuses.items())
        )
        manifest = _write_partition_outputs(
            partition_dir,
            checkpoint,
            cutoff,
            catalog_rows=[],
            artifact_rows=[],
            error_rows=[],
            data_origin=origin,
            observed_at=observation_time,
            requests_attempted=0,
            stop_reason="PREFLIGHT_BLOCKED_RIGHTS",
            access_action=access_action,
            catalog_enumeration_complete=False,
        )
        return {
            **manifest,
            "partition_dir": str(partition_dir),
        }

    checkpoint.rights_status = "APPROVED"
    checkpoint.rights_ref = rights_statuses.get("store") or rights_statuses.get(access_action, "")

    limiter = rate_limiter or SharedRateLimiter()
    if fetcher is None and specs:
        raise ValueError("an approved partition with document specs requires a fetcher")
    control = (
        _NetworkControl(
            fetcher,
            limiter,
            registry=registry,
            source_id=source_id,
            access_action=access_action,
            purpose=purpose,
            data_class=effective_data_class,
            region=region,
            document_type=document_type,
            authorization_time_fn=auth_time_fn,
            infra_group=infra_group,
            allow_network=(access_action != "manual_download"),
            sleep_func=sleep_func,
        )
        if fetcher
        else None
    )

    catalog_rows: list[dict[str, Any]] = []
    artifact_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []

    completed = set(checkpoint.completed_record_ids)
    for record_id in sorted(completed):
        state = _load_record_state(partition_dir, record_id)
        if state is None:
            completed.discard(record_id)
            continue
        catalog_rows.append(state["catalog"])
        artifact_rows.extend(state["artifacts"])
    checkpoint.completed_record_ids = sorted(completed)
    checkpoint.last_completed_cursor = len(completed)
    prior_status = canonical_partition_status(checkpoint.status)
    checkpoint.status = "RUNNING" if specs else "COMPLETED"

    existing_manifest_path = partition_dir / "partition-manifest.json"
    all_specs_complete = all(
        (spec.source_record_id or docid_from_url(spec.page_url)) in completed for spec in specs
    )
    if (
        prior_status == "COMPLETED"
        and all_specs_complete
        and existing_manifest_path.exists()
    ):
        existing = json.loads(existing_manifest_path.read_text(encoding="utf-8"))
        existing["status"] = canonical_partition_status(existing.get("status", "COMPLETED"))
        return {**existing, "partition_dir": str(partition_dir)}

    stop_reason = ""
    try:
        for spec in specs:
            record_hint = spec.source_record_id or docid_from_url(spec.page_url)
            if record_hint and record_hint in completed:
                continue
            if control is None:
                raise ValueError("fetcher is required to process document specs")
            try:
                catalog_row, record_artifacts, record_id = _ingest_document(
                    spec=spec,
                    control=control,
                    cutoff=cutoff,
                    partition_id=partition_id,
                    partition_year=year,
                    source_id=source_id,
                    data_origin=origin,
                    observed_at=observation_time,
                    partition_dir=partition_dir,
                    checkpoint=checkpoint,
                )
            except RightsDenied as denied:
                stop_reason = f"BLOCKED_RIGHTS:{denied}"
                checkpoint.status = "BLOCKED_RIGHTS"
                error_rows.append(
                    _error_row(
                        cutoff=cutoff,
                        source_id=source_id,
                        partition_id=partition_id,
                        error_type="BLOCKED_RIGHTS",
                        message=str(denied),
                        url=spec.page_url,
                        source_record_id=record_hint,
                        observed_at=observation_time,
                    )
                )
                break
            except NetworkPolicyStop as stop:
                stop_reason = stop.code
                checkpoint.status = "STOPPED"
                error_rows.append(
                    _error_row(
                        cutoff=cutoff,
                        source_id=source_id,
                        partition_id=partition_id,
                        error_type=stop.code,
                        message=str(stop),
                        url=spec.page_url,
                        source_record_id=record_hint,
                        observed_at=observation_time,
                    )
                )
                break
            _write_record_state(partition_dir, record_id, catalog_row, record_artifacts)
            catalog_rows.append(catalog_row)
            artifact_rows.extend(record_artifacts)
            completed.add(record_id)
            checkpoint.completed_record_ids = sorted(completed)
            checkpoint.last_completed_cursor = len(completed)
            checkpoint.status = "RUNNING"
            checkpoint.updated_at = observation_time
            save_checkpoint(checkpoint_path, checkpoint)

        if not stop_reason:
            checkpoint.status = "COMPLETED"
    except Exception:
        checkpoint.status = "INTERRUPTED"
        checkpoint.updated_at = observation_time
        _write_partition_outputs(
            partition_dir,
            checkpoint,
            cutoff,
            catalog_rows=catalog_rows,
            artifact_rows=artifact_rows,
            error_rows=error_rows,
            data_origin=origin,
            observed_at=observation_time,
            requests_attempted=control.requests_attempted if control else 0,
            stop_reason="INTERRUPTED",
            access_action=access_action,
            catalog_enumeration_complete=False,
        )
        raise

    checkpoint.updated_at = observation_time
    manifest = _write_partition_outputs(
        partition_dir,
        checkpoint,
        cutoff,
        catalog_rows=catalog_rows,
        artifact_rows=artifact_rows,
        error_rows=error_rows,
        data_origin=origin,
        observed_at=observation_time,
        requests_attempted=control.requests_attempted if control else 0,
        stop_reason=stop_reason,
        access_action=access_action,
        catalog_enumeration_complete=(catalog_enumeration_complete and checkpoint.status == "COMPLETED"),
    )
    return {
        **manifest,
        "partition_dir": str(partition_dir),
    }


def _ingest_document(
    *,
    spec: PartitionRecordSpec,
    control: _NetworkControl,
    cutoff: RunCutoff,
    partition_id: str,
    partition_year: int,
    source_id: str,
    data_origin: str,
    observed_at: str,
    partition_dir: Path,
    checkpoint: PartitionCheckpoint,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    initial_doc_date = parse_vn_date(spec.issued_date_hint) or date(partition_year, 1, 1)
    page_result = control.fetch(spec.page_url, document_date=initial_doc_date)
    if spec.expected_html_sha256 and sha256_bytes(page_result.body) != spec.expected_html_sha256.lower():
        raise NetworkPolicyStop(
            "HTML_CHECKSUM_MISMATCH",
            f"HTML checksum mismatch for {spec.page_url}",
        )
    parsed = parse_src03_document_html(
        page_result.body.decode("utf-8", errors="replace"), spec.page_url
    )
    effective_doc_date = parse_vn_date(parsed.issued_date) or initial_doc_date
    page_final_url = page_result.final_url or page_result.url or spec.page_url
    page_auths = control.authorize(
        actions=(control._access_action, "store"),
        url=spec.page_url,
        document_date=effective_doc_date,
        size_bytes=len(page_result.body),
        redirect_urls=page_result.redirect_urls,
        final_url=page_final_url,
    )
    page_rights_ref = (
        f"APPROVED:{page_auths['store'].registry_revision}:{page_auths['store'].evidence_ref}"
    )

    record_id = parsed.source_record_id or spec.source_record_id or docid_from_url(spec.page_url)
    if not record_id:
        raise ValueError(f"cannot determine source_record_id for {spec.page_url}")
    if not parsed.document_number:
        raise ValueError(f"document page {spec.page_url} has no Số ký hiệu")

    window = evaluate_date_window(
        parsed.issued_date,
        cutoff,
        observed_effective_date_str=parsed.observed_effective_date,
    )
    relation_role = parsed.relation_role
    is_pre_2020 = bool(window["is_pre_2020_reference"])
    if is_pre_2020 and relation_role == "catalog_entry":
        relation_role = "pre_2020_reference"
    eligible = bool(window["eligible_for_pilot_denominator"]) and not is_pre_2020
    if relation_role == "pre_2020_reference":
        eligible = False

    if "MISSING_ISSUED_DATE" in window["date_reconciliation_flag"]:
        status = "NEEDS_DATE_RECONCILIATION"
    elif is_pre_2020:
        status = "EXCLUDED_PRE_2020"
    elif window["is_post_cutoff"]:
        status = "EXCLUDED_POST_CUTOFF"
    else:
        status = "CANDIDATE"

    catalog_row = {
        "source_id": source_id,
        "source_record_id": record_id,
        "partition_id": partition_id,
        "data_origin": data_origin,
        "page_url": spec.page_url,
        "year": window["year"],
        "quarter": window["quarter"],
        "observed_at": observed_at,
        "gazette_issue": "",
        "gazette_page": "",
        "continuation_issues": [],
        "issuer": parsed.issuer,
        "document_type": parsed.document_type,
        "document_number": parsed.document_number,
        "title": parsed.title,
        "issued_date": parsed.issued_date,
        "gazette_published_date": "",
        "observed_effective_date": parsed.observed_effective_date,
        "version": "",
        "relation_role": relation_role,
        "related_to_document_number": parsed.related_to_document_number,
        "domain_candidate": spec.domain_candidate,
        "rights_ref": page_rights_ref,
        "status": status,
        "date_reconciliation_flag": window["date_reconciliation_flag"],
        "is_pre_2020_reference": is_pre_2020,
        "eligible_for_pilot_denominator": eligible,
        "legal_status_verified": False,
        "error": "",
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
    }

    record_artifacts: list[dict[str, Any]] = []
    for link in parsed.attachments:
        result = control.fetch(link.file_url, document_date=effective_doc_date)
        att_final_url = result.final_url or result.url or link.file_url
        att_auths = control.authorize(
            actions=("store",),
            url=link.file_url,
            document_date=effective_doc_date,
            size_bytes=len(result.body),
            redirect_urls=result.redirect_urls,
            final_url=att_final_url,
        )
        att_rights_ref = (
            f"APPROVED:{att_auths['store'].registry_revision}:{att_auths['store'].evidence_ref}"
        )
        declared_mime = result.declared_mime or link.declared_mime
        digest, detected_mime, quarantine_reason = validate_blob_integrity(
            result.body,
            declared_mime=declared_mime,
            expected_sha256=result.expected_sha256 or None,
        )
        role = link.relation_role
        if role == "signed_original" and relation_role in ("consolidated", "corrigendum", "amending"):
            role = relation_role
        if quarantine_reason:
            status = "QUARANTINED"
            stored_path = f"quarantine/{digest}.bin"
            atomic_write_bytes(partition_dir / stored_path, result.body)
            if link.attachment_id not in checkpoint.quarantined_attachment_ids:
                checkpoint.quarantined_attachment_ids.append(link.attachment_id)
        else:
            status = "STORED"
            stored_path = f"blobs/{digest[:2]}/{digest}.bin"
            atomic_write_bytes(partition_dir / stored_path, result.body)
        record_artifacts.append(
            {
                "source_id": source_id,
                "source_record_id": record_id,
                "partition_id": partition_id,
                "data_origin": data_origin,
                "parent_id": link.parent_id or record_id,
                "attachment_id": link.attachment_id,
                "page_url": spec.page_url,
                "file_url": link.file_url,
                "year": window["year"],
                "quarter": window["quarter"],
                "observed_at": observed_at,
                "gazette_issue": "",
                "gazette_page": "",
                "document_number": parsed.document_number,
                "version": "",
                "relation_role": role,
                "file_type": link.file_type,
                "declared_mime": declared_mime,
                "detected_mime": detected_mime,
                "size_bytes": len(result.body),
                "sha256": digest,
                "stored_blob_path": stored_path,
                "rights_ref": att_rights_ref,
                "status": status,
                "quarantine_reason": quarantine_reason,
                "error": "",
                "cutoff_utc": cutoff.cutoff_utc,
                "cutoff_vn": cutoff.cutoff_vn,
            }
        )
    return catalog_row, record_artifacts, record_id


# --------------------------------------------------------------------------------------
# Synthetic fixtures
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FixtureAttachment:
    file_name: str
    file_url: str
    body: bytes
    declared_mime: str = ""
    expected_sha256: str = ""


@dataclass(frozen=True)
class FixtureDocument:
    source_record_id: str
    page_url: str
    partition_id: str
    html: str
    domain_candidate: str
    attachments: tuple[FixtureAttachment, ...]


@dataclass(frozen=True)
class SyntheticFixtureSuite:
    destination: Path
    registry_path: Path
    registry: SourceRegistry
    fetcher: Callable[[str], FetchResult]
    documents: tuple[FixtureDocument, ...]
    partitions: Mapping[int, tuple[PartitionRecordSpec, ...]]


@dataclass(frozen=True)
class _DocumentSpec:
    docid: str
    partition_year: int
    document_number: str
    document_type: str
    issuer: str
    issued_date: str
    effective_date: str
    title: str
    domain: str
    attachments: tuple[tuple[str, bytes, str, str], ...] = ()
    # attachment tuple = (file_name, body, declared_mime, expected_sha256)


def _fixture_documents() -> tuple[_DocumentSpec, ...]:
    def pdf(marker: str) -> bytes:
        return f"%PDF-1.4\n%{marker}\n%%EOF\n".encode("utf-8")

    return (
        _DocumentSpec(
            docid="900045",
            partition_year=2020,
            document_number="45/2019/QH14",
            document_type="Bộ luật",
            issuer="Quốc hội",
            issued_date="20-11-2019",
            effective_date="01-01-2020",
            title="Bộ luật Lao động",
            domain="LAB",
            attachments=(("45_2019_qh14-signed.signed.pdf", pdf("SYNTH-45-2019-QH14-V1"), "application/pdf", ""),),
        ),
        _DocumentSpec(
            docid="900059",
            partition_year=2020,
            document_number="59/2020/QH14",
            document_type="Luật",
            issuer="Quốc hội",
            issued_date="17-06-2020",
            effective_date="01-01-2021",
            title="Luật Đấu thầu",
            domain="BUS",
            attachments=(("59_2020_qh14-signed.signed.pdf", pdf("SYNTH-59-2020-QH14-V1"), "application/pdf", ""),),
        ),
        _DocumentSpec(
            docid="900031",
            partition_year=2024,
            document_number="31/2024/QH15",
            document_type="Luật",
            issuer="Quốc hội",
            issued_date="18-01-2024",
            effective_date="01-08-2024",
            title="Luật Đất đai",
            domain="LND",
            attachments=(
                ("31-2024-qh15-signed.signed.pdf", pdf("SYNTH-31-2024-QH15-V1"), "application/pdf", ""),
                (
                    "31-pl1.xlsx",
                    b"PK\x03\x04" + b"xl/workbook.xml" + b"\x00" * 32,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "",
                ),
                ("31-pl-empty.pdf", b"", "application/pdf", ""),
            ),
        ),
        _DocumentSpec(
            docid="900036",
            partition_year=2024,
            document_number="36/2024/QH15",
            document_type="Luật",
            issuer="Quốc hội",
            issued_date="27-06-2024",
            effective_date="01-01-2025",
            title="Luật Đường bộ",
            domain="TRA",
            attachments=(
                (
                    "36-2024-qh15.html",
                    "<!doctype html><html><body><p>Luật Đường bộ</p></body></html>".encode("utf-8"),
                    "text/html",
                    "",
                ),
                ("36-2024-qh15-scan.pdf", b"%PDF-1.4\n" + bytes(range(32)) + b"\n%%EOF\n", "application/pdf", ""),
                ("36-scan-bad.pdf", pdf("SYNTH-36-2024-BAD-CHECKSUM"), "application/pdf", "0" * 64),
            ),
        ),
        _DocumentSpec(
            docid="213310",
            partition_year=2025,
            document_number="78/2025/NĐ-CP",
            document_type="Nghị định",
            issuer="Chính phủ",
            issued_date="01-04-2025",
            effective_date="01-04-2025",
            title=(
                "Quy định chi tiết một số điều và biện pháp để tổ chức, hướng dẫn thi hành "
                "Luật Ban hành văn bản quy phạm pháp luật"
            ),
            domain="ADM",
            attachments=(
                ("78ndcp-1.signed.pdf", SHARED_SYNTHETIC_PDF, "application/pdf", ""),
                ("78-pl1.pdf", pdf("SYNTH-78-PL1"), "application/pdf", ""),
                ("pl2.pdf", pdf("SYNTH-78-PL2"), "application/pdf", ""),
                ("pl3.pdf", pdf("SYNTH-78-PL3"), "application/pdf", ""),
                ("pl4.pdf", pdf("SYNTH-78-PL4"), "application/pdf", ""),
            ),
        ),
        _DocumentSpec(
            docid="900012",
            partition_year=2025,
            document_number="12/QĐ-TTg-DC",
            document_type="Quyết định",
            issuer="Thủ tướng Chính phủ",
            issued_date="10-05-2025",
            effective_date="10-05-2025",
            title="Đính chính Nghị định số 78/2025/NĐ-CP quy định chi tiết một số điều",
            domain="ADM",
            attachments=(
                (
                    "12-qdttg-dc.html",
                    "<!doctype html><html><body><p>Đính chính</p></body></html>".encode("utf-8"),
                    "text/html",
                    "",
                ),
                (
                    "12-qdttg-dc.docx",
                    b"PK\x03\x04" + b"word/document.xml" + b"\x00" * 32,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "",
                ),
            ),
        ),
        _DocumentSpec(
            docid="900205",
            partition_year=2025,
            document_number="205/2025/TT-BYT",
            document_type="Thông tư",
            issuer="Bộ Y tế",
            issued_date="",
            effective_date="",
            title="Quy định về hồ sơ bệnh án điện tử",
            domain="EDU",
            attachments=(("205-tt-byt-signed.signed.pdf", pdf("SYNTH-205-2025-TT-BYT"), "application/pdf", ""),),
        ),
        _DocumentSpec(
            docid="900116",
            partition_year=2026,
            document_number="116/VBHN-BNNMT",
            document_type="Văn bản hợp nhất",
            issuer="Bộ Nông nghiệp và Môi trường",
            issued_date="20-11-2026",
            effective_date="20-11-2026",
            title="Văn bản hợp nhất Nghị định số 78/2025/NĐ-CP quy định chi tiết một số điều",
            domain="ENV",
            attachments=(("116-vbhn-bnnmt.signed.pdf", pdf("SYNTH-116-VBHN-BNNMT"), "application/pdf", ""),),
        ),
        _DocumentSpec(
            docid="900413",
            partition_year=2026,
            document_number="413/2026/NĐ-CP",
            document_type="Nghị định",
            issuer="Chính phủ",
            issued_date="16-11-2026",
            effective_date="01-12-2026",
            title=(
                "Sửa đổi, bổ sung một số điều của Nghị định số 104/2025/NĐ-CP ngày 15 tháng 5 "
                "năm 2025 của Chính phủ"
            ),
            domain="LND",
            attachments=(("413_2026_ndcp-signed.signed.pdf", pdf("SYNTH-413-2026-ND-CP"), "application/pdf", ""),),
        ),
        _DocumentSpec(
            docid="900999",
            partition_year=2026,
            document_number="999/2026/NĐ-CP",
            document_type="Nghị định",
            issuer="Chính phủ",
            issued_date="28-11-2026",
            effective_date="28-11-2026",
            title="Nghị định quy định ngoài cửa sổ pilot",
            domain="ADM",
            attachments=(("999_2026_ndcp-signed.signed.pdf", pdf("SYNTH-999-2026-ND-CP"), "application/pdf", ""),),
        ),
    )


def _attachment_url(spec: _DocumentSpec, file_name: str) -> str:
    issued = parse_vn_date(spec.issued_date) or date(spec.partition_year, 1, 1)
    return (
        f"https://{SRC03_FILE_HOST}/cpp/files/vbpq/{issued.year}/{issued.month:02d}/"
        f"{file_name}"
    )


def _fixture_page_html(spec: _DocumentSpec, attachment_urls: tuple[str, ...]) -> str:
    rows = [
        ("Số ký hiệu", spec.document_number),
        ("Ngày ban hành", spec.issued_date),
        ("Ngày có hiệu lực", spec.effective_date),
        ("Loại văn bản", spec.document_type),
        ("Cơ quan ban hành", spec.issuer),
    ]
    row_html = "\n".join(
        f'<tr><td class="label">{escape(label)}</td><td class="value">{escape(value)}</td></tr>'
        for label, value in rows
        if value
    )
    attachment_html = "\n".join(
        (
            f'<li class="attachment"><a href="{escape(url, quote=True)}">'
            f"{escape(file_name)}</a> "
            f'<a class="viewer" href="javascript:__doPostBack('
            f"'ctrl_{spec.docid}$rpTep$ctl{index:02d}$btn_showfile','')\">Xem tệp</a></li>"
        )
        for index, (url, (file_name, *_)) in enumerate(
            zip(attachment_urls, spec.attachments, strict=True)
        )
    )
    page_title = f"{spec.document_type} số {spec.document_number} của {spec.issuer}: {spec.title}"
    return f"""<!DOCTYPE html>
<html lang="vi">
<head><meta charset="utf-8"><title>{escape(page_title)}</title></head>
<body>
<div class="page-detail">
<h1 class="title-detail">{escape(spec.title)}</h1>
<table class="document-metadata"><tbody>
{row_html}
</tbody></table>
<div class="attachments">
<h3>Tài liệu đính kèm</h3>
<ul>
{attachment_html}
</ul>
<div class="viewer-extra">
<a href="javascript:__doPostBack('ctrl_{spec.docid}$btn_showfile','')"></a>
</div>
</div>
<div class="navigation">
<a href="https://vanban.chinhphu.vn/?pageid=27160">Hệ thống văn bản</a>
<a href="https://example.invalid/not-an-attachment.pdf">Liên kết ngoài</a>
</div>
</div>
</body>
</html>
"""


def _all_synthetic_fixture_urls() -> tuple[str, ...]:
    urls: set[str] = {FIXTURE_BASE_URL}
    for spec in _fixture_documents():
        urls.add(f"https://vanban.chinhphu.vn/?classid=1&docid={spec.docid}&pageid=27160")
        for file_name, *_ in spec.attachments:
            urls.add(_attachment_url(spec, file_name))
    return tuple(sorted(urls))


def build_src03_synthetic_registry(
    path: Path,
    *,
    source_ids: Iterable[str] = (FIXTURE_SOURCE_ID,),
    max_actions_per_minute: int = 120,
    urls: Iterable[str] | None = None,
    actions: Iterable[str] = ("automated_access", "store"),
    max_bytes_per_item: int = 1048576,
    approved_at: str = "2020-01-01T00:00:00Z",
    expires_at: str = "2040-01-01T00:00:00Z",
    document_from: str = "2019-01-01",
    document_through: str = "2027-12-31",
    data_class: str = "synthetic-fixture",
) -> SourceRegistry:
    """Write and load a test-only approved registry for synthetic SRC-03 fixtures."""
    scope_urls = sorted({*(urls if urls is not None else _all_synthetic_fixture_urls())})
    policy = {
        "status": "APPROVED",
        "evidence_ref": "SYNTHETIC-SRC03-ONLY",
        "approved_by": "test-fixture",
        "policy_url": "https://fixture-src03.test/policy",
        "policy_version": "1",
        "policy_date": "2026-01-01",
        "approved_at": approved_at,
        "expires_at": expires_at,
        "revocation_procedure": "replace approval with DENIED",
        "max_bytes_per_item": max_bytes_per_item,
        "max_actions_per_minute": max_actions_per_minute,
        "scope": {
            "purpose": ["g1-pilot"],
            "data_class": [data_class],
            "region": ["VN"],
            "document_type": ["regulation"],
            "url": scope_urls,
            "document_from": document_from,
            "document_through": document_through,
        },
    }
    sources = {
        source_id: {
            "name": f"Synthetic SRC-03 fixture source {source_id}",
            "url": FIXTURE_BASE_URL,
            "owner": "pilot-fixture",
            "contact": "fixture-only",
            "actions": {action: json.loads(json.dumps(policy)) for action in actions},
        }
        for source_id in source_ids
    }
    atomic_write_text(
        path,
        json.dumps(
            {"revision": "g1-src03-synthetic-v1", "sources": sources},
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
    )
    return SourceRegistry(path)


def build_src03_synthetic_fixtures(destination: Path) -> SyntheticFixtureSuite:
    """Build deterministic HTML/blob fixtures, their registry, and a pluggable fetcher."""
    destination = Path(destination)
    fixtures_dir = destination
    documents_dir = fixtures_dir / "documents"
    attachments_dir = fixtures_dir / "attachments"
    registry_path = destination / "synthetic-rights.json"
    registry = build_src03_synthetic_registry(registry_path)

    fetcher_map: dict[str, FetchResult] = {}
    documents: list[FixtureDocument] = []
    partitions: dict[int, list[PartitionRecordSpec]] = {}
    manifest_documents: list[dict[str, Any]] = []

    for spec in sorted(_fixture_documents(), key=lambda item: item.docid):
        page_url = f"https://vanban.chinhphu.vn/?classid=1&docid={spec.docid}&pageid=27160"
        attachment_urls = tuple(
            _attachment_url(spec, file_name) for file_name, *_ in spec.attachments
        )
        html = _fixture_page_html(spec, attachment_urls)
        atomic_write_text(documents_dir / f"{spec.docid}.html", html)
        fetcher_map[page_url] = FetchResult(
            url=page_url,
            status_code=200,
            body=html.encode("utf-8"),
            headers={"content-type": "text/html; charset=utf-8"},
            declared_mime="text/html",
        )

        fixture_attachments: list[FixtureAttachment] = []
        attachment_manifest: list[dict[str, Any]] = []
        for (file_name, body, declared_mime, expected_sha256), url in zip(
            spec.attachments, attachment_urls, strict=True
        ):
            atomic_write_bytes(attachments_dir / f"{spec.docid}__{file_name}", body)
            fetcher_map[url] = FetchResult(
                url=url,
                status_code=200,
                body=body,
                declared_mime=declared_mime,
                expected_sha256=expected_sha256,
            )
            fixture_attachments.append(
                FixtureAttachment(
                    file_name=file_name,
                    file_url=url,
                    body=body,
                    declared_mime=declared_mime,
                    expected_sha256=expected_sha256,
                )
            )
            attachment_manifest.append(
                {
                    "file_name": file_name,
                    "file_url": url,
                    "sha256": sha256_bytes(body),
                    "size_bytes": len(body),
                    "declared_mime": declared_mime,
                    "expected_sha256": expected_sha256,
                }
            )

        partition_id = f"{FIXTURE_SOURCE_ID}__{spec.partition_year}"
        fixture_document = FixtureDocument(
            source_record_id=spec.docid,
            page_url=page_url,
            partition_id=partition_id,
            html=html,
            domain_candidate=spec.domain,
            attachments=tuple(fixture_attachments),
        )
        documents.append(fixture_document)
        partitions.setdefault(spec.partition_year, []).append(
            PartitionRecordSpec(
                page_url=page_url,
                source_record_id=spec.docid,
                domain_candidate=spec.domain,
            )
        )
        manifest_documents.append(
            {
                "source_record_id": spec.docid,
                "page_url": page_url,
                "partition_id": partition_id,
                "document_number": spec.document_number,
                "issued_date": spec.issued_date,
                "observed_effective_date": spec.effective_date,
                "domain_candidate": spec.domain,
                "html_sha256": sha256_bytes(html.encode("utf-8")),
                "attachments": attachment_manifest,
            }
        )

    def fetcher(url: str) -> FetchResult:
        if url not in fetcher_map:
            raise KeyError(f"no synthetic fixture for {url}")
        return fetcher_map[url]

    manifest = {
        "schema_version": "1.0",
        "data_origin": "SYNTHETIC_FIXTURE",
        "source_id": FIXTURE_SOURCE_ID,
        "registry_revision": registry.revision,
        "documents": manifest_documents,
        "partitions": {
            f"{FIXTURE_SOURCE_ID}__{year}": sorted(item.docid for item in _fixture_documents() if item.partition_year == year)
            for year in sorted(partitions)
        },
    }
    atomic_write_text(
        fixtures_dir / "fixture-manifest.json",
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )
    return SyntheticFixtureSuite(
        destination=destination,
        registry_path=registry_path,
        registry=registry,
        fetcher=fetcher,
        documents=tuple(documents),
        partitions={year: tuple(items) for year, items in sorted(partitions.items())},
    )


def run_src03_synthetic_pilot(
    staging_root: Path,
    cutoff: RunCutoff,
    *,
    suite: SyntheticFixtureSuite | None = None,
    rate_limiter: SharedRateLimiter | None = None,
    observed_at: str = "",
) -> dict[str, Any]:
    """Run every synthetic fixture partition and return per-partition manifest summaries."""
    staging_root = Path(staging_root)
    if suite is None:
        suite = build_src03_synthetic_fixtures(staging_root / "fixtures")
    # Fixtures intentionally exceed the conservative live caps; replay uses generous caps.
    limiter = rate_limiter or SharedRateLimiter(
        per_source_max_per_minute=120, shared_infra_max_per_minute=240
    )
    partitions: list[dict[str, Any]] = []
    for year, specs in suite.partitions.items():
        partition_id = f"{FIXTURE_SOURCE_ID}__{year}"
        partitions.append(
            run_src03_partition(
                staging_root=staging_root,
                registry=suite.registry,
                cutoff=cutoff,
                partition_id=partition_id,
                year=year,
                source_id=FIXTURE_SOURCE_ID,
                document_specs=specs,
                fetcher=suite.fetcher,
                rate_limiter=limiter,
                data_origin="SYNTHETIC_FIXTURE",
                observed_at=observed_at or cutoff.cutoff_vn,
            )
        )
    completed_count = sum(
        1 for item in partitions if canonical_partition_status(item["status"]) == "COMPLETED"
    )
    aggregate = {
        "partitions": len(partitions),
        "completed": completed_count,
        "complete": completed_count,
        "records_observed": sum(item["counts"]["records_observed"] for item in partitions),
        "records_eligible": sum(item["counts"]["records_eligible"] for item in partitions),
        "artifacts_total": sum(item["counts"]["artifacts_total"] for item in partitions),
        "artifacts_stored": sum(item["counts"]["artifacts_stored"] for item in partitions),
        "artifacts_quarantined": sum(
            item["counts"]["artifacts_quarantined"] for item in partitions
        ),
    }
    return {
        "source_id": FIXTURE_SOURCE_ID,
        "data_origin": "SYNTHETIC_FIXTURE",
        "staging_root": str(staging_root),
        "suite": suite,
        "partitions": partitions,
        "aggregate": aggregate,
    }


# --------------------------------------------------------------------------------------
# CLI and worker manifest
# --------------------------------------------------------------------------------------


def _summary_from_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return {
        "partition_id": manifest["partition_id"],
        "year": manifest["year"],
        "status": manifest["status"],
        "rights_status": manifest["rights_status"],
        "counts": manifest["counts"],
        "network": manifest["network"],
        "manifest_sha256": sha256_bytes(path.read_bytes()),
    }


def _worker_manifest(
    *,
    cutoff: RunCutoff,
    registry_revision: str,
    real_manifests: list[dict[str, Any]],
    synthetic_manifests: list[dict[str, Any]],
    quarantine_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    synthetic_counts = {
        key: sum(item["counts"][key] for item in synthetic_manifests)
        for key in (
            "records_observed",
            "records_eligible",
            "records_pre_2020_reference",
            "records_post_cutoff_excluded",
            "records_missing_issued_date",
            "artifacts_total",
            "artifacts_stored",
            "artifacts_quarantined",
            "blobs_unique",
            "quarantine_unique",
            "errors",
        )
    }
    real_blocked = [item for item in real_manifests if item["status"] == "BLOCKED_RIGHTS"]
    synthetic_completed = [
        item for item in synthetic_manifests if canonical_partition_status(item["status"]) == "COMPLETED"
    ]
    return {
        "schema_version": "1.0",
        "worker": OWNER_WORKER,
        "run_id": cutoff.run_id,
        "source_id": SRC03_SOURCE_ID,
        "source_url": SRC03_PORTAL_URL,
        "file_host": f"https://{SRC03_FILE_HOST}/",
        "registry_revision": registry_revision,
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
        "cutoff_timezone": "Asia/Ho_Chi_Minh",
        "window_start_date": cutoff.window_start_date,
        "real_partitions": real_manifests,
        "synthetic_partitions": synthetic_manifests,
        "aggregate": {
            "real_partitions_total": len(real_manifests),
            "real_partitions_blocked": len(real_blocked),
            "real_network_requests": sum(
                item["network"]["requests_attempted"] for item in real_manifests
            ),
            "real_blobs_written": sum(
                item["counts"]["blobs_unique"] for item in real_manifests
            ),
            "synthetic_partitions_total": len(synthetic_manifests),
            "synthetic_partitions_completed": len(synthetic_completed),
            "synthetic_partitions_complete": len(synthetic_completed),
            "synthetic_counts": synthetic_counts,
        },
        "quarantine_evidence": quarantine_rows,
        "determinism": {
            "fixture_revision": "g1-src03-synthetic-v1",
            "observed_at": cutoff.cutoff_vn,
            "replay_note": "same fixture bytes, cutoff, and observed_at yield identical catalog/artifact hashes",
        },
        "validation_commands": [
            '$env:PYTHONPATH = "services/data-ingestion/src"; '
            "rtk proxy python -X utf8 -m unittest services/data-ingestion/tests/test_src03_adapter.py -v",
            "rtk proxy python -X utf8 -m luatvn_ai_data_ingestion.src03_adapter "
            "--run-dir build/g1/G1-PILOT-SRC01-SRC03-20261126-01 "
            "--cutoff-vn 2026-11-26T19:58:39+07:00 --cutoff-utc 2026-11-26T12:58:39Z",
        ],
        "blockers": [
            "SRC-03 all six actions PENDING_RIGHTS in experiments/g1/source-rights.json; "
            "no live network requests or real blob storage were performed.",
        ]
        if len(real_blocked) == len(real_manifests)
        else [],
    }


def _quarantine_rows(manifest_paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in manifest_paths:
        artifacts_path = path.parent / "artifacts.jsonl"
        if not artifacts_path.exists():
            continue
        for line in artifacts_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("status") == "QUARANTINED":
                rows.append(
                    {
                        "partition_id": row["partition_id"],
                        "source_record_id": row["source_record_id"],
                        "file_url": row["file_url"],
                        "sha256": row["sha256"],
                        "quarantine_reason": row["quarantine_reason"],
                        "stored_blob_path": row["stored_blob_path"],
                    }
                )
    return sorted(rows, key=lambda row: (row["partition_id"], row["source_record_id"], row["file_url"]))


def run_src03_manual_intake(
    *,
    run_dir: Path,
    cutoff: RunCutoff,
    registry_path: Path,
    intake_manifest_path: Path,
    at: datetime | None = None,
) -> dict[str, Any]:
    """Ingest a rights-approved locally downloaded SRC-03 manual batch with provenance & checksums."""
    run_dir = Path(run_dir)
    intake_manifest_path = Path(intake_manifest_path)
    intake_root = intake_manifest_path.parent
    manifest_data = json.loads(intake_manifest_path.read_text(encoding="utf-8"))
    source_id = str(manifest_data.get("source_id") or SRC03_SOURCE_ID)
    purpose = str(manifest_data.get("purpose") or "g1-pilot")
    data_class = str(manifest_data.get("data_class") or "public")
    region = str(manifest_data.get("region") or "VN")
    document_type = str(manifest_data.get("document_type") or "regulation")
    enumeration_flag = bool(manifest_data.get("catalog_enumeration_complete", False))
    registry = SourceRegistry(Path(registry_path))

    by_year: dict[int, list[PartitionRecordSpec]] = {}
    url_to_entry: dict[str, tuple[Path, str, str]] = {}
    for item in manifest_data.get("items", []):
        year = int(item["partition_year"])
        page_url = str(item["page_url"])
        html_path = resolve_safe_local_path(intake_root, str(item["html_path"]))
        url_to_entry[page_url] = (html_path, "text/html", str(item.get("html_sha256") or ""))
        for att in item.get("attachments", []):
            file_url = str(att["file_url"])
            local_file = resolve_safe_local_path(intake_root, str(att["local_path"]))
            url_to_entry[file_url] = (
                local_file,
                str(att.get("declared_mime") or ""),
                str(att.get("expected_sha256") or ""),
            )
        by_year.setdefault(year, []).append(
            PartitionRecordSpec(
                page_url=page_url,
                source_record_id=str(item.get("source_record_id") or docid_from_url(page_url)),
                domain_candidate=str(item.get("domain_candidate") or "UNMAPPED"),
                issued_date_hint=str(item.get("issued_date") or ""),
                expected_html_sha256=str(item.get("html_sha256") or ""),
            )
        )

    def local_fetcher(url: str) -> FetchResult:
        if url not in url_to_entry:
            return FetchResult(url=url, status_code=404, body=b"", body_snippet=f"not in manual intake: {url}")
        local_path, declared_mime, expected_sha = url_to_entry[url]
        if not local_path.exists():
            return FetchResult(url=url, status_code=404, body=b"", body_snippet=f"missing file: {local_path.name}")
        return FetchResult(
            url=url,
            final_url=url,
            status_code=200,
            body=local_path.read_bytes(),
            declared_mime=declared_mime,
            expected_sha256=expected_sha,
        )

    staging_root = run_dir / "staging" / SRC03_SOURCE_ID
    real_root = staging_root / "real"
    real_root.mkdir(parents=True, exist_ok=True)
    real_manifests: list[dict[str, Any]] = []
    real_manifest_paths: list[Path] = []
    results: dict[str, dict[str, Any]] = {}
    for year in sorted(by_year):
        specs = by_year[year]
        partition_id = f"{source_id}__{year}"
        summary = run_src03_partition(
            staging_root=real_root,
            registry=registry,
            cutoff=cutoff,
            partition_id=partition_id,
            year=year,
            source_id=source_id,
            document_specs=specs,
            fetcher=local_fetcher,
            observed_at=cutoff.cutoff_vn,
            access_action="manual_download",
            purpose=purpose,
            data_class=data_class,
            region=region,
            document_type=document_type,
            probe_url=specs[0].page_url,
            probe_document_date=parse_vn_date(specs[0].issued_date_hint) or date(year, 1, 1),
            at=at,
            catalog_enumeration_complete=enumeration_flag,
        )
        results[partition_id] = summary
        manifest_path = Path(summary["partition_dir"]) / "partition-manifest.json"
        real_manifest_paths.append(manifest_path)
        real_manifests.append(_summary_from_manifest(manifest_path))

    worker_manifest = _worker_manifest(
        cutoff=cutoff,
        registry_revision=registry.revision,
        real_manifests=real_manifests,
        synthetic_manifests=[],
        quarantine_rows=_quarantine_rows(real_manifest_paths),
    )
    atomic_write_text(
        staging_root / "worker-manifest.json",
        json.dumps(worker_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )
    all_completed = bool(results) and all(item["status"] == "COMPLETED" for item in results.values())
    all_blocked = bool(results) and all(item["status"] == "BLOCKED_RIGHTS" for item in results.values())
    return {
        "run_id": cutoff.run_id,
        "source_id": source_id,
        "mode": "manual-intake",
        "registry_revision": registry.revision,
        "status": "COMPLETED" if all_completed else ("BLOCKED_RIGHTS" if all_blocked else "PARTIAL"),
        "results": results,
    }


def run_src03_automated_batch(
    *,
    run_dir: Path,
    cutoff: RunCutoff,
    registry_path: Path,
    batch_spec_path: Path,
    rate_limit_db: Path | None = None,
    fetcher: Callable[[str], Any] | None = None,
    rate_limiter: SharedRateLimiter | None = None,
    at: datetime | None = None,
    sleep_func: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """Run an authorized SRC-03 real automated batch with pagination, transport, and checkpointing."""
    run_dir = Path(run_dir)
    spec = json.loads(Path(batch_spec_path).read_text(encoding="utf-8"))
    source_id = str(spec.get("source_id") or SRC03_SOURCE_ID)
    purpose = str(spec.get("purpose") or "g1-pilot")
    data_class = str(spec.get("data_class") or "public")
    region = str(spec.get("region") or "VN")
    document_type = str(spec.get("document_type") or "regulation")
    registry = SourceRegistry(Path(registry_path))
    auth_time_fn = authorization_clock(source_id, cutoff.cutoff_datetime_vn, at=at)
    limiter = rate_limiter or SharedRateLimiter(
        per_source_max_per_minute=int(spec.get("per_source_max_per_minute", 20)),
        shared_infra_max_per_minute=int(spec.get("shared_infra_max_per_minute", 30)),
        state_path=rate_limit_db or (run_dir / "staging" / "shared-rate-limit.sqlite"),
    )
    staging_root = run_dir / "staging" / SRC03_SOURCE_ID
    real_root = staging_root / "real"
    real_root.mkdir(parents=True, exist_ok=True)
    real_manifests: list[dict[str, Any]] = []
    real_manifest_paths: list[Path] = []
    results: dict[str, dict[str, Any]] = {}

    for partition_spec in spec.get("partitions", []):
        year = int(partition_spec["year"])
        quarter = str(partition_spec.get("quarter") or "")
        partition_id = f"{source_id}__{year}" if not quarter else f"{source_id}__{year}__{quarter}"
        declared_enum = bool(partition_spec.get("catalog_enumeration_complete", False))
        listing_urls = [str(u) for u in partition_spec.get("listing_urls", [])]
        probe_date = parse_vn_date(str(partition_spec.get("probe_document_date") or "")) or date(year, 1, 1)
        max_pages = int(partition_spec.get("max_listing_pages", 50))

        def _make_transport(target_date: date) -> Callable[[str], Any]:
            if fetcher is not None:
                return fetcher

            def _guard_redirect(target_url: str) -> None:
                authorize_actions(
                    registry,
                    source_id=source_id,
                    actions=("automated_access",),
                    purpose=purpose,
                    data_class=data_class,
                    region=region,
                    document_type=document_type,
                    url=target_url,
                    document_date=target_date,
                    size_bytes=0,
                    at=auth_time_fn(),
                )

            return build_authorized_https_fetcher(on_redirect=_guard_redirect)

        active_fetcher = _make_transport(probe_date)
        discovered_specs: list[PartitionRecordSpec] = [
            PartitionRecordSpec(
                page_url=str(item["page_url"]),
                source_record_id=str(item.get("source_record_id") or docid_from_url(str(item["page_url"]))),
                domain_candidate=str(item.get("domain_candidate") or "UNMAPPED"),
                issued_date_hint=str(item.get("issued_date") or ""),
            )
            for item in partition_spec.get("documents", [])
        ]
        seen_urls = {item.page_url for item in discovered_specs}
        pagination_complete = True
        pagination_stop: tuple[str, str, str] | None = None

        if listing_urls:
            control = _NetworkControl(
                active_fetcher,
                limiter,
                registry=registry,
                source_id=source_id,
                access_action="automated_access",
                purpose=purpose,
                data_class=data_class,
                region=region,
                document_type=document_type,
                authorization_time_fn=auth_time_fn,
                sleep_func=sleep_func,
            )
            queue = list(listing_urls)
            visited_listings: set[str] = set()
            while queue and len(visited_listings) < max_pages:
                list_url = queue.pop(0)
                if list_url in visited_listings:
                    continue
                visited_listings.add(list_url)
                try:
                    resp = control.fetch(list_url, document_date=probe_date)
                except RightsDenied as denied:
                    pagination_complete = False
                    pagination_stop = ("BLOCKED_RIGHTS", f"BLOCKED_RIGHTS:{denied}", list_url)
                    break
                except NetworkPolicyStop as stop:
                    pagination_complete = False
                    pagination_stop = (stop.code, str(stop), list_url)
                    break
                parsed_listing = parse_src03_listing_html(
                    resp.body.decode("utf-8", errors="replace"),
                    base_url=resp.final_url or list_url,
                )
                for doc_url in parsed_listing["document_urls"]:
                    if doc_url not in seen_urls:
                        seen_urls.add(doc_url)
                        discovered_specs.append(
                            PartitionRecordSpec(
                                page_url=doc_url,
                                source_record_id=docid_from_url(doc_url),
                            )
                        )
                next_url = parsed_listing["next_page_url"]
                if next_url and next_url not in visited_listings:
                    queue.append(next_url)
            if queue:
                pagination_complete = False

        if pagination_stop is not None:
            stop_code, stop_msg, stop_url = pagination_stop
            part_dir = real_root / partition_id
            part_dir.mkdir(parents=True, exist_ok=True)
            cp = PartitionCheckpoint(
                source_id=source_id,
                partition_id=partition_id,
                year=year,
                quarter=quarter,
                owner_worker=OWNER_WORKER,
                status="BLOCKED_RIGHTS" if stop_code == "BLOCKED_RIGHTS" else "STOPPED",
                last_completed_cursor=0,
                rights_status="BLOCKED_RIGHTS" if stop_code == "BLOCKED_RIGHTS" else "APPROVED",
                rights_ref=stop_msg if stop_code == "BLOCKED_RIGHTS" else "",
                updated_at=cutoff.cutoff_vn,
            )
            manifest = _write_partition_outputs(
                part_dir,
                cp,
                cutoff,
                catalog_rows=[],
                artifact_rows=[],
                error_rows=[
                    _error_row(
                        cutoff=cutoff,
                        source_id=source_id,
                        partition_id=partition_id,
                        error_type=stop_code,
                        message=stop_msg,
                        url=stop_url,
                        observed_at=cutoff.cutoff_vn,
                    )
                ],
                data_origin="SYNTHETIC_FIXTURE" if source_id.startswith("FIXTURE-") else "REAL",
                observed_at=cutoff.cutoff_vn,
                requests_attempted=0,
                stop_reason=stop_code,
                access_action="automated_access",
                catalog_enumeration_complete=False,
            )
            results[partition_id] = {**manifest, "partition_dir": str(part_dir)}
            manifest_path = part_dir / "partition-manifest.json"
            real_manifest_paths.append(manifest_path)
            real_manifests.append(_summary_from_manifest(manifest_path))
            continue

        probe_url = discovered_specs[0].page_url if discovered_specs else (
            listing_urls[0] if listing_urls else SRC03_PORTAL_URL
        )
        summary = run_src03_partition(
            staging_root=real_root,
            registry=registry,
            cutoff=cutoff,
            partition_id=partition_id,
            year=year,
            quarter=quarter,
            source_id=source_id,
            document_specs=discovered_specs,
            fetcher=active_fetcher,
            rate_limiter=limiter,
            observed_at=cutoff.cutoff_vn,
            access_action="automated_access",
            purpose=purpose,
            data_class=data_class,
            region=region,
            document_type=document_type,
            probe_url=probe_url,
            probe_document_date=probe_date,
            at_fn=auth_time_fn,
            sleep_func=sleep_func,
            catalog_enumeration_complete=(declared_enum and pagination_complete),
        )
        results[partition_id] = summary
        manifest_path = Path(summary["partition_dir"]) / "partition-manifest.json"
        real_manifest_paths.append(manifest_path)
        real_manifests.append(_summary_from_manifest(manifest_path))

    worker_manifest = _worker_manifest(
        cutoff=cutoff,
        registry_revision=registry.revision,
        real_manifests=real_manifests,
        synthetic_manifests=[],
        quarantine_rows=_quarantine_rows(real_manifest_paths),
    )
    atomic_write_text(
        staging_root / "worker-manifest.json",
        json.dumps(worker_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )
    all_completed = bool(results) and all(item["status"] == "COMPLETED" for item in results.values())
    all_blocked = bool(results) and all(item["status"] == "BLOCKED_RIGHTS" for item in results.values())
    return {
        "run_id": cutoff.run_id,
        "source_id": source_id,
        "mode": "real-automated",
        "registry_revision": registry.revision,
        "status": "COMPLETED" if all_completed else ("BLOCKED_RIGHTS" if all_blocked else "PARTIAL"),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--cutoff-vn", required=True)
    parser.add_argument("--cutoff-utc", required=True)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--rights", "--registry", dest="rights", default="experiments/g1/source-rights.json")
    parser.add_argument(
        "--mode",
        choices=("pilot-fixture", "manual-intake", "real-automated"),
        default="pilot-fixture",
    )
    parser.add_argument("--intake-manifest", default="")
    parser.add_argument("--batch-spec", default="")
    parser.add_argument("--rate-limit-db", default="")
    arguments = parser.parse_args(argv)

    cutoff = RunCutoff(
        run_id=arguments.run_id,
        cutoff_utc=arguments.cutoff_utc,
        cutoff_vn=arguments.cutoff_vn,
    )
    run_dir = Path(arguments.run_dir)
    registry_path = Path(arguments.rights)

    if arguments.mode == "manual-intake":
        intake_path = (
            Path(arguments.intake_manifest)
            if arguments.intake_manifest
            else run_dir / "manual-intake" / SRC03_SOURCE_ID / "intake-manifest.json"
        )
        result = run_src03_manual_intake(
            run_dir=run_dir,
            cutoff=cutoff,
            registry_path=registry_path,
            intake_manifest_path=intake_path,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if result["status"] in {"COMPLETED", "BLOCKED_RIGHTS"} else 1

    if arguments.mode == "real-automated":
        if not arguments.batch_spec:
            parser.error("--batch-spec is required with --mode real-automated")
        result = run_src03_automated_batch(
            run_dir=run_dir,
            cutoff=cutoff,
            registry_path=registry_path,
            batch_spec_path=Path(arguments.batch_spec),
            rate_limit_db=Path(arguments.rate_limit_db) if arguments.rate_limit_db else None,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if result["status"] in {"COMPLETED", "BLOCKED_RIGHTS"} else 1

    registry = SourceRegistry(registry_path)
    staging_root = run_dir / "staging" / SRC03_SOURCE_ID

    limiter = SharedRateLimiter(
        per_source_max_per_minute=60,
        shared_infra_max_per_minute=120,
        state_path=Path(arguments.rate_limit_db) if arguments.rate_limit_db else None,
    )

    real_manifests: list[dict[str, Any]] = []
    real_manifest_paths: list[Path] = []
    for year in range(2020, 2027):
        partition_id = f"{SRC03_SOURCE_ID}__{year}"
        summary = run_src03_partition(
            staging_root=staging_root / "real-blocked",
            registry=registry,
            cutoff=cutoff,
            partition_id=partition_id,
            year=year,
            source_id=SRC03_SOURCE_ID,
            rate_limiter=limiter,
            observed_at=cutoff.cutoff_vn,
        )
        manifest_path = Path(summary["partition_dir"]) / "partition-manifest.json"
        real_manifest_paths.append(manifest_path)
        real_manifests.append(_summary_from_manifest(manifest_path))

    synthetic_root = staging_root / "synthetic"
    suite = build_src03_synthetic_fixtures(synthetic_root / "fixtures")
    pilot = run_src03_synthetic_pilot(
        synthetic_root,
        cutoff,
        suite=suite,
        rate_limiter=limiter,
        observed_at=cutoff.cutoff_vn,
    )
    synthetic_manifests: list[dict[str, Any]] = []
    synthetic_manifest_paths: list[Path] = []
    for summary in pilot["partitions"]:
        manifest_path = Path(summary["partition_dir"]) / "partition-manifest.json"
        synthetic_manifest_paths.append(manifest_path)
        synthetic_manifests.append(_summary_from_manifest(manifest_path))

    worker_manifest = _worker_manifest(
        cutoff=cutoff,
        registry_revision=registry.revision,
        real_manifests=real_manifests,
        synthetic_manifests=synthetic_manifests,
        quarantine_rows=_quarantine_rows(synthetic_manifest_paths),
    )
    worker_manifest_path = staging_root / "worker-manifest.json"
    atomic_write_text(
        worker_manifest_path,
        json.dumps(worker_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )

    summary = {
        "run_id": cutoff.run_id,
        "source_id": SRC03_SOURCE_ID,
        "registry_revision": registry.revision,
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
        "real_partitions_blocked": worker_manifest["aggregate"]["real_partitions_blocked"],
        "real_network_requests": worker_manifest["aggregate"]["real_network_requests"],
        "synthetic_partitions_completed": worker_manifest["aggregate"][
            "synthetic_partitions_completed"
        ],
        "synthetic_partitions_complete": worker_manifest["aggregate"][
            "synthetic_partitions_complete"
        ],
        "synthetic_records": worker_manifest["aggregate"]["synthetic_counts"][
            "records_observed"
        ],
        "synthetic_artifacts": worker_manifest["aggregate"]["synthetic_counts"][
            "artifacts_total"
        ],
        "synthetic_quarantined": worker_manifest["aggregate"]["synthetic_counts"][
            "artifacts_quarantined"
        ],
        "worker_manifest": str(worker_manifest_path),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))

    all_blocked = all(item["status"] == "BLOCKED_RIGHTS" for item in real_manifests)
    all_completed = all(
        canonical_partition_status(item["status"]) == "COMPLETED" for item in synthetic_manifests
    )
    return 0 if all_blocked and all_completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
