# Bằng chứng kiểm toán dữ liệu thật G1 ngày 27/11/2026

Run `G1-REAL-20261127-01` · Cutoff `2026-11-27T00:23:31.340392+07:00` (`2026-11-26T17:23:31.340392+00:00`) · Căn cứ quyền [G1-D01-20261127-STATUTORY](owner-decision-g1-d01-2026-11-27.md) · Chủ dự án Trần Xuân Khoa

## 1. Snapshot Catalog Cổng Chính Thức (`POC-01`)

Truy vấn lịch sự trực tiếp (giãn cách `>= 1,5s`, strict TLS, lưu `29` trang HTML kèm SHA-256 ngoài Git tại `build/g1/G1-REAL-20261127-01/catalog-snapshot/catalog-counts.json`):

| Nguồn & lát cắt | Số liệu cổng báo cáo tại cutoff | Ghi chú kỹ thuật về mẫu số |
|---|---:|---|
| `SRC-03` Văn bản Chính phủ (toàn thời kỳ) | `48.101` | Hiển thị tại `#document_page_info` (`classid=1&mode=1`) |
| `SRC-03` theo loại toàn thời kỳ (GET, không trần) | Hiến pháp `5` · Sắc lệnh `917` · Luật/Pháp lệnh `865` · Nghị định `5.248` · Quyết định `23.608` · Thông tư `12.151` | Tổng 6 nhóm chính `42.794` + loại khác `5.307` = `48.101` |
| `SRC-03` Luật - Pháp lệnh (`2020–cutoff`, chính xác < 500) | `195` (`2020: 18, 2021: 3, 2022: 14, 2023: 16, 2024: 31, 2025: 89, 2026: 24`) | Truy vấn POST theo năm dưới ngưỡng trần 500 |
| `SRC-03` Nghị định (`2020–cutoff`, chính xác < 500) | `1.441` (`2020: 157, 2021: 136, 2022: 122, 2023: 91, 2024: 178, 2025: 357, 2026: 400`) | Truy vấn POST theo năm dưới ngưỡng trần 500 |
| `SRC-03` Mọi loại (`2020–cutoff`) | Mỗi năm chạm trần `500` (`>= 3.500` cho 7 năm) | Cổng giới hạn `btnSearch` ở `drdRecordPerPage <= 500` |
| `SRC-01` Công báo điện tử | `totalPageSodo = 2.673` (~`26.730` vị trí, `10` mục/trang) | Số họ khử trùng riêng `2020–cutoff` giữ `UNKNOWN_WITHOUT_PAGINATED_CRAWL` (chuyển sang G2 crawler) |
| Mẫu số giao hai nguồn đã khử trùng | `UNKNOWN_PENDING_G2_FULL_ENUMERATION` | Giữ đúng nguyên tắc `G1-02`, không cộng thô |

## 2. Corpus Pilot (`45` họ) và Taxonomy `g1-taxonomy-0.2.0-candidate` (`G1-T04`)

- Quy mô lô mẫu thật đã thu thập ngoài Git (`data/raw/`): **`50` bản ghi nguồn** (`5 SRC-01` + `45 SRC-03`), **`45` họ duy nhất** (`5` họ × `9` lĩnh vực pilot), **`48` phiên bản**, **`3` họ giao thoa hai nguồn**, **`70` tệp duy nhất theo SHA-256** (`82` occurrences).
- Đã ánh xạ sub-domain cho toàn bộ 45 họ tại `build/g1/G1-REAL-20261127-01/taxonomy-candidate.json` và lập danh sách **`9` khoảng trống V1 cho G2**: hiến định, tài chính/ngân hàng/ngân sách, sở hữu trí tuệ độc lập, hôn nhân & gia đình, quốc phòng/an ninh/cơ yếu, văn bản địa phương (`SRC-06`), án lệ/bản án (`SRC-04`/`SRC-05`), văn bản trước `2020`, đối chiếu `SRC-02`.

## 3. Kiểm toán Đa Định Dạng & OCR (`POC-02` — 36 mẫu thật tách `tuning`/`audit`)

Manifest `poc02-audit-manifest.json` (`sha256: 4b4f4f06...fdba4`) khóa trước khi chạy cho **`36` tệp thật duy nhất trên `23` họ**: `7 tuning` / `29 audit`, **`0` rò rỉ họ**.

| Nhóm định dạng | Số mẫu (tuning/audit) | Quy mô đo | Kết quả kỹ thuật quan sát (`OBSERVED`) |
|---|---:|---|---|
| `pdf_text` | `10` (`3/7`) | `484` trang (`7,45 MB`) | `pypdf plain` (`592` Điều, P50 `1,428s`); `pypdf layout` (`588` Điều, P50 `1,653s`); `pdfplumber` phát hiện `140` bảng / `1.834` ô (`P50 2,894s`) |
| `pdf_scan` | `8` (`1/7`) | `264` trang (`22,64 MB`); OCR `16` trang (`32` ảnh raw vs prep) | Tesseract.js `vie 7.0.0` đạt confidence trung bình `91,19` (cả raw 200 DPI & prep 250 DPI); `31.992 / 31.993` ký tự; `1` tệp đẩy hàng đợi `NEEDS_REVIEW`; tốc độ `1,638s/ảnh` |
| `table_appendix` | `6` (`3/3`) | `384` trang (`4,28 MB`) | `pdfplumber` bóc tách **`360` bảng / `9.153` ô** (`P50 3,822s`); lưu ý `0` tệp `.xlsx` xuất hiện trong lô mẫu thật `SRC-01/03` |
| `html` | `6` (`0/6`) | `845 KB` | `BeautifulSoup4 + lxml` giảm trung bình `52,59%` nhiễu (`P50 0,0019s`); trung bình `0,83` trường metadata (do DOM `SRC-01` cần extractor riêng ở G2) |
| `doc_docx` | `6` (`0/6`) | `1` DOCX (`79,7 KB`) + `5` DOC (`6,31 MB`) | DOCX (`413/2026/NĐ-CP`) khớp `31/31` mốc Điều với PDF + `2` bảng. `5` DOC xác nhận container OLE2 hợp lệ và định tuyến `NEEDS_CONVERTER_OR_REVIEW` |

- **Kiểm thử Quarantine & Bảo mật (`6/6 PASS`)**: `synthetic_xlsx_openpyxl` (giữ công thức `=C2+D2`), `malformed_pdf_quarantine` (`PdfStreamError`), `malformed_docx_quarantine` (`BadZipFile`), `html_script_strip_and_rights_guard` (`QUARANTINED`), `oversize_rights_guard` (`OUTSIDE_APPROVED_SCOPE`), `real_date_anomaly_59_2020_qh14` (giữ `01/01/1900` vs `01-01-2021` thành conflict).

## 4. Bitemporal (`T08`), Graph 18 Họ (`T09`) và Storage Sizing trên PG 18.6 (`T10`)

- **Bitemporal (`T08`)**: PostgreSQL `18.6` `PASS` toàn bộ `docs/g0/examples/temporal-example.test.sql` và `experiments/g1/temporal-fixture.sql`, sau đó nạp và khôi phục MD5 toàn vẹn **`4.436` candidate chunks** (`PENDING_REVIEW`).
- **Graph Gold Draft (`T09`)**: `build_real_graph_candidates.py` sinh **`187` bản ghi trên đủ `18` họ / `9` lĩnh vực** (`186 candidate`, `1 conflict`), `100%` hợp lệ schema [graph-gold-draft.schema.json](../../../experiments/g1/graph-gold-draft.schema.json):
  - `structural`: `18 document`, `18 provision`, `1 jurisdiction`, `18 contains`, `18 locality`, `11 references`, `5 guides`, `5 modifies`, `2 lineage`, `1 repeals` (`0 corrects` được ghi nhận trung thực).
  - `normative` (đủ cả 9 domain): `45` nodes (`9` mỗi loại `Subject`, `Right`, `Obligation`, `Condition`, `Exception`) + `45` edges (`9` mỗi loại `applies_to`, `grants`, `imposes`, `conditioned_by`, `excepted_by`).
- **Sizing PG 18.6 (`T10`)**: `173.803.902` B raw khử trùng (`165,75 MiB`), `4.675.855` B UTF-8 chuẩn hóa (`4.436` chunks), heap + B-tree `6.414.336` B, FTS `GIN` `1.425.408` B (`0,51s`), Graph table + index `172.032` B (`2-hop CTE 40,54ms`), `pg_dump -Fc` `865.767` B (backup `0,371s`, restore `0,524s`, MD5 PASS). Dự báo Low/Base/High đạt `43,74 / 354,98 / 1.217,61 GiB` (chi tiết trong [ADR-02](../../adr/ADR-02-storage-and-indexing.md)).

## 5. `POC-11` (`T11`) và Cách chạy lại

- `review_pilot.py` xác nhận **`27` cases trên `27` connected groups**, trạng thái **`18 PENDING_L2`**, **`9 PENDING_L3`**, **`0 L2 verified`**, **`0 L3 verified`** (`human-reviews.json` = `[]`).

```powershell
# Tạo lại chuỗi kiểm thử đầy đủ tại local (từ thư mục gốc LuatVN-AI)
$env:PATH = "C:\Program Files\PostgreSQL\18-local\bin;$env:PATH"
build/g1-venv/Scripts/python.exe -B -X utf8 experiments/g1/poc02/build_audit_manifest.py
build/g1-venv/Scripts/python.exe -B -X utf8 experiments/g1/poc02/audit_real_formats.py
build/g1-venv/Scripts/python.exe -B -X utf8 experiments/g1/build_real_graph_candidates.py
build/g1-venv/Scripts/python.exe -B -X utf8 experiments/g1/check_graph_fixture.py
python -B -X utf8 experiments/g1/run_temporal_fixture.py --chunks build/g1/G1-REAL-20261127-01/poc02/chunks.jsonl --sizing-output build/g1/G1-REAL-20261127-01/relational-sizing.json
build/g1-venv/Scripts/python.exe -B -X utf8 experiments/g1/measure_storage_sizing.py --chunks build/g1/G1-REAL-20261127-01/poc02/chunks.jsonl --graph build/g1/G1-REAL-20261127-01/graph-gold-candidates.json --catalog-counts build/g1/G1-REAL-20261127-01/catalog-snapshot/catalog-counts.json --prev-dir build/g1/G1-REAL-20261126-02 --output build/g1/G1-REAL-20261127-01/full-storage-sizing.json
build/g1-venv/Scripts/python.exe -B -X utf8 experiments/g1/prepare_poc11_real.py
python -B -X utf8 services/evaluation/src/luatvn_ai_evaluation/review_pilot.py --cases build/g1/G1-REAL-20261127-01/poc11/cases.json --reviews build/g1/G1-REAL-20261127-01/poc11/human-reviews.json --output build/g1/G1-REAL-20261127-01/poc11/summary.json
```
