# G1 Dữ liệu và PoC

**G1 đã bắt đầu, chờ nghiệm thu.** Đợt ngày 26/11/2026 đã khảo sát khả năng truy cập nguồn, đối chiếu chín nhóm taxonomy pilot với các bản ghi công khai và chạy parser/OCR trên ba PDF tổng hợp. G1 còn cần quyết định quyền theo từng hành động, corpus có mẫu số, kiểm chất lượng trên mẫu thật và số đo review của người thật. [Điều kiện G1](../g0/14-acceptance-test-plan.md#gate-severity-và-rollback).

| Hạng mục | Bằng chứng đã có | Điều kiện còn thiếu |
|---|---|---|
| POC-01 | `G1-POC01-20261126-DISCOVERY-01`. Quan sát các cổng, căn cứ về quyền, taxonomy `0.1.0` và chín bản ghi dẫn đường. | Quyền theo nguồn/hành động, snapshot catalog, mẫu số phân tầng và sizing thật. [Khảo sát nguồn](poc01-sources.md) |
| POC-02 | `G1-POC02-20261126-SYNTH-01`. pypdf và Tesseract `vie` đã chạy trên PDF văn bản, scan rõ và scan suy giảm. | Mẫu thật được duyệt, kiểm thêm HTML/DOC/DOCX và bảng với cấu trúc khác, ngưỡng do chủ dự án duyệt. [Kết quả pilot](poc02-parser-ocr.md) |
| POC-11 | Giao thức đo và mẫu ghi review đã chuẩn bị. Số case L2/L3 xác minh trong đợt này là `0/0`. | Người review, dữ liệu hợp lệ, thời gian median/P90, số nhóm độc lập và tỷ lệ cần L3. [Giao thức review](poc11-review-pilot.md) |
| Data model và graph | Thiết kế bitemporal và fixture G0 có sẵn. Pilot trích xuất đã quan sát lỗi ID điều khoản và mất liên kết hàng bảng. | Chọn mẫu thật cho structural và normative graph, chốt mẫu số theo loại node/edge, xác nhận migration và sizing theo dữ liệu G1. [Database và graph](../g0/06-database-design.md) |
| Monorepo và CI | Mã V1, contracts và bằng chứng G1 nằm trong monorepo. Repo demo quản lý sandbox theo ADR-07. | Theo dõi kết quả workflow hợp nhất trên commit chuyển đổi. [ADR-07](../adr/ADR-07-monorepo-and-demo.md) · [Kiểm kê](../repo-inventory.md) |

Ưu tiên xác nhận phạm vi pilot thủ công với `SRC-01` hoặc `SRC-03`. Khi có xác nhận, tạo snapshot mẫu, chạy parser/OCR và đo review trên cùng phạm vi có provenance. Giữ các phép đo tổng hợp trong tập fixture. ADR-02/03/06 tiếp tục ở trạng thái đề xuất cho đến khi có bằng chứng tương ứng. [Sổ quyết định](../g0/registers.md#adr).
