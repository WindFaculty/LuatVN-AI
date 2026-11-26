# Kiểm kê repo và nguồn mã chuyển đổi

| Repo hoạt động | Phạm vi |
|---|---|
| [WindFaculty/LuatVN-AI](https://github.com/WindFaculty/LuatVN-AI) | Monorepo công khai (public), tiếp nối lịch sử Git của LuatVN-AI-control |
| [WindFaculty/LuatVN-AI-demo](https://github.com/WindFaculty/LuatVN-AI-demo) | Cấu hình triển khai, dữ liệu mẫu và hướng dẫn sandbox |

Ngày 26/11/2026, 15 repo đã archive được xóa khỏi GitHub sau khi chủ dự án xác nhận. Danh mục bên dưới ghi tên và SHA nguồn của các phần trước khi chuyển đổi. [Manifest](../workspace.manifest.json) · [ADR-07](adr/ADR-07-monorepo-and-demo.md) · [Actions](https://github.com/WindFaculty/LuatVN-AI/actions).

| Repo trước chuyển đổi | Commit nguồn | Phạm vi sau chuyển đổi |
|---|---|---|
| `WindFaculty/LuatVN-AI-account-workspace` | `1d0233be3d54` | `services/account-workspace` |
| `WindFaculty/LuatVN-AI-legal-knowledge` | `bf6f179a056c` | `services/legal-knowledge` |
| `WindFaculty/LuatVN-AI-data-ingestion` | `77475b595a77` | `services/data-ingestion` |
| `WindFaculty/LuatVN-AI-retrieval` | `a690bbcf8235` | `services/retrieval` |
| `WindFaculty/LuatVN-AI-ai-orchestrator` | `734b2998c5ea` | `services/ai-orchestrator` |
| `WindFaculty/LuatVN-AI-model-gateway` | `11a85646702e` | `services/model-gateway` |
| `WindFaculty/LuatVN-AI-evaluation` | `52f713674196` | `services/evaluation` |
| `WindFaculty/LuatVN-AI-web` | `407fc84feed3` | `apps/web` |
| `WindFaculty/LuatVN-AI-studio` | `84315ca941fa` | `apps/studio` |
| `WindFaculty/LuatVN-AI-contracts` | `da324ba45977` | `packages/contracts` |
| `WindFaculty/LuatVN-AI-document-intelligence` | `a0308dda3ca3` | [Backlog LATER](../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md#later--các-phiên-bản-sau-giữ-trong-product-backlog) |
| `WindFaculty/LuatVN-AI-legal-monitoring` | `973779c00e5c` | [Backlog LATER](../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md#later--các-phiên-bản-sau-giữ-trong-product-backlog) |
| `WindFaculty/LuatVN-AI-billing-enterprise` | `204eab24951f` | [Backlog LATER](../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md#later--các-phiên-bản-sau-giữ-trong-product-backlog) |
| `WindFaculty/LuatVN-AI-community` | `e18723072d19` | [Backlog LATER](../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md#later--các-phiên-bản-sau-giữ-trong-product-backlog) |
| `WindFaculty/LuatVN-AI-mobile` | `5017f19dfc39` | [Backlog LATER](../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md#later--các-phiên-bản-sau-giữ-trong-product-backlog) |
