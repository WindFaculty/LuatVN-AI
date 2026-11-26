# 01. Product Requirements Document

Phiên bản 0.2 · 26/11/2026 · Chờ chủ dự án duyệt G0

## Mục tiêu và người dùng

Luật Việt Nam AI giúp người dùng tìm quy định Việt Nam, biết quy định có hiệu lực tại thời điểm nào và kiểm tra từng căn cứ AI viện dẫn. V1 là Technical Preview cho cộng đồng và hồ sơ năng lực AI Engineering của Trần Xuân Khoa. Mục tiêu dài hạn gồm web, mobile và dịch vụ doanh nghiệp.

| Người dùng | Nhu cầu | Kết quả quan sát được |
|---|---|---|
| Khách và sinh viên | Tìm văn bản, học cách đọc điều khoản | Mở đúng điều/khoản, xem bản gốc khi được phép, chọn ngày áp dụng và dùng Standard trong hạn mức |
| Người dùng đăng ký | Làm rõ tình huống qua nhiều lượt | Bổ sung dữ kiện, xem lịch sử được cấp quyền, kiểm tra nguồn từng kết luận và gửi báo sai |
| Người tra cứu cho tổ chức | So sánh quy định theo thời gian và địa bàn | Phân biệt văn bản nguồn, hiệu lực, điều kiện áp dụng và khoảng thiếu bằng chứng |
| Technical Reviewer | Tái hiện retrieval, agent, verification và release gate | Dùng đầy đủ nhóm chức năng Studio với dữ liệu được duyệt hoặc giả lập trong sandbox |
| System Admin | Duyệt dữ liệu và xử lý sự cố | Quản trị production qua tài khoản riêng có MFA và audit |

## Phạm vi và ưu tiên phát hành

- G1–G3 hình thành kho nguồn, tra cứu từ khóa/ngữ nghĩa, thời gian pháp lý, graph quyền/nghĩa vụ/điều kiện/ngoại lệ, rule engine và trích dẫn đến điều/khoản/điểm. Dữ liệu chưa xác minh có thể xuất hiện ở tra cứu với cảnh báo nếu quyền nguồn cho phép.
- G4 hoàn chỉnh Standard cho hỏi đáp, giải thích, tóm tắt, phản biện và phân tích có giới hạn. Advanced thể hiện lập kế hoạch, gọi công cụ giới hạn và đo chất lượng cùng Standard. Hỗ trợ VI/EN, dẫn nguyên bản tiếng Việt và gắn nhãn phần dịch AI.
- G5–G7 yêu cầu 1.000 case L2/L3 thực tế, chất lượng theo [Test Plan](14-acceptance-test-plan.md), AI khả dụng ở mọi lĩnh vực taxonomy được duyệt, và cloud demo, Studio, kiểm soát quota và bằng chứng portfolio.
- Phạm vi dài hạn gồm mobile Android rồi iOS, Document Intelligence cá nhân, workspace vụ việc, thông báo theo dõi, community, tính pháp lý chuyên biệt, Expert Research, freemium, SSO và doanh nghiệp. Roadmap [12](12-roadmap-backlog.md) giữ các nhóm này trong backlog.

## Chỉ số và điều kiện mở tính năng

| Kết quả | Cách đọc bằng chứng | Điều kiện |
|---|---|---|
| Tìm và kiểm tra được căn cứ | Recall@20, nDCG@10, trích dẫn mở đúng version, đúng ngày | AC-01–02, AC-05–06, AC-08 |
| Phân tích có thể kiểm tra | Correctness, faithfulness, correct abstention và kiểm tra rủi ro theo strata | AC-03–04, AC-07, AC-11–13 |
| Demo vận hành và học được từ lỗi | Báo sai có mã, trace đã che dữ liệu, release/rollback và diễn tập debug | AC-09, AC-14–15 |
| Hiểu mức sử dụng | Đếm đăng ký, người dùng hoạt động và số lần kiểm tra nguồn theo policy | 100–500 tài khoản là giả định tải đăng ký. Mục tiêu sử dụng và tải đỉnh chốt bằng thử nghiệm G6 |

Quota, entitlements, miền pháp lý, tác vụ, độ rủi ro và mode cùng quyết định quyền AI. Mỗi lĩnh vực cần ít nhất một chức năng AI qua gate. Trường hợp thiếu dữ kiện có thể được hỏi lại. Trường hợp rủi ro cao giới hạn ở thông tin đã xác minh và đánh dấu nhu cầu review. Giữ chế độ tra cứu cho phạm vi chưa đạt gate.

## Internal preview

Internal preview chỉ phục vụ nhóm truy cập hạn chế trong khi BLOCKER-01/02 còn mở. Điều kiện tối thiểu gồm kiểm quyền nguồn, manifest đã pin, smoke test tra cứu và trích dẫn đến bản gốc, cùng đường tắt AI khi có lỗi. Người dùng chỉ truy vấn AI trên cell đã qua gate. Cell còn lại dùng tra cứu hoặc chạy kịch bản synthetic trong sandbox kiểm thử. Ghi số case L2/L3 thực tế, phạm vi taxonomy, known issues và nhãn `Internal preview`. Điều kiện hoàn thành V1 vẫn theo G7. [Gate và rollback](14-acceptance-test-plan.md#gate-severity-và-rollback).

## Quyết định còn mở

Chủ dự án duyệt bộ hồ sơ và danh mục repo tại G0. Chủ dự án chốt taxonomy và phạm vi corpus sau bằng chứng G1. Giải quyết năng lực L3 trước G5 và phê duyệt sandbox riêng cho demo trước G6. Các giới hạn tiến độ, dữ liệu, tải và chi phí được theo dõi trong [sổ đăng ký](registers.md).

[Căn cứ baseline §§1–4, 7 và 10–16](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md)
