# G1 Dữ liệu và PoC

**G1 đã bắt đầu, chờ nghiệm thu.** Đợt ngày 26/11/2026 đã khảo sát khả năng truy cập nguồn, đối chiếu chín nhóm taxonomy pilot với các bản ghi công khai và chạy parser/OCR trên ba PDF tổng hợp. G1-D01–06 đã được chủ dự án duyệt ngày 26/11/2026; G1 còn cần bằng chứng quyền theo từng hành động, corpus có mẫu số, kiểm chất lượng trên mẫu thật và số đo review của người thật. [Điều kiện G1](../g0/14-acceptance-test-plan.md#gate-severity-và-rollback).

| Hạng mục | Bằng chứng đã có | Điều kiện còn thiếu |
|---|---|---|
| POC-01 | `G1-POC01-20261126-DISCOVERY-01`. Quan sát các cổng, căn cứ về quyền, taxonomy `0.1.0` và chín bản ghi dẫn đường. | Quyền theo nguồn/hành động, snapshot catalog, mẫu số phân tầng và sizing thật. [Khảo sát nguồn](poc01-sources.md) |
| POC-02 | `G1-POC02-20261126-SYNTH-01`. pypdf và Tesseract `vie` đã chạy trên PDF văn bản, scan rõ và scan suy giảm. | Mẫu thật được duyệt, kiểm thêm HTML/DOC/DOCX và bảng với cấu trúc khác, ngưỡng đã duyệt theo G1-D04 nhưng cần khóa audit manifest và đo real samples. [Kết quả pilot](poc02-parser-ocr.md) |
| POC-11 | Giao thức đo và mẫu ghi review đã chuẩn bị. Số case L2/L3 xác minh trong đợt này là `0/0`. | Owner đã nhận thực hiện L2; còn dữ liệu hợp lệ, review logs, thời gian median/P90, số nhóm độc lập và tỷ lệ cần L3. [Giao thức review](poc11-review-pilot.md) |
| Data model và graph | Thiết kế bitemporal và fixture G0 có sẵn. Pilot trích xuất đã quan sát lỗi ID điều khoản và mất liên kết hàng bảng. | Chọn mẫu thật cho structural và normative graph, chốt mẫu số theo loại node/edge, xác nhận migration và sizing theo dữ liệu G1. [Database và graph](../g0/06-database-design.md) |
| Monorepo và CI | Mã V1, contracts và bằng chứng G1 nằm trong monorepo. Repo demo quản lý sandbox theo ADR-07. | Theo dõi kết quả workflow hợp nhất trên commit chuyển đổi. [ADR-07](../adr/ADR-07-monorepo-and-demo.md) · [Kiểm kê](../repo-inventory.md) |

Theo G1-D01, ưu tiên `SRC-01` và `SRC-03`, xác minh quyền từng action trước tải và xử lý. Khi có xác nhận, tạo snapshot mẫu, chạy parser/OCR và đo review trên cùng phạm vi có provenance. Giữ các phép đo tổng hợp trong tập fixture. ADR-02/03/06 tiếp tục ở trạng thái đề xuất cho đến khi có bằng chứng tương ứng. [Sổ quyết định](../g0/registers.md#adr).

## Kế hoạch thực thi G1 — v1.0

Bộ kế hoạch v1.0 cập nhật 6/6 quyết định của chủ dự án xác nhận ngày 26/11/2026, sẵn sàng giao task cho AI Coding Agent theo Baseline v1.1/ADR-07. Thời gian 30–40 giờ/tuần; ngân sách ưu tiên miễn phí; local-first với Docker và database local. Các trang dưới đây là kế hoạch, không thay kết quả pilot đã lưu và không xác nhận G1 PASS.

| Hồ sơ | Mục đích |
|---|---|
| [G1-01](01-execution-plan.md) | Workstream, timeline, dependency và quy tắc thực thi |
| [G1-02](02-source-corpus-plan.md) | Quyền nguồn, taxonomy, corpus và coverage |
| [G1-03](03-parser-quality-plan.md) | Gold sample, parser/OCR và quality gates |
| [G1-04](04-data-graph-storage-plan.md) | Temporal/graph golden set, storage & sizing |
| [G1-05](05-review-evaluation-plan.md) | Human review pilot, benchmark và holdout feasibility |
| [G1-06](06-backlog-gate.md) | Backlog, acceptance, quyết định đã duyệt, checklist và handoff G2 |

**Việc tiếp theo:** 6/6 quyết định [G1-D01–06](06-backlog-gate.md#3-quyết-định-chủ-dự-án-đã-duyệt) đã ACCEPTED; bắt đầu G1-T01/T02, có thể chuẩn bị fixture synthetic độc lập. T03 và các task thực dữ liệu chỉ chạy khi có bằng chứng quyền theo action. Khóa audit manifest trước đánh giá; khóa phân bổ holdout thực sau POC-11. Giữ nguyên hồ sơ G0 đã hash. Chưa có PoC mới hoặc G1 PASS từ lần cập nhật tài liệu này.
