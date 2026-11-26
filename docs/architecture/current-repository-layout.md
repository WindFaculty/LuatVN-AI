# Kiến trúc repo và truy vết hiện hành

Phần này cập nhật tổ chức mã nguồn theo [ADR-07](../adr/ADR-07-monorepo-and-demo.md). Hồ sơ G0 là bản đã nghiệm thu trước quyết định chuyển đổi. [Baseline v1.1](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md) là yêu cầu hiện hành.

| Vị trí | Phạm vi |
|---|---|
| `apps/web`, `apps/studio` | Legal Web và mã Studio dùng cho các bản triển khai tương ứng |
| `services/account-workspace` | Tài khoản, quyền, hội thoại và consent |
| `services/data-ingestion` | Nguồn, parser/OCR, quarantine và chất lượng nạp |
| `services/legal-knowledge` | Phiên bản pháp lý, taxonomy, graph, rule và snapshot |
| `services/retrieval` | Chỉ mục dẫn xuất, truy xuất và rerank |
| `services/ai-orchestrator`, `services/model-gateway` | Luồng trả lời, verification, provider policy và usage |
| `services/evaluation` | Benchmark, thẩm định, regression và gate report |
| `packages/contracts`, `docs`, `infra` | Hợp đồng, truy vết, thử nghiệm và cấu hình phát hành |
| `WindFaculty/LuatVN-AI-demo` | Cấu hình sandbox, dữ liệu mẫu, hướng dẫn, tham chiếu digest |

Document Intelligence, Legal Monitoring, Billing/Enterprise, Community và Mobile được theo dõi trong phạm vi [LATER](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md#later--các-phiên-bản-sau-giữ-trong-product-backlog). Các ranh giới dịch vụ và dữ liệu trong [SAD G0](../g0/03-sad.md) làm căn cứ thiết kế component.

| Mã | Yêu cầu hiện hành | Kiểm tra và bằng chứng |
|---|---|---|
| `DEC-07`, `REQ-ARCH-02` | Một monorepo sản phẩm, một repo demo và backlog LATER | TST-01 bổ sung kiểm Git root, đường dẫn các component, nguồn commit nhập, visibility và tình trạng lưu trữ repo cũ |
| `REQ-ARCH-04` | Hợp đồng dùng chung và CI trong một checkout | TST-01 kiểm manifest và baseline. Contract tests kiểm codegen, Answer/SSE và JSON Schema. TST-03/TST-11 kiểm tích hợp và release ở gate tương ứng |
| `REQ-STUDIO-02`, `REQ-SEC-12` | Repo demo tham chiếu artifact sản phẩm và triển khai trong sandbox cô lập | TST-09/TST-10/TST-11 ở G6 đo chức năng, phân quyền và vận hành thật |
| `RISK-03` | Phụ thuộc chéo giữa các component và drift demo | Kiểm loại component, contract pin, smoke tests và digest khi phát hành demo |

Đổi hợp đồng cùng producer, consumer và test trong một PR. Đổi ranh giới dữ liệu hoặc phạm vi ghi giữa service qua ADR và kiểm tương thích tương ứng. [RTM G0](../g0/rtm.md) · [Kế hoạch nghiệm thu](../g0/14-acceptance-test-plan.md).
