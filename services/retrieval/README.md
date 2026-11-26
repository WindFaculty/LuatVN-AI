# retrieval

- **Namespace**: `github.com/WindFaculty` (`PRIVATE`, nhánh mặc định `main`)
- **Phạm vi**: `V1` · **Mốc gate**: `G2/G3`
- **Chủ sở hữu**: Trần Xuân Khoa
- **Phiên bản Contract pin**: `0.2.1-draft` ([contracts](../../packages/contracts/README.md))
- **Trạng thái**: Skeleton G0 (V1) — sẵn sàng cho triển khai theo gate sau khi G0 được đóng.

## Ranh giới sở hữu
Derived keyword/dense/graph indexes, query execution, filtering and reranking

## Hợp đồng & tương tác liên service
Consumes SnapshotReady.v1; serves EvidenceQuery.v1 and Search API

## Kiểm thử tối thiểu
```bash
python -m unittest discover -s tests -v
```

## Tài liệu tham chiếu
- Danh mục & quy chuẩn polyrepo: `WindFaculty/LuatVN-AI-control` (`docs/g0/adr/ADR-01-polyrepo-catalog.md`, `docs/g0/03-sad.md`)
- Chính sách bảo mật & secrets: [SECURITY.md](SECURITY.md)
