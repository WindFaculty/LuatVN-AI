# 09. UI/UX Specification

Phiên bản 0.2 · 26/11/2026 · Flows và design tokens đề xuất

## Legal Web

| Route đề xuất | Nội dung chính | Luồng kiểm tra |
|---|---|---|
| `/` | Tra cứu và ô hỏi AI, nhóm lĩnh vực, văn bản mới | Tách nút Tra cứu/Hỏi AI. Trước lần dùng AI đầu tiên, kiểm điều kiện tuổi và hiển thị thông báo xử lý dữ liệu |
| `/search` | Tra theo số hiệu, từ khóa, ngữ nghĩa hoặc điều khoản. Lọc theo hiệu lực, ngày, lĩnh vực, cấp và địa bàn | URL lưu filters công khai. Hiện lý do không có dữ liệu, nguồn và trạng thái xác minh |
| `/documents/:id` | Mục lục, điều khoản, phiên bản, hiệu lực từng phần, link gốc và tải theo quyền | Liên kết trực tiếp theo ID điều khoản và phiên bản. Giữ vị trí đọc khi đóng mở panel |
| `/chat/:id` | Chat nhiều lượt, Standard/Advanced theo quyền, panel tương tác, progress | Hỏi dữ kiện thiếu, hủy, retry khi phù hợp, report sai gắn answer/citation ID. Mất kết nối nhận lại stage theo ID |
| `/account` | Tài khoản, quyền, trạng thái điều kiện tuổi, lịch sử, consent và yêu cầu dữ liệu | Cho xem lý do hạn chế và cập nhật khai báo/consent theo policy. Thông báo rõ lịch sử và chế độ áp dụng |

Từ mỗi kết luận mở citation panel với Điều/Khoản/Điểm, nguyên văn highlight đúng anchor, URL, nguồn, version, phạm vi hiệu lực, lịch sử và ngày đang trả lời. Drill-down mở đúng snapshot, hiển thị cảnh báo khi nguồn bị thu hồi và cung cấp báo lỗi. Trên desktop hiện panel cạnh chat, trên mobile dùng dialog có focus trap và trả focus về citation trigger. EN hiện bản dịch phần giải thích và giữ căn cứ tiếng Việt.

Tiến trình có các trạng thái phân loại, truy xuất, đối chiếu, xác minh và hoàn tất. Advanced có thể hiện bước lập kế hoạch khi nhận stage `planning`. UI chỉ thông báo trạng thái và kết quả đã được phép công bố. Hỏi thêm, partial, thiếu căn cứ, restricted, quota exhausted, cancelled và unavailable có microcopy riêng. Khi không nên phân tích, đề xuất hành động trong phạm vi hỗ trợ như bổ sung ngày, mở kết quả tra cứu hoặc xem nguồn đã xác minh.

### Kiểm điều kiện tuổi và quyền dùng AI

Guest bấm Hỏi AI thì UI lấy trạng thái eligibility từ server trước khi gửi câu hỏi. Nếu thiếu khai báo, hiển thị phương án khai nhóm tuổi tối thiểu theo policy và thông báo mục đích xử lý, lịch sử và giới hạn Guest. Khi policy yêu cầu xác minh hoặc đồng ý phù hợp, UI hướng dẫn điều kiện và giữ quyền tra cứu công khai. Nếu từ chối, chưa đủ điều kiện, hoặc policy chưa cho phép, hiển thị lý do và nút Tra cứu. Với người đã đăng ký, `/account` có cùng trạng thái và luồng sửa. Server kiểm lại khi policy/consent thay đổi. Consent dùng dữ liệu để cải thiện AI là lựa chọn riêng, mặc định tắt. Ngưỡng tuổi, chứng cứ và thời hạn lưu chờ policy được duyệt.

### Chờ kết quả xác minh

Đo riêng `time_to_first_progress_event_ms` từ lúc gửi đến event tiến trình đầu tiên (không tính heartbeat) và `time_to_verified_answer_ms` đến event có kết quả đã xác minh. Hiện tên bước và giữ nút Hủy dễ thao tác bằng phím. Khi chờ lâu theo ngưỡng cấu hình, hiển thị trạng thái đang xác minh và cho người dùng tiếp tục chờ hoặc hủy. Khi mất kết nối, duy trì trạng thái và nối lại qua Last-Event-ID. Nếu replay hết hạn, gọi điểm đọc trạng thái theo quyền phiên. Nội dung pháp lý xuất hiện trong kết quả cuối sau gate. Đo tách theo mode và loại tác vụ trước chốt thời lượng UX. [Hợp đồng SSE](02-srs.md#vòng-đời-answer-và-sse).

## Legal AI Studio

| Khu vực | Hành động Technical Reviewer trong sandbox |
|---|---|
| Dashboard & Data Sources | Xem health, crawl jobs, parser/OCR, diff, lineage. Chạy lại demo và duyệt candidate giả lập |
| Model / Prompt / Config | Xem revision và so sánh cấu hình mẫu. Tạo candidate version có thể reset |
| RAG Playground | Chọn tối ưu retrieval, snapshot, câu hỏi mẫu. Xem rank, citation và trace đã che |
| Agent Visualizer | Xem plan đã rút gọn, bước/tool có scope, progress, timeout và verification state |
| Evaluation & Release | Chạy suite mẫu, xem ablation và cell strata, mô phỏng gate/rollback trong sandbox |
| Monitoring & Feedback | Xem token/cost/latency/error/data quality, xem và phân loại report mẫu |
| Access | Xem policy và role mapping mẫu, thử thêm role trong sandbox theo quota |

Menu Production Admin tách route, deployment, credential và data. UI role label lấy từ backend policy. Quyền thực thi kiểm ở service.

Reviewer có thể tạo hoặc reset cấu hình, chạy job và ghi nhận kết quả mô phỏng trong namespace demo. UI hiển thị quota, thời hạn và phạm vi thay đổi trước thao tác. Các hành động publish, tích hợp ngoài hoặc sửa quyền production bị chặn tại Sandbox API. Nếu agent đề xuất ghi, Studio hiển thị phạm vi, hash input và thời hạn phê duyệt, rồi gửi action được duyệt qua API theo role. [Ranh giới Studio](08-security-threat-model.md).

## Tokens và accessibility

| Token đề xuất | Light | Dark |
|---|---|---|
| Surface | `#F8FAFC` | `#0F172A` |
| Text | `#0F172A` | `#F1F5F9` |
| Link / action | `#0F766E` | `#5EEAD4` |
| Warning | `#92400E` | `#FCD34D` |
| Typography | Source Sans 3 cho VI/EN | Scale mặc định 16 px, linh hoạt khi zoom |
| Spacing | 4, 8, 12, 16, 24, 32 px | Theme light/dark/system |

Dùng heading/landmark, skip link, tab order, focus visible, labels, thông báo tiến trình bằng live region không ngắt câu, text đi cùng màu trạng thái và dialog có keyboard escape. Pin VI/EN strings và thuật ngữ pháp lý. Kiểm keyboard, screen reader, zoom, contrast, citation deep links và responsive bằng hành trình UC-01–03/06. Đề xuất WCAG 2.2 AA làm đích thảo luận. Chốt scope và tiêu chí compliance tại G6. [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/).

OpenAPI typed clients, lint translation keys và component tokens dùng chung. SEO dành cho trang pháp luật công khai. Chọn prerender/SSR sau khi đo indexability và thời gian tải.

[Căn cứ baseline §§4, 7, 9 và AC-15](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md)
