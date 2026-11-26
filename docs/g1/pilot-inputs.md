# Dữ liệu đầu vào cho pilot G1

Ngày 26/11/2026 · Biểu mẫu chuẩn bị cho G1-T03–T06, T09–T12 tại thời điểm trước khi mở quyền. Tình trạng hiện hành và đường dẫn lô thật xem tại [báo cáo thực thi](execution-status-2026-11-26.md).

## Quyền, catalog và taxonomy

| Nguồn | Trạng thái | Phạm vi cần xác nhận trước |
|---|---|---|
| SRC-01 Công báo | `PENDING_RIGHTS` | Số Công báo và URL mẫu, PDF/DOC, yêu cầu ghi nguồn, từng thao tác dự kiến |
| SRC-03 Hệ thống văn bản Chính phủ | `PENDING_RIGHTS` | URL catalog và tệp đính kèm, loại bản ký, phạm vi đối chiếu với SRC-01, từng thao tác dự kiến |
| SRC-02, SRC-04–07 | `PENDING_RIGHTS` | Kênh chính thức, lớp dữ liệu, độ bao phủ, điều kiện dùng và nguồn thay thế khi thiếu |

Chủ dự án xác nhận từng action trong [registry](../../experiments/g1/source-rights.json) từ URL chính sách hoặc thư xác nhận. Mỗi bản ghi duyệt gồm source owner/contact, action, URL và phiên bản/ngày chính sách, evidence ref, người duyệt, khoảng hiệu lực, quy trình thu hồi, mục đích, lớp dữ liệu, địa bàn, loại văn bản, khoảng ngày ban hành, URL chính xác và giới hạn theo byte/lượt. Sáu action là `manual_download`, `automated_access`, `store`, `index`, `cite`, `redistribute`. [Mẫu policy trong test fixture](../../services/data-ingestion/tests/test_g1_ingest.py).

Phiên bản taxonomy dự thảo giữ `CIV`, `CRI`, `ADM`, `LAB`, `LND`, `BUS`, `TRA`, `EDU`, `ENV` và `UNMAPPED` để chờ review. Mapping dẫn đường hiện có gồm giao dịch/sở hữu, tội phạm/hình phạt, xử lý vi phạm, quan hệ lao động, quyền sử dụng đất, doanh nghiệp, giao thông đường bộ, giáo dục và bảo vệ môi trường. Chín seed vùng trung ương có nguồn tham chiếu trong discovery cũ. Mẫu số theo domain, phân ngành, loại, cấp, địa bàn và thời kỳ hiện `UNKNOWN`. Ưu tiên rà hiến định, tố tụng, y tế, tài chính, thuế, địa phương và văn bản lịch sử khi có catalog. [Mapping và nguồn dẫn đường](poc01-sources.md#taxonomy-pilot-010) · [Quy tắc phân tầng](02-source-corpus-plan.md).

Khi có quyền, snapshot cần `snapshot_id`, `taxonomy_revision`, `recorded_at`, scope/cutoff, registry revision và các quyền được dùng. Mỗi bản ghi cần issuer, type, number, year, disambiguation, family/version ID, source record ID/revision, URL và hash/MIME/bytes của artifact nếu có quyền giữ; gắn locality, language, temporal/binding/review states, nhãn domain, reference và split eligibility. Khử trùng theo identity/version có đối chiếu, giữ từng provenance và nhóm conflict riêng. Mẫu số là eligible identity/version của catalog đã được phép. Mẫu số vắng thì ghi `UNKNOWN`, số đo chưa chạy thì ghi `NOT_RUN`.

## Manifest chọn mẫu và audit parser/OCR

| Tập | Mục tiêu đã duyệt | Trạng thái thu thập thật |
|---|---:|---|
| Pilot catalog | 45 families, mục tiêu 5 mỗi domain | `BLOCKED` |
| Gold extraction | 36 artifacts trở lên | `BLOCKED` |
| Graph | 18 families, mục tiêu 2 mỗi domain | `BLOCKED` |
| Human review | 27 case, mục tiêu 3 mỗi domain | `BLOCKED` |

| Định dạng | Mục tiêu tối thiểu | Điểm đối chiếu | Kết quả trên mẫu thật |
|---|---:|---|---|
| PDF text | 6 | Layout, heading, anchor, nhiều cột và ký số | `NOT_RUN` |
| PDF scan | 6 | Scan rõ/kém, điều/khoản, dấu, tên và bảng | `NOT_RUN` |
| HTML | 4 | DOM, locator, menu và nội dung chen vào | `NOT_RUN` |
| DOC/DOCX | 4 | Native/isolation conversion, cấu trúc, bảng | `NOT_RUN` |
| Bảng tính/bảng biểu | 4 | Ô/hàng/cột, merge/header, công thức, ghi chú và phụ lục | `NOT_RUN` |
| Mẫu bổ sung | Phân bổ đủ mục tiêu 36 | Bố cục hiếm, nhiều trang, scan lệch và ảnh | `NOT_RUN` |

Mỗi dòng manifest gồm family/artifact ID, split (tuning hoặc audit), source scope/rights ref, checksum, format, condition, tags, unit và reviewer. Gold ghi metadata cần kiểm, exact quote, version, parent/order, page/offset/DOM locator, cell relations và trạng thái missing/ambiguous. Mỗi artifact có thể nhiều tag, đếm duy nhất trong tổng. Trước audit, khóa hash manifest, rubric và ngưỡng G1-D04 với tool/version, configuration, model/font, tập mẫu, unit/mẫu số, chuẩn hóa Unicode giữ dấu, quarantine rules và điều kiện lỗi nghiêm trọng. Báo từng format với tử/mẫu và các lỗi được review. [Ngưỡng và phép đo đã duyệt](03-parser-quality-plan.md#3-các-phép-đo-và-ngưỡng-đã-duyệt-g1-d04).

## Graph và sizing

[Schema graph dự thảo](../../experiments/g1/graph-gold-draft.schema.json) và [hai ví dụ tổng hợp](../../experiments/g1/graph-gold-fixture.json) lưu source/target, version/anchor, locator, quote, scope, thời gian pháp lý và thời gian ghi nhận. Mỗi bộ audit cần xác minh khóa tham chiếu, khớp quote, thứ tự biên, quyền và trạng thái người review. Chốt phạm vi theo domain, loại node/edge và group. Thống kê eligible corpus và số gold/predicted/TP/FP/FN theo type/domain. Graph audit thuộc G3. [Phạm vi và ngưỡng](04-data-graph-storage-plan.md#2-graph-hai-tầng).

Sau khi có snapshot, lập một dòng đo trên mỗi artifact gồm dedup identity, raw/normalized bytes, pages, provisions, chunks theo chunker revision, node/edge và size từng index; ghi peak RAM/disk và thời gian parse/build/rebuild. Lập mean/P50/P90 theo format/source/time. Ước lượng low/base/high theo số bản ghi mỗi năm, tốc độ tăng revision, retention, replica, backup và headroom có căn cứ. Size vector tối thiểu bằng số chunks × dimension × bytes/scalar. Đo thêm overhead và tránh đếm lặp khi dùng chung lưu trữ. Đối chứng relational/object tại G1, keyword/vector tại G2, temporal/graph tại G3 và chi phí cloud tại G6. [Mô hình sizing](04-data-graph-storage-plan.md#4-sizing-report-thực-đo).

## Nhật ký review

| Case/revision/group | Domain / task / risk | Ngày luật / cutoff / snapshot | Scope / rights / anchors | Required tier | Reviewer / role / evidence | Active / wait / adjudication (phút) | Verdict / thời điểm / adjudicated |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

Owner bổ sung family IDs, scenario ID, bản gốc nếu có bản dịch, cùng mã tham chiếu năng lực cho L3. Giữ case có required tier L3 ở `PENDING_L3` khi chưa có review đủ điều kiện. Chuẩn bị record hiện hành và kết quả đã phân xử theo tier cho [validator](../../services/evaluation/src/luatvn_ai_evaluation/review_pilot.py). Dữ liệu gốc, PII và holdout giữ ngoài Git. [Protocol POC-11](poc11-review-pilot.md) · [Đề xuất ADR-06](../adr/ADR-06-evaluation-protocol.md).
