# Phê duyệt G1-D01 bổ sung ngày 27/11/2026 — Cơ sở luật định cho văn bản pháp luật công khai

Ngày 27/11/2026 · Chủ dự án Trần Xuân Khoa xác nhận trực tiếp · Mã `G1-D01-20261127-STATUTORY` · Tiếp nối [Phê duyệt G1-D01 ngày 26/11/2026](owner-decision-g1-d01-2026-11-26.md)

## 1. Căn cứ luật định và chính sách nguồn

Chủ dự án xác nhận văn bản quy phạm pháp luật, văn bản hành chính và văn bản tư pháp công khai của Việt Nam thuộc đối tượng **không áp dụng bảo hộ quyền tác giả**, cho phép tải về và khai thác hợp pháp phục vụ nghiên cứu, xây dựng dữ liệu và đối chiếu kỹ thuật G1 theo đúng quy định pháp luật hiện hành và nghĩa vụ dẫn nguồn:

1. **Điều 15 khoản 2 Luật Sở hữu trí tuệ số 50/2005/QH11** (hợp nhất sửa đổi, bổ sung các năm 2009, 2019, 2022): văn bản quy phạm pháp luật, văn bản hành chính, văn bản khác thuộc lĩnh vực tư pháp và bản dịch chính thức của văn bản đó là các đối tượng không thuộc phạm vi bảo hộ quyền tác giả ([Bản ghi văn bản hợp nhất trên Cổng Thông tin điện tử Chính phủ](https://vanban.chinhphu.vn/?docid=219876&pageid=27160)).
2. **Điều 18 Nghị định số 52/2015/NĐ-CP** về Cơ sở dữ liệu quốc gia về pháp luật: tổ chức, cá nhân được khai thác, sử dụng miễn phí văn bản quy phạm pháp luật trên cơ sở dữ liệu chính thức ([Nghị định 52/2015/NĐ-CP](https://vanban.chinhphu.vn/default.aspx?docid=180104&pageid=27160)).
3. **Điều 2 Thông tư số 02/2025/TT-VPCP** và yêu cầu ghi nguồn của Cổng Thông tin điện tử Chính phủ: khai thác miễn phí ấn phẩm Công báo điện tử kèm ghi nguồn đầy đủ khi trích dẫn/phát hành lại ([Yêu cầu ghi nguồn](https://vanban.chinhphu.vn/?pageid=473)).
4. **Chính sách kỹ thuật của cổng gốc**: `robots.txt` tại `https://congbao.chinhphu.vn/robots.txt` và `https://vanban.chinhphu.vn/robots.txt` đều `Allow: /` và ghi rõ đầu mối chính thức; mọi thao tác giữ strict TLS, tốc độ lịch sự (giãn cách tối thiểu 1,5 giây/request, tối đa `<= 20` lượt/phút/nguồn và `<= 30` lượt/phút dùng chung hạ tầng `chinhphu.vn`), và **dừng ngay** nếu gặp HTTP 403, 429 hoặc CAPTCHA.

## 2. Phạm vi hành động được phép cho lô G1 (`G1-REAL-20261127-01`)

| Nguồn | Hành động được phép ở G1 | Giới hạn và điều kiện bắt buộc |
|---|---|---|
| `SRC-01` Công báo điện tử | `manual_download`, `automated_access`, `store`, `index`, `cite` | Pin chính xác danh sách URL/công cụ và giới hạn tốc độ trong registry vận hành từng lô (`build/g1/.../source-rights.real.json`). Lưu bản gốc ngoài Git (`data/raw/`), kèm provenance, SHA-256 và ghi nguồn `congbao.chinhphu.vn`. |
| `SRC-03` Hệ thống văn bản Chính phủ | `manual_download`, `automated_access`, `store`, `index`, `cite` | Pin chính xác danh sách URL và giới hạn tốc độ trong registry vận hành lô. Lưu bản gốc ngoài Git (`data/raw/`), kèm provenance, SHA-256 và ghi nguồn Cục Thông tin và Truyền thông Chính phủ. |
| `SRC-02`, `SRC-04`–`SRC-07` | Giữ `PENDING_RIGHTS` trong `G1` | Không vượt qua HTTP 403 (`SRC-02`) hoặc lỗi chuỗi chứng chỉ TLS (`SRC-04`/`SRC-05`); giữ fail-closed trong registry mặc định. |

> **Lưu ý kiểm soát an toàn (`experiments/g1/source-rights.json`):** Registry mặc định của repo (`experiments/g1/source-rights.json`, revision `g1-rights-pending-v1`) tiếp tục giữ `PENDING_RIGHTS` làm lớp bảo vệ fail-closed mặc định cho kiểm thử đơn vị và CI. Mọi lần chạy thật trên dữ liệu G1 bắt buộc truyền registry vận hành có phạm vi URL, khoảng ngày và thời hạn cụ thể dưới `build/g1/<run-id>/source-rights.real.json`.
