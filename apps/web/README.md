# web

- **Namespace**: `github.com/WindFaculty` (`PRIVATE`, nhánh mặc định `main`)
- **Phạm vi**: `V1` · **Mốc gate**: `G4/G6`
- **Chủ sở hữu**: Trần Xuân Khoa
- **Phiên bản Contract pin**: `0.2.1-draft` ([contracts](../../packages/contracts/README.md))
- **Trạng thái**: Skeleton G0 (V1) — sẵn sàng cho triển khai theo gate sau khi G0 được đóng.

## Ranh giới sở hữu
Legal Web application (React + Vite + TypeScript): search, document viewer, chat, citations, age gate

## Hợp đồng & tương tác liên service
Consumes Answer/SSE & Search OpenAPI via Public API Gateway/BFF

## Kiểm thử tối thiểu
```bash
npm test
```

## Tài liệu tham chiếu
- Danh mục & quy chuẩn polyrepo: `WindFaculty/LuatVN-AI-control` (`docs/g0/adr/ADR-01-polyrepo-catalog.md`, `docs/g0/03-sad.md`)
- Chính sách bảo mật & secrets: [SECURITY.md](SECURITY.md)
