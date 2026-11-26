# POC-02 Pilot trích xuất PDF và OCR

Run `G1-POC02-20261126-SYNTH-01` kiểm liệu có nhận diện được mốc điều, khoản và bảng khi chất lượng đầu vào thay đổi. Bộ `synthetic-v1` dựng cùng một trang theo ba dạng PDF văn bản, scan rõ và scan giảm độ phân giải, làm mờ, xoay 3°. Sáu mốc kỳ vọng gồm `Điều 1`, khoản `1`, `Điều 5a`, khoản `2`, khoản `2a` và `Phụ lục I`. Bảng có ba hàng tính cả tiêu đề. [JSON kết quả, hash và văn bản trích xuất](evidence/poc02-synthetic-2026-11-26.json).

| Đầu vào và cấu hình | Mốc đúng | Hàng bảng đúng | Lỗi ký tự | Byte PDF thô |
|---|---:|---:|---:|---:|
| PDF văn bản, pypdf plain | 6/6 | 0/3 | 0/256 | 46.791 |
| Cùng PDF, pypdf layout | 6/6 | 3/3 | 0/256 | 46.791 |
| Scan rõ, Tesseract `vie` | 6/6 | 0/3 | 4/256 (1,56%) | 31.069 |
| Scan suy giảm, Tesseract `vie` | 1/6 | 0/3 | 66/256 (25,78%) | 18.345 |

Tỷ lệ lỗi ký tự chuẩn hóa khoảng trắng. Vì vậy PDF plain có thể đạt 0 lỗi ký tự trong khi làm mất liên kết cột trong cả ba hàng. Scan suy giảm chỉ giữ được định danh `Điều 5a` và sinh nhầm mốc `3a`. Kết quả ủng hộ thử tiếp chế độ layout cho PDF có text layer và kiểm cấu trúc riêng cho bảng/OCR. Đưa ca thiếu hoặc xung đột mốc sang review trước khi công bố anchor. Các byte ở bảng đo trên một trang tổng hợp và chỉ minh họa cách ghi sizing.

Phạm vi pilot hiện gồm một bố cục PDF tạo tại chỗ. Cần gold samples được phép cho PDF nhiều cột, bảng qua trang, scan có dấu và scan lệch, HTML, DOC/DOCX, PDF ký số, phụ lục tách và văn bản sửa đổi trước khi chốt ngưỡng hoặc công nghệ. [Điều kiện G1](README.md) · [Đặc tả dữ liệu](../g0/05-data-engineering.md).

## Chạy lại

Từ thư mục gốc `LuatVN-AI`, dùng Python 3.12, Node.js và font TrueType hỗ trợ tiếng Việt. Phiên bản và SHA-256 của font/model trong JSON dùng để đối chiếu lần chạy. Cài gói vào venv và thư mục build. OCR xử lý ảnh tổng hợp cục bộ sau khi cài model tiếng Việt.

```powershell
rtk proxy python -m venv build/g1-venv
rtk proxy build/g1-venv/Scripts/python.exe -m pip install pypdf==6.19.0 reportlab==5.0.1 pillow==13.0.0
rtk proxy npm.cmd install --prefix build/g1-poc02 --save-exact --ignore-scripts --no-audit --no-fund tesseract.js@7.0.0 '@tesseract.js-data/vie@1.0.0'
rtk proxy build/g1-venv/Scripts/python.exe -X utf8 experiments/g1/poc02/pilot.py --font 'C:/Windows/Fonts/arial.ttf' --ocr-dir build/g1-poc02 --output build/poc02-replay.json --run-id G1-POC02-REPLAY
```

## Chạy trên mẫu thật

[Probe nội bộ](../../experiments/g1/poc02/probe_real.py) nhận manifest intake và registry của lô. Nó kiểm quyền xử lý, kích thước và SHA-256 trước khi đọc file. pypdf trích text theo trang và chạy layout mode ở trang đầu. PDFium kết xuất một số trang ít text được chọn theo họ và Tesseract `vie` đọc ảnh cục bộ. DOCX được đọc qua XML. Chunks, ảnh, văn bản OCR và kết quả riêng từng tệp nằm ngoài Git.

Cài thêm `pypdfium2==5.15.2` và `fonttools==4.69.1` trong venv PoC. Truyền hai đường dẫn `--intake`, registry `--registry`, thư mục OCR đã cài và một `--output-dir` dưới `build/g1/`. Probe ghi `measurements.json` và `chunks.jsonl`. Số mốc trích được và confidence OCR là quan sát kỹ thuật. Precision, recall, CER và chất lượng bảng cần đối chiếu gold thật theo [G1-03](03-parser-quality-plan.md#5-khóa-tập-audit-thật).
