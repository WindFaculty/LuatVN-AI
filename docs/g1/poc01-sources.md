# POC-01 Khảo sát nguồn và taxonomy pilot

Run `G1-POC01-20261126-DISCOVERY-01` thực hiện ngày 26/11/2026. Khảo sát dùng truy cập công khai giới hạn và đối chiếu các trang chính thức. Giả thuyết làm việc là SRC-01/03 có thể làm nguồn pilot cho văn bản trung ương và SRC-02 có thể cung cấp catalog đối chiếu khi xác nhận kênh. Kết quả hiện đủ để chọn ứng viên. Trạng thái quyền cho ingest vẫn là `PENDING_RIGHTS`. [Log quan sát HTTP](evidence/poc01-source-access-2026-11-26.json) · [Đặc tả quyền nguồn](../g0/05-data-engineering.md#danh-mục-nguồn-và-taxonomy).

Kết quả trên ghi trạng thái lúc discovery. Sau đó, G1-D01 mở lô nội bộ SRC-01/03. Lô chính có 45 họ và mapping đủ 9 nhóm pilot. Catalog đối chứng vẫn chờ phạm vi và mẫu số. [Quyết định D01](evidence/owner-decision-g1-d01-2026-11-26.md) · [Kết quả lô thật](evidence/real-pilot-2026-11-26.md)

| Nguồn | Quan sát và căn cứ | Việc cần xác nhận |
|---|---|---|
| SRC-01 Công báo điện tử | HTTP 200. Trang văn bản mẫu cung cấp PDF và DOC; một văn bản có thể nằm trên nhiều số Công báo. Công báo yêu cầu ghi nguồn khi phát hành lại. Hướng dẫn 02/2025/TT-VPCP mô tả ấn phẩm PDF ký số. [Văn bản mẫu 78/2025/NĐ-CP](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-78-2025-nd-cp-44704/55991.htm) · [Thông tư](https://vanban.chinhphu.vn/?docid=215203&pageid=27160&typegroupid=6) · [Chân trang Công báo](https://congbao.chinhphu.vn/van-ban-dang-cong-bao/trang-1729.htm) | Chọn số Công báo và phần đính kèm đủ; xác nhận phương thức lấy mẫu, lưu bản gốc, lập chỉ mục, trích dẫn và phân phối. |
| SRC-02 CSDL quốc gia về pháp luật | Một lượt cục bộ nhận HTTP 200 ở mức header. Lượt xem nội dung với client mặc định và lần tra cứu web trả 403. Trang Bộ Tư pháp về Nghị định 52/2015/NĐ-CP đọc được qua tra cứu web, còn DNS cục bộ không phân giải tên miền đó. Điều 18 nêu quyền khai thác, sử dụng miễn phí văn bản trong CSDL. [Nghị định 52](https://vanban.chinhphu.vn/default.aspx?docid=180104&pageid=27160) · [Toàn văn ở Bộ Tư pháp](https://vbpl.moj.gov.vn/botuphap/Pages/vbpq-toanvan.aspx?ItemID=67193&dvid=41) | Xác nhận kênh lấy catalog/API/batch, phạm vi trường, hạn mức và cách dùng từng loại dữ liệu. Quyền khai thác miễn phí văn bản là một căn cứ thẩm định phạm vi sử dụng. |
| SRC-03 Hệ thống văn bản Chính phủ | HTTP 200, đọc được bản ghi và danh sách tệp đính kèm. Cổng yêu cầu ghi nguồn khi phát hành lại. Đầu mối công khai là Cục Thông tin và Truyền thông Chính phủ. [Hệ thống văn bản](https://vanban.chinhphu.vn/) · [Đầu mối công khai](https://vanban.chinhphu.vn/gioi-thieu-69424) | Chọn một nhóm bản ghi trung ương, xác nhận quyền theo hành động và phân biệt bản ký với bản hợp nhất. |
| SRC-04 Án lệ và SRC-05 Bản án | Client cục bộ báo lỗi xác minh chuỗi chứng chỉ. Tra cứu web hết thời gian chờ. | Xác minh kênh chính thức và tình trạng công bố. Ghi phạm vi bản án, tình trạng ẩn danh và quyền dùng trước khi lấy mẫu. |
| SRC-06 và SRC-07 | Chờ định danh nguồn cụ thể theo cấp/địa bàn và loại tài liệu. | Chọn một catalog địa phương và một nhóm hồ sơ lịch sử để đánh giá khoảng trống của mẫu trung ương. |

Tách trạng thái quyền cho `manual_download`, `automated_access`, `store`, `index`, `cite` và `redistribute`. Mỗi quyết định cần URL chính sách hoặc thư xác nhận, ngày, giới hạn và người duyệt. Ưu tiên xác nhận phạm vi nhỏ gồm mẫu PDF/DOC có đính kèm công khai, lưu và đo nội bộ, giới hạn lưu, cách trích dẫn và cơ chế thu hồi. Xin thông tin riêng về API/batch, giới hạn truy cập và phạm vi phân phối nếu cần. [Cơ chế đề nghị chia sẻ dữ liệu trong Nghị định 194/2025/NĐ-CP](https://vanban.chinhphu.vn/?classid=1&docid=214448&pageid=27160).

## Taxonomy pilot 0.1.0

Mỗi nhóm dưới đây có một bản ghi chính thức dùng để thử ánh xạ. Chín bản ghi này đều thuộc nhóm mẫu trung ương và được chọn theo chủ đích. Bản ghi dùng dẫn đường đến họ văn bản, các sửa đổi, văn bản hợp nhất và bản đính kèm cần đối chiếu. Tình trạng hiệu lực tính theo từng phiên bản khi dựng snapshot.

| Mã | Nhóm pilot | Nhánh cần đối chiếu | Bản ghi quan sát |
|---|---|---|---|
| CIV | Dân sự | Giao dịch, sở hữu | [91/2015/QH13](https://vanban.chinhphu.vn/?docid=183188&pageid=27160) |
| CRI | Hình sự | Tội phạm, hình phạt | [100/2015/QH13](https://vanban.chinhphu.vn/?docid=183216&pageid=27160) |
| ADM | Hành chính và tư pháp | Xử lý vi phạm hành chính | [15/2012/QH13](https://vanban.chinhphu.vn/?docid=163070&pageid=27160) |
| LAB | Lao động và an sinh | Quan hệ lao động | [45/2019/QH14](https://vanban.chinhphu.vn/?docid=198540&pageid=27160) |
| LND | Đất đai và nhà ở | Quyền sử dụng đất | [31/2024/QH15](https://vanban.chinhphu.vn/?docid=211189&pageid=27160) |
| BUS | Kinh doanh và thuế | Doanh nghiệp | [59/2020/QH14](https://vanban.chinhphu.vn/?docid=200447&pageid=27160) |
| TRA | Giao thông | Trật tự, an toàn giao thông đường bộ | [36/2024/QH15](https://vanban.chinhphu.vn/?docid=211194&pageid=27160) |
| EDU | Giáo dục và y tế | Giáo dục | [43/2019/QH14](https://vanban.chinhphu.vn/?docid=197310&pageid=27160) |
| ENV | Môi trường | Bảo vệ môi trường | [72/2020/QH14](https://vanban.chinhphu.vn/?docid=202613&pageid=27160) |

Mẫu số độ bao phủ hiện `unknown`. Sau khi xác nhận quyền, đếm record duy nhất theo snapshot và theo nhóm lĩnh vực, loại, cấp, địa bàn, thời kỳ. Tử số gồm record đã đối chiếu số hiệu, nguồn và phiên bản. Cho phép một văn bản có nhiều nhãn nhưng báo tổng toàn corpus sau khử trùng. Đo riêng nhóm địa phương, lịch sử, tư pháp và các nhánh còn thiếu trong mẫu trên như y tế, thuế, an sinh và nhà ở. Báo raw bytes, normalized bytes, số chunks, dung lượng chỉ mục và snapshot backup trên corpus thật trước khi chốt sizing.
