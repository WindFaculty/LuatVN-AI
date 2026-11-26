"""Measure text and structure extraction on three synthetic Vietnamese PDFs."""

import argparse
import hashlib
import json
import platform
import re
import subprocess
import unicodedata
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pypdf import PdfReader
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


BODY = (
    "MẪU TỔNG HỢP — DỮ LIỆU KIỂM THỬ",
    "Điều 1. Phạm vi của mẫu",
    "1. Văn bản giả lập chỉ dùng để kiểm thử.",
    "Điều 5a. Quy trình đối chiếu",
    "2. Đối chiếu mã hồ sơ với phụ lục.",
    "2a. Ghi nhận ngày và địa bàn kiểm tra.",
    "Phụ lục I. Bảng dữ liệu mẫu",
)
ROWS = (("Mã", "Giá trị"), ("M-01", "123"), ("M-02", "456"))
ANCHOR = re.compile(r"^(Điều \d+[a-z]?|Phụ lục [IVX]+|\d+[a-z]?)\.", re.MULTILINE)
PAGE_WIDTH, PAGE_HEIGHT = 595, 842
LEFT, TOP, STEP = 60, 70, 31
COLUMN = 130


def draw_fixture(path: Path, font: Path, profile: str) -> None:
    canvas = Canvas(str(path), pagesize=(PAGE_WIDTH, PAGE_HEIGHT), invariant=1)
    rows = (*((line, "") for line in BODY), *ROWS)
    if profile == "digital":
        canvas.setFont("PilotFont", 15)
        for index, (left_text, right_text) in enumerate(rows):
            y = PAGE_HEIGHT - (TOP + index * STEP)
            canvas.drawString(LEFT, y, left_text)
            if right_text:
                canvas.drawString(LEFT + COLUMN, y, right_text)
    else:
        scale = 2
        image = Image.new("L", (PAGE_WIDTH * scale, PAGE_HEIGHT * scale), 255)
        draw = ImageDraw.Draw(image)
        image_font = ImageFont.truetype(str(font), 15 * scale)
        for index, (left_text, right_text) in enumerate(rows):
            y = (TOP + index * STEP) * scale
            draw.text((LEFT * scale, y), left_text, fill=0, font=image_font)
            if right_text:
                draw.text(((LEFT + COLUMN) * scale, y), right_text, fill=0, font=image_font)
        if profile == "scan_degraded":
            image = image.resize((420, 594), Image.Resampling.BILINEAR)
            image = image.filter(ImageFilter.GaussianBlur(0.7))
            image = image.rotate(3, expand=False, fillcolor=255)
        canvas.drawImage(ImageReader(image), 0, 0, PAGE_WIDTH, PAGE_HEIGHT)
    canvas.save()


def text_lines(text: str) -> list[str]:
    return [" ".join(line.split()) for line in unicodedata.normalize("NFC", text).splitlines() if line.strip()]


def edit_distance(expected: str, actual: str) -> int:
    previous = list(range(len(actual) + 1))
    for index, expected_char in enumerate(expected, start=1):
        row = [index]
        for offset, actual_char in enumerate(actual, start=1):
            row.append(min(row[-1] + 1, previous[offset] + 1, previous[offset - 1] + (expected_char != actual_char)))
        previous = row
    return previous[-1]


def score(text: str) -> dict:
    expected = [*BODY, *(" ".join(cells) for cells in ROWS)]
    actual = text_lines(text)
    expected_anchors = ANCHOR.findall("\n".join(expected))
    observed_anchors = ANCHOR.findall("\n".join(actual))
    reference = " ".join(expected)
    normalized = " ".join(actual)
    edits = edit_distance(reference, normalized)
    return {
        "expected_anchors": expected_anchors,
        "observed_anchors": observed_anchors,
        "missing_anchors": [value for value in expected_anchors if value not in observed_anchors],
        "exact_expected_lines_found": sum(line in actual for line in expected),
        "expected_line_count": len(expected),
        "exact_table_rows_found": sum(row in actual for row in expected[-len(ROWS):]),
        "expected_table_row_count": len(ROWS),
        "missing_exact_lines": [line for line in expected if line not in actual],
        "extracted_lines": actual,
        "character_edits": edits,
        "reference_characters": len(reference),
        "character_error_rate": round(edits / len(reference), 4),
        "normalized_utf8_bytes": len(normalized.encode("utf-8")),
    }


def run(args: argparse.Namespace) -> dict:
    font = args.font.resolve(strict=True)
    tool_dir = args.ocr_dir.resolve(strict=True)
    pdfmetrics.registerFont(TTFont("PilotFont", str(font)))
    profiles = ("digital", "scan_clear", "scan_degraded")
    results = {}
    with TemporaryDirectory(prefix="luatvn-poc02-") as temp:
        scan_paths = []
        for profile in profiles:
            pdf = Path(temp) / f"{profile}.pdf"
            draw_fixture(pdf, font, profile)
            page = PdfReader(pdf).pages[0]
            text = page.extract_text()
            raw = pdf.read_bytes()
            results[profile] = {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "raw_bytes": len(raw),
                "has_text_layer": bool(text.strip()),
            }
            if profile == "digital":
                results[profile].update(score(text))
                results[profile]["layout_mode"] = score(page.extract_text(extraction_mode="layout"))
            else:
                if text.strip() or len(page.images) != 1:
                    raise ValueError(f"Expected an image-only synthetic page for {profile}")
                image_path = Path(temp) / f"{profile}.png"
                page.images[0].image.save(image_path)
                scan_paths.append(image_path)

        ocr = subprocess.run(
            ["node", str(Path(__file__).with_name("ocr.cjs")), str(tool_dir), *map(str, scan_paths)],
            check=True, capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
        output = json.loads(ocr.stdout)
        for profile, observation in zip(profiles[1:], output["images"], strict=True):
            results[profile].update(score(observation["text"]))
            results[profile]["ocr_confidence"] = observation["confidence"]

    return {
        "run_id": args.run_id,
        "dataset": "synthetic-v1",
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "python_packages": {name: version(name) for name in ("pypdf", "reportlab", "pillow")},
        "ocr": output["config"],
        "fixture_font": {"file": font.name, "sha256": hashlib.sha256(font.read_bytes()).hexdigest()},
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, required=True, help="TTF with Vietnamese glyphs")
    parser.add_argument("--ocr-dir", type=Path, required=True, help="Directory with installed OCR dependencies")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    arguments = parser.parse_args()
    result = run(arguments)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(arguments.output)
