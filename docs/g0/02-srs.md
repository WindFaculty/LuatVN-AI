# 02. Software Requirements Specification

Phiên bản 0.2 · 26/11/2026 · Chờ chủ dự án duyệt G0

## Vai trò và quyền

| Vai trò | Quyền cơ bản | Điều kiện |
|---|---|---|
| Guest | Đọc và tra cứu công khai, Standard giới hạn | Gate, hạn mức, tuổi và phân lớp rủi ro |
| Registered User | Tra cứu, AI theo entitlement, chat và lịch sử của mình, báo sai | Resource ownership/tenant, policy dữ liệu và quyền mode |
| Technical Reviewer | Chạy nhóm chức năng Studio trong sandbox, xem trace đã che dữ liệu | Môi trường, scope và quota sandbox |
| System Admin | Duyệt publish, quản trị quyền, dữ liệu, release | MFA bắt buộc, audit, quyền theo tác vụ |
| AI Agent / Worker | Thực hiện tác vụ theo danh tính dịch vụ | Phạm vi tài nguyên, bước, thời gian và phê duyệt hiệu ứng ngoài |
| Premium, Legal Expert, Enterprise | Quyền tương ứng cơ chế thuê bao, hồ sơ phân công và tenant | LATER. MFA bắt buộc với chuyên gia khi triển khai |

## Use case và điều kiện kết thúc

| ID | Luồng chính | Nhánh và điều kiện kiểm tra |
|---|---|---|
| UC-01 | Tra từ khóa, số hiệu, điều khoản hoặc ngữ nghĩa, lọc theo lĩnh vực/thời gian/địa bàn rồi mở bản gốc | Thiếu quyền tải chỉ hiện metadata hợp lệ. Hit chưa xác minh/dự thảo có nhãn, bị loại khỏi evidence AI |
| UC-02 | Chat VI/EN, xác định dữ kiện và ngày, tìm căn cứ nội bộ, xác minh, xem trích dẫn và lịch sử phiên bản | Thiếu ngày/địa bàn ảnh hưởng kết quả thì hỏi thêm. Snapshot thiếu hoặc lệch version thì trả phần đã kiểm chứng hoặc từ chối |
| UC-03 | Advanced lập kế hoạch, dùng tool chỉ đọc kho đã xác minh, phát trạng thái và trả kết luận sau verification | Hủy hoặc hết hạn mức dừng bước mới, kết toán token, giữ trace đã che. API người dùng ghi trạng thái lượt hỏi và feedback qua lệnh rõ ràng của người dùng |
| UC-04 | Admin nhập nguồn, xem parse/diff, duyệt tài liệu và xuất bản snapshot | Kiểm tra quyền nguồn, malware, cấu trúc và mâu thuẫn. Retry tiếp tục checkpoint, không tạo dữ liệu trùng |
| UC-05 | Người dùng truy cập lịch sử, gửi báo sai và gửi yêu cầu dữ liệu cá nhân | Khóa truy cập sai tenant. Xóa theo policy đã duyệt qua cache, bản sao và quy trình backup. Hạn chế private mode nếu provider chưa đủ điều kiện |
| UC-06 | Reviewer chạy Playground, so sánh mô hình và xem báo cáo gate tại Studio | Credential, trace, dữ liệu và job được cô lập theo sandbox. Thao tác giới hạn có thể reset |
| UC-07 | Admin duyệt cấu hình, chạy regression, mở phạm vi và rollback | Chỉ promotion manifest đạt gate. Rollback đồng bộ image, snapshot, index, rule, prompt và policy |
| UC-08 | Ứng phó báo cáo sai trích dẫn, rò rỉ hoặc lỗi nguồn | Khóa phạm vi liên quan, ghi incident, tái hiện, sửa và chạy lại gate |

## Hợp đồng tại biên

| Nhóm | Điểm vào dự kiến | Quyền chính |
|---|---|---|
| Tra cứu | `GET /v1/search`, `GET /v1/provisions/{id}/versions` | Công khai trong phạm vi quyền nguồn và trạng thái được phép hiển thị |
| Answer và phản hồi | `POST /v1/answers`, `GET /v1/answers/{id}`, `GET /v1/answers/{id}/events`, `POST /v1/answers/{id}/cancel`, `POST /v1/feedback` | Policy tuổi/consent, scope release, quota và quyền trên câu hỏi. Guest có session ngắn hạn, Registered User có identity trong tenant |
| Account | `GET /v1/account/me`, `GET /v1/account/ai-eligibility`, `PUT /v1/account/ai-eligibility`, `PUT /v1/account/consents/{purpose}`, `GET /v1/account/conversations` | Guest quản lý khai báo của session theo policy. Lịch sử và quyền dữ liệu cá nhân cần identity phù hợp |
| Studio | `GET /v1/studio/runs`, `POST /v1/studio/playground/runs`, `POST /v1/studio/evaluations`, `GET /v1/studio/gate-reports`, `POST /v1/studio/approvals` | Reviewer chỉ dùng stack sandbox cho demo. Quyền production admin yêu cầu ingress, scope và MFA riêng |
| Ingestion | `GET /v1/studio/sources`, `POST /v1/studio/ingestion/jobs`, `GET /v1/studio/ingestion/jobs/{id}`, `POST /v1/studio/candidates/{id}/review` | API nội bộ sau Admin/Sandbox BFF theo môi trường. Quyền crawl, review và publish tách biệt |

Mọi request có request ID và mã lỗi ổn định. Dùng 401 cho thiếu phiên hợp lệ, 403 với policy hoặc role từ chối, 404 khi tài nguyên riêng không tồn tại hoặc bên gọi không có quyền biết, 409 cho xung đột idempotency hoặc cursor cũ theo hợp đồng, 429 khi vượt quota, 503 khi dependency bắt buộc thiếu và 500 `internal_error` cho lỗi máy chủ ngoài dự kiến trước khi gửi HTTP headers. Error payload có `code`, `message` và `request_id`, thêm `retry_after_seconds` nếu có. Các nhóm ngoài Answer là danh mục API để đặc tả tiếp. [OpenAPI 3.1 cho Answer, SSE và error](contracts/answers.openapi.yaml).

### Vòng đời Answer và SSE

- `POST /v1/answers` nhận question, mode, language, thời điểm pháp lý tùy chọn và conversation/jurisdiction tùy trường hợp. Server xác thực phiên và policy trước khi lưu hoặc chuyển nội dung sang provider, pin snapshot và trả 202 với answer ID. Idempotency key gắn owner/session và hash payload. Gửi lại cùng key và cùng payload trả cùng ID. Payload khác trả 409. Với session cookie, kiểm CSRF trước POST.
- `GET /v1/answers/{id}/events` xác thực quyền owner, trả `text/event-stream`. Các frame có `id` tăng đơn điệu trong một answer, `event` là `answer.progress` hoặc `answer.completed`, `data` là JSON đúng schema. Heartbeat là comment SSE không có ID. Progress gồm stage, trạng thái và số liệu an toàn. Advanced có thể phát `planning` khi lập kế hoạch. Sau khi mở stream, lỗi xử lý lượt hỏi đi qua terminal state `failed` nếu còn phát được event. Khi mất kết nối, client khôi phục trạng thái qua replay hoặc GET. Chỉ terminal result đã qua verification mang kết luận pháp lý.
- Client gửi `Last-Event-ID` để nhận phần sau cursor trong giới hạn lưu replay. Nếu replay hết hạn, server trả 409 cho chủ phiên và client dùng `GET /v1/answers/{id}` để lấy trạng thái và kết quả còn được lưu. SSE trả 204 khi client báo đã nhận terminal event. Nếu không còn dữ liệu theo policy, điểm đọc trả 404.
- `POST /v1/answers/{id}/cancel` idempotent. Trả 202 khi đã ghi nhận yêu cầu hủy hoặc 200 cùng trạng thái khi lượt đã kết thúc. Worker phát một terminal state cho cùng run kể cả khi hủy cạnh tranh với hoàn tất. Câu trả lời, SSE và lỗi riêng tư dùng `Cache-Control: no-store`.
- Service kiểm riêng các quan hệ mà schema không thể bảo đảm bằng kiểu dữ liệu. `answer_id` của result phải khớp stream. Mọi evidence ID trong claim phải trỏ tới evidence đã xác minh ở cùng snapshot và được phép đọc. Public client nhận thông tin từ result sau khi qua các kiểm tra này.

Agent cho end-user V1 chỉ gọi tool đọc. Tạo lượt hỏi, lịch sử, hủy và gửi feedback là hành động người dùng trên API ứng dụng. Studio có thể trình bày thao tác ghi có approval trên sandbox hoặc cổng quản trị được cấp quyền. Agent không tự ghi vào dữ liệu production từ chat. [AI/RAG và quyền tool](04-ai-rag.md#standard-và-advanced).

## Ràng buộc nghiệp vụ và phi chức năng

- Áp dụng BR-LEGAL-01–08 khi phân loại nguồn, chọn phiên bản, hỏi thêm, kiểm tra điều khoản và trình bày giới hạn. BR-RELEASE-01–02 kiểm soát mọi mode. BR-SEC-01 chi phối việc dùng lại dữ liệu khách hàng. [Căn cứ baseline §5.3](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md)
- NFR-01–12 giữ nguyên yêu cầu baseline. Giá trị availability, tải, latency, cost, freshness, recovery, retention, accessibility và data quality được khóa theo mục [quyết định mở](registers.md#quyết-định-mở) và kiểm tra bằng [Test Plan](14-acceptance-test-plan.md).
- [RTM](rtm.md) truy vết từng mã REQ, BR, NFR và AC tới use case, hồ sơ, kiểm tra và gate. Yêu cầu LATER được giữ trong [backlog](12-roadmap-backlog.md).

[Căn cứ baseline §§3–11](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md)
