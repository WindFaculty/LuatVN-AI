# LuatVN-AI-control

- **Namespace**: `github.com/WindFaculty` (`PRIVATE`, nhánh mặc định `main`)
- **Phạm vi**: `V1` · **Chủ sở hữu**: Trần Xuân Khoa
- **Phiên bản Contract pin**: `0.2.1-draft` (`WindFaculty/LuatVN-AI-contracts`)
- **Trạng thái**: Đã chốt G0 (2026-11-26) — chứa Requirements Baseline, 14 hồ sơ G0, ADR-01/05, `workspace.manifest.json` và `docs/repo-inventory.md`.

## Cấu trúc chính
- `Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md` — Căn cứ yêu cầu gốc
- `docs/g0/` — Bộ 14 hồ sơ nền G0, RTM, sổ đăng ký, ADR-01/05, contracts mẫu và SQL mẫu
- `docs/repo-inventory.md` — Bảng kiểm kê 16 repository private (URL, visibility, branch, commit SHA)
- `workspace.manifest.json` — Manifest pin toàn bộ 16 repo cho meta-workspace
- `scripts/verify-control.py` — Kiểm tra SHA-256, 123/123 RTM, liên kết nội bộ và manifest
- `scripts/sync-workspace.py` — Kiểm tra trạng thái meta-workspace thư mục anh em và chặn drift contract

## Kiểm thử
```bash
python scripts/verify-control.py
python scripts/sync-workspace.py --all
```
