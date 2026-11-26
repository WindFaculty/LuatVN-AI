# ADR-06 Giao thức đánh giá và holdout

Trạng thái `PROPOSED` · Cập nhật bằng chứng cấu trúc nhóm thật ngày 27/11/2026 (`G1-REAL-20261127-01`) · Chờ chủ dự án thực hiện L2 trên `POC-11` · `REQ-EVAL-01–03` · `AC-10/11`

## 1. Quy tắc nhóm liên thông và hiện trạng lô pilot `POC-11`

Đưa mọi biến thể theo họ văn bản, tình huống và bản dịch vào một `connected group` (`group_id`) trước khi phân bổ split. Mỗi group có một `primary_domain` duy nhất để thống kê độc lập, chống rò rỉ dữ liệu giữa `authoring / dev / tuning / holdout`.

- **Hiện trạng `POC-11` (`G1-REAL-20261127-01`)**: Đã dựng đủ `27` ca ứng viên trên `27` nhóm độc lập (mỗi lĩnh vực `CIV`, `CRI`, `ADM`, `LAB`, `LND`, `BUS`, `TRA`, `EDU`, `ENV` có `3` nhóm: `1 lookup` L2, `1 temporal` L2, `1 risk` L3) kèm trích đoạn và locator thật từ tệp gốc (`review_pilot.py` xác nhận `0` rò rỉ nhóm).
- **Trạng thái kiểm chứng người thật**: **`18 PENDING_L2`**, **`9 PENDING_L3`**, **`0 L2 verified`**, **`0 L3 verified`**. Tuyệt đối giữ nguyên `0/0` theo `G1-D03` cho đến khi chủ dự án Trần Xuân Khoa tự review 18 ca L2 và chuyên gia độc lập review các ca L3.

## 2. Phân tích tính khả thi cho mục tiêu `AC-10` (≥ 1.000 ca) và sàn holdout 50%

| Ràng buộc đề xuất | Hệ quả toán học trên 9 lĩnh vực | Rà soát khả thi từ G1 | Dữ liệu thực đo còn thiếu |
|---|---|---|---|
| `50` independent holdout groups / domain | `9 × 50 = 450` holdout groups; nếu holdout chiếm `50%` theo `G1-D06` cần tối thiểu `900` groups toàn tập (`≥ 100` họ/domain) | `SRC-03` toàn thời kỳ có `48.101` bản ghi (riêng 2020–cutoff có `195` Luật và `1.441` Nghị định): nguồn văn bản đủ để sinh `≥ 900` groups độc lập | Cần xác nhận mức phủ đủ đều cho mọi sub-domain trong `taxonomy-0.2.0-candidate` |
| `20` eligible groups / metric, `≥ 50` units citation/temporal | Bảo đảm độ tin cậy cho từng chỉ số `AC-01..07` và lát cắt citation/temporal | Lô pilot chỉ có `3` group/domain (`1` temporal/domain), chưa đủ ước lượng phương sai thực tế | Cần log thực đo theo domain/task sau G2 |
| `10` independent groups / cell đã đăng ký, `0` S0/S1 | Nếu mở đủ Standard × Advanced × 9 domains × 3 task sẽ cần hàng nghìn group; cần đăng ký cell trọng điểm trước | Khả thi khi giới hạn cell V1 rõ theo mức rủi ro (`G1-05` §3) | Đăng ký ma trận cell trước model selection |
| Sàn `≥ 1.000` verified cases (`AC-10`) & tỷ lệ `PENDING_L3` | Trong `POC-11`, `9/27` (`33,33%`) ca được phân tầng yêu cầu `L3` do cấu trúc pilot; nếu tỷ lệ ca cần L3 trong 1.000 ca cao, chuyên gia độc lập là đường găng cứng (`BLOCKER-02`) | Cần tách riêng luồng L2 (chủ dự án tự review) và luồng L3 (chờ chuyên gia độc lập theo `DEC-04` / `G1-D03`) | Tỷ lệ cần L3 thực tế trên phân bố truy vấn thật và kế hoạch chuyên gia |

## 3. Bảng độ nhạy công sức L2 (chủ dự án tự review trên quỹ 30–40 giờ/tuần)

Vì chưa có log thời gian người thật từ `POC-11`, bảng dưới đây lập phân tích độ nhạy minh bạch (`median / P90` thực sẽ thay thế sau khi Trần Xuân Khoa hoàn tất 18 ca L2):

| Giả định thời gian hoạt động L2 | Tổng giờ thuần cho `700` ca L2 (tương ứng ~70% tập 1.000 ca) | Tổng giờ gồm chuẩn bị + đối chiếu/phân xử (+35%) | Số tuần ở nhịp `30–40 giờ/tuần` | Ghi chú cho phần `L3` (~300 ca) |
|---:|---:|---:|---:|---|
| `5 phút / ca` | `58,3 giờ` | `78,8 giờ` | `2,0 – 2,6 tuần` | Chuyên gia L3 độc lập chạy song song hoặc sau G5 |
| `10 phút / ca` | `116,7 giờ` | `157,5 giờ` | `3,9 – 5,3 tuần` | Khớp mức cảnh báo `RISK-02` (~167 giờ cho 1.000 ca) |
| `15 phút / ca` | `175,0 giờ` | `236,3 giờ` | `5,9 – 7,9 tuần` | Chiếm trọn ngân sách lịch 2–3 tháng nếu không ưu tiên L2 trước |
| `20 phút / ca` | `233,3 giờ` | `315,0 giờ` | `7,9 – 10,5 tuần` | Cần bổ sung cộng tác viên L2 hoặc điều chỉnh lịch qua change control |

## 4. Chính sách Holdout và điều kiện khóa ADR-06

1. `G1-D06` xác nhận mục tiêu kế hoạch `50%` holdout theo `connected group` (`10%` authoring/train, `20%` dev, `20%` tuning chỉ dùng tham chiếu nội bộ). Tập test độc lập **chưa** được coi là frozen ở G1 và chỉ được khóa manifest + SHA-256 + kiểm soát truy cập sau khi `POC-11` có đo người thật và trước khi chọn model (`model selection`).
2. Chỉ các ca đạt đủ `required_tier` (`L2` có nguồn gốc + locator xác nhận bởi con người; `L3` có bằng chứng chuyên môn độc lập và `reviewer_id != L2`) mới được tính vào tập nghiệm thu `AC-10`. Ca yêu cầu `L3` nhưng thiếu chuyên gia giữ nguyên `PENDING_L3`.
3. Chủ dự án sử dụng `build/g1/G1-REAL-20261127-01/poc11/review-worksheet.md` và `build/g1/G1-REAL-20261127-01/poc11/human-reviews.json` để hoàn tất đo thực `18` ca L2 trước khi phê duyệt chốt chính thức `ADR-06`.

Tài liệu liên quan: [Kế hoạch G1-05](../g1/05-review-evaluation-plan.md) · [Giao thức POC-11](../g1/poc11-review-pilot.md) · [Tiêu chuẩn G0](../g0/07-benchmark-evaluation.md).
