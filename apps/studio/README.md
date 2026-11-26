# studio

- **Namespace**: `github.com/WindFaculty` (`PUBLIC`, nhánh mặc định `main`)
- **Phạm vi**: `V1` · **Mốc gate**: `G6`
- **Chủ sở hữu**: Trần Xuân Khoa
- **Phiên bản Contract pin**: `0.2.1-draft` ([contracts](../../packages/contracts/README.md))
- **Trạng thái**: Skeleton G0 (V1) — sẵn sàng cho triển khai theo gate sau khi G0 được đóng.

## Ranh giới sở hữu
Legal AI Studio (React + Vite + TypeScript): isolated Public Sandbox (ADR-05) & MFA Production Admin

## Hợp đồng & tương tác liên service
Consumes Studio/Ingestion APIs via Sandbox/Admin BFF

## Kiểm thử tối thiểu
```bash
npm test
```

## Tài liệu tham chiếu
- Danh mục & quy chuẩn polyrepo: `WindFaculty/LuatVN-AI-control` (`docs/g0/adr/ADR-01-polyrepo-catalog.md`, `docs/g0/03-sad.md`)
- Chính sách bảo mật & secrets: [SECURITY.md](SECURITY.md)
