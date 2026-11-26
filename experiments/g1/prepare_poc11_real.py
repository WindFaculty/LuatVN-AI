"""Prepare real 27-case POC-11 package grounded in G1-REAL-20261127-01 without fabricating human reviews."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]


def nfc(text: str) -> str:
    return "\n".join(line for line in (" ".join(l.split()) for l in unicodedata.normalize("NFC", text).splitlines()) if line)


def extract_locator_excerpt(sha_list: list[str], task: str, graph_ocr_dir: Path, poc_ocr_dir: Path) -> tuple[str, str]:
    for sha in sha_list:
        pdf_matches = list((ROOT / "data/raw").rglob(f"{sha}.pdf"))
        if not pdf_matches:
            continue
        rdr = PdfReader(pdf_matches[0])
        # Try text layer first
        for idx, page in enumerate(rdr.pages[:5], 1):
            txt = nfc(page.extract_text(extraction_mode="layout") or "")
            if len(txt) >= 100:
                if task == "temporal":
                    # check last 2 pages first for hiệu lực thi hành
                    for tidx in range(len(rdr.pages), max(0, len(rdr.pages) - 3), -1):
                        ttxt = nfc(rdr.pages[tidx - 1].extract_text(extraction_mode="layout") or "")
                        m = re.search(r"(Điều\s+\d+\s*[.:]\s*Hiệu lực[^\n]*)", ttxt, re.I)
                        if m:
                            return f"{sha[:12]}:page:{tidx}", ttxt[m.start() : m.start() + 260].replace("\n", " ")
                return f"{sha[:12]}:page:{idx}", txt[:260].replace("\n", " ")
        # Fallback to local OCR text if previously generated
        for cache_dir in (graph_ocr_dir, poc_ocr_dir):
            txts = sorted(cache_dir.glob(f"{sha[:12]}-p*.txt"))
            if txts:
                content = txts[0].read_text(encoding="utf-8")
                return f"{sha[:12]}:ocr:{txts[0].name}", content[:260].replace("\n", " ")
    return "metadata-only", "Bản gốc thuần scan chưa trích trang tương ứng; reviewer mở trực tiếp tệp PDF theo SHA-256."


def main() -> None:
    prev_dir = ROOT / "build/g1/G1-REAL-20261126-02"
    run_dir = ROOT / "build/g1/G1-REAL-20261127-01"
    target = run_dir / "poc11"
    target.mkdir(parents=True, exist_ok=True)

    cutoff = json.loads((run_dir / "run-cutoff.json").read_text(encoding="utf-8"))
    rights_ref = "APPROVED:G1-D01-20261127-STATUTORY-R01:G1-D01-20261127-STATUTORY"

    prev_cases = json.loads((prev_dir / "poc11/cases.json").read_text(encoding="utf-8"))
    prev_evid = {r["case_id"]: r for r in json.loads((prev_dir / "poc11/candidate-evidence.json").read_text(encoding="utf-8"))}

    new_cases = []
    new_evid = []
    ws_lines = [
        "# Phiếu review POC-11 (Lô G1-REAL-20261127-01)",
        "",
        f"27 ca ứng viên trên 27 connected group độc lập (9 lĩnh vực × 3 tác vụ). Cutoff `{cutoff['cutoff_vn']}`. "
        "Chủ dự án Trần Xuân Khoa tự thực hiện 18 ca L2 (đối chiếu tệp gốc & ghi `active_minutes`, `wait_minutes`, `adjudication_minutes`); "
        "9 ca L3 giữ `PENDING_L3` cho đến khi có chuyên gia đủ điều kiện (G1-D03). **Không bịa kết quả L2/L3.**",
        "",
    ]

    current_domain = None
    for c in prev_cases:
        cid = c["case_id"]
        ev = prev_evid[cid]
        loc, excerpt = extract_locator_excerpt(
            ev["artifact_sha256"],
            c["task"],
            run_dir / "graph-ocr",
            run_dir / "poc02/ocr-images",
        )
        updated_case = {
            **c,
            "revision": "g1-r2",
            "recorded_at": cutoff["cutoff_utc"],
            "snapshot": cutoff["run_id"],
            "rights_ref": rights_ref,
            "anchor_refs": [loc, *c["anchor_refs"]],
        }
        updated_ev = {
            **ev,
            "legal_refs": cutoff["legal_refs"],
            "extracted_locator": loc,
            "extracted_excerpt": excerpt,
            "state": f"PENDING_{c['required_tier']}",
            "gold": None,
        }
        new_cases.append(updated_case)
        new_evid.append(updated_ev)

        if c["primary_domain"] != current_domain:
            current_domain = c["primary_domain"]
            ws_lines.extend([f"## {current_domain}", ""])
        ws_lines.extend([
            f"### {cid} · {c['required_tier']}",
            "",
            ev["prompt"],
            "",
            f"- Nguồn: {ev['source_url']}",
            f"- Family/Version: `{c['group_id']}` / `{ev['version_id']}`",
            f"- Locator & trích đoạn hỗ trợ (`PENDING_REVIEW`): `{loc}` — {excerpt}",
            "",
            "| Người review | Căn cứ và locator xác nhận | Active (phút) | Chờ (phút) | Phân xử (phút) | Kết luận |",
            "|---|---|---:|---:|---:|---|",
            "| | | | | | |",
            "",
        ])

    (target / "cases.json").write_text(json.dumps(new_cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (target / "candidate-evidence.json").write_text(json.dumps(new_evid, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Never fabricate human reviews: keep empty array
    (target / "human-reviews.json").write_text("[]\n", encoding="utf-8")
    (target / "review-worksheet.md").write_text("\n".join(ws_lines), encoding="utf-8")
    print(f"Prepared POC-11 real package: {len(new_cases)} cases, human-reviews.json=[] (0 fabricated)")


if __name__ == "__main__":
    main()
