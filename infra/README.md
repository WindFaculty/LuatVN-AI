# Build và cấu hình phát hành

Mỗi app hoặc service có đầu mối build/test tại thư mục của nó. Workflow ở gốc điều phối kiểm chung và contract tests. Khi phát hành có image thực thi, ghi commit nguồn, digest image và phiên bản contract. [ADR-07](../docs/adr/ADR-07-monorepo-and-demo.md).

Sandbox có cấu hình triển khai riêng trong [repo demo](https://github.com/WindFaculty/LuatVN-AI-demo). Kiểm IAM, Auth, cơ sở dữ liệu, quota, dữ liệu mẫu, reset và cách ly Production trước nghiệm thu G6. [ADR-05](../docs/g0/adr/ADR-05-studio-sandbox.md).
