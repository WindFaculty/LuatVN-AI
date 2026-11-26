# Phê duyệt G1-D01 cho pilot nội bộ

Ngày 26/11/2026 · Chủ dự án xác nhận trực tiếp trong phiên triển khai G1 · Mã `G1-D01-20261126-PILOT`

| Phạm vi | Quyết định |
|---|---|
| Nguồn và lớp dữ liệu | SRC-01 Công báo điện tử và SRC-03 Văn bản Chính phủ. Chọn mẫu văn bản pháp luật công khai và phần đính kèm của mẫu đó. |
| Truy cập | Tải từng mẫu đã chọn qua URL công khai bằng phương thức truy cập thông thường. Chủ dự án xác nhận phạm vi này có thể thực hiện dựa trên các căn cứ bên dưới. |
| Xử lý nội bộ | Lưu tệp, OCR, parsing, chuẩn hóa, chunking, embedding, Knowledge Graph và benchmark cho G1. Lưu URL nguồn, provenance, SHA-256 và căn cứ pháp lý trên mỗi bản ghi. |
| Giới hạn | Crawl hàng loạt chờ xem xét chính sách riêng của mỗi nguồn. Giữ kiểm tra TLS và dừng khi bị chặn. Tái phân phối toàn bộ ấn phẩm và cơ sở dữ liệu nằm ngoài phạm vi đã duyệt. |
| Chứng cứ kỹ thuật | Ghi `manual_download`, `store` và `index` chỉ cho URL lô chọn, kết quả và dẫn nguồn nội bộ. Căn cứ cho `automated_access` ở quy mô catalog và `redistribute` vẫn để mở. |

Căn cứ chủ dự án cung cấp gồm khoản 2 Điều 15 của văn bản hợp nhất Luật Sở hữu trí tuệ, Điều 2 của Thông tư 02/2025/TT-VPCP và yêu cầu ghi nguồn của Cổng Thông tin điện tử Chính phủ. Thông tư quy định khai thác ấn phẩm Công báo điện tử không thu tiền và ghi quyền đối với ấn phẩm. Giữ provenance, dẫn nguồn và phạm vi nội bộ theo quyết định này. [Luật Sở hữu trí tuệ](https://vanban.chinhphu.vn/?docid=219876&pageid=27160) · [Thông tư 02/2025/TT-VPCP](https://xaydungchinhsach.chinhphu.vn/toan-van-thong-tu-so-02-2025-tt-vpcp-huong-dan-thuc-hien-quy-dinh-ve-cong-bao-dien-tu-119250908164045867.htm) · [Yêu cầu ghi nguồn](https://vanban.chinhphu.vn/?pageid=473)

Tệp gốc và manifest từng URL đặt ngoại tuyến dưới `data/raw/SRC-01/` và `data/raw/SRC-03/`. Registry vận hành riêng cho lô đã chọn nằm dưới `build/g1/` cùng quan sát truy cập và manifest hợp nhất. Registry mặc định vẫn từ chối chạy live bên ngoài lô đã được pin. Mọi bản ghi của pilot là ứng viên cho đến khi qua quy trình xác minh.
