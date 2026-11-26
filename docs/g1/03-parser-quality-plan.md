# G1-03 — Parser/OCR & Data Quality protocol

Phiên bản 1.0 · Quyết định G1-D01–06 đã được chủ dự án duyệt ngày 26/11/2026 · POC-02/TST-02 · REQ-DATA-04–07, REQ-TEMP-01, REQ-SEC-05 · ADR-03 proposed

## 1. Bắt đầu từ bằng chứng đã có

[pilot synthetic](poc02-parser-ocr.md) cho thấy pypdf plain và layout đều giữ 6/6 mốc, nhưng plain mất cả 3 hàng bảng. Scan rõ giữ 6/6 mốc nhưng lỗi ký tự 1,56%, mất bảng; scan suy giảm chỉ 1/6 mốc và CER 25,78%. Vì vậy CER tốt không đảm bảo giữ cấu trúc pháp lý. Không suy từ một trang synthetic sang tỷ lệ toàn corpus.

## 2. Gold sample & đối chứng

Sau POC-01 xác minh/phê duyệt quyền theo action, chọn tối thiểu 36 artifacts theo G1-D02 (không trùng trang được tính hai lần trong cùng đơn vị đo). Gắn format, source, family, bố cục, scan condition và quyền. Ưu tiên tối thiểu 6 PDF text, 6 PDF scan (rõ/kém), 4 HTML, 4 DOC/DOCX, 4 bảng tính/bảng biểu và phụ lục/biểu mẫu, phần còn lại phân bổ ca ký số, đa cột, nhiều trang, hình ảnh, công thức, scan lệch và các định dạng hiếm; một artifact có thể thuộc nhiều tag. Báo strata thiếu thay vì coi đạt.

Gold do người thật lập/đối chiếu: metadata fields; exact spans pháp lý; hierarchy node, parent, order; anchor page/offset/HTML locator/cell; bảng row/column/header/merge/notes; bản ký và provenance; trạng thái missing/ambiguous. Reviewer ghi reference, snapshot, quyền, timestamp và adjudication. Không dùng parser output làm gold duy nhất.

| Format | Đối chứng proposed |
|---|---|
| PDF có text layer | pypdf plain/layout đã có vs parser layout thay thế nếu cần |
| Scan/image | Tesseract vie hiện có vs cấu hình preprocessing/deskew, engine khác nếu cần, OCR local |
| HTML | Cấu trúc DOM vs normalized text; kiểm menu/boilerplate/injection |
| DOC/DOCX | Native extraction hoặc conversion cách ly; so cấu trúc, table và anchor |
| Spreadsheet/table | Giữ row/cell/header/merge/formula và liên kết phụ lục; đo mất ngữ nghĩa dù text đúng |

Pin version, config, hardware, font/model hash; chạy cùng inputs và gold. Tách tuning sample và audit sample theo family; không tối ưu trên holdout G5.

## 3. Các phép đo và ngưỡng đã duyệt (G1-D04)

| Metric | Định nghĩa trên gold | Ngưỡng pilot đã duyệt (không thay AC V1) |
|---|---|---|
| Metadata | required fields hợp lệ / fields bắt buộc áp dụng | ≥ 98%, thiếu identity/version/rights thì quarantine |
| Legal anchors & hierarchy | node/parent/locator precision/recall; report riêng | ≥ 98% precision, ≥ 95% recall ở nhóm đầu vào được phép auto-verify |
| Text CER | edit distance ký tự / gold characters, định nghĩa normalize được pin, không bỏ dấu | ≤ 1% text layer; ≤ 3% scan rõ; scan kém báo riêng |
| Table structure | exact correct cell relation / gold cell relations, missing tính sai | ≥ 95% ở nhóm hỗ trợ tự động; không bỏ notes/phụ lục |
| Critical identity/version | số hiệu, điều/khoản/điểm, version, date/quote/anchor quan trọng | 0 lỗi lọt qua verified channel trong audit |
| Freshness/throughput | thời gian/byte/trang/artifact, P50/P90; stages error/retry | Đo baseline; chốt capacity sau run |
| Recovery | replay, interruption, checkpoint và idempotency | 0 duplicate logical revision trên cases thiết kế; rollback được |

Các ngưỡng số ở trên đã được chủ dự án duyệt theo G1-D04 ngày 26/11/2026. Trước audit phải khóa manifest có revision/hash: gold sample và group split, format strata, đơn vị đo/mẫu số, công thức metric/normalization, config/tool versions, ngưỡng, critical-error rule, tiêu chí quarantine và rubric; lưu commit/digest cùng run ID. Không điều chỉnh ngưỡng hoặc chuyển mẫu audit sang tuning sau khi thấy kết quả; nếu cần thay đổi, lập change control và audit mới độc lập. Ngưỡng throughput chưa có số liệu là TBD sau run. Báo numerator/denominator từng format/subgroup, counts missing, failure samples, và mức bất định; không tuyên bố bao phủ nếu audit ít/denominator 0. Nếu engine không qua ở nhóm đầu vào khó, có manual/quarantine pipeline đã kiểm thay vì tự hạ chuẩn hoặc tự loại format khỏi V1. Scan cần review nếu confidence thấp, thiếu cấu trúc/anchor, date conflict, unexpected amendment, table mismatch; chỉ verified evidence vào snapshot AI. Không auto xác minh legal binding từ OCR.

## 4. Pipeline PoC tối thiểu và failure tests

Nguồn được duyệt → fetch/checkpoint → raw hash/immutable metadata → MIME/security quarantine → parse/OCR → normalize candidate → validate structure/lineage → human review cần thiết → snapshot candidate. Dùng Docker và database/object store local tạm, không deploy production, không dùng API trả phí mặc định (G1-D05).
- TST-02.1: ngắt sau raw write, chạy lại cùng artifact, xác nhận 1 logical revision và audit 2 runs; cùng text nhưng khác source giữ provenance.
- Fixture mismatch source/version; duplicate labels theo context; missing bounds/unknown dates; scan tạo mốc giả; phụ lục/table nhiều trang; malformed document, injection, oversized input, blocked action. Chuyển trạng thái đúng, không xuất verified.
- Lưu nguyên bản và map normalized offsets → page/locator; guardrail quarantine/review test phải qua cho mọi ca quan trọng.
- Lưu extraction diff JSON/CSV đã che, summary by format, version/time/size/log và manual correction time. Số liệu thật tách synthetic, chưa chạy ghi NOT_RUN.

Khi hoàn thành, đề xuất parser configurable theo format và đường fallback/review; ADR-03 chỉ ghi phần có evidence POC-02. Các phần embedding/rerank/rule/LLM chờ G2–G4; không ACCEPTED toàn stack tại G1.

## 5. Khóa tập audit thật

Ghi trước khi chạy audit chính thức số họ độc lập và đơn vị gold theo từng định dạng được đề xuất cho xử lý tự động. Dùng các mức 6 PDF text, 6 PDF scan, 4 HTML, 4 DOC/DOCX và 4 bảng/biểu của §2 để duyệt phân bổ. Ghi rõ mẫu thuộc tuning hoặc audit, nhóm có đủ mẫu, nhóm phải chuyển review/quarantine và quy tắc xử lý khi thiếu. Số liệu parser trên lô quan sát được giữ dưới trạng thái `OBSERVED` đến khi có gold độc lập. [Cách đo trên tệp thật](poc02-parser-ocr.md#chạy-trên-mẫu-thật)

Theo NFR-05, freshness cần mốc thu thập, xác minh và index theo cùng phiên bản. Ledger của lô thủ công giữ thời điểm tải thực. Các mốc xác minh và index được đo khi những bước tương ứng thực thi. Báo số bản ghi đủ điều kiện và độ trễ theo nguồn, ghi SLO sau khi có quan sát đại diện.
