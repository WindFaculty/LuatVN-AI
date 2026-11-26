# Kiểm kê repo và nguồn mã chuyển đổi

| Repo hoạt động | Phạm vi |
|---|---|
| [WindFaculty/LuatVN-AI](https://github.com/WindFaculty/LuatVN-AI) | Monorepo private, tiếp nối lịch sử Git của LuatVN-AI-control |
| [WindFaculty/LuatVN-AI-demo](https://github.com/WindFaculty/LuatVN-AI-demo) | Cấu hình triển khai, dữ liệu mẫu và hướng dẫn sandbox |

Manifest ghi SHA gốc cho các phần đã nhập. Các repo cũ lưu lịch sử và là điểm đối chiếu khi cần. [Manifest](../workspace.manifest.json) · [ADR-07](adr/ADR-07-monorepo-and-demo.md) · [Actions](https://github.com/WindFaculty/LuatVN-AI/actions).

| Repo trước chuyển đổi | Commit nguồn | Phạm vi sau chuyển đổi |
|---|---|---|
| [WindFaculty/LuatVN-AI-account-workspace](https://github.com/WindFaculty/LuatVN-AI-account-workspace) | [`1d0233be3d54`](https://github.com/WindFaculty/LuatVN-AI-account-workspace/commit/1d0233be3d54bac247bfa763fced4a5dba401906) | `services/account-workspace` |
| [WindFaculty/LuatVN-AI-legal-knowledge](https://github.com/WindFaculty/LuatVN-AI-legal-knowledge) | [`bf6f179a056c`](https://github.com/WindFaculty/LuatVN-AI-legal-knowledge/commit/bf6f179a056c28dbd2af66618e56fdad547c5d1b) | `services/legal-knowledge` |
| [WindFaculty/LuatVN-AI-data-ingestion](https://github.com/WindFaculty/LuatVN-AI-data-ingestion) | [`77475b595a77`](https://github.com/WindFaculty/LuatVN-AI-data-ingestion/commit/77475b595a77eba60cf635bea52389f3237f344f) | `services/data-ingestion` |
| [WindFaculty/LuatVN-AI-retrieval](https://github.com/WindFaculty/LuatVN-AI-retrieval) | [`a690bbcf8235`](https://github.com/WindFaculty/LuatVN-AI-retrieval/commit/a690bbcf8235a3fc15a17dfed8701d37f35a5f83) | `services/retrieval` |
| [WindFaculty/LuatVN-AI-ai-orchestrator](https://github.com/WindFaculty/LuatVN-AI-ai-orchestrator) | [`734b2998c5ea`](https://github.com/WindFaculty/LuatVN-AI-ai-orchestrator/commit/734b2998c5ea6a3b3d855f3bce8142d4b782bb0d) | `services/ai-orchestrator` |
| [WindFaculty/LuatVN-AI-model-gateway](https://github.com/WindFaculty/LuatVN-AI-model-gateway) | [`11a85646702e`](https://github.com/WindFaculty/LuatVN-AI-model-gateway/commit/11a85646702e25540ac4267d625337a9ee4e5b9d) | `services/model-gateway` |
| [WindFaculty/LuatVN-AI-evaluation](https://github.com/WindFaculty/LuatVN-AI-evaluation) | [`52f713674196`](https://github.com/WindFaculty/LuatVN-AI-evaluation/commit/52f7136741964002ecebb94ed67618359670e0bc) | `services/evaluation` |
| [WindFaculty/LuatVN-AI-web](https://github.com/WindFaculty/LuatVN-AI-web) | [`407fc84feed3`](https://github.com/WindFaculty/LuatVN-AI-web/commit/407fc84feed3db32792dc2159c8e4fade31dee36) | `apps/web` |
| [WindFaculty/LuatVN-AI-studio](https://github.com/WindFaculty/LuatVN-AI-studio) | [`84315ca941fa`](https://github.com/WindFaculty/LuatVN-AI-studio/commit/84315ca941fa6c686dba32808179d7e96591027f) | `apps/studio` |
| [WindFaculty/LuatVN-AI-contracts](https://github.com/WindFaculty/LuatVN-AI-contracts) | [`da324ba45977`](https://github.com/WindFaculty/LuatVN-AI-contracts/commit/da324ba459778526456a0e19e03973f3ab71684f) | `packages/contracts` |
| [WindFaculty/LuatVN-AI-document-intelligence](https://github.com/WindFaculty/LuatVN-AI-document-intelligence) | [`a0308dda3ca3`](https://github.com/WindFaculty/LuatVN-AI-document-intelligence/commit/a0308dda3ca395631dd7c887829b090577c8beb2) | [Backlog LATER](../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md#later--các-phiên-bản-sau-giữ-trong-product-backlog) |
| [WindFaculty/LuatVN-AI-legal-monitoring](https://github.com/WindFaculty/LuatVN-AI-legal-monitoring) | [`973779c00e5c`](https://github.com/WindFaculty/LuatVN-AI-legal-monitoring/commit/973779c00e5c4b3ae0c02e3c782c531cf35f3abb) | [Backlog LATER](../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md#later--các-phiên-bản-sau-giữ-trong-product-backlog) |
| [WindFaculty/LuatVN-AI-billing-enterprise](https://github.com/WindFaculty/LuatVN-AI-billing-enterprise) | [`204eab24951f`](https://github.com/WindFaculty/LuatVN-AI-billing-enterprise/commit/204eab24951fdcf70aa293d975823aff147d4071) | [Backlog LATER](../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md#later--các-phiên-bản-sau-giữ-trong-product-backlog) |
| [WindFaculty/LuatVN-AI-community](https://github.com/WindFaculty/LuatVN-AI-community) | [`e18723072d19`](https://github.com/WindFaculty/LuatVN-AI-community/commit/e18723072d19d16d7c1e178e372241b02b7493d7) | [Backlog LATER](../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md#later--các-phiên-bản-sau-giữ-trong-product-backlog) |
| [WindFaculty/LuatVN-AI-mobile](https://github.com/WindFaculty/LuatVN-AI-mobile) | [`5017f19dfc39`](https://github.com/WindFaculty/LuatVN-AI-mobile/commit/5017f19dfc393779987544ff66207bf0180ffba3) | [Backlog LATER](../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md#later--các-phiên-bản-sau-giữ-trong-product-backlog) |
