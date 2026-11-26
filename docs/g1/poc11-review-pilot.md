# POC-11 Đo công sức kiểm chứng

Pilot cần người thật review và ghi thời gian. Hiện có `0` case L2 và `0` case L3 đã xác minh trong đợt G1. Median, P90, tỷ lệ cần L3 và cỡ mẫu theo tầng đều chờ dữ liệu. [Tiêu chí L2/L3 và holdout](../g0/07-benchmark-evaluation.md) · [Kế hoạch POC-11](../g0/12-roadmap-backlog.md#kế-hoạch-chạy-poc-sau-g0).

Run `G1-REAL-20261126-02` có 27 ca ứng viên trên 27 nhóm. Phiếu tại `build/g1/G1-REAL-20261126-02/poc11/review-worksheet.md` trỏ đến tài liệu và phiên bản. Ghi kết quả đã phân xử trong `human-reviews.json` cùng thư mục. Mỗi record gồm `case_id`, `revision`, `reviewer_id`, `reviewer_role`, `tier`, `verdict`, `reviewed_at`, `evidence_ref`, `credential_ref`, `active_minutes`, `wait_minutes`, `adjudication_minutes` và `adjudicated`. Thời gian dùng ISO 8601 có múi giờ. Với L3, ghi tham chiếu năng lực và người review độc lập. [Lệnh tổng hợp review](evidence/real-pilot-2026-11-26.md#vị-trí-hồ-sơ-và-lệnh-chạy-lại)

## Giao thức pilot

1. Khi POC-01 có mẫu được phép, tạo đợt thăm dò dự kiến 27 case, mỗi nhóm taxonomy 3 case nếu đủ nhóm độc lập. Bao gồm tra cứu, kiểm hiệu lực và một tình huống cần đánh giá rủi ro nếu có người phù hợp. Ghi số case và nhóm thực thu theo từng lĩnh vực khi thiếu mẫu. Dùng dữ liệu pilot để đo công sức và hiệu chỉnh rubric.
2. Gắn `group_id` theo họ văn bản, tình huống gốc và bản dịch để tránh một họ rơi vào nhiều split. Mỗi case có ID, scope, ngày áp dụng, tác vụ, mức rủi ro, căn cứ và phiên bản dữ liệu.
3. Người review ghi số phút thao tác trực tiếp, thời gian chờ riêng và số phút xử lý bất đồng. Ghi reviewer ID, vai trò và bằng chứng chuyên môn cần thiết cho L3. Case chờ L3 giữ `PENDING_L3`, chưa cộng vào số verified.
4. Báo count, median, P90 và tỷ lệ case cần L3. Ước tính tổng giờ theo cơ cấu L2/L3 thực đo, cộng chuẩn bị và adjudication. Chốt số nhóm độc lập và sàn holdout qua ADR-06 theo bằng chứng trước khi chọn model.

## Mẫu ghi một case

| Case ID | Group ID | Domain, task, risk | Snapshot và căn cứ | Reviewer và mức yêu cầu | Phút trực tiếp | Phút chờ | Kết luận và bằng chứng |
|---|---|---|---|---|---:|---:|---|
|  |  |  |  |  |  |  |  |
