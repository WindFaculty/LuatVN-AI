"""Measure real official portal catalog counts for G1 POC-01 (SRC-01 & SRC-03)."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
USER_AGENT = "LuatVN-AI-G1-CatalogCheck/1.0"
TYPEGROUPS = {
    1: "Hiến pháp",
    2: "Sắc lệnh - Sắc luật",
    3: "Luật - Pháp lệnh",
    4: "Nghị định",
    5: "Quyết định",
    6: "Thông tư",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def curl_get(url: str, *, delay: float = 1.5) -> tuple[int, str, bytes]:
    if delay > 0:
        time.sleep(delay)
    proc = subprocess.run(
        ["curl.exe", "-sSL", "--max-time", "25", "-A", USER_AGENT, "-w", "\n__HTTP_CODE__:%{http_code}", url],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: rc={proc.returncode} err={proc.stderr.decode(errors='replace')}")
    raw, _, code_bytes = proc.stdout.rpartition(b"\n__HTTP_CODE__:")
    status = int(code_bytes.decode("ascii").strip())
    if status in (403, 429):
        raise RuntimeError(f"Portal returned HTTP {status} on {url}; stopping per rights policy")
    return status, raw.decode("utf-8", errors="replace"), raw


def curl_post_src03(url: str, base_html: str, overrides: dict[str, str], *, delay: float = 1.5) -> tuple[int, str, bytes]:
    soup = BeautifulSoup(base_html, "lxml")
    fields: dict[str, str] = {}
    for inp in soup.find_all("input"):
        kind = (inp.get("type") or "").lower()
        name = inp.get("name")
        if name and kind in ("hidden", "text", ""):
            fields[name] = inp.get("value", "")
    for sel in soup.find_all("select"):
        name = sel.get("name")
        if name:
            opt = sel.find("option", selected=True) or sel.find("option")
            fields[name] = opt.get("value", "") if opt else ""
    fields.update(overrides)
    encoded = urllib.parse.urlencode(fields)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(encoded)
        body_path = Path(handle.name)
    try:
        if delay > 0:
            time.sleep(delay)
        proc = subprocess.run(
            [
                "curl.exe", "-sSL", "--max-time", "25", "-A", USER_AGENT,
                "-X", "POST", "--data-binary", f"@{body_path}",
                "-w", "\n__HTTP_CODE__:%{http_code}", url,
            ],
            capture_output=True,
        )
    finally:
        body_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(f"curl POST failed for {url}: rc={proc.returncode}")
    raw, _, code_bytes = proc.stdout.rpartition(b"\n__HTTP_CODE__:")
    status = int(code_bytes.decode("ascii").strip())
    if status in (403, 429):
        raise RuntimeError(f"Portal returned HTTP {status} on POST {url}; stopping per rights policy")
    return status, raw.decode("utf-8", errors="replace"), raw


def parse_src03_page_info(html: str) -> tuple[str | None, int | None]:
    match = re.search(r'id="document_page_info"[^>]*>(.*?)</div>', html, re.S)
    if not match:
        return None, None
    text = " ".join(match.group(1).split())
    count_match = re.search(r"\|\s*(\d+)\s*$", text)
    return text, (int(count_match.group(1)) if count_match else None)


def main() -> None:
    run_dir = ROOT / "build/g1/G1-REAL-20261127-01"
    snap_dir = run_dir / "catalog-snapshot"
    snap_dir.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(timezone.utc)
    now_vn = now_utc.astimezone(timezone(timedelta(hours=7)))
    cutoff_payload = {
        "run_id": "G1-REAL-20261127-01",
        "cutoff_utc": now_utc.isoformat(),
        "cutoff_vn": now_vn.isoformat(),
        "rights_decision_ref": "G1-D01-20261127-STATUTORY",
        "legal_refs": [
            "https://vanban.chinhphu.vn/?docid=219876&pageid=27160",
            "https://vanban.chinhphu.vn/default.aspx?docid=180104&pageid=27160",
            "https://xaydungchinhsach.chinhphu.vn/toan-van-thong-tu-so-02-2025-tt-vpcp-huong-dan-thuc-hien-quy-dinh-ve-cong-bao-dien-tu-119250908164045867.htm",
            "https://vanban.chinhphu.vn/?pageid=473",
        ],
    }
    (run_dir / "run-cutoff.json").write_text(json.dumps(cutoff_payload, indent=2) + "\n", encoding="utf-8")

    evidence_pages: list[dict] = []

    def record_page(tag: str, url: str, status: int, raw: bytes) -> None:
        out = snap_dir / f"{tag}.html"
        out.write_bytes(raw)
        evidence_pages.append({
            "tag": tag,
            "url": url,
            "http_status": status,
            "bytes": len(raw),
            "sha256": sha256_bytes(raw),
        })

    # 1. SRC-03 all-time + typegroupid breakdown (GET, uncapped)
    base_url = "https://vanban.chinhphu.vn/he-thong-van-ban?classid=1&mode=1"
    st, h_base, raw_base = curl_get(base_url, delay=0.0)
    record_page("src03_all", base_url, st, raw_base)
    base_info, base_total = parse_src03_page_info(h_base)

    src03_by_type_all_time: dict[str, dict] = {}
    type_html_cache: dict[int, str] = {}
    for tg_id, tg_name in TYPEGROUPS.items():
        url = f"{base_url}&typegroupid={tg_id}"
        st_t, h_t, raw_t = curl_get(url)
        record_page(f"src03_type_{tg_id}", url, st_t, raw_t)
        info_t, count_t = parse_src03_page_info(h_t)
        src03_by_type_all_time[str(tg_id)] = {
            "name": tg_name,
            "url": url,
            "page_info": info_t,
            "portal_total": count_t,
        }
        type_html_cache[tg_id] = h_t

    # 2. SRC-03 year-by-year 2020..2026 across all types (POST with rpp=500 -> note cap at 500!)
    src03_all_types_by_year: dict[str, dict] = {}
    for year in range(2020, 2027):
        st_y, h_y, raw_y = curl_post_src03(
            base_url,
            h_base,
            {
                "ctrl_191017_163$drdDocYear": str(year),
                "ctrl_191017_163$drdRecordPerPage": "500",
                "ctrl_191017_163$btnSearch": "Tìm kiếm",
            },
        )
        record_page(f"src03_year_{year}", base_url, st_y, raw_y)
        info_y, count_y = parse_src03_page_info(h_y)
        src03_all_types_by_year[str(year)] = {
            "page_info": info_y,
            "returned_total": count_y,
            "capped_at_500": count_y == 500,
        }

    # 3. SRC-03 Laws (typegroupid=3) & Decrees (typegroupid=4) by year 2020..2026 (using drdDocCategory filter or type url)
    src03_major_types_by_year: dict[str, dict[str, dict]] = {}
    for tg_id in (3, 4):
        tg_url = f"{base_url}&typegroupid={tg_id}"
        src03_major_types_by_year[TYPEGROUPS[tg_id]] = {}
        for year in range(2020, 2027):
            st_ty, h_ty, raw_ty = curl_post_src03(
                tg_url,
                type_html_cache[tg_id],
                {
                    "ctrl_191017_163$drdDocYear": str(year),
                    "ctrl_191017_163$drdRecordPerPage": "500",
                    "ctrl_191017_163$btnSearch": "Tìm kiếm",
                },
            )
            record_page(f"src03_type_{tg_id}_year_{year}", tg_url, st_ty, raw_ty)
            info_ty, count_ty = parse_src03_page_info(h_ty)
            src03_major_types_by_year[TYPEGROUPS[tg_id]][str(year)] = {
                "page_info": info_ty,
                "returned_total": count_ty,
                "exact_under_500_cap": count_ty is not None and count_ty < 500,
            }

    # 4. SRC-01 listing snapshot
    cb_url = "https://congbao.chinhphu.vn/van-ban-dang-cong-bao/trang-1.htm"
    st_cb, h_cb, raw_cb = curl_get(cb_url)
    record_page("src01_trang_1", cb_url, st_cb, raw_cb)
    m_pages = re.search(r"totalPageSodo\s*=\s*(\d+)", h_cb)
    cb_total_pages = int(m_pages.group(1)) if m_pages else None
    cb_items_page1 = len(set(re.findall(r"/van-ban/[^\"']+\.htm", h_cb)))

    summary = {
        "run_id": "G1-REAL-20261127-01",
        "cutoff_utc": cutoff_payload["cutoff_utc"],
        "cutoff_vn": cutoff_payload["cutoff_vn"],
        "rights_decision_ref": cutoff_payload["rights_decision_ref"],
        "src03_vanban_chinhphu": {
            "all_time_portal_total": base_total,
            "all_time_page_info": base_info,
            "by_type_all_time_uncapped": src03_by_type_all_time,
            "all_types_by_year_post_rpp500": src03_all_types_by_year,
            "laws_and_decrees_by_year_post_rpp500": src03_major_types_by_year,
            "server_behavior_note": "ASP.NET btnSearch caps returned result set at drdRecordPerPage<=500; cells <500 are exact for that query, cells ==500 indicate >=500 documents.",
        },
        "src01_congbao_chinhphu": {
            "listing_url": cb_url,
            "total_pages_reported": cb_total_pages,
            "items_on_page_1": cb_items_page1,
            "estimated_unfiltered_listing_slots": (cb_total_pages * cb_items_page1) if (cb_total_pages and cb_items_page1) else None,
            "year_2020_to_cutoff_dedup_count": "UNKNOWN_WITHOUT_PAGINATED_CRAWL",
            "note": "Portal exposes totalPageSodo across all Công báo issues (~10 doc links/page, some docs span multiple Công báo numbers); full 2020-to-cutoff deduplicated count deferred to G2 polite pagination to respect G1 rate caps.",
        },
        "cross_source_dedup_denominator_2020_to_cutoff": "UNKNOWN_PENDING_G2_FULL_ENUMERATION",
        "observed_html_snapshots": evidence_pages,
    }
    out_json = snap_dir / "catalog-counts.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_json} ({len(evidence_pages)} HTML snapshots captured)")
    print("SRC-03 all-time total:", base_total)
    print("SRC-03 by type all-time:", {k: v["portal_total"] for k, v in src03_by_type_all_time.items()})
    print("SRC-03 2020-2026 overall:", {y: v["returned_total"] for y, v in src03_all_types_by_year.items()})
    for tg_name, yearly in src03_major_types_by_year.items():
        print(f"SRC-03 {tg_name} 2020-2026:", {y: v["returned_total"] for y, v in yearly.items()})
    print("SRC-01 total pages:", cb_total_pages, "slots~", summary["src01_congbao_chinhphu"]["estimated_unfiltered_listing_slots"])


if __name__ == "__main__":
    main()
