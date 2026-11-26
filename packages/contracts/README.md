# contracts

- **Namespace**: `github.com/WindFaculty` (`PRIVATE`, nhánh mặc định `main`)
- **Phạm vi**: `V1` · **Mốc gate**: `G0/G1`
- **Chủ sở hữu**: Trần Xuân Khoa
- **Phiên bản Contract pin**: `0.2.1-draft` · [OpenAPI](contracts/answers.openapi.yaml) · [Schema nội bộ](contracts/internal-v1.schema.json)
- **Trạng thái**: Skeleton G0 (V1) — sẵn sàng cho triển khai theo gate sau khi G0 được đóng.

## Ranh giới sở hữu
OpenAPI 3.1 schemas, Internal v1 JSON Schemas, typed SDK generation & compatibility CI

## Hợp đồng & tương tác liên service
Source of truth for cross-service schemas and SDK generation

## Kiểm thử tối thiểu
```bash
Xem contracts/README.md (Redocly + openapi-typescript + datamodel-codegen + verify-contracts.py)
```

## Tài liệu tham chiếu
- Kiến trúc hiện hành: [ADR-07](../../docs/adr/ADR-07-monorepo-and-demo.md)
- Chính sách bảo mật & secrets: [SECURITY.md](SECURITY.md)
