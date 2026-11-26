"""Measure extraction on an authorized manual intake. Results are candidates for review."""

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import time
import unicodedata
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from pypdfium2 import PdfDocument, PdfiumError

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/data-ingestion/src"))

from luatvn_ai_data_ingestion.pilot_schema import parse_vn_date, resolve_safe_local_path
from luatvn_ai_data_ingestion.source_rights import SourceOperation, SourceRegistry


CHUNK_SIZE = 1000
ARTICLE = re.compile(r"(?m)^\s*Điều\s+(\d+[a-zđ]?)\s*[.:]")
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def normalize(text: str) -> str:
    return "\n".join(line for line in (
        " ".join(line.split()) for line in unicodedata.normalize("NFC", text).splitlines()
    ) if line)


def admitted_files(paths: list[Path], registry: SourceRegistry) -> dict:
    files = {}
    for path in paths:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        source = manifest["source_id"]
        for document in manifest["items"]:
            issued = parse_vn_date(document["issued_date"])
            if issued is None:
                raise ValueError(f"missing issued date for {document['source_record_id']}")
            for artifact in document["attachments"]:
                ref = artifact["rights_ref"]
                data_path = resolve_safe_local_path(path.parent, artifact["local_path"])
                size = data_path.stat().st_size
                if size != artifact["bytes"]:
                    raise ValueError(f"size mismatch for {data_path.name}")
                auth = registry.authorize(SourceOperation(
                    source, "index", "g1-pilot", manifest["data_class"], "VN",
                    "regulation", artifact["file_url"], issued, size,
                ), at=datetime.now(UTC))
                digest = artifact["expected_sha256"]
                with data_path.open("rb") as stream:
                    file_digest = hashlib.file_digest(stream, "sha256").hexdigest()
                if auth.evidence_ref != ref or file_digest != digest:
                    raise ValueError(f"provenance mismatch for {data_path.name}")
                item = files.setdefault(digest, {"path": data_path, "source": source, "refs": []})
                item["refs"].append({
                    "source_id": source, "document_number": document["document_number"],
                    "source_record_id": document["source_record_id"], "url": artifact["file_url"],
                    "rights_ref": ref,
                })
    return files


def pdf_probe(data: bytes) -> tuple[list[str], str]:
    reader = PdfReader(io.BytesIO(data))
    texts = [normalize(page.extract_text()) for page in reader.pages]
    layout = normalize(reader.pages[0].extract_text(extraction_mode="layout")) if texts else ""
    return texts, layout


def render_page(data: bytes, page_no: int, path: Path) -> float:
    with PdfDocument(data) as pdf:
        page = pdf[page_no - 1]
        scale = min(200 / 72, 2500 / max(page.get_size()))
        bitmap = page.render(scale=scale)
        try:
            bitmap.to_pil().save(path, format="PNG")
        finally:
            bitmap.close()
    return round(scale * 72, 1)


def docx_probe(data: bytes) -> tuple:
    with ZipFile(io.BytesIO(data)) as archive:
        xml_info = archive.getinfo("word/document.xml")
        if xml_info.file_size > 32 * 1024 * 1024:
            raise ValueError("DOCX document.xml exceeds probe limit")
        tree = ElementTree.fromstring(archive.read(xml_info))
    paragraphs = [
        "".join(run.text or "" for run in paragraph.findall(".//w:t", WORD_NS))
        for paragraph in tree.findall(".//w:p", WORD_NS)
    ]
    return [normalize("\n".join(paragraphs))], len(tree.findall(".//w:tbl", WORD_NS))


def run(args: argparse.Namespace) -> dict:
    started = time.perf_counter()
    engines = {name: version(name) for name in ("pypdf", "pypdfium2", "fonttools")}
    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    registry = SourceRegistry(args.registry)
    files = admitted_files(args.intake, registry)
    rows, ocr_queue = [], []
    ocr_by_source = {}
    ocr_families = set()
    with (root / "chunks.jsonl").open("w", encoding="utf-8") as chunk_file:
        for digest, item in files.items():
            file_start = time.perf_counter()
            data = item["path"].read_bytes()
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError(f"artifact changed after admission: {digest}")
            kind = item["path"].suffix.removeprefix(".").lower()
            row = {"sha256": digest, "format": kind, "raw_bytes": len(data),
                   "source_refs": item["refs"], "status": "NOT_RUN"}
            source = item["source"]
            try:
                if kind == "pdf":
                    family = (source, item["refs"][0]["document_number"])
                    prepare_ocr = ocr_by_source.get(source, 0) < args.ocr_pages_per_source and family not in ocr_families
                    texts, layout = pdf_probe(data)
                    row.update(pages=len(texts), low_text_pages=sum(len(text) < 80 for text in texts),
                               first_page_layout_chars=len(layout),
                               first_page_layout_article_markers=len(ARTICLE.findall(layout)))
                    page_no = next((n for n, text in enumerate(texts, 1) if len(text) < 80), None)
                    if prepare_ocr and page_no is not None:
                        image = root / f"{digest}-p{page_no}.png"
                        try:
                            row["render_dpi"] = render_page(data, page_no, image)
                        except (PdfiumError, OSError, ValueError) as error:
                            row["ocr_error"] = type(error).__name__
                        else:
                            ocr_queue.append((row, page_no, image))
                            ocr_by_source[source] = ocr_by_source.get(source, 0) + 1
                            ocr_families.add(family)
                elif kind == "docx":
                    texts, tables = docx_probe(data)
                    row["tables_observed"] = tables
                else:
                    rows.append(row)
                    continue
            except (PdfReadError, OSError, ValueError, KeyError, BadZipFile, ElementTree.ParseError) as error:
                row.update(status="ERROR", error_type=type(error).__name__)
                rows.append(row)
                continue
            count = 0
            for unit, text in enumerate(texts, start=1):
                for offset in range(0, len(text), CHUNK_SIZE):
                    chunk = text[offset:offset + CHUNK_SIZE]
                    chunk_file.write(json.dumps({
                        "artifact_sha256": digest, "unit": unit, "unit_kind": "page" if kind == "pdf" else "document",
                        "offset": offset, "text": chunk, "review_state": "PENDING_REVIEW",
                    }, ensure_ascii=False) + "\n")
                    count += 1
            row.update(status="OBSERVED", normalized_bytes=sum(len(text.encode("utf-8")) for text in texts),
                       chunks=count, article_markers=sum(len(ARTICLE.findall(text)) for text in texts),
                       wall_seconds=round(time.perf_counter() - file_start, 4))
            rows.append(row)
    ocr_config = None
    if ocr_queue:
        result = subprocess.run(
            ["node", str(Path(__file__).with_name("ocr.cjs")), str(args.ocr_dir.resolve()),
             *(str(path) for _, _, path in ocr_queue)],
            capture_output=True, encoding="utf-8", check=True,
        )
        ocr = json.loads(result.stdout)
        ocr_config = ocr["config"]
        for (row, page, image), observation in zip(ocr_queue, ocr["images"], strict=True):
            text = normalize(observation["text"])
            text_path = root / f"{row['sha256']}-p{page}-ocr.txt"
            text_path.write_text(text, encoding="utf-8")
            row["ocr"] = {"page": page, "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                          "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                          "text_chars": len(text), "article_markers": len(ARTICLE.findall(text)),
                          "engine_confidence": observation["confidence"]}
    return {"status": "OBSERVED", "registry_revision": registry.revision, "engines": engines,
            "ocr": ocr_config, "wall_seconds": round(time.perf_counter() - started, 3), "artifacts": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path, nargs="+", required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ocr-dir", type=Path, required=True)
    parser.add_argument("--ocr-pages-per-source", type=int, default=3)
    args = parser.parse_args()
    report = run(args)
    report_path = args.output_dir / "measurements.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report_path)


if __name__ == "__main__":
    main()
