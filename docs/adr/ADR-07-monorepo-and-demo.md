# ADR-07 Monorepo sản phẩm và repo demo

| Thuộc tính | Giá trị |
|---|---|
| Quyết định | `ACCEPTED` ngày 26/11/2026, theo phê duyệt của chủ dự án trong cuộc trao đổi về phương án monorepo |
| Thay thế | [ADR-01](../g0/adr/ADR-01-polyrepo-catalog.md) về tổ chức mã nguồn và cấu trúc repo |
| Yêu cầu liên quan | `DEC-07`, `REQ-ARCH-02`, `REQ-ARCH-04`, `RISK-03`, `REQ-STUDIO-02`, `REQ-SEC-12` |

Ở G1, các repo thành phần chủ yếu chứa skeleton. Một Git root cho sản phẩm cho phép sửa contract, producer, consumer và test trong cùng PR. Duy trì giao diện, ownership dữ liệu và cấu hình build/test theo component để từng service triển khai theo gate cần thiết.

1. `WindFaculty/LuatVN-AI` là monorepo private, tiếp nối lịch sử Git của Control. `apps/` chứa Web và Studio, `services/` chứa bảy backend V1 và `packages/contracts/` là nguồn hợp đồng dùng chung. Manifest ghi đường dẫn và commit nhập. CI ở gốc kiểm tính toàn vẹn hồ sơ, contract và các component. Khi có ứng dụng chạy được, đưa test tích hợp và build image vào workflow chung.
2. `WindFaculty/LuatVN-AI-demo` quản lý cấu hình sandbox, hướng dẫn và dữ liệu mẫu. Demo sử dụng artifact của một commit sản phẩm và ghim theo image digest. Mã Web, Studio và backend được bảo trì trong monorepo. Mức truy cập vào demo được quản lý qua môi trường vận hành. [Thiết kế cô lập ADR-05](../g0/adr/ADR-05-studio-sandbox.md).
3. Phần LATER đưa vào backlog. Các repo cũ sau khi kiểm đủ mã, hồ sơ và kết quả kiểm tra chuyển đổi được lưu trữ trên GitHub cùng lịch sử commit. Bản yêu cầu v1.1 ghi thay đổi. SHA-256 của baseline v1.0 và hồ sơ G0 v0.2.1 dùng kiểm mốc nghiệm thu gốc.

Các tác vụ G1 tiếp tục dựa trên [bằng chứng đã có](../g1/README.md). Xem xét tách thêm repo khi trách nhiệm sở hữu, quyền truy cập mã hoặc lịch phát hành độc lập tạo yêu cầu cụ thể. [Phụ lục kiến trúc và truy vết](../architecture/current-repository-layout.md).
