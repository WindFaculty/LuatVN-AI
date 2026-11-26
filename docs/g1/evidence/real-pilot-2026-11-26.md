# Bằng chứng pilot thật G1 ngày 26/11/2026

Run `G1-REAL-20261126-02` · Cutoff ngày ban hành `2026-11-26T23:38:10.713372+07:00` · Registry `G1-D01-20261126-PILOT-R02` · Phân tích và kiểm thử đến 27/11/2026. [Quyết định D01](owner-decision-g1-d01-2026-11-26.md)

## Nguồn và khử trùng

| Chỉ số | Kết quả trên lô đã chọn |
|---|---:|
| Bản ghi nguồn SRC-01 / SRC-03 | 5 / 45 |
| Họ ứng viên / phiên bản ứng viên sau hợp nhất | 45 / 48 |
| Họ xuất hiện ở cả hai nguồn | 3 |
| Lần xuất hiện tệp / tệp duy nhất theo SHA-256 | 82 / 70 |
| Byte theo occurrence / byte đã khử trùng | 186.754.814 / 173.803.902 |
| Intake | 10 phân đoạn `COMPLETED`, 0 lỗi ingest, 0 tệp vào quarantine trong lô này |
| Catalog toàn phạm vi có mẫu số | `UNKNOWN` |

Mỗi nhóm CIV, CRI, ADM, LAB, LND, BUS, TRA, EDU và ENV có 5 họ. Taxonomy `g1-taxonomy-0.2.0-candidate` giữ mapping theo bản ghi, loại văn bản và cơ quan. Lô chọn theo URL gồm văn bản công khai từ 2020 đến cutoff. Phần địa phương, tư pháp, lịch sử trước 2020 và catalog nguồn khác còn thiếu mẫu số. [Quy tắc đếm](../02-source-corpus-plan.md#4-snapshot-và-phương-pháp-coverage)

Đã tải các URL mẫu theo phương thức truy cập thông thường từ 23:38 đến 23:52 ngày 26/11/2026, sau đó intake bằng registry đã pin URL. Thử nghiệm Python trên CDN Công báo gặp lỗi chuỗi chứng chỉ. `curl.exe` với Schannel tải được 12 tệp Công báo ở các URL công khai từ trang nguồn và kiểm TLS thành công. Trong lượt mở rộng, 11 mã có chữ Đ bị đổi ký tự khi truyền danh sách qua shell. Chạy lại đối chiếu đúng Unicode đã hoàn thành cả 11 bản ghi. Lô hợp nhất tái hiện cùng digest trên hai lượt nội bộ, khớp bundle giữ lại `6550178c719e317c417e05d9d1aa059ef182411ffed018d2c62134d63865697e`. [Giao diện CLI intake và hợp nhất](src01-src03-pilot-2026-11-26.md)

Danh sách review có 10 mục gồm 5 mục thiếu locator trang Công báo, 3 khác biệt tiêu đề giữa hai cổng và 2 cảnh báo liên quan ngày hiệu lực của `59/2020/QH14`. Công báo hiển thị `01/01/1900` và Văn bản Chính phủ hiển thị `01/01/2021`. Hai giá trị được giữ làm provenance, trạng thái hiệu lực chờ đối chiếu bản gốc. [Công báo](https://congbao.chinhphu.vn/van-ban/luat-so-59-2020-qh14-31674/31830.htm) · [Văn bản Chính phủ](https://vanban.chinhphu.vn/?docid=200447&pageid=27160)

## Parser và kích thước

- pypdf 6.19.0 và fonttools 4.69.1 đọc 64 PDF với 4.197 trang. Có 2.522 trang dưới 80 ký tự từ text layer. Đọc XML trên 1 DOCX quan sát được 2 bảng. 5 DOC cũ chưa dùng engine trích xuất.
- PDFium 5.15.2 kết xuất 8 trang cho Tesseract `vie` 7.0.0. OCR trả 9.141 ký tự sau chuẩn hóa. Confidence của engine nằm trong khoảng 90–94. CER, anchor precision/recall và độ chính xác bảng chờ gold độc lập.
- Text trích trực tiếp có 4.673.280 byte chuẩn hóa và 4.453 chunk ứng viên. Dữ liệu OCR nằm ở các tệp riêng để review. Probe mất 62,014 giây trên máy local. Chuẩn hóa và chunking vẫn giữ tham chiếu tệp và trang. [Cấu hình và lệnh](../poc02-parser-ocr.md#chạy-trên-mẫu-thật)
- PostgreSQL 18.6 nhập và lập B-tree cho 4.453 chunk, tổng dung lượng bảng và index 6.414.336 byte. Dump 898.202 byte được restore sang database tạm, khớp số dòng và fingerprint nội dung. Raw P50/P90 theo tệp là 1.045.395,5 / 6.176.759 byte. [Harness PostgreSQL](../../../experiments/g1/run_temporal_fixture.py)

| Giả định lưu cùng lô | Dung lượng mẫu, MiB |
|---|---:|
| Một bản hoạt động gồm raw đã khử trùng và bảng có index | 171,87 |
| Bản hoạt động, một bản sao raw và một dump | 338,48 |
| Hai bản hoạt động và hai bản backup gồm raw và dump | 676,96 |

Các kịch bản dùng cùng 70 tệp, chưa tính log, headroom hay index search/vector/graph. Dự báo toàn corpus chờ mẫu số và tăng trưởng theo nguồn. [Phạm vi sizing](../04-data-graph-storage-plan.md#5-bằng-chứng-graph-và-sizing-cần-bàn-giao)

## Graph và kiểm chứng người thật

Đã chọn 18 họ thực tế, hai họ mỗi nhóm, để chuẩn bị graph gold. File ứng viên ghi 5 quan hệ `guides`, 5 quan hệ `modifies` và đích nằm ngoài lô khi có. Nguồn của các đề xuất là metadata công khai và bản ghi canonical. Chủ dự án còn cần duyệt scope, anchor điều/khoản, rubric và mẫu số theo type trước khi khóa gold. [Phạm vi graph](../04-data-graph-storage-plan.md#2-graph-hai-tầng)

POC-11 có 27 ca trên 27 group, mỗi nhóm gồm ca tra cứu, ca hiệu lực và ca rủi ro. Log người thật đang trống, với 18 `PENDING_L2` và 9 `PENDING_L3`. Tỷ lệ 9/27 đến từ cách phân tầng pilot. Effort và tỷ lệ cần chuyên gia của benchmark chính chưa đo. [Giao thức review](../poc11-review-pilot.md)

## Vị trí hồ sơ và lệnh chạy lại

Raw và hai `intake-manifest-expanded.json` nằm dưới `data/raw/SRC-01/G1-REAL-20261126-01/` và `data/raw/SRC-03/G1-REAL-20261126-01/`. Manifest từng bản ghi có URL, SHA-256, thời gian quan sát, tham chiếu quyền và căn cứ. URL tải tệp có tham số và nội dung nguồn nằm ngoài Git.

Trong `build/g1/G1-REAL-20261126-02/`, thư mục `reconciled/` giữ ledger, catalog và conflicts. `parser-final/` giữ phép đo và ứng viên chunk. `relational-sizing-final.json` giữ số đo restore. `taxonomy-candidate.json`, `graph-review-candidates.json` và `poc11/` là đầu vào review.

```powershell
rtk proxy build/g1-venv/Scripts/python.exe -X utf8 experiments/g1/poc02/probe_real.py --intake data/raw/SRC-01/G1-REAL-20261126-01/intake-manifest-expanded.json data/raw/SRC-03/G1-REAL-20261126-01/intake-manifest-expanded.json --registry build/g1/G1-REAL-20261126-02/source-rights.pilot.json --output-dir build/g1/G1-REAL-20261126-02/parser-replay --ocr-dir build/g1-poc02 --ocr-pages-per-source 6
rtk proxy python -X utf8 experiments/g1/run_temporal_fixture.py --chunks build/g1/G1-REAL-20261126-02/parser-replay/chunks.jsonl --sizing-output build/g1/G1-REAL-20261126-02/relational-sizing-replay.json
rtk proxy python -X utf8 services/evaluation/src/luatvn_ai_evaluation/review_pilot.py --cases build/g1/G1-REAL-20261126-02/poc11/cases.json --reviews build/g1/G1-REAL-20261126-02/poc11/human-reviews.json --output build/g1/G1-REAL-20261126-02/poc11/summary.json
```

Registry lô có thời hạn kỹ thuật 7 ngày kể từ mốc mở lô, giới hạn từng URL và kích thước mỗi mục. Replay cần quyền còn hiệu lực. Trạng thái G1 tổng hợp tại [báo cáo thực thi](../execution-status-2026-11-26.md).
