# ADR-01: Danh mục Polyrepo, Namespace và Quy chuẩn Khởi tạo

| Thuộc tính | Giá trị |
|---|---|
| Mã ADR | `ADR-01` |
| Ngày quyết định | 26/11/2026 |
| Chủ trì & phê duyệt | Trần Xuân Khoa (Chủ dự án) |
| Trạng thái | `ACCEPTED` (chốt tại G0; repo inventory ghi nhận ngay sau khi tạo skeleton) |
| Liên kết yêu cầu | `DEC-07`, `REQ-ARCH-01`, `REQ-ARCH-02`, `REQ-ARCH-04`, `RISK-03`, `AC-16` |
| Tài liệu liên quan | [SAD](../03-sad.md) · [AI Coding Agent Guidelines](../13-ai-coding-agent-guidelines.md) · [Test Plan](../14-acceptance-test-plan.md) · [Sổ đăng ký](../registers.md) |

---

## 1. Bối cảnh (Context)

`DEC-07` và `REQ-ARCH-02` yêu cầu tổ chức mã nguồn theo mô hình **polyrepo private**, tạo đủ skeleton cho toàn bộ danh mục service sau khi phê duyệt SAD (không đồng nghĩa lập trình hay triển khai đồng thời các service `LATER`). Đồng thời, chủ dự án làm việc solo kết hợp AI Coding Agents trên tài khoản GitHub cá nhân **`WindFaculty`** (vốn đang chứa nhiều dự án khác), nên cần tiền tố rõ ràng theo sản phẩm và quy chuẩn meta-workspace để vận hành gọn gàng.

---

## 2. Quyết định chính thức (Decision)

1. **Git Namespace & Visibility**:
   - Tài khoản / namespace Git: **`github.com/WindFaculty`**
   - Tiền tố đặt tên repo: **`LuatVN-AI-`** ghép với tên nghiệp vụ tiếng Anh dạng kebab-case.
   - Quyền hiển thị: **`PRIVATE`** cho toàn bộ 16 repository.
   - Nhánh mặc định: **`main`**.
2. **Package & Container Registry**:
   - Sử dụng **GitHub Packages / GHCR** thuộc `WindFaculty` và release tag/artifact từ private repo `WindFaculty/LuatVN-AI-contracts`.
   - Quy ước chuẩn hóa chữ thường cho các hệ sinh thái bắt buộc lowercase:
     - Container images (GHCR): `ghcr.io/windfaculty/luatvn-ai-<service>`
     - Python packages: `luatvn-ai-<service>` / module `luatvn_ai_<service>`
     - TypeScript/npm packages: `@windfaculty/luatvn-ai-<package>`
3. **Danh mục chính thức 16 Repository**:

| # | Repository | Phạm vi | Ranh giới sở hữu chính |
|---:|---|---|---|
| 1 | `WindFaculty/LuatVN-AI-account-workspace` | V1 | Membership, session scopes, conversation, feedback, consent |
| 2 | `WindFaculty/LuatVN-AI-legal-knowledge` | V1 | Legal versions, bitemporal assertions, taxonomy, graph & rule registry, snapshot manifest |
| 3 | `WindFaculty/LuatVN-AI-data-ingestion` | V1 | Source metadata, checkpoints, raw/quarantine objects, parser/OCR, validation reports |
| 4 | `WindFaculty/LuatVN-AI-retrieval` | V1 | Chỉ mục dẫn xuất (keyword/dense/graph projection), truy vấn và xếp hạng |
| 5 | `WindFaculty/LuatVN-AI-ai-orchestrator` | V1 | Routing, Standard/Advanced workflow, answer envelope, run state và verification |
| 6 | `WindFaculty/LuatVN-AI-model-gateway` | V1 | Provider allowlist, routing policy, quota reservations và usage ledger |
| 7 | `WindFaculty/LuatVN-AI-evaluation` | V1 | Benchmark dataset 1.000 case L2/L3, holdout, ablation và `GateReport.v1` |
| 8 | `WindFaculty/LuatVN-AI-web` | V1 | Giao diện Legal Web (React/Vite/TS) |
| 9 | `WindFaculty/LuatVN-AI-studio` | V1 | Giao diện Legal AI Studio (Public Sandbox theo ADR-05 + bản Production Admin tách biệt) |
| 10 | `WindFaculty/LuatVN-AI-control` | V1 | Hồ sơ nền, ADR, IaC, workspace manifest, repo inventory, integration tests & CI templates |
| 11 | `WindFaculty/LuatVN-AI-contracts` | V1 | OpenAPI (`answers.openapi.yaml`), JSON Schema nội bộ, codegen SDK/types & compatibility checks |
| 12 | `WindFaculty/LuatVN-AI-document-intelligence` | LATER | Hồ sơ tải lên và phân tích tài liệu riêng theo tenant |
| 13 | `WindFaculty/LuatVN-AI-legal-monitoring` | LATER | Theo dõi hiệu lực văn bản, subscription và thông báo |
| 14 | `WindFaculty/LuatVN-AI-billing-enterprise` | LATER | Billing, entitlements nâng cao và policy doanh nghiệp |
| 15 | `WindFaculty/LuatVN-AI-community` | LATER | Đóng góp cộng đồng, kiểm duyệt và chuyển ứng viên sang Ingestion |
| 16 | `WindFaculty/LuatVN-AI-mobile` | LATER | Ứng dụng Android/iOS (React Native/Expo), dùng chung API versioned |

4. **Yêu cầu cho Initial Commit của mỗi repo**:
   - `README.md` nêu rõ ranh giới sở hữu, phạm vi (`V1` hoặc `LATER`), chủ sở hữu (`Trần Xuân Khoa`), phiên bản contract pin (`0.2.1-draft`), cách chạy kiểm thử tối thiểu và trạng thái triển khai.
   - `SECURITY.md` nêu chính sách bảo mật, quản lý secret (cấm commit secrets/PII/credentials) và báo cáo sự cố.
   - `.gitignore` phù hợp ngăn lọt `.env`, secrets, build artifacts và dữ liệu tạm.
   - `.github/workflows/ci.yml` tối thiểu: kiểm tra secret/hygiene cơ bản và chạy test tối thiểu của repo; riêng `LuatVN-AI-contracts` chạy đầy đủ bộ lint OpenAPI (Redocly), codegen TypeScript/Pydantic, `tsc --strict` và `verify-contracts.py`.
   - `LuatVN-AI-control` lưu bản sao chuẩn của Baseline, bộ hồ sơ G0, `workspace.manifest.json`, script kiểm tra/đồng bộ meta-workspace và `repo-inventory.md` ghi đầy đủ URL, visibility, default branch và initial commit SHA của cả 16 repo.

---

## 3. Tác động, phương án đảo và điều kiện xem xét lại

- **Tác động**: Đáp ứng đầy đủ `DEC-07`, đồng thời giảm ma sát cho solo + AI Coding Agents bằng meta-workspace thư mục anh em điều phối từ `LuatVN-AI-control` và kiểm drift contract tự động.
- **Phương án đảo**: Có thể archive các repo `LATER` nếu có change request hợp nhất phạm vi; mọi thay đổi danh mục repo phải qua ADR sửa đổi và cập nhật `workspace.manifest.json`.
- **Revisit triggers**:
  1. Khi chuyển sang tổ chức GitHub riêng (GitHub Organization) trước G8/thương mại hóa → transfer toàn bộ 16 repo sang org và cập nhật `workspace.manifest.json`.
  2. Khi mở rộng phạm vi `LATER` → kích hoạt pipeline build/deploy đầy đủ của repo tương ứng theo gate.
