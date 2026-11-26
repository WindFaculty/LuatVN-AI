# Polyrepo Inventory — Luật Việt Nam AI

- **Namespace**: `github.com/WindFaculty`
- **Tiền tố**: `LuatVN-AI-`
- **Visibility**: `PRIVATE` (16/16 theo [ADR-01](adr/ADR-01-polyrepo-catalog.md))
- **Default Branch**: `main`
- **Package / Container Registry**: GitHub Packages / `ghcr.io/windfaculty`
- **Contracts Version Pin**: `0.2.1-draft`
- **Ngày khởi tạo**: 26/11/2026
- **Thư mục meta-workspace cục bộ**: `repos/LuatVN-AI-*`

| # | Repository | Phạm vi | Visibility | Branch | Initial Commit | Trạng thái GitHub Remote | URL |
|---:|---|---|---|---|---|---|---|
| 1 | `LuatVN-AI-account-workspace` | `V1` | `PRIVATE` | `main` | `1d0233be3d54` | `PUSHED` | https://github.com/WindFaculty/LuatVN-AI-account-workspace |
| 2 | `LuatVN-AI-legal-knowledge` | `V1` | `PRIVATE` | `main` | `bf6f179a056c` | `PUSHED` | https://github.com/WindFaculty/LuatVN-AI-legal-knowledge |
| 3 | `LuatVN-AI-data-ingestion` | `V1` | `PRIVATE` | `main` | `77475b595a77` | `PUSHED` | https://github.com/WindFaculty/LuatVN-AI-data-ingestion |
| 4 | `LuatVN-AI-retrieval` | `V1` | `PRIVATE` | `main` | `a690bbcf8235` | `PUSHED` | https://github.com/WindFaculty/LuatVN-AI-retrieval |
| 5 | `LuatVN-AI-ai-orchestrator` | `V1` | `PRIVATE` | `main` | `734b2998c5ea` | `PUSHED` | https://github.com/WindFaculty/LuatVN-AI-ai-orchestrator |
| 6 | `LuatVN-AI-model-gateway` | `V1` | `PRIVATE` | `main` | `11a85646702e` | `PUSHED` | https://github.com/WindFaculty/LuatVN-AI-model-gateway |
| 7 | `LuatVN-AI-evaluation` | `V1` | `PRIVATE` | `main` | `52f713674196` | `PUSHED` | https://github.com/WindFaculty/LuatVN-AI-evaluation |
| 8 | `LuatVN-AI-web` | `V1` | `PRIVATE` | `main` | `407fc84feed3` | `PUSHED` | https://github.com/WindFaculty/LuatVN-AI-web |
| 9 | `LuatVN-AI-studio` | `V1` | `PRIVATE` | `main` | `84315ca941fa` | `PUSHED` | https://github.com/WindFaculty/LuatVN-AI-studio |
| 10 | `LuatVN-AI-control` | `V1` | `PRIVATE` | `main` | `5a6814f445d9` | `PUSHED` | https://github.com/WindFaculty/LuatVN-AI-control |
| 11 | `LuatVN-AI-contracts` | `V1` | `PRIVATE` | `main` | `da324ba45977` | `LOCAL_READY` *(GitHub rate limit)* | https://github.com/WindFaculty/LuatVN-AI-contracts |
| 12 | `LuatVN-AI-document-intelligence` | `LATER` | `PRIVATE` | `main` | `a0308dda3ca3` | `LOCAL_READY` *(GitHub rate limit)* | https://github.com/WindFaculty/LuatVN-AI-document-intelligence |
| 13 | `LuatVN-AI-legal-monitoring` | `LATER` | `PRIVATE` | `main` | `973779c00e5c` | `LOCAL_READY` *(GitHub rate limit)* | https://github.com/WindFaculty/LuatVN-AI-legal-monitoring |
| 14 | `LuatVN-AI-billing-enterprise` | `LATER` | `PRIVATE` | `main` | `204eab24951f` | `LOCAL_READY` *(GitHub rate limit)* | https://github.com/WindFaculty/LuatVN-AI-billing-enterprise |
| 15 | `LuatVN-AI-community` | `LATER` | `PRIVATE` | `main` | `e18723072d19` | `LOCAL_READY` *(GitHub rate limit)* | https://github.com/WindFaculty/LuatVN-AI-community |
| 16 | `LuatVN-AI-mobile` | `LATER` | `PRIVATE` | `main` | `5017f19dfc39` | `LOCAL_READY` *(GitHub rate limit)* | https://github.com/WindFaculty/LuatVN-AI-mobile |

## Hoàn tất 6 repo còn lại sau khi hết GitHub rate limit

GitHub áp giới hạn tần suất `createRepository` (~10 repo trong một cửa sổ ngắn trên tài khoản cá nhân). Sau khoảng 15–60 phút, chạy lệnh sau để tự động tạo và đẩy nốt 6 repo đã dựng sẵn ở local:

```powershell
python repos/LuatVN-AI-control/scripts/finish-remaining-repos.py
```
