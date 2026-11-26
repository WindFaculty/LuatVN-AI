"""SRC-01 (Công báo điện tử) adapter: rights-gated, checkpointed pilot staging.

The live portal is PENDING_RIGHTS in experiments/g1/source-rights.json, so no live
request is ever issued here. The complete pipeline is exercised through the
deterministic SYNTHETIC_FIXTURE registry and fixture HTML/blob payloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import parse_qs, quote, urljoin, urlsplit

from .pilot_schema import (
    ALL_DOMAIN_LABELS,
    ARTIFACT_RECORD_FIELDS,
    CATALOG_RECORD_FIELDS,
    ArtifactRecord,
    CatalogRecord,
    HttpTransportResponse,
    NetworkPolicyStop,
    PartitionCheckpoint,
    RunCutoff,
    SharedRateLimiter,
    atomic_write_bytes,
    atomic_write_text,
    authorize_actions,
    build_authorized_https_fetcher,
    check_source_actions,
    classify_http_stop,
    evaluate_date_window,
    load_checkpoint,
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

SRC01_SOURCE_ID = "SRC-01"
FIXTURE_SOURCE_ID = "FIXTURE-SRC-01"
SRC01_HOSTS = frozenset({"congbao.chinhphu.vn", "g7.cdnchinhphu.vn"})
INFRA_GROUP = "chinhphu.vn"
DEFAULT_SOURCE_URL = "https://congbao.chinhphu.vn/"
SHAREABLE_PDF_BYTES = b"%PDF-1.4\n%SYNTH-SHARED-78-2025-ND-CP-V1\n%%EOF\n"

FILE_TYPE_MIME = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "html": "text/html",
    "htm": "text/html",
    "txt": "text/plain",
}
ERROR_FIELDS = (
    "source_id",
    "source_record_id",
    "partition_id",
    "data_origin",
    "page_url",
    "file_url",
    "attachment_id",
    "code",
    "message",
    "observed_at",
    "cutoff_utc",
    "cutoff_vn",
)

_METADATA_LABELS = {
    "cơ quan ban hành": "issuer",
    "loại văn bản": "document_type",
    "số ký hiệu": "document_number",
    "số, ký hiệu": "document_number",
    "số hiệu": "document_number",
    "ngày ban hành": "issued_date",
    "ngày đăng công báo": "gazette_published_date",
    "ngày công báo": "gazette_published_date",
    "ngày hiệu lực": "observed_effective_date",
    "ngày có hiệu lực": "observed_effective_date",
    "công báo số": "gazette_issue",
    "số công báo": "gazette_issue",
    "trang": "gazette_page",
    "trang công báo": "gazette_page",
    "trích yếu": "title",
}
_DATA_FIELDS = {
    "data-document-number": "document_number",
    "data-document-type": "document_type",
    "data-issuer": "issuer",
    "data-issued-date": "issued_date",
    "data-gazette-published-date": "gazette_published_date",
    "data-observed-effective-date": "observed_effective_date",
    "data-gazette-issue": "gazette_issue",
    "data-gazette-page": "gazette_page",
    "data-title": "title",
    "data-source-record-id": "source_record_id",
    "data-parent-id": "parent_id",
}
_PARSED_FIELDS = (
    "document_number",
    "document_type",
    "issuer",
    "issued_date",
    "gazette_published_date",
    "observed_effective_date",
    "title",
    "gazette_issue",
    "gazette_page",
)
_CONTINUATION_RE = re.compile(r"^\d+(?:\s*\+\s*\d+)*$")
_RECORD_ID_RE = re.compile(r"/(\d+)\.htm(?:$|[?#])")
_PARENT_ID_RE = re.compile(r"-(\d+)/[^/]+\.htm(?:$|[?#])")


@dataclass(frozen=True)
class FetchResponse:
    """Pluggable fetcher result; future authorized clients can map HTTP/TLS errors."""

    status_code: int | None
    body: bytes = b""
    retry_after: str | None = None
    tls_error: str | None = None
    message: str = ""
    final_url: str = ""
    redirect_urls: tuple[str, ...] = ()


class _PartitionStop(Exception):
    def __init__(self, code: str, message: str, *, url: str = "", attachment_id: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message
        self.url = url
        self.attachment_id = attachment_id


class _DocumentHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.rows: list[list[str]] = []
        self.anchors: list[dict[str, Any]] = []
        self.h1: list[str] = []
        self.title: list[str] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._anchor: dict[str, Any] | None = None
        self._h1_depth = 0
        self._title_depth = 0
        self._div_depth = 0
        self._focus_depth: int | None = None
        self._detail_row_depth: int | None = None
        self._detail_value_depth: int | None = None
        self._detail_label: list[str] | None = None
        self._detail_label_open = False
        self._detail_value: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): (value or "") for key, value in attrs}
        classes = attributes.get("class", "").split()
        if tag == "div":
            self._div_depth += 1
            if "document--focus" in classes:
                self._focus_depth = self._div_depth
            elif self._focus_depth is not None and self._detail_row_depth is None and "row" in classes:
                self._detail_row_depth = self._div_depth
                self._detail_label = None
                self._detail_value = []
            elif self._detail_row_depth is not None and "value" in classes:
                self._detail_value_depth = self._div_depth
        elif tag == "span" and self._detail_row_depth is not None and "name" in classes:
            self._detail_label = []
            self._detail_label_open = True
        for key, value in attributes.items():
            if key.startswith("data-") and value and key not in self.meta:
                self.meta[key] = value
        if tag == "tr":
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")
        elif tag == "h1":
            self._h1_depth += 1
        elif tag == "title":
            self._title_depth += 1
        elif tag == "a":
            self._anchor = {"href": attributes.get("href", ""), "text": [], "attrs": attributes}

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "div":
            if self._div_depth == self._detail_value_depth:
                self._detail_value_depth = None
            if self._div_depth == self._detail_row_depth:
                if self._detail_label and self._detail_value:
                    self.rows.append(["".join(self._detail_label), "".join(self._detail_value)])
                self._detail_row_depth = None
                self._detail_label = None
                self._detail_label_open = False
            if self._div_depth == self._focus_depth:
                self._focus_depth = None
            self._div_depth = max(0, self._div_depth - 1)
        elif tag == "span":
            self._detail_label_open = False
        if tag in {"th", "td"} and self._cell is not None and self._row is not None:
            self._row.append(normalize_text_nfc("".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None
        elif tag == "h1":
            self._h1_depth = max(0, self._h1_depth - 1)
        elif tag == "title":
            self._title_depth = max(0, self._title_depth - 1)
        elif tag == "a" and self._anchor is not None:
            self._anchor["text"] = normalize_text_nfc("".join(self._anchor["text"]))
            self.anchors.append(self._anchor)
            self._anchor = None

    def handle_data(self, data: str) -> None:
        if self._detail_value_depth is not None:
            self._detail_value.append(data)
        elif self._detail_label_open and self._detail_label is not None:
            self._detail_label.append(data)
        if self._cell is not None:
            self._cell.append(data)
        if self._anchor is not None:
            self._anchor["text"].append(data)
        if self._h1_depth:
            self.h1.append(data)
        if self._title_depth:
            self.title.append(data)


def _record_id_from_url(page_url: str) -> str:
    path = urlsplit(page_url).path
    match = _RECORD_ID_RE.search(path) or re.search(r"-(\d+)\.htm$", path)
    if match:
        return match.group(1)
    return hashlib.sha256(page_url.encode("utf-8")).hexdigest()[:16]


def _parent_id_from_url(page_url: str) -> str:
    match = _PARENT_ID_RE.search(urlsplit(page_url).path)
    return match.group(1) if match else ""


def _file_type(file_name: str) -> str:
    return file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""


def _attachment_from_anchor(anchor: Mapping[str, Any], page_url: str, source_record_id: str) -> dict | None:
    href = str(anchor.get("href", "")).strip()
    parts = urlsplit(href)
    if parts.scheme not in {"http", "https"} or parts.netloc.lower() not in SRC01_HOSTS:
        return None
    query = parse_qs(parts.query, keep_blank_values=True)
    file_name = (query.get("file_name") or [""])[0]
    if not file_name:
        file_name = parts.path.rsplit("/", 1)[-1]
    file_type = _file_type(file_name)
    if file_type not in FILE_TYPE_MIME or file_type in {"html", "htm"}:
        return None
    attrs = anchor.get("attrs", {})
    attachment_id = attrs.get("data-attachment-id") or f"att-{sha256_bytes(href.encode('utf-8'))[:12]}"
    parent_id = attrs.get("data-parent-id") or _parent_id_from_url(page_url) or source_record_id
    return {
        "attachment_id": attachment_id,
        "parent_id": parent_id,
        "file_url": href,
        "file_name": file_name,
        "file_type": file_type,
        "declared_mime": FILE_TYPE_MIME[file_type],
    }


def parse_src01_document_html(
    html: str,
    *,
    page_url: str = "",
    source_record_id: str = "",
) -> dict[str, Any]:
    """Parse a Công báo document page into catalog metadata + attachments."""
    parser = _DocumentHTMLParser()
    parser.feed(html)
    parser.close()

    fields: dict[str, str] = {field: "" for field in _PARSED_FIELDS}
    for data_key, field in _DATA_FIELDS.items():
        if data_key in parser.meta:
            fields[field] = normalize_text_nfc(parser.meta[data_key])
    for row in parser.rows:
        if len(row) < 2:
            continue
        label = normalize_text_nfc(row[0]).casefold().rstrip(":")
        field = _METADATA_LABELS.get(label)
        if field and row[1]:
            fields[field] = normalize_text_nfc(row[1])

    heading = normalize_text_nfc("".join(parser.h1))
    if heading:
        fields["title"] = heading
    elif not fields["title"]:
        fields["title"] = normalize_text_nfc("".join(parser.title))

    record_id = source_record_id or normalize_text_nfc(parser.meta.get("data-source-record-id", ""))
    if not record_id:
        record_id = _record_id_from_url(page_url)
    parent_id = normalize_text_nfc(parser.meta.get("data-parent-id", "")) or _parent_id_from_url(page_url)

    continuation_links: list[dict[str, str]] = []
    seen_continuations: set[tuple[str, str]] = set()
    attachments: list[dict[str, str]] = []
    seen_attachments: set[str] = set()
    for anchor in parser.anchors:
        href = str(anchor.get("href", "")).strip()
        text = str(anchor.get("text", ""))
        link = urljoin(page_url or DEFAULT_SOURCE_URL, href)
        host = urlsplit(link).hostname
        if (host in {"congbao.chinhphu.vn", "www.congbao.chinhphu.vn"}
                and _CONTINUATION_RE.fullmatch(text)
                and _parent_id_from_url(link) == (parent_id or record_id)):
            issue = re.sub(r"\s*\+\s*", " + ", text)
            if (issue, link) not in seen_continuations:
                seen_continuations.add((issue, link))
                continuation_links.append({"issue": issue, "url": link})
        attachment = _attachment_from_anchor(anchor, page_url, record_id)
        if attachment is not None and attachment["file_url"] not in seen_attachments:
            seen_attachments.add(attachment["file_url"])
            attachments.append(attachment)

    if not fields["gazette_issue"]:
        issues = [link["issue"] for link in continuation_links if _record_id_from_url(link["url"]) == record_id]
        if issues or len(continuation_links) == 1:
            fields["gazette_issue"] = issues[0] if issues else continuation_links[0]["issue"]

    return {
        "source_record_id": record_id,
        "page_url": page_url,
        "parent_id": parent_id,
        **fields,
        "continuation_issues": [link["issue"] for link in continuation_links],
        "continuation_links": continuation_links,
        "attachments": attachments,
    }


def parse_src01_listing_html(html: str, *, base_url: str = DEFAULT_SOURCE_URL) -> dict[str, Any]:
    """Parse a Công báo listing page into ordered document page URLs and optional next page URL."""
    parser = _DocumentHTMLParser()
    parser.feed(html)
    parser.close()
    document_urls: list[str] = []
    seen_docs: set[str] = set()
    next_page_url = ""
    for anchor in parser.anchors:
        raw_href = str(anchor.get("href", "")).strip()
        if not raw_href or raw_href.lower().startswith("javascript:"):
            continue
        href = urljoin(base_url, raw_href)
        parts = urlsplit(href)
        host = parts.netloc.lower()
        attrs = anchor.get("attrs", {})
        rel = str(attrs.get("rel", "")).casefold()
        css_class = str(attrs.get("class", "")).casefold()
        text = str(anchor.get("text", "")).casefold()
        if host in {"congbao.chinhphu.vn", "www.congbao.chinhphu.vn"}:
            if not next_page_url and (
                "next" in rel.split()
                or "next-page" in css_class
                or text in {"tiếp", "trang sau", "next", ">"}
            ):
                next_page_url = href
            if "/van-ban/" in parts.path and _RECORD_ID_RE.search(parts.path):
                if href not in seen_docs:
                    seen_docs.add(href)
                    document_urls.append(href)
    return {"document_urls": document_urls, "next_page_url": next_page_url}


# ---------------------------------------------------------------------------
# Synthetic fixture suite
# ---------------------------------------------------------------------------

def _pdf_bytes(label: str) -> bytes:
    return f"%PDF-1.4\n%SYNTH-{label}\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n".encode("utf-8")


def _doc_bytes(label: str) -> bytes:
    return b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + f"SYNTH-DOC-{label}\n".encode("utf-8")


def _cdn_url(token: str, file_name: str) -> str:
    return (
        "https://g7.cdnchinhphu.vn/api/download/stream?Url="
        + quote(token, safe="-_.~")
        + "&file_name="
        + quote(file_name, safe="")
    )


def _render_document_html(
    document: Mapping[str, str],
    *,
    page_url: str,
    parent_id: str,
    continuation_links: Iterable[Mapping[str, str]],
    attachments: Iterable[Mapping[str, str]],
) -> str:
    rows = (
        ("Số ký hiệu", document["document_number"]),
        ("Loại văn bản", document["document_type"]),
        ("Cơ quan ban hành", document["issuer"]),
        ("Ngày ban hành", document["issued_date"]),
        ("Ngày đăng Công báo", document["gazette_published_date"]),
        ("Ngày hiệu lực", document["observed_effective_date"]),
        ("Công báo số", document["gazette_issue"]),
        ("Trang", document["gazette_page"]),
        ("Trích yếu", document["title"]),
    )
    table = "\n".join(
        f"      <tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>" for label, value in rows
    )
    continuations = "\n".join(
        f'      <a class="gazette-continuation" href="{escape(link["url"], quote=True)}">'
        f'{escape(link["issue"])}</a>'
        for link in continuation_links
    )
    attachment_links = "\n".join(
        f'      <a class="attachment" data-attachment-id="{escape(item["attachment_id"], quote=True)}" '
        f'data-parent-id="{escape(parent_id, quote=True)}" '
        f'href="{escape(item["file_url"], quote=True)}">{escape(item["file_name"])}</a>'
        for item in attachments
    )
    return (
        "<!DOCTYPE html>\n<html lang=\"vi\">\n<head><meta charset=\"utf-8\">"
        f"<title>{escape(document['title'])}</title></head>\n<body>\n"
        f'  <div id="document-detail" data-source-record-id="{escape(document["source_record_id"], quote=True)}" '
        f'data-parent-id="{escape(parent_id, quote=True)}" data-issued-date="{escape(document["issued_date"], quote=True)}">\n'
        f"    <h1>{escape(document['title'])}</h1>\n"
        f"    <p class=\"page-url\">{escape(page_url)}</p>\n"
        "    <table class=\"document-metadata\">\n"
        f"{table}\n"
        "    </table>\n"
        "    <nav class=\"gazette-continuations\">\n"
        f"{continuations}\n"
        "    </nav>\n"
        "    <div class=\"attachments\">\n"
        f"{attachment_links}\n"
        "    </div>\n"
        "  </div>\n</body>\n</html>\n"
    )


def _make_fixture_document(
    *,
    source_record_id: str,
    slug: str,
    parent_id: str,
    partition_year: int,
    domain_candidate: str,
    relation_role: str,
    document_number: str,
    document_type: str,
    issuer: str,
    issued_date: str,
    gazette_published_date: str,
    observed_effective_date: str,
    title: str,
    gazette_issue: str,
    gazette_page: str,
    continuation_links: Iterable[tuple[str, str]] = (),
    related_to_document_number: str = "",
    attachments: Iterable[tuple[str, str, str, str, bytes]] = (),
    blobs: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    page_url = f"https://congbao.chinhphu.vn/van-ban/{slug}-{parent_id}/{source_record_id}.htm"
    attachment_rows = []
    expected_sha256: dict[str, str] = {}
    for attachment_id, token, file_name, file_type, payload in attachments:
        file_url = _cdn_url(token, file_name)
        if blobs is not None:
            blobs[file_url] = payload
        attachment_rows.append(
            {
                "attachment_id": attachment_id,
                "file_url": file_url,
                "file_name": file_name,
                "file_type": file_type,
            }
        )
        if payload:
            expected_sha256[attachment_id] = sha256_bytes(payload)
    continuation = [{"issue": issue, "url": url} for issue, url in continuation_links]
    document = {
        "source_record_id": source_record_id,
        "page_url": page_url,
        "partition_year": partition_year,
        "domain_candidate": domain_candidate,
        "relation_role": relation_role,
        "version": "v1",
        "related_to_document_number": related_to_document_number,
        "document_number": document_number,
        "document_type": document_type,
        "issuer": issuer,
        "issued_date": issued_date,
        "gazette_published_date": gazette_published_date,
        "observed_effective_date": observed_effective_date,
        "title": title,
        "gazette_issue": gazette_issue,
        "gazette_page": gazette_page,
        "expected_sha256_by_attachment_id": expected_sha256,
    }
    document["html"] = _render_document_html(
        document,
        page_url=page_url,
        parent_id=parent_id,
        continuation_links=continuation,
        attachments=attachment_rows,
    )
    document["attachment_urls"] = [row["file_url"] for row in attachment_rows]
    return document


def build_src01_synthetic_fixtures(*, source_id: str = FIXTURE_SOURCE_ID) -> dict[str, Any]:
    """Build deterministic synthetic Công báo HTML pages and blob payloads."""
    del source_id  # URLs stay on the real portal/CDN hosts; the registry is fixture-only.
    blobs: dict[str, bytes] = {}

    def pdf(label: str) -> bytes:
        return _pdf_bytes(label)

    def doc(label: str) -> bytes:
        return _doc_bytes(label)

    documents = [
        _make_fixture_document(
            source_record_id="50059",
            slug="synthetic-luat-so-59-2020-qh14",
            parent_id="50001",
            partition_year=2020,
            domain_candidate="BUS",
            relation_role="gazette_publication",
            document_number="59/2020/QH14",
            document_type="Luật",
            issuer="QUỐC HỘI",
            issued_date="17/06/2020",
            gazette_published_date="24/06/2020",
            observed_effective_date="01/01/2021",
            title="Luật số 59/2020/QH14 về đầu tư công (mô hình tổng hợp)",
            gazette_issue="123/2020",
            gazette_page="1-20",
            attachments=(
                (
                    "att-50059-pdf",
                    "SYNTH-59-2020-QH14-PDF",
                    "2020_123_59-2020-QH14.pdf",
                    "pdf",
                    pdf("59-2020-QH14"),
                ),
                (
                    "att-50059-doc",
                    "SYNTH-59-2020-QH14-DOC",
                    "2020_123_59-2020-QH14.doc",
                    "doc",
                    doc("59-2020-QH14"),
                ),
            ),
            blobs=blobs,
        ),
        _make_fixture_document(
            source_record_id="30091",
            slug="synthetic-bo-luat-so-91-2015-qh13",
            parent_id="30001",
            partition_year=2020,
            domain_candidate="CIV",
            relation_role="pre_2020_reference",
            related_to_document_number="59/2020/QH14",
            document_number="91/2015/QH13",
            document_type="Bộ luật",
            issuer="QUỐC HỘI",
            issued_date="24/11/2015",
            gazette_published_date="30/11/2015",
            observed_effective_date="01/01/2017",
            title="Bộ luật số 91/2015/QH13 - Bộ luật Dân sự (mô hình tổng hợp)",
            gazette_issue="200/2015",
            gazette_page="1-50",
            attachments=(
                (
                    "att-30091-pdf",
                    "SYNTH-91-2015-QH13-PDF",
                    "2015_200_91-2015-QH13.pdf",
                    "pdf",
                    pdf("91-2015-QH13"),
                ),
            ),
            blobs=blobs,
        ),
        _make_fixture_document(
            source_record_id="55991",
            slug="synthetic-nghi-dinh-so-78-2025-nd-cp",
            parent_id="44704",
            partition_year=2025,
            domain_candidate="ADM",
            relation_role="gazette_publication",
            document_number="78/2025/NĐ-CP",
            document_type="Nghị định",
            issuer="CHÍNH PHỦ",
            issued_date="01/04/2025",
            gazette_published_date="03/04/2025",
            observed_effective_date="01/04/2025",
            title=(
                "Nghị định số 78/2025/NĐ-CP quy định chi tiết một số điều và biện pháp để tổ chức, "
                "hướng dẫn thi hành Luật Ban hành văn bản quy phạm pháp luật (mô hình tổng hợp)"
            ),
            gazette_issue="649+650/2025",
            gazette_page="1-52",
            continuation_links=(
                (
                    "649 + 650",
                    "https://congbao.chinhphu.vn/van-ban/synthetic-nghi-dinh-so-78-2025-nd-cp-44704/56011.htm",
                ),
                (
                    "651 + 652",
                    "https://congbao.chinhphu.vn/van-ban/synthetic-nghi-dinh-so-78-2025-nd-cp-44704/55988.htm",
                ),
                (
                    "653 + 654",
                    "https://congbao.chinhphu.vn/van-ban/synthetic-nghi-dinh-so-78-2025-nd-cp-44704/55991.htm",
                ),
            ),
            attachments=(
                (
                    "att-55991-649-650-pdf",
                    "SYNTH-78-2025-649-650-PDF",
                    "2025_649 + 650_78-2025-NĐ-CP.pdf",
                    "pdf",
                    SHAREABLE_PDF_BYTES,
                ),
                (
                    "att-55991-649-650-doc",
                    "SYNTH-78-2025-649-650-DOC",
                    "2025_649 + 650_78-2025-NĐ-CP.doc",
                    "doc",
                    doc("78-2025-649-650"),
                ),
                (
                    "att-55991-651-652-pdf",
                    "SYNTH-78-2025-651-652-PDF",
                    "2025_651 + 652_78-2025-NĐ-CP.pdf",
                    "pdf",
                    pdf("78-2025-651-652"),
                ),
                (
                    "att-55991-651-652-doc",
                    "SYNTH-78-2025-651-652-DOC",
                    "2025_651 + 652_78-2025-NĐ-CP.doc",
                    "doc",
                    doc("78-2025-651-652"),
                ),
                (
                    "att-55991-653-654-pdf",
                    "SYNTH-78-2025-653-654-PDF",
                    "2025_653 + 654_78-2025-NĐ-CP.pdf",
                    "pdf",
                    pdf("78-2025-653-654"),
                ),
                (
                    "att-55991-653-654-doc",
                    "SYNTH-78-2025-653-654-DOC",
                    "2025_653 + 654_78-2025-NĐ-CP.doc",
                    "doc",
                    doc("78-2025-653-654"),
                ),
            ),
            blobs=blobs,
        ),
        _make_fixture_document(
            source_record_id="56000",
            slug="synthetic-thong-tu-so-99-2025-tt-btnmt",
            parent_id="44800",
            partition_year=2025,
            domain_candidate="ENV",
            relation_role="gazette_publication",
            document_number="99/2025/TT-BTNMT",
            document_type="Thông tư",
            issuer="BỘ TÀI NGUYÊN VÀ MÔI TRƯỜNG",
            issued_date="10/09/2025",
            gazette_published_date="15/09/2025",
            observed_effective_date="01/11/2025",
            title="Thông tư số 99/2025/TT-BTNMT quy định về bảo vệ môi trường (mô hình tổng hợp)",
            gazette_issue="700/2025",
            gazette_page="",
            attachments=(
                (
                    "att-56000-pdf",
                    "SYNTH-99-2025-BTNMT-PDF",
                    "2025_700_99-2025-TT-BTNMT.pdf",
                    "pdf",
                    pdf("99-2025-BTNMT"),
                ),
                (
                    "att-56000-truncated",
                    "SYNTH-99-2025-BTNMT-TRUNCATED",
                    "2025_700_99-2025-TT-BTNMT-phu-luc.pdf",
                    "pdf",
                    b"%PDF-1.4\n%SYNTH-TRUNCATED-99-2025-BTNMT\n1 0 obj\n<< /Type /Catalog >>",
                ),
            ),
            blobs=blobs,
        ),
        _make_fixture_document(
            source_record_id="56001",
            slug="synthetic-quyet-dinh-so-101-2025-qd-ttg",
            parent_id="44801",
            partition_year=2025,
            domain_candidate="TRA",
            relation_role="gazette_publication",
            document_number="101/2025/QĐ-TTg",
            document_type="Quyết định",
            issuer="THỦ TƯỚNG CHÍNH PHỦ",
            issued_date="20/10/2025",
            gazette_published_date="18/10/2025",
            observed_effective_date="01/11/2025",
            title="Quyết định số 101/2025/QĐ-TTg về phê duyệt kế hoạch (mô hình tổng hợp)",
            gazette_issue="710/2025",
            gazette_page="5-8",
            attachments=(
                (
                    "att-56001-doc",
                    "SYNTH-101-2025-QD-TTG-DOC",
                    "2025_710_101-2025-QD-TTg.doc",
                    "doc",
                    doc("101-2025-QD-TTg"),
                ),
                (
                    "att-56001-mime-mismatch",
                    "SYNTH-101-2025-QD-TTG-MISMATCH",
                    "2025_710_101-2025-QD-TTg.pdf",
                    "pdf",
                    "Tệp văn bản thuần, không phải PDF.\n".encode("utf-8"),
                ),
            ),
            blobs=blobs,
        ),
        _make_fixture_document(
            source_record_id="57011",
            slug="synthetic-nghi-dinh-so-413-2026-nd-cp",
            parent_id="47615",
            partition_year=2026,
            domain_candidate="LND",
            relation_role="amending",
            related_to_document_number="104/2025/NĐ-CP",
            document_number="413/2026/NĐ-CP",
            document_type="Nghị định",
            issuer="CHÍNH PHỦ",
            issued_date="16/11/2026",
            gazette_published_date="26/11/2026",
            observed_effective_date="16/11/2026",
            title=(
                "Nghị định số 413/2026/NĐ-CP sửa đổi, bổ sung một số điều của Nghị định số "
                "104/2025/NĐ-CP (mô hình tổng hợp)"
            ),
            gazette_issue="588/2026",
            gazette_page="1-10",
            attachments=(
                (
                    "att-57011-pdf",
                    "SYNTH-413-2026-ND-CP-PDF",
                    "2026_588_413-2026-ND-CP.pdf",
                    "pdf",
                    pdf("413-2026-ND-CP"),
                ),
                (
                    "att-57011-doc",
                    "SYNTH-413-2026-ND-CP-DOC",
                    "2026_588_413-2026-ND-CP.doc",
                    "doc",
                    doc("413-2026-ND-CP"),
                ),
            ),
            blobs=blobs,
        ),
        _make_fixture_document(
            source_record_id="57012",
            slug="synthetic-nghi-dinh-so-414-2026-nd-cp",
            parent_id="47616",
            partition_year=2026,
            domain_candidate="LND",
            relation_role="amending",
            related_to_document_number="413/2026/NĐ-CP",
            document_number="414/2026/NĐ-CP",
            document_type="Nghị định",
            issuer="CHÍNH PHỦ",
            issued_date="27/11/2026",
            gazette_published_date="28/11/2026",
            observed_effective_date="27/11/2026",
            title="Nghị định số 414/2026/NĐ-CP (mô hình tổng hợp, sau cutoff)",
            gazette_issue="589/2026",
            gazette_page="1-4",
            attachments=(
                (
                    "att-57012-pdf",
                    "SYNTH-414-2026-ND-CP-PDF",
                    "2026_589_414-2026-ND-CP.pdf",
                    "pdf",
                    pdf("414-2026-ND-CP"),
                ),
            ),
            blobs=blobs,
        ),
    ]
    page_urls = [document["page_url"] for document in documents]
    attachment_urls = [url for document in documents for url in document["attachment_urls"]]
    return {
        "source_id": FIXTURE_SOURCE_ID,
        "documents": documents,
        "blobs": blobs,
        "page_urls": page_urls,
        "attachment_urls": attachment_urls,
        "shared_pdf_sha256": sha256_bytes(SHAREABLE_PDF_BYTES),
        "partition_years": sorted({document["partition_year"] for document in documents}),
    }


def build_fixture_registry_payload(
    *,
    source_ids: Iterable[str],
    urls: Iterable[str],
    revision: str = "g1-src01-fixture-v1",
    actions: Iterable[str] = ("automated_access", "store"),
    max_bytes_per_item: int = 8 * 1024 * 1024,
    max_actions_per_minute: int = 120,
    approved_at: str = "2020-01-01T00:00:00Z",
    expires_at: str = "2040-01-01T00:00:00Z",
    document_from: str = "2015-01-01",
    document_through: str = "2026-12-31",
    data_class: str = "synthetic",
) -> dict[str, Any]:
    """Build a test-only registry approving synthetic access/store for fixture URLs."""
    scope_urls = sorted({*urls, DEFAULT_SOURCE_URL})
    policy = {
        "status": "APPROVED",
        "evidence_ref": "SYNTHETIC-FIXTURE-ONLY",
        "approved_by": "test-fixture",
        "policy_url": "https://congbao.chinhphu.vn/synthetic-fixture-policy",
        "policy_version": "fixture-1",
        "policy_date": "2020-01-01",
        "approved_at": approved_at,
        "expires_at": expires_at,
        "revocation_procedure": "delete this fixture registry",
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
    sources = {}
    for source_id in sorted(set(source_ids)):
        sources[source_id] = {
            "name": f"Synthetic fixture source {source_id} (test-only)",
            "url": DEFAULT_SOURCE_URL,
            "owner": "fixture-owner",
            "contact": "fixture-only",
            "actions": {action: json.loads(json.dumps(policy)) for action in actions},
        }
    return {"revision": revision, "sources": sources}


# ---------------------------------------------------------------------------
# Rights-gated partition runner
# ---------------------------------------------------------------------------

@dataclass
class _RunContext:
    source_id: str
    partition_id: str
    partition_year: int
    data_origin: str
    partition_dir: Path
    cutoff: RunCutoff
    registry: SourceRegistry
    access_action: str
    purpose: str
    data_class: str
    region: str
    document_type: str
    authorization_time_fn: Callable[[], datetime]
    rights_ref: str
    observed_at: str
    fetcher: Callable[[str], Any]
    rate_limiter: SharedRateLimiter
    sleep_func: Callable[[float], None]
    max_transient_retries: int
    fetch_count: list[int]
    allow_network: bool = True


def _authorize_context_op(
    context: _RunContext,
    *,
    actions: Iterable[str],
    url: str,
    document_date: date,
    size_bytes: int,
    redirect_urls: Iterable[str] = (),
    final_url: str = "",
    attachment_id: str = "",
) -> dict[str, Any]:
    try:
        return authorize_actions(
            context.registry,
            source_id=context.source_id,
            actions=actions,
            purpose=context.purpose,
            data_class=context.data_class,
            region=context.region,
            document_type=context.document_type,
            url=url,
            document_date=document_date,
            size_bytes=size_bytes,
            at=context.authorization_time_fn(),
            redirect_urls=redirect_urls,
            final_url=final_url,
        )
    except RightsDenied as err:
        raise _PartitionStop(
            "BLOCKED_RIGHTS",
            f"BLOCKED_RIGHTS:{err} at {url}",
            url=final_url or url,
            attachment_id=attachment_id,
        ) from err


def _state_file(partition_dir: Path, source_record_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", source_record_id) or "record"
    suffix = hashlib.sha256(source_record_id.encode("utf-8")).hexdigest()[:8]
    return partition_dir / "records" / f"{safe}-{suffix}.json"


def _read_record_state(partition_dir: Path, source_record_id: str) -> dict[str, Any] | None:
    path = _state_file(partition_dir, source_record_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _record_state_is_complete(partition_dir: Path, state: dict[str, Any] | None) -> bool:
    if not state or not state.get("catalog"):
        return False
    expected = set(state.get("expected_attachment_ids", []))
    actual = {artifact.get("attachment_id", "") for artifact in state.get("artifacts", [])}
    if expected != actual:
        return False
    for artifact in state.get("artifacts", []):
        if artifact.get("status") == "STORED" and artifact.get("stored_blob_path"):
            if not (partition_dir / artifact["stored_blob_path"]).exists():
                return False
    return True


def _fetch_bytes(
    context: _RunContext,
    url: str,
    *,
    document_date: date,
    attachment_id: str = "",
) -> tuple[bytes, tuple[str, ...], str]:
    retries = 0
    while True:
        auths = _authorize_context_op(
            context,
            actions=(context.access_action,),
            url=url,
            document_date=document_date,
            size_bytes=0,
            attachment_id=attachment_id,
        )
        if context.allow_network:
            context.rate_limiter.acquire(
                context.source_id,
                INFRA_GROUP,
                per_source_limit=auths[context.access_action].max_actions_per_minute,
            )
            context.fetch_count[0] += 1
        try:
            response = context.fetcher(url)
        except RightsDenied as err:
            raise _PartitionStop(
                "BLOCKED_RIGHTS",
                f"BLOCKED_RIGHTS:{err} at {url}",
                url=url,
                attachment_id=attachment_id,
            ) from err
        if isinstance(response, (bytes, bytearray, memoryview)):
            response = FetchResponse(status_code=200, body=bytes(response), final_url=url)
        elif isinstance(response, HttpTransportResponse):
            response = FetchResponse(
                status_code=response.status_code,
                body=response.body,
                retry_after=response.retry_after,
                tls_error=response.tls_error,
                message=response.message,
                final_url=response.final_url,
                redirect_urls=response.redirect_urls,
            )
        if not isinstance(response, FetchResponse):
            raise TypeError("fetcher must return bytes, FetchResponse, or HttpTransportResponse")
        outcome, wait = classify_http_stop(
            status_code=response.status_code,
            body_snippet=response.body[:1024].decode("utf-8", "replace"),
            retry_after=response.retry_after,
            tls_error=response.tls_error,
            retries_used=retries,
            max_transient_retries=context.max_transient_retries,
        )
        if outcome == "PROCEED":
            final_url = response.final_url or url
            _authorize_context_op(
                context,
                actions=(context.access_action,),
                url=url,
                document_date=document_date,
                size_bytes=len(response.body),
                redirect_urls=response.redirect_urls,
                final_url=final_url,
                attachment_id=attachment_id,
            )
            return response.body, response.redirect_urls, final_url
        if outcome == "RETRY":
            retries += 1
            if wait:
                context.sleep_func(wait)
            continue
        message = response.message or response.tls_error or f"network policy stop at {url}"
        raise _PartitionStop(outcome, message, url=url, attachment_id=attachment_id)


def _process_document(context: _RunContext, document: Mapping[str, Any]) -> dict[str, Any]:
    fetches_before = context.fetch_count[0]
    page_url = str(document["page_url"])
    initial_doc_date = parse_vn_date(str(document.get("issued_date") or "")) or date(
        context.partition_year, 1, 1
    )
    page_redirects: tuple[str, ...] = ()
    page_final_url = page_url
    html = document.get("html")
    if html is None:
        raw_html_bytes, page_redirects, page_final_url = _fetch_bytes(
            context,
            page_url,
            document_date=initial_doc_date,
        )
        html_text = raw_html_bytes.decode("utf-8", "replace")
    elif isinstance(html, (bytes, bytearray)):
        raw_html_bytes = bytes(html)
        html_text = raw_html_bytes.decode("utf-8", "replace")
    else:
        html_text = str(html)
        raw_html_bytes = html_text.encode("utf-8")

    expected_html_sha = str(document.get("expected_html_sha256") or "").strip().lower()
    if expected_html_sha and sha256_bytes(raw_html_bytes) != expected_html_sha:
        raise _PartitionStop(
            "HTML_CHECKSUM_MISMATCH",
            f"HTML checksum mismatch at {page_url}",
            url=page_url,
        )

    parsed = parse_src01_document_html(
        html_text,
        page_url=page_url,
        source_record_id=str(document.get("source_record_id", "")),
    )
    effective_doc_date = parse_vn_date(parsed["issued_date"]) or initial_doc_date
    page_auths = _authorize_context_op(
        context,
        actions=(context.access_action, "store"),
        url=page_url,
        document_date=effective_doc_date,
        size_bytes=len(raw_html_bytes),
        redirect_urls=page_redirects,
        final_url=page_final_url,
    )
    page_rights_ref = (
        f"APPROVED:{page_auths['store'].registry_revision}:{page_auths['store'].evidence_ref}"
    )
    source_record_id = parsed["source_record_id"]
    relation_role = str(document.get("relation_role") or "gazette_publication")
    domain = str(document.get("domain_candidate") or "UNMAPPED")
    if domain not in ALL_DOMAIN_LABELS:
        domain = "UNMAPPED"

    window = evaluate_date_window(
        parsed["issued_date"],
        context.cutoff,
        gazette_published_date_str=parsed["gazette_published_date"],
        observed_effective_date_str=parsed["observed_effective_date"],
    )
    flags = [flag for flag in window["date_reconciliation_flag"].split(";") if flag]
    if not parsed["gazette_published_date"]:
        flags.append("MISSING_GAZETTE_PUBLISHED_DATE")
    is_pre_2020 = bool(window["is_pre_2020_reference"] or relation_role == "pre_2020_reference")
    eligible = bool(window["eligible_for_pilot_denominator"] and relation_role != "pre_2020_reference")

    catalog = CatalogRecord(
        source_id=context.source_id,
        source_record_id=source_record_id,
        partition_id=context.partition_id,
        data_origin=context.data_origin,
        page_url=page_url,
        year=window["year"],
        quarter=window["quarter"],
        observed_at=context.observed_at,
        gazette_issue=parsed["gazette_issue"],
        gazette_page=parsed["gazette_page"],
        continuation_issues=parsed["continuation_issues"],
        issuer=parsed["issuer"],
        document_type=parsed["document_type"],
        document_number=parsed["document_number"],
        title=parsed["title"],
        issued_date=parsed["issued_date"],
        gazette_published_date=parsed["gazette_published_date"],
        observed_effective_date=parsed["observed_effective_date"],
        version=str(document.get("version") or "v1"),
        relation_role=relation_role,
        related_to_document_number=str(document.get("related_to_document_number") or ""),
        domain_candidate=domain,
        rights_ref=page_rights_ref,
        status="CATALOGED",
        date_reconciliation_flag=";".join(flags),
        is_pre_2020_reference=is_pre_2020,
        eligible_for_pilot_denominator=eligible,
        legal_status_verified=False,
        error="",
        cutoff_utc=context.cutoff.cutoff_utc,
        cutoff_vn=context.cutoff.cutoff_vn,
    )

    expected_hashes = document.get("expected_sha256_by_attachment_id") or {}
    expected_hashes_by_url = document.get("expected_sha256_by_url") or {}
    declared_mimes_by_url = document.get("declared_mime_by_url") or {}
    artifacts: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    quarantine: list[dict[str, str]] = []
    for attachment in parsed["attachments"]:
        attachment_id = attachment["attachment_id"]
        file_url = attachment["file_url"]
        payload, att_redirects, att_final_url = _fetch_bytes(
            context,
            file_url,
            document_date=effective_doc_date,
            attachment_id=attachment_id,
        )
        att_auths = _authorize_context_op(
            context,
            actions=("store",),
            url=file_url,
            document_date=effective_doc_date,
            size_bytes=len(payload),
            redirect_urls=att_redirects,
            final_url=att_final_url,
            attachment_id=attachment_id,
        )
        att_rights_ref = (
            f"APPROVED:{att_auths['store'].registry_revision}:{att_auths['store'].evidence_ref}"
        )
        expected_sha256 = expected_hashes.get(attachment_id) or expected_hashes_by_url.get(file_url)
        declared_mime = declared_mimes_by_url.get(file_url) or attachment["declared_mime"]
        sha256, detected_mime, quarantine_reason = validate_blob_integrity(
            payload,
            declared_mime=declared_mime,
            expected_sha256=expected_sha256,
        )
        stored_blob_path = ""
        status = "STORED"
        error = ""
        if quarantine_reason:
            status = "QUARANTINED"
            quarantine_path = f"quarantine/{sha256}.bin"
            atomic_write_bytes(context.partition_dir / quarantine_path, payload)
            quarantine.append(
                {
                    "attachment_id": attachment_id,
                    "sha256": sha256,
                    "path": quarantine_path,
                    "reason": quarantine_reason,
                }
            )
        else:
            stored_blob_path = f"blobs/{sha256[:2]}/{sha256}.bin"
            try:
                atomic_write_bytes(context.partition_dir / stored_blob_path, payload)
            except ValueError as conflict:
                status = "ERROR"
                stored_blob_path = ""
                error = f"BLOB_CONFLICT:{conflict}"
                errors.append(
                    {
                        "source_id": context.source_id,
                        "source_record_id": source_record_id,
                        "partition_id": context.partition_id,
                        "data_origin": context.data_origin,
                        "page_url": page_url,
                        "file_url": file_url,
                        "attachment_id": attachment_id,
                        "code": "BLOB_CONFLICT",
                        "message": str(conflict),
                        "observed_at": context.observed_at,
                        "cutoff_utc": context.cutoff.cutoff_utc,
                        "cutoff_vn": context.cutoff.cutoff_vn,
                    }
                )
        artifacts.append(
            ArtifactRecord(
                source_id=context.source_id,
                source_record_id=source_record_id,
                partition_id=context.partition_id,
                data_origin=context.data_origin,
                parent_id=attachment["parent_id"],
                attachment_id=attachment_id,
                page_url=page_url,
                file_url=file_url,
                year=catalog.year,
                quarter=catalog.quarter,
                observed_at=context.observed_at,
                gazette_issue=catalog.gazette_issue,
                gazette_page=catalog.gazette_page,
                document_number=catalog.document_number,
                version=catalog.version,
                relation_role=catalog.relation_role,
                file_type=attachment["file_type"],
                declared_mime=declared_mime,
                detected_mime=detected_mime,
                size_bytes=len(payload),
                sha256=sha256,
                stored_blob_path=stored_blob_path,
                rights_ref=att_rights_ref,
                status=status,
                quarantine_reason=quarantine_reason,
                error=error,
                cutoff_utc=context.cutoff.cutoff_utc,
                cutoff_vn=context.cutoff.cutoff_vn,
            ).to_dict()
        )

    return {
        "source_record_id": source_record_id,
        "expected_attachment_ids": [item["attachment_id"] for item in parsed["attachments"]],
        "requests_attempted": context.fetch_count[0] - fetches_before,
        "catalog": catalog.to_dict(),
        "artifacts": artifacts,
        "errors": errors,
        "quarantine": quarantine,
    }


def _stop_error_row(context: _RunContext, stop: _PartitionStop, page_url: str) -> dict[str, Any]:
    return {
        "source_id": context.source_id,
        "source_record_id": _record_id_from_url(page_url) if page_url else "",
        "partition_id": context.partition_id,
        "data_origin": context.data_origin,
        "page_url": page_url,
        "file_url": stop.url,
        "attachment_id": stop.attachment_id,
        "code": stop.code,
        "message": stop.message,
        "observed_at": context.observed_at,
        "cutoff_utc": context.cutoff.cutoff_utc,
        "cutoff_vn": context.cutoff.cutoff_vn,
    }


def _collect_states(
    partition_dir: Path, checkpoint: PartitionCheckpoint
) -> tuple[list[dict[str, Any]], list[str]]:
    states: list[dict[str, Any]] = []
    retained: list[str] = []
    for source_record_id in checkpoint.completed_record_ids:
        state = _read_record_state(partition_dir, source_record_id)
        if _record_state_is_complete(partition_dir, state):
            states.append(state)
            retained.append(source_record_id)
    checkpoint.completed_record_ids = retained
    return states, retained


def _write_partition_bundle(
    context: _RunContext,
    checkpoint: PartitionCheckpoint,
    states: list[dict[str, Any]],
    stop_errors: list[dict[str, Any]],
    *,
    status: str,
    rights_status: str,
    rights_checks: Mapping[str, str],
    blocked_actions: Mapping[str, str] | None = None,
    stop_reason: str = "",
    catalog_enumeration_complete: bool = False,
    uncommitted_fetches: int = 0,
) -> dict[str, Any]:
    partition_dir = context.partition_dir
    catalog_rows = sorted(
        (state["catalog"] for state in states),
        key=lambda row: (str(row["document_number"]), str(row["source_record_id"])),
    )
    artifact_rows = sorted(
        (artifact for state in states for artifact in state["artifacts"]),
        key=lambda row: (str(row["source_record_id"]), str(row["attachment_id"]), str(row["file_url"])),
    )
    error_rows = sorted(
        [error for state in states for error in state["errors"]] + stop_errors,
        key=lambda row: (
            str(row["code"]),
            str(row["source_record_id"]),
            str(row["attachment_id"]),
            str(row["file_url"]),
        ),
    )
    quarantine_files = sorted(
        (
            {
                "source_record_id": str(state["source_record_id"]),
                "attachment_id": entry["attachment_id"],
                "sha256": entry["sha256"],
                "path": entry["path"],
                "reason": entry["reason"],
            }
            for state in states
            for entry in state.get("quarantine", [])
        ),
        key=lambda entry: (entry["source_record_id"], entry["attachment_id"], entry["sha256"]),
    )

    checkpoint.status = status
    checkpoint.rights_status = rights_status
    checkpoint.last_completed_cursor = len(checkpoint.completed_record_ids)
    checkpoint.quarantined_attachment_ids = sorted(
        {entry["attachment_id"] for entry in quarantine_files}
    )
    checkpoint.updated_at = context.observed_at
    checkpoint_path = partition_dir / "checkpoint.json"
    checkpoint_sha = save_checkpoint(checkpoint_path, checkpoint)

    catalog_jsonl_sha = write_jsonl_atomic(partition_dir / "catalog.jsonl", catalog_rows)
    catalog_csv_sha = write_csv_atomic(
        partition_dir / "catalog.csv", CATALOG_RECORD_FIELDS, catalog_rows
    )
    artifacts_jsonl_sha = write_jsonl_atomic(partition_dir / "artifacts.jsonl", artifact_rows)
    artifacts_csv_sha = write_csv_atomic(
        partition_dir / "artifacts.csv", ARTIFACT_RECORD_FIELDS, artifact_rows
    )
    errors_sha = write_jsonl_atomic(partition_dir / "errors.jsonl", error_rows)

    stored = [row for row in artifact_rows if row["status"] == "STORED"]
    enumeration_complete = bool(
        catalog_enumeration_complete and status == "COMPLETED" and rights_status == "APPROVED"
    )
    committed_requests = sum(int(state.get("requests_attempted", 0)) for state in states)
    effective_requests = (
        committed_requests
        if status == "COMPLETED"
        else committed_requests + max(uncommitted_fetches, 0)
    )
    manifest = {
        "run_id": context.cutoff.run_id,
        "source_id": context.source_id,
        "partition_id": context.partition_id,
        "year": checkpoint.year,
        "quarter": checkpoint.quarter,
        "owner_worker": checkpoint.owner_worker,
        "data_origin": context.data_origin,
        "access_action": context.access_action,
        "status": status,
        "rights_status": rights_status,
        "rights_ref": context.rights_ref,
        "rights_checks": dict(rights_checks),
        "blocked_actions": dict(blocked_actions or {}),
        "catalog_enumeration_complete": enumeration_complete,
        "cutoff_utc": context.cutoff.cutoff_utc,
        "cutoff_vn": context.cutoff.cutoff_vn,
        "window_start_date": context.cutoff.window_start_date,
        "observed_at": context.observed_at,
        "network": {
            "requests_attempted": effective_requests,
            "stop_reason": stop_reason,
        },
        "counts": {
            "documents_observed": len(catalog_rows),
            "eligible_for_pilot_denominator": sum(
                1 for row in catalog_rows if row["eligible_for_pilot_denominator"]
            ),
            "pre_2020_references": sum(1 for row in catalog_rows if row["is_pre_2020_reference"]),
            "post_cutoff_excluded": sum(
                1 for row in catalog_rows if "POST_CUTOFF_ISSUED_DATE" in row["date_reconciliation_flag"]
            ),
            "date_flagged": sum(1 for row in catalog_rows if row["date_reconciliation_flag"]),
            "artifacts_total": len(artifact_rows),
            "stored_blobs": len(stored),
            "unique_blobs": len({row["sha256"] for row in stored}),
            "quarantined_artifacts": len(quarantine_files),
            "errors": len(error_rows),
        },
        "quarantine_files": quarantine_files,
        "files": {
            "catalog.jsonl": catalog_jsonl_sha,
            "catalog.csv": catalog_csv_sha,
            "artifacts.jsonl": artifacts_jsonl_sha,
            "artifacts.csv": artifacts_csv_sha,
            "errors.jsonl": errors_sha,
            "checkpoint.json": checkpoint_sha,
        },
    }
    atomic_write_text(
        partition_dir / "partition-manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        allow_overwrite=True,
    )
    manifest_sha = sha256_bytes((partition_dir / "partition-manifest.json").read_bytes())
    return {
        "source_id": context.source_id,
        "partition_id": context.partition_id,
        "year": checkpoint.year,
        "quarter": checkpoint.quarter,
        "status": status,
        "rights_status": rights_status,
        "rights_ref": context.rights_ref,
        "catalog_enumeration_complete": enumeration_complete,
        "counts": manifest["counts"],
        "network": manifest["network"],
        "files": manifest["files"],
        "manifest_sha256": manifest_sha,
        "partition_dir": str(partition_dir),
        "fetch_attempts": context.fetch_count[0],
    }


def run_src01_partition(
    *,
    registry: SourceRegistry,
    cutoff: RunCutoff,
    source_id: str,
    year: int,
    staging_dir: Path,
    documents: Iterable[Mapping[str, Any]],
    fetcher: Callable[[str], Any] | None = None,
    rate_limiter: SharedRateLimiter | None = None,
    quarter: str = "",
    purpose: str = "g1-pilot",
    data_class: str = "synthetic",
    region: str = "VN",
    document_type: str = "regulation",
    probe_url: str = "",
    probe_document_date: date | None = None,
    observed_at: str | None = None,
    at: datetime | None = None,
    at_fn: Callable[[], datetime] | None = None,
    sleep_func: Callable[[float], None] | None = None,
    max_transient_retries: int = 2,
    access_action: str = "automated_access",
    catalog_enumeration_complete: bool = False,
) -> dict[str, Any]:
    """Run one SRC-01 source×year partition with pre-flight and per-operation rights checks."""
    document_list = list(documents)
    partition_id = f"{source_id}__{year}" if not quarter else f"{source_id}__{year}__{quarter}"
    partition_dir = Path(staging_dir) / partition_id
    data_origin = "SYNTHETIC_FIXTURE" if source_id.startswith("FIXTURE-") else "REAL"
    observed_at = observed_at or cutoff.cutoff_vn
    probe_url = probe_url or (document_list[0]["page_url"] if document_list else DEFAULT_SOURCE_URL)
    probe_date = probe_document_date or date(year, 1, 1)
    auth_time_fn = authorization_clock(source_id, cutoff.cutoff_datetime_vn, at=at, at_fn=at_fn)

    rights_ok, rights_checks = check_source_actions(
        registry,
        source_id=source_id,
        actions=(access_action, "store"),
        purpose=purpose,
        data_class=data_class,
        region=region,
        document_type=document_type,
        url=probe_url,
        document_date=probe_date,
        size_bytes=0,
        at=auth_time_fn(),
    )

    partition_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = load_checkpoint(partition_dir / "checkpoint.json")
    if checkpoint is None or checkpoint.partition_id != partition_id:
        checkpoint = PartitionCheckpoint(
            source_id=source_id,
            partition_id=partition_id,
            year=year,
            quarter=quarter,
            owner_worker="worker-src01",
            status="PENDING",
            last_completed_cursor=0,
            rights_status="PENDING_RIGHTS",
        )
    checkpoint.source_id = source_id
    checkpoint.year = year
    checkpoint.quarter = quarter
    checkpoint.owner_worker = "worker-src01"

    context = _RunContext(
        source_id=source_id,
        partition_id=partition_id,
        partition_year=year,
        data_origin=data_origin,
        partition_dir=partition_dir,
        cutoff=cutoff,
        registry=registry,
        access_action=access_action,
        purpose=purpose,
        data_class=data_class,
        region=region,
        document_type=document_type,
        authorization_time_fn=auth_time_fn,
        rights_ref=rights_checks.get("store", "") if rights_ok else "",
        observed_at=observed_at,
        fetcher=fetcher or (lambda url: FetchResponse(status_code=403, message="no fetcher configured")),
        rate_limiter=rate_limiter or SharedRateLimiter(),
        sleep_func=sleep_func or time.sleep,
        max_transient_retries=max_transient_retries,
        fetch_count=[0],
        allow_network=(access_action != "manual_download"),
    )

    if not rights_ok:
        checkpoint.rights_status = "BLOCKED_RIGHTS"
        checkpoint.status = "BLOCKED_RIGHTS"
        checkpoint.completed_record_ids = []
        return _write_partition_bundle(
            context,
            checkpoint,
            [],
            [],
            status="BLOCKED_RIGHTS",
            rights_status="BLOCKED_RIGHTS",
            rights_checks=rights_checks,
            blocked_actions=rights_checks,
            stop_reason="PREFLIGHT_BLOCKED_RIGHTS",
            catalog_enumeration_complete=False,
        )

    checkpoint.rights_status = "APPROVED"
    checkpoint.rights_ref = context.rights_ref
    states, completed = _collect_states(partition_dir, checkpoint)
    completed_set = set(completed)
    seen_documents: set[str] = set()
    stop_errors: list[dict[str, Any]] = []
    status = "COMPLETED"
    stop_reason = ""
    current_page = ""

    committed_this_run = 0
    try:
        for document in document_list:
            page_url = str(document["page_url"])
            current_page = page_url
            source_record_id = str(document.get("source_record_id") or _record_id_from_url(page_url))
            if source_record_id in seen_documents or source_record_id in completed_set:
                continue
            seen_documents.add(source_record_id)
            state = _process_document(context, document)
            state_path = _state_file(partition_dir, source_record_id)
            atomic_write_text(
                state_path,
                json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                allow_overwrite=True,
            )
            committed_this_run += int(state.get("requests_attempted", 0))
            checkpoint.completed_record_ids.append(source_record_id)
            completed_set.add(source_record_id)
            checkpoint.status = "RUNNING"
            checkpoint.updated_at = observed_at
            save_checkpoint(partition_dir / "checkpoint.json", checkpoint)
    except _PartitionStop as stop:
        status = stop.code
        stop_reason = stop.code
        checkpoint.status = status
        stop_errors.append(_stop_error_row(context, stop, current_page))
    except NetworkPolicyStop as stop:
        status = stop.code
        stop_reason = stop.code
        checkpoint.status = status
        stop_errors.append(
            _stop_error_row(context, _PartitionStop(stop.code, str(stop)), current_page)
        )
    except Exception:
        checkpoint.status = "INTERRUPTED"
        save_checkpoint(partition_dir / "checkpoint.json", checkpoint)
        states, _ = _collect_states(partition_dir, checkpoint)
        _write_partition_bundle(
            context,
            checkpoint,
            states,
            stop_errors,
            status="INTERRUPTED",
            rights_status="APPROVED",
            rights_checks=rights_checks,
            stop_reason="INTERRUPTED",
            catalog_enumeration_complete=False,
            uncommitted_fetches=max(context.fetch_count[0] - committed_this_run, 0),
        )
        raise

    states, _ = _collect_states(partition_dir, checkpoint)
    return _write_partition_bundle(
        context,
        checkpoint,
        states,
        stop_errors,
        status=status,
        rights_status="APPROVED",
        rights_checks=rights_checks,
        stop_reason=stop_reason,
        catalog_enumeration_complete=(catalog_enumeration_complete and status == "COMPLETED"),
        uncommitted_fetches=max(context.fetch_count[0] - committed_this_run, 0),
    )


# ---------------------------------------------------------------------------
# Synthetic pilot + worker manifest
# ---------------------------------------------------------------------------

def _summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "partition_id": result["partition_id"],
        "source_id": result["source_id"],
        "year": result["year"],
        "quarter": result["quarter"],
        "status": result["status"],
        "rights_status": result["rights_status"],
        "counts": result["counts"],
        "manifest_sha256": result["manifest_sha256"],
    }


def _hash_tree(root: Path, *, exclude: Iterable[str] = ()) -> dict[str, str]:
    excluded = set(exclude)
    hashes = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        hashes[relative] = sha256_bytes(path.read_bytes())
    return hashes


def _write_worker_manifest(
    staging_root: Path,
    *,
    cutoff: RunCutoff,
    worker: str,
    real_results: Mapping[str, Mapping[str, Any]],
    synthetic: Mapping[str, Any] | None,
    registry_revision: str,
) -> dict[str, str]:
    all_results = [*real_results.values()]
    if synthetic:
        all_results.extend(synthetic.get("results", {}).values())
    real_blocked = bool(real_results) and all(
        result["status"] == "BLOCKED_RIGHTS" and result["rights_status"] == "BLOCKED_RIGHTS"
        for result in real_results.values()
    )
    real_completed = bool(real_results) and all(
        result["status"] == "COMPLETED" for result in real_results.values()
    )
    synthetic_completed = bool(synthetic) and all(
        result["status"] == "COMPLETED" for result in synthetic.get("results", {}).values()
    )
    worker_status = (
        ("COMPLETED" if synthetic_completed else "PARTIAL")
        if synthetic is not None
        else ("COMPLETED" if real_completed else ("BLOCKED_RIGHTS" if real_blocked else "PARTIAL"))
    )
    manifest = {
        "worker": worker,
        "run_id": cutoff.run_id,
        "source_id": SRC01_SOURCE_ID,
        "source_name": "Công báo điện tử",
        "registry_revision": registry_revision,
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
        "window_start_date": cutoff.window_start_date,
        "network_policy": {
            "live_network_requests": sum(result["fetch_attempts"] for result in real_results.values()),
            "infra_group": INFRA_GROUP,
            "hosts_allowed_for_future_authorized_runs": sorted(SRC01_HOSTS),
        },
        "real_blocked_partitions": {key: _summary(value) for key, value in real_results.items()},
        "synthetic_partitions": (
            {key: _summary(value) for key, value in synthetic.get("results", {}).items()}
            if synthetic
            else {}
        ),
        "synthetic_fixture": synthetic.get("fixture", {}) if synthetic else {},
        "validation": {
            "real_partitions_blocked": real_blocked,
            "real_partition_count": len(real_results),
            "real_fetch_attempts": sum(result["fetch_attempts"] for result in real_results.values()),
            "synthetic_all_completed": synthetic_completed,
            "synthetic_catalog_records": sum(
                result["counts"]["documents_observed"]
                for result in (synthetic.get("results", {}).values() if synthetic else ())
            ),
            "synthetic_artifacts": sum(
                result["counts"]["artifacts_total"]
                for result in (synthetic.get("results", {}).values() if synthetic else ())
            ),
            "synthetic_quarantined": sum(
                result["counts"]["quarantined_artifacts"]
                for result in (synthetic.get("results", {}).values() if synthetic else ())
            ),
            "synthetic_pre_2020_references": sum(
                result["counts"]["pre_2020_references"]
                for result in (synthetic.get("results", {}).values() if synthetic else ())
            ),
            "synthetic_post_cutoff_excluded": sum(
                result["counts"]["post_cutoff_excluded"]
                for result in (synthetic.get("results", {}).values() if synthetic else ())
            ),
            "shared_hash_sha256": synthetic.get("fixture", {}).get("shared_pdf_sha256", "")
            if synthetic
            else "",
        },
        "worker_status": worker_status,
        "files": _hash_tree(staging_root, exclude={"worker-manifest.json"}),
    }
    atomic_write_text(
        staging_root / "worker-manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        allow_overwrite=True,
    )
    return manifest["files"]


def run_src01_synthetic_pilot(
    *,
    run_dir: Path,
    cutoff: RunCutoff,
    source_id: str = FIXTURE_SOURCE_ID,
    registry_path: Path | None = None,
    live_registry_path: Path | None = None,
    write_worker_manifest: bool = True,
) -> dict[str, Any]:
    """Run synthetic SRC-01 fixtures and prove every live partition fails closed."""
    run_dir = Path(run_dir)
    staging_root = run_dir / "staging" / "SRC-01"
    synthetic_root = staging_root / "synthetic"
    synthetic_root.mkdir(parents=True, exist_ok=True)
    fixtures = build_src01_synthetic_fixtures(source_id=source_id)

    if live_registry_path is None:
        try:
            live_registry_path = _locate_registry(run_dir)
        except FileNotFoundError:
            live_registry_path = None
    real_results: dict[str, dict[str, Any]] = {}
    live_registry_revision = ""
    if live_registry_path is not None:
        live_registry = SourceRegistry(Path(live_registry_path))
        live_registry_revision = live_registry.revision
        for year in range(2020, 2027):
            result = run_src01_partition(
                registry=live_registry,
                cutoff=cutoff,
                source_id=SRC01_SOURCE_ID,
                year=year,
                staging_dir=staging_root / "real-blocked",
                documents=[],
                probe_url=DEFAULT_SOURCE_URL,
                probe_document_date=date(year, 1, 1),
                observed_at=cutoff.cutoff_vn,
                data_class="public",
            )
            real_results[result["partition_id"]] = result

    if registry_path is None:
        registry_path = synthetic_root / "synthetic-rights.json"
        payload = build_fixture_registry_payload(
            source_ids=[source_id],
            urls=[*fixtures["page_urls"], *fixtures["attachment_urls"]],
        )
        atomic_write_text(
            registry_path,
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            allow_overwrite=True,
        )
    registry = SourceRegistry(Path(registry_path))
    rate_limiter = SharedRateLimiter(per_source_max_per_minute=60, shared_infra_max_per_minute=120)
    fetcher = fixtures["blobs"].__getitem__
    results: dict[str, dict[str, Any]] = {}
    for year in fixtures["partition_years"]:
        documents = [
            document for document in fixtures["documents"] if document["partition_year"] == year
        ]
        partition_id = f"{source_id}__{year}"
        results[partition_id] = run_src01_partition(
            registry=registry,
            cutoff=cutoff,
            source_id=source_id,
            year=year,
            staging_dir=synthetic_root,
            documents=documents,
            fetcher=fetcher,
            rate_limiter=rate_limiter,
            probe_url=documents[0]["page_url"],
            observed_at=cutoff.cutoff_vn,
            data_class="synthetic",
        )

    summary = {
        "run_id": cutoff.run_id,
        "source_id": source_id,
        "status": "COMPLETED"
        if all(result["status"] == "COMPLETED" for result in results.values())
        else "PARTIAL",
        "results": results,
        "real_results": real_results,
        "partitions": {key: _summary(value) for key, value in results.items()},
        "real_partitions": {key: _summary(value) for key, value in real_results.items()},
        "fixture": {
            "documents": len(fixtures["documents"]),
            "attachment_blobs": len(fixtures["blobs"]),
            "partition_years": fixtures["partition_years"],
            "shared_pdf_sha256": fixtures["shared_pdf_sha256"],
        },
        "synthetic_registry_revision": registry.revision,
        "live_registry_revision": live_registry_revision,
        "synthetic_registry_path": registry_path.relative_to(staging_root).as_posix()
        if registry_path.is_relative_to(staging_root)
        else registry_path.name,
    }
    if write_worker_manifest:
        summary["worker_manifest_files"] = _write_worker_manifest(
            staging_root,
            cutoff=cutoff,
            worker="worker-src01",
            real_results=real_results,
            synthetic=summary,
            registry_revision=live_registry_revision or registry.revision,
        )
    return summary


# ---------------------------------------------------------------------------
# Manual-intake and authorized real-batch runners
# ---------------------------------------------------------------------------

def run_src01_manual_intake(
    *,
    run_dir: Path,
    cutoff: RunCutoff,
    registry_path: Path,
    intake_manifest_path: Path,
    at: datetime | None = None,
    write_worker_manifest: bool = True,
) -> dict[str, Any]:
    """Ingest a rights-approved locally downloaded SRC-01 manual batch with checksums."""
    run_dir = Path(run_dir)
    intake_manifest_path = Path(intake_manifest_path)
    intake_root = intake_manifest_path.parent
    manifest_data = json.loads(intake_manifest_path.read_text(encoding="utf-8"))
    source_id = str(manifest_data.get("source_id") or SRC01_SOURCE_ID)
    purpose = str(manifest_data.get("purpose") or "g1-pilot")
    data_class = str(manifest_data.get("data_class") or "public")
    region = str(manifest_data.get("region") or "VN")
    document_type = str(manifest_data.get("document_type") or "regulation")
    registry = SourceRegistry(Path(registry_path))

    by_year: dict[int, list[dict[str, Any]]] = {}
    url_to_local: dict[str, Path] = {}
    for item in manifest_data.get("items", []):
        year = int(item["partition_year"])
        page_url = str(item["page_url"])
        html_path = resolve_safe_local_path(intake_root, str(item["html_path"]))
        url_to_local[page_url] = html_path
        expected_by_url: dict[str, str] = {}
        declared_by_url: dict[str, str] = {}
        for att in item.get("attachments", []):
            file_url = str(att["file_url"])
            local_file = resolve_safe_local_path(intake_root, str(att["local_path"]))
            url_to_local[file_url] = local_file
            if att.get("expected_sha256"):
                expected_by_url[file_url] = str(att["expected_sha256"])
            if att.get("declared_mime"):
                declared_by_url[file_url] = str(att["declared_mime"])
        by_year.setdefault(year, []).append(
            {
                "page_url": page_url,
                "source_record_id": str(item.get("source_record_id") or _record_id_from_url(page_url)),
                "domain_candidate": str(item.get("domain_candidate") or "UNMAPPED"),
                "relation_role": str(item.get("relation_role") or "gazette_publication"),
                "version": str(item.get("version") or "v1"),
                "related_to_document_number": str(item.get("related_to_document_number") or ""),
                "issued_date": str(item.get("issued_date") or ""),
                "expected_html_sha256": str(item.get("html_sha256") or ""),
                "expected_sha256_by_url": expected_by_url,
                "declared_mime_by_url": declared_by_url,
            }
        )

    def local_fetcher(url: str) -> FetchResponse:
        if url not in url_to_local:
            return FetchResponse(status_code=404, message=f"URL not present in manual-intake manifest: {url}")
        local_path = url_to_local[url]
        if not local_path.exists():
            return FetchResponse(status_code=404, message=f"Local intake file missing: {local_path.name}")
        return FetchResponse(status_code=200, body=local_path.read_bytes(), final_url=url)

    staging_root = run_dir / "staging" / SRC01_SOURCE_ID
    real_root = staging_root / "real"
    real_root.mkdir(parents=True, exist_ok=True)
    enumeration_flag = bool(manifest_data.get("catalog_enumeration_complete", False))
    results: dict[str, dict[str, Any]] = {}
    for year in sorted(by_year):
        docs = by_year[year]
        probe_date = parse_vn_date(docs[0].get("issued_date")) or date(year, 1, 1)
        result = run_src01_partition(
            registry=registry,
            cutoff=cutoff,
            source_id=source_id,
            year=year,
            staging_dir=real_root,
            documents=docs,
            fetcher=local_fetcher,
            purpose=purpose,
            data_class=data_class,
            region=region,
            document_type=document_type,
            probe_url=docs[0]["page_url"],
            probe_document_date=probe_date,
            observed_at=cutoff.cutoff_vn,
            at=at,
            access_action="manual_download",
            catalog_enumeration_complete=enumeration_flag,
        )
        results[result["partition_id"]] = result

    if write_worker_manifest:
        _write_worker_manifest(
            staging_root,
            cutoff=cutoff,
            worker="worker-src01",
            real_results=results,
            synthetic=None,
            registry_revision=registry.revision,
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


def run_src01_automated_batch(
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
    write_worker_manifest: bool = True,
) -> dict[str, Any]:
    """Run an authorized SRC-01 real automated batch with pagination, transport, and checkpointing."""
    run_dir = Path(run_dir)
    spec = json.loads(Path(batch_spec_path).read_text(encoding="utf-8"))
    source_id = str(spec.get("source_id") or SRC01_SOURCE_ID)
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
    staging_root = run_dir / "staging" / SRC01_SOURCE_ID
    real_root = staging_root / "real"
    real_root.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict[str, Any]] = {}
    for partition_spec in spec.get("partitions", []):
        year = int(partition_spec["year"])
        quarter = str(partition_spec.get("quarter") or "")
        declared_enum = bool(partition_spec.get("catalog_enumeration_complete", False))
        listing_urls = [str(u) for u in partition_spec.get("listing_urls", [])]
        explicit_docs = [dict(d) for d in partition_spec.get("documents", [])]
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
        discovered_docs: list[dict[str, Any]] = list(explicit_docs)
        seen_urls = {str(item["page_url"]) for item in discovered_docs}
        pagination_complete = True
        pagination_stop: tuple[str, str, str] | None = None

        if listing_urls:
            queue = list(listing_urls)
            visited_listings: set[str] = set()
            while queue and len(visited_listings) < max_pages:
                list_url = queue.pop(0)
                if list_url in visited_listings:
                    continue
                visited_listings.add(list_url)
                try:
                    auths = authorize_actions(
                        registry,
                        source_id=source_id,
                        actions=("automated_access",),
                        purpose=purpose,
                        data_class=data_class,
                        region=region,
                        document_type=document_type,
                        url=list_url,
                        document_date=probe_date,
                        size_bytes=0,
                        at=auth_time_fn(),
                    )
                    limiter.acquire(
                        source_id,
                        INFRA_GROUP,
                        per_source_limit=auths["automated_access"].max_actions_per_minute,
                    )
                    resp = active_fetcher(list_url)
                    if isinstance(resp, (bytes, bytearray, memoryview)):
                        resp = FetchResponse(status_code=200, body=bytes(resp), final_url=list_url)
                    elif isinstance(resp, HttpTransportResponse):
                        resp = FetchResponse(
                            status_code=resp.status_code,
                            body=resp.body,
                            retry_after=resp.retry_after,
                            tls_error=resp.tls_error,
                            message=resp.message,
                            final_url=resp.final_url,
                            redirect_urls=resp.redirect_urls,
                        )
                    outcome, _ = classify_http_stop(
                        status_code=resp.status_code,
                        body_snippet=resp.body[:1024].decode("utf-8", "replace"),
                        retry_after=resp.retry_after,
                        tls_error=resp.tls_error,
                    )
                    if outcome != "PROCEED":
                        pagination_complete = False
                        pagination_stop = (outcome, resp.message or outcome, list_url)
                        break
                    authorize_actions(
                        registry,
                        source_id=source_id,
                        actions=("automated_access",),
                        purpose=purpose,
                        data_class=data_class,
                        region=region,
                        document_type=document_type,
                        url=list_url,
                        document_date=probe_date,
                        size_bytes=len(resp.body),
                        at=auth_time_fn(),
                        redirect_urls=resp.redirect_urls,
                        final_url=resp.final_url or list_url,
                    )
                except RightsDenied as err:
                    pagination_complete = False
                    pagination_stop = ("BLOCKED_RIGHTS", f"BLOCKED_RIGHTS:{err}", list_url)
                    break
                except NetworkPolicyStop as stop:
                    pagination_complete = False
                    pagination_stop = (stop.code, str(stop), list_url)
                    break

                parsed_listing = parse_src01_listing_html(
                    resp.body.decode("utf-8", "replace"), base_url=resp.final_url or list_url
                )
                for doc_url in parsed_listing["document_urls"]:
                    if doc_url not in seen_urls:
                        seen_urls.add(doc_url)
                        discovered_docs.append({"page_url": doc_url})
                next_url = parsed_listing["next_page_url"]
                if next_url and next_url not in visited_listings:
                    queue.append(next_url)
            if queue:
                pagination_complete = False

        if pagination_stop is not None:
            stop_code, stop_msg, stop_url = pagination_stop
            part_id = f"{source_id}__{year}" if not quarter else f"{source_id}__{year}__{quarter}"
            part_dir = real_root / part_id
            part_dir.mkdir(parents=True, exist_ok=True)
            cp = load_checkpoint(part_dir / "checkpoint.json") or PartitionCheckpoint(
                source_id=source_id,
                partition_id=part_id,
                year=year,
                quarter=quarter,
                owner_worker="worker-src01",
                status=stop_code,
                last_completed_cursor=0,
                rights_status="BLOCKED_RIGHTS" if stop_code == "BLOCKED_RIGHTS" else "APPROVED",
            )
            ctx = _RunContext(
                source_id=source_id,
                partition_id=part_id,
                partition_year=year,
                data_origin="SYNTHETIC_FIXTURE" if source_id.startswith("FIXTURE-") else "REAL",
                partition_dir=part_dir,
                cutoff=cutoff,
                registry=registry,
                access_action="automated_access",
                purpose=purpose,
                data_class=data_class,
                region=region,
                document_type=document_type,
                authorization_time_fn=auth_time_fn,
                rights_ref="",
                observed_at=cutoff.cutoff_vn,
                fetcher=active_fetcher,
                rate_limiter=limiter,
                sleep_func=sleep_func or time.sleep,
                max_transient_retries=2,
                fetch_count=[0],
            )
            results[part_id] = _write_partition_bundle(
                ctx,
                cp,
                [],
                [_stop_error_row(ctx, _PartitionStop(stop_code, stop_msg, url=stop_url), stop_url)],
                status=stop_code,
                rights_status="BLOCKED_RIGHTS" if stop_code == "BLOCKED_RIGHTS" else "APPROVED",
                rights_checks={},
                stop_reason=stop_code,
                catalog_enumeration_complete=False,
            )
            continue

        probe_url = discovered_docs[0]["page_url"] if discovered_docs else (
            listing_urls[0] if listing_urls else DEFAULT_SOURCE_URL
        )
        result = run_src01_partition(
            registry=registry,
            cutoff=cutoff,
            source_id=source_id,
            year=year,
            quarter=quarter,
            staging_dir=real_root,
            documents=discovered_docs,
            fetcher=active_fetcher,
            rate_limiter=limiter,
            purpose=purpose,
            data_class=data_class,
            region=region,
            document_type=document_type,
            probe_url=probe_url,
            probe_document_date=probe_date,
            observed_at=cutoff.cutoff_vn,
            at_fn=auth_time_fn,
            sleep_func=sleep_func,
            access_action="automated_access",
            catalog_enumeration_complete=(declared_enum and pagination_complete),
        )
        results[result["partition_id"]] = result

    if write_worker_manifest:
        _write_worker_manifest(
            staging_root,
            cutoff=cutoff,
            worker="worker-src01",
            real_results=results,
            synthetic=None,
            registry_revision=registry.revision,
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _locate_registry(run_dir: Path) -> Path:
    candidates = [Path.cwd(), run_dir.resolve(), Path(__file__).resolve()]
    for candidate in candidates:
        for parent in (candidate, *candidate.parents):
            registry = parent / "experiments" / "g1" / "source-rights.json"
            if registry.exists():
                return registry
    raise FileNotFoundError("experiments/g1/source-rights.json not found from the working directory")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SRC-01 rights-gated pilot adapter")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--cutoff-vn", required=True)
    parser.add_argument("--cutoff-utc", required=True)
    parser.add_argument("--run-id", default="G1-PILOT-SRC01-SRC03-20261126-01")
    parser.add_argument("--registry", "--rights", dest="registry", default="")
    parser.add_argument(
        "--mode",
        choices=("pilot-fixture", "manual-intake", "real-automated"),
        default="pilot-fixture",
    )
    parser.add_argument("--intake-manifest", default="")
    parser.add_argument("--batch-spec", default="")
    parser.add_argument("--rate-limit-db", default="")
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    cutoff = RunCutoff(run_id=args.run_id, cutoff_utc=args.cutoff_utc, cutoff_vn=args.cutoff_vn)
    registry_path = Path(args.registry) if args.registry else _locate_registry(run_dir)
    live_registry = SourceRegistry(registry_path)
    staging_root = run_dir / "staging" / "SRC-01"

    if args.mode == "manual-intake":
        intake_path = (
            Path(args.intake_manifest)
            if args.intake_manifest
            else run_dir / "manual-intake" / SRC01_SOURCE_ID / "intake-manifest.json"
        )
        result = run_src01_manual_intake(
            run_dir=run_dir,
            cutoff=cutoff,
            registry_path=registry_path,
            intake_manifest_path=intake_path,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["status"] in {"COMPLETED", "BLOCKED_RIGHTS"} else 1

    if args.mode == "real-automated":
        if not args.batch_spec:
            parser.error("--batch-spec is required with --mode real-automated")
        result = run_src01_automated_batch(
            run_dir=run_dir,
            cutoff=cutoff,
            registry_path=registry_path,
            batch_spec_path=Path(args.batch_spec),
            rate_limit_db=Path(args.rate_limit_db) if args.rate_limit_db else None,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["status"] in {"COMPLETED", "BLOCKED_RIGHTS"} else 1

    synthetic = run_src01_synthetic_pilot(
        run_dir=run_dir,
        cutoff=cutoff,
        live_registry_path=registry_path,
        write_worker_manifest=False,
    )
    real_results = synthetic["real_results"]
    files = _write_worker_manifest(
        staging_root,
        cutoff=cutoff,
        worker="worker-src01",
        real_results=real_results,
        synthetic=synthetic,
        registry_revision=live_registry.revision,
    )
    summary = {
        "worker": "worker-src01",
        "run_id": cutoff.run_id,
        "registry_path": "experiments/g1/source-rights.json",
        "registry_revision": live_registry.revision,
        "cutoff_utc": cutoff.cutoff_utc,
        "cutoff_vn": cutoff.cutoff_vn,
        "real_partitions": {key: result["status"] for key, result in real_results.items()},
        "synthetic_partitions": {
            key: result["status"] for key, result in synthetic["results"].items()
        },
        "worker_manifest": str(staging_root / "worker-manifest.json"),
        "file_count": len(files),
        "status": "COMPLETED",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if synthetic["status"] != "COMPLETED":
        return 1
    if not all(result["status"] == "BLOCKED_RIGHTS" for result in real_results.values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
