# G1 Dữ liệu và PoC

> **Cập nhật 27/11/2026 (`G1-REAL-20261127-01`):** Đã chuyển repo sang `PUBLIC`, ghi nhận cơ sở quyền luật định, đo snapshot catalog cổng chính thức, kiểm toán 36 mẫu thật đa định dạng (OCR + bảng + quarantine), hợp lệ hóa 187 bản ghi graph 18 họ, đo sizing 5 năng lực trên PostgreSQL 18.6 và chuẩn bị đủ 27 ca `POC-11`. Gate G1 giữ **`BLOCKED` chờ kiểm chứng L2 người thật và ký duyệt của chủ dự án**. Xem **[Báo cáo nghiệm thu G1 (27/11)](g1-exit-report-2026-11-27.md)** · **[Kiểm toán thực nghiệm 27/11](evidence/g1-real-audit-2026-11-27.md)** · **[Phê duyệt quyền luật định 27/11](evidence/owner-decision-g1-d01-2026-11-27.md)**.

**G1 đã chạy pilot thật và còn chờ nghiệm thu.** G1-D01 cập nhật quyền tải mẫu công khai SRC-01/03 và xử lý nội bộ. Lô `G1-REAL-20261126-02` có 45 họ trên chín nhóm, 70 tệp theo SHA-256 và 27 ca ứng viên review trên 27 nhóm. Mẫu số catalog toàn phạm vi, audit gold và review của người thật còn mở. [Quyết định D01](evidence/owner-decision-g1-d01-2026-11-26.md) · [Báo cáo thực thi](execution-status-2026-11-26.md) · [Điều kiện G1](../g0/14-acceptance-test-plan.md#gate-severity-và-rollback)

| Hạng mục | Bằng chứng đã có | Điều kiện còn thiếu |
|---|---|---|
| POC-01 | Pilot chọn trước từ hai nguồn. Đã lưu provenance, SHA-256 và xung đột theo hạng mục. | Catalog đối chứng đầy đủ trong phạm vi đã chốt và taxonomy được duyệt. [Khảo sát nguồn](poc01-sources.md) |
| POC-02 | Có phép đo parser/OCR trên tệp thật và kết quả fixture tổng hợp làm đối chứng. | Gold có người duyệt, audit manifest theo từng định dạng và số đo precision/recall, CER, bảng. [Cách chạy](poc02-parser-ocr.md) |
| POC-11 | 18 ca chờ L2 và 9 ca chờ L3. Số case xác minh là `0/0`. | Review logs, thời gian median/P90 và quyết định khả thi. [Giao thức review](poc11-review-pilot.md) |
| Data model và graph | Migration bitemporal đã qua fixture. Có lô graph 18 họ và bằng chứng sizing/restore trên candidate chunks. | Duyệt anchor, graph gold và mẫu số theo loại node/edge. [Database và graph](../g0/06-database-design.md) |
| Monorepo và CI | Mã V1, contracts và bằng chứng G1 nằm trong monorepo. Repo demo quản lý sandbox theo ADR-07. | Theo dõi kết quả workflow hợp nhất trên commit chuyển đổi. [ADR-07](../adr/ADR-07-monorepo-and-demo.md) · [Kiểm kê](../repo-inventory.md) |

Scope hiện hành là mẫu có URL cụ thể, xử lý nội bộ và provenance theo G1-D01. ADR-02/03/06 tiếp tục ở trạng thái đề xuất trong lúc cần audit và review. [Quyết định G1-D01](evidence/owner-decision-g1-d01-2026-11-26.md) · [Sổ quyết định](../g0/registers.md#adr)

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

## Thực thi cục bộ ngày 26/11/2026

Đã xác minh workspace và contract, retry, checkpoint, quarantine, migration bitemporal, schema graph và validator review bằng fixture. Sau cập nhật D01, đã dùng intake cục bộ trên lô thật và tái hiện manifest hợp nhất. [Báo cáo T01–T13](execution-status-2026-11-26.md) · [Kiểm chứng fixture](evidence/local-verification-2026-11-26.md)
