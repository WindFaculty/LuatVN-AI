# LuatVN-AI

Monorepo công khai (public) cho Luật Việt Nam AI. G0 đã nghiệm thu theo bộ hồ sơ v0.2.1. G1 đang triển khai khảo sát và PoC. [Baseline v1.1](Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md) · [ADR-07](docs/adr/ADR-07-monorepo-and-demo.md) · [Bằng chứng G1](docs/g1/README.md).

| Thư mục | Nội dung |
|---|---|
| `apps/` | Legal Web và Legal AI Studio |
| `services/` | Account Workspace, Data Ingestion, Legal Knowledge, Retrieval, AI Orchestrator, Model Gateway và Evaluation |
| `packages/contracts/` | OpenAPI, JSON Schema, kiểm sinh kiểu và fixture |
| `docs/` | Kiến trúc hiện hành, hồ sơ G0 và bằng chứng G1 |
| `experiments/g1/` | Harness parser/OCR tổng hợp |
| `infra/` | Ranh giới build, phát hành và cấu hình hạ tầng |

`workspace.manifest.json` ghi danh mục component và SHA nhập từ các repo cũ. Phạm vi LATER theo backlog. [Kiến trúc và truy vết hiện hành](docs/architecture/current-repository-layout.md) · [Kiểm kê chuyển đổi](docs/repo-inventory.md).

[LuatVN-AI-demo](https://github.com/WindFaculty/LuatVN-AI-demo) quản lý cấu hình triển khai và dữ liệu mẫu cho sandbox. Bản phát hành demo ghim image theo digest từ monorepo.

## Kiểm thử

Chạy tại thư mục gốc với Python 3.12+ và Node.js. Dùng `--smoke` để kiểm tất cả service và app trong cùng checkout.

```powershell
rtk proxy python -X utf8 scripts/verify-workspace.py --smoke
```

Workflow chung chạy bước trên và kiểm contract bằng Redocly, TypeScript, Pydantic và fixture Answer/SSE. [Lệnh kiểm hợp đồng](packages/contracts/contracts/README.md) · [Workflow](.github/workflows/ci.yml).
