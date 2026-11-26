# ADR-03 Kiến trúc phân tích đa định dạng, OCR và kiểm soát chất lượng nạp

| Thuộc tính | Giá trị |
|---|---|
| Trạng thái | `PROPOSED` (lát cắt G1 dựa trên kiểm toán 36 mẫu thật `G1-REAL-20261127-01`; embedding/rerank/LLM chờ G2–G4) |
| Yêu cầu liên quan | `REQ-DATA-04–07`, `REQ-SEC-05`, `TST-02`, `TST-02.1`, `NFR-10`, `POC-02` |
| Căn cứ G0 / G1 | [Đặc tả dữ liệu G0](../g0/05-data-engineering.md) · [Giao thức G1-03](../g1/03-parser-quality-plan.md) |

## 1. Bối cảnh và phân bổ định dạng thật quan sát được

Trong 70 tệp duy nhất thu thập từ `SRC-01` và `SRC-03`, có tới `35/64` PDF là bản thuần scan (text layer < 80 ký tự/trang), `10/64` PDF hỗn hợp (chữ + trang ký số/scan cuối), `19/64` PDF có text layer sạch, `1` DOCX, `5` DOC nhị phân cũ (OLE2) và `50` trang HTML cổng nguồn (`0` tệp `.xls`/`.xlsx` xuất hiện trong lô 50 văn bản mẫu). Vì vậy không thể giả định một bộ trích xuất PDF đơn lẻ xử lý được toàn bộ văn bản pháp luật Việt Nam.

Theo [kiểm toán POC-02 ngày 27/11/2026](../g1/evidence/g1-real-audit-2026-11-27.md), 36 mẫu thật tách hoàn toàn họ văn bản giữa `tuning` (`7` mẫu) và `audit` (`29` mẫu) cho các quan sát kỹ thuật sau (chưa tính precision/recall/CER chính thức cho đến khi chủ dự án duyệt gold thủ công):

| Tầng / Định dạng | Công cụ đối chứng G1 | Số mẫu & quy mô thật | Quan sát kỹ thuật chính | Đường xử lý đề xuất |
|---|---|---:|---|---|
| PDF có text layer (`pdf_text`) | `pypdf` (`plain` vs `layout`) vs `pdfplumber` | `10` tệp / `484` trang | `pypdf layout` giữ cấu trúc bảng tốt hơn `plain` (`P50 = 1,653s` vs `1,428s`); phát hiện `588` mốc Điều và `140` bảng | Mặc định dùng `pypdf layout`; chuyển `pdfplumber` cho trang có bảng |
| Bảng biểu / phụ lục (`table_appendix`) | `pdfplumber` bảng lưới vs `pypdf` | `6` tệp / `384` trang | `pdfplumber` bóc tách được `360` bảng / `9.153` ô (`P50 = 3,822s`) | Bắt buộc định tuyến trang phụ lục bảng qua `pdfplumber` và kiểm đối chiếu thủ công với bảng đa trang |
| PDF scan (`pdf_scan`) | PDFium `200 DPI` thô vs `250 DPI` tiền xử lý xám + `Tesseract.js vie 7.0.0` | `8` tệp / `16` trang OCR (`32` ảnh) | Confidence trung bình `91,19`; `1` tệp có trang rơi vào điều kiện rà soát (`NEEDS_REVIEW`); tốc độ `1,638 giây/ảnh` | OCR cục bộ toàn bộ trang scan; **cấm auto-verify** kết quả OCR; dưới ngưỡng `conf < 80` hoặc thiếu `Điều/Khoản` đẩy hàng đợi `NEEDS_REVIEW` |
| HTML cổng nguồn (`html`) | `BeautifulSoup4 + lxml` DOM vs bóc text thô | `6` trang (`SRC-01` & `SRC-03`) | Giảm trung bình `52,59%` nhiễu HTML (`P50 = 0,0019s`); `SRC-03` trích đủ bảng metadata, `SRC-01` hiện mới đạt `0,83` trường/trang | Bổ sung parser chuyên biệt cho DOM `congbao.chinhphu.vn` ở G2 |
| DOC / DOCX (`doc_docx`) | `zipfile` + XML cho `.docx`; `olefile` OLE2 cho `.doc` | `1` DOCX (`413/2026/NĐ-CP`) + `5` DOC | DOCX khớp `31/31` mốc Điều với PDF cùng số hiệu và trích `2` bảng gốc. `5` DOC đạt kiểm tra OLE2 `WordDocument` nhưng thiếu bộ chuyển đổi `.doc -> .docx` cục bộ | Giữ nguyên DOCX native XML; `.doc` cũ đưa vào `NEEDS_CONVERTER_OR_REVIEW` (tách container LibreOffice cô lập ở G2 hoặc rà soát thủ công) |
| Bảng tính (`.xlsx`) | `openpyxl` (kiểm thử kỹ thuật tổng hợp) | `0` tệp `.xlsx` thật trong lô (`1` fixture PASS) | Giữ nguyên công thức (`=C2+D2`) và tên sheet/cột | Sẵn sàng tiếp nhận `.xlsx` qua `openpyxl` khi gặp ở G2 |

## 2. Hàng rào Quarantine, Bảo mật và Khôi phục (`REQ-DATA-05–07`, `REQ-SEC-05`, `TST-02.1`)

Toàn bộ `6/6` kịch bản lỗi và bảo mật đã kiểm chứng `PASS`:
1. Tệp `.pdf` / `.docx` cắt cụt hoặc hỏng cấu trúc → bắt lỗi (`PdfStreamError` / `BadZipFile`) và cô lập vào `QUARANTINED`, không phát sinh revision.
2. HTML chứa `<script>` hoặc chuỗi prompt injection (`IGNORE PREVIOUS INSTRUCTIONS`) → loại bỏ script tại tầng DOM và đánh dấu `QUARANTINED` ở ingestion (`0` verified emission).
3. Tệp vượt trần `max_bytes_per_item` hoặc ngoài phạm vi URL/thời hạn quyền → chặn tức thời (`RightsDenied: OUTSIDE_APPROVED_SCOPE`).
4. Sai lệch ngày hiệu lực giữa cổng gốc (`59/2020/QH14` trên `SRC-01` ghi `01/01/1900`, `SRC-03` ghi `01-01-2021`) → giữ xung đột, gắn `legal_status_verified = false`, không tự suy diễn.
5. Chạy lại khi gián đoạn sau raw write (`TST-02.1`) → `0` trùng lặp logical revision, giữ 2 lượt chạy truy vết độc lập.

## 3. Quyết định giữ nguyên ở trạng thái `PROPOSED` cho G2–G4

- **Không tự giảm ngưỡng G1-D04**: Các ngưỡng `metadata ≥ 98%`, `anchor precision ≥ 98%`, `recall ≥ 95%`, `CER ≤ 1% (text)` / `≤ 3% (scan rõ)`, `table cell ≥ 95%` giữ cố định; các định dạng vượt ngoài khả năng auto-verify (`.doc` cũ, scan mờ, bảng qua nhiều trang) được định tuyến sang kênh `NEEDS_REVIEW` có kiểm chứng của người thật thay vì hạ chuẩn.
- **Phần chờ ở pha sau**: Chunking nâng cao theo cấu trúc `Điều/Khoản/Điểm`, so sánh OCR engine khác nếu cần, embedding/rerank và xác minh Gold có chữ ký reviewer từ `gold-review-sheet.md` thực hiện ở G2.
