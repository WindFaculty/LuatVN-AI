# Hồ sơ nền G0 của Luật Việt Nam AI

Phiên bản bộ hồ sơ 0.2 · Cập nhật kỹ thuật 0.2.1 · Chủ dự án chốt ngày 26/11/2026

[Căn cứ Requirements Baseline v1.0](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md)

Chủ dự án đã duyệt 14/14 hồ sơ v0.2 kèm cập nhật kỹ thuật v0.2.1 làm mốc thiết kế trước PoC. Danh sách SHA-256 định danh bản đã chốt gồm Baseline, 14 hồ sơ, RTM, các hợp đồng và fixture kiểm tra. Các quyết định kỹ thuật còn mở được theo dõi trong sổ đăng ký. [Manifest v0.2.1](g0-v0.2.1.sha256) · [Quyết định mở](registers.md#quyết-định-mở).

| # | Hồ sơ | Nội dung dùng khi duyệt |
|---|---|---|
| 01 | [PRD](01-prd.md) | Người dùng, phạm vi, mục tiêu, release priorities |
| 02 | [SRS](02-srs.md) | Vai trò, use cases, interfaces và RTM |
| 03 | [SAD](03-sad.md) | Ranh giới, ownership, contracts và 16 repo đề xuất |
| 04 | [AI/RAG](04-ai-rag.md) | Routing, retrieval, verification, modes và model policy |
| 05 | [Data Engineering](05-data-engineering.md) | Nguồn, quyền, taxonomy, acquisition/parse/validation |
| 06 | [Database Design](06-database-design.md) | ERD, bitemporal, graph và phương án lưu trữ |
| 07 | [Benchmark & Evaluation](07-benchmark-evaluation.md) | Review L2/L3, holdout, metric, ablation và regression |
| 08 | [Security & Threat Model](08-security-threat-model.md) | DFD, phân quyền, privacy và các kiểm soát |
| 09 | [UI/UX](09-ui-ux.md) | Web/Studio flows, citations, tokens, accessibility |
| 10 | [Cloud & Deployment](10-cloud-deployment.md) | Môi trường, CI/CD, cost, restore/rollback |
| 11 | [Cost Estimation](11-cost-estimation.md) | Ba kịch bản và chi phí ngoài dự toán |
| 12 | [Roadmap & Backlog](12-roadmap-backlog.md) | Lịch, effort, POC-01–11, backlog LATER |
| 13 | [AI Coding Agent Guidelines](13-ai-coding-agent-guidelines.md) | Task contract, kiểm thử, review, bằng chứng chủ dự án |
| 14 | [Acceptance Criteria & Test Plan](14-acceptance-test-plan.md) | AC-01–16, TST-01–13, gates và rollback |

[Sổ đăng ký quyết định/nguồn/rủi ro/bằng chứng](registers.md) · [Ma trận truy vết từng yêu cầu](rtm.md)

## Thay đổi theo báo cáo đánh giá

| Mức ưu tiên | Nội dung trong v0.2 |
|---|---|
| P0 | Đồng bộ danh sách ADR và sơ đồ, bổ sung luồng kiểm tuổi, xác định agent end-user chỉ đọc. Chia gate benchmark theo tầng, phân 11 PoC theo gate, tách công sức agent-assisted và review. Dự toán tách Production, Sandbox, Staging và các khoản Eval/Ingestion. [Giao thức benchmark](07-benchmark-evaluation.md) · [Roadmap](12-roadmap-backlog.md) · [Chi phí](11-cost-estimation.md) |
| P1 | Phân hai tầng graph và hai lớp Rule Engine, thêm meta-workspace cho 16 polyrepo, theo dõi SRC-02/05 và reviewer L3 từ tuần 1–2. [SAD](03-sad.md) · [Database Design](06-database-design.md) · [Sổ đăng ký](registers.md) |
| P2 | Thêm hợp đồng API/SSE và năm hợp đồng nội bộ, SQL minh họa temporal/amendment/jurisdiction, mẫu giao task và quy trình PR xuyên repo. [OpenAPI](contracts/answers.openapi.yaml) · [JSON Schema nội bộ](contracts/internal-v1.schema.json) · [SQL minh họa](examples/temporal-example.sql) · [Hướng dẫn agent](13-ai-coding-agent-guidelines.md) |

[Báo cáo đánh giá hồ sơ v0.1](../g0-evaluation-report.md).

Bản cập nhật 0.2.1 bổ sung metric/CI/S0/S1 cho GateReport, kiểm codegen và SSE cho Answer, truy vấn gốc tùy chọn cho EvidenceQuery và ràng buộc temporal cho migration G1. G1 dùng taxonomy 9 nhóm để pilot. POC-06/09 đo thêm cache và chi phí DB Sandbox. [Kiểm tra hợp đồng](contracts/README.md) · [SQL mẫu](examples/temporal-example.sql) · [Kế hoạch PoC](12-roadmap-backlog.md).

## Kiểm tra bộ hồ sơ

SHA-256 của Requirements Baseline v1.0 là `d06b7ace9d5252c1e09ab5e79ad4d34198f8fc2bfd1ebe91b9b85d3d2e4e4a03`.

Đã đối chiếu 14 hồ sơ v0.2, 123/123 dòng RTM, 305 liên kết nội bộ, 16 repo đề xuất, 6 ADR và 11 PoC theo pha. Đã tính lại ngưỡng, ba kịch bản chi phí và tổng công sức. Bốn sơ đồ Mermaid dựng thành công. Redocly kiểm OpenAPI, và JSON Schema nhận đúng các mẫu Answer/SSE, lỗi và năm hợp đồng nội bộ. DDL chạy trên PostgreSQL 18.6 tạm với fixture synthetic, kiểm hai mốc thời gian, biên khoảng, ràng buộc chồng lấn, thao tác sửa đổi và lineage. Đây là kết quả kiểm hồ sơ và ví dụ thiết kế ở G0.

Kiểm tra cục bộ bản 0.2.1 đã qua Redocly, biên dịch kiểu TypeScript sinh tự động, fixture JSON Schema/Pydantic và frame SSE. Fixture SQL trên PostgreSQL 18.6 tạm đã kiểm FK ghép, cận dưới hữu hạn, chuyển trạng thái duyệt và một lần chia tách có nhiều cạnh. [Lệnh kiểm hợp đồng](contracts/README.md) · [Fixture SQL](examples/temporal-example.test.sql).

## Phê duyệt và theo dõi

| Hạng mục | Trạng thái | Người quyết định | Ngày và bằng chứng |
|---|---|---|---|
| 14 hồ sơ v0.2, cập nhật kỹ thuật 0.2.1 và AC-16 | Đã duyệt bộ hồ sơ | Chủ dự án | 26/11/2026 · “chốt phiên bản này” trong cuộc trao đổi về v0.2.1 · [SHA-256](g0-v0.2.1.sha256) |
| Catalog và namespace polyrepo, [ADR-01](adr/ADR-01-polyrepo-catalog.md) | Đã chốt (G0) | Trần Xuân Khoa | 26/11/2026 · [ADR-01](adr/ADR-01-polyrepo-catalog.md) (`github.com/WindFaculty`, 16 repo `LuatVN-AI-*` PRIVATE, registry GitHub Packages/GHCR) |
| Ranh giới Studio sandbox, [ADR-05](adr/ADR-05-studio-sandbox.md) | Đã chốt thiết kế (G0) · chờ kiểm G6 | Trần Xuân Khoa | 26/11/2026 · [ADR-05](adr/ADR-05-studio-sandbox.md) (chung project tách cứng tài nguyên/IAM/Auth, tài khoản demo invite/CV có anti-bot + rate limit, reset hàng tuần + nút Reset) |
| G0 | **PASS (Đã đóng G0)** | Trần Xuân Khoa | 26/11/2026 · Đủ 14 hồ sơ v0.2/0.2.1, AC-16, ADR-01 và ADR-05 · Mở khóa tạo skeleton & pha G1 ([Tiêu chí đóng G0](14-acceptance-test-plan.md#gate-severity-và-rollback)) |
| POC-01–11 | NOT_RUN | Thực hiện khi G0 được duyệt, theo [roadmap](12-roadmap-backlog.md#kế-hoạch-chạy-poc-sau-g0) | Chưa có run ID |
| G1–G7 | Chờ bằng chứng | [Test Plan](14-acceptance-test-plan.md#gate-severity-và-rollback) định nghĩa đầu ra và người duyệt gate | Chưa nghiệm thu |
| G8 | LATER | Thẩm định chuyên môn, bảo mật và thương mại | Theo roadmap |

Ghi ngày, người duyệt và bằng chứng khi chốt các ADR mở. Hồ sơ tác vụ PoC bắt đầu sau khi đóng G0. Kết quả cập nhật Experiment Log, báo cáo gate và ADR tương ứng.
