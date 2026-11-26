# ADR-05: Thiết kế cô lập Public Studio Sandbox

| Thuộc tính | Giá trị |
|---|---|
| Mã ADR | `ADR-05` |
| Ngày quyết định | 26/11/2026 |
| Chủ trì & phê duyệt | Trần Xuân Khoa (Chủ dự án) |
| Trạng thái | `ACCEPTED` (chốt thiết kế tại G0; nghiệm thu vận hành tại G6) |
| Liên kết yêu cầu | `DEC-11`, `REQ-STUDIO-01`, `REQ-STUDIO-02`, `REQ-SEC-01`, `REQ-SEC-06`, `REQ-SEC-12`, `BLOCKER-03` |
| Tài liệu liên quan | [SAD](../03-sad.md) · [Security & Threat Model](../08-security-threat-model.md) · [UI/UX](../09-ui-ux.md) · [Cloud Deployment](../10-cloud-deployment.md) · [Cost Estimation](../11-cost-estimation.md) · [Test Plan](../14-acceptance-test-plan.md) |

---

## 1. Bối cảnh (Context)

Requirements Baseline v1.0 đặt ra hai yêu cầu đồng thời (`BLOCKER-03`):
1. Mở demo công khai **đầy đủ 7 nhóm chức năng của Legal AI Studio** cho Technical Reviewer / nhà tuyển dụng kiểm chứng năng lực thực tế (`DEC-11`, `REQ-STUDIO-01`, `REQ-STUDIO-02`).
2. Bảo vệ tuyệt đối secrets, prompt nội bộ, dữ liệu hội thoại/PII người dùng thật, bộ holdout nghiệm thu G5 và quyền quản trị Production vốn yêu cầu MFA riêng (`REQ-SEC-01`, `REQ-SEC-06`, `REQ-SEC-12`).

Do chủ dự án vận hành **solo** (1 người quản trị cloud cùng hỗ trợ từ AI Coding Agents), giải pháp cô lập cần bảo đảm ranh giới bảo mật cứng ở tầng ứng dụng/IAM/dữ liệu mà vẫn gọn gàng trong quản trị hạ tầng, chi phí và vận hành demo hàng ngày.

---

## 2. Các phương án đã cân nhắc (Options)

### 2.1 Mô hình cô lập Cloud Project
- **Phương án 1A — Tách GCP Project riêng cho Sandbox**: Cô lập hoàn toàn ở cấp Project (IAM, billing, VPC). Điểm mạnh là blast radius nhỏ nhất, nhưng tăng gánh nặng thiết lập IaC, CI/CD workload identity, billing/quota và quản lý đa project cho một người làm solo.
- **Phương án 1B — Chung Cloud Project, tách cứng toàn bộ tài nguyên theo ranh giới IAM/Data/Auth *(ĐƯỢC CHỌN)***: Dùng chung 1 GCP Project nhưng tách biệt hoàn toàn Cloud Run services, Service Accounts & IAM least-privilege, Database riêng, Object bucket riêng, Secrets Manager (prefix + IAM riêng), Managed Auth tenant/issuer/audience riêng, Model Gateway riêng và domain/ingress riêng.

### 2.2 Mô hình cấp quyền truy cập Technical Reviewer
- **Phương án 2A — Mở tự đăng ký công khai cho Sandbox**: Dễ tiếp cận nhưng rủi ro cao về bot/scraper lạm dụng và đốt quota LLM.
- **Phương án 2B — Tài khoản demo cấp sẵn trong invite/CV kèm chống bot và rate limit *(ĐƯỢC CHỌN)***: Chủ dự án tạo và quản lý tài khoản Technical Reviewer demo để gắn trong lời mời/CV/portfolio (có thể xoay vòng hoặc thu hồi khi cần), không mở tự đăng ký trên Sandbox; lớp edge áp anti-bot (vd. Cloudflare Turnstile) và rate limit chặt theo IP + tài khoản.

### 2.3 Cơ chế làm sạch & khôi phục trạng thái demo (Reset)
- **Phương án 3A — Namespace tách riêng theo từng phiên kèm reset hàng ngày**: Tránh ảnh hưởng chéo giữa người xem đồng thời, nhưng phức tạp hơn trong quản trị schema/cleanup ở V1.
- **Phương án 3B — Reset tự động hàng tuần + nút Reset thủ công trên UI *(ĐƯỢC CHỌN)***: Chạy job định kỳ hàng tuần khôi phục Sandbox về *golden seed snapshot* đã pin, đồng thời cung cấp nút **Reset Demo State** trên giao diện Studio (có cooldown/rate limit) để Reviewer chủ động làm sạch dữ liệu thử nghiệm bất cứ lúc nào.

---

## 3. Quyết định chính thức (Decision)

1. **Hạ tầng & IAM (Chung project, tách cứng tài nguyên)**:
   - Triển khai Public Studio Sandbox trên **cùng Cloud Project** để tối ưu vận hành solo, nhưng bắt buộc tách cứng toàn bộ tài nguyên runtime và dữ liệu:
     - Domain/ingress riêng (tách hẳn khỏi Legal Web public và Admin ingress có MFA của Production).
     - Cloud Run services, Service Accounts và IAM bindings riêng; Service Account của Sandbox bị từ chối tuyệt đối (`deny-by-default`) quyền đọc/ghi vào DB Production, Object bucket Production, Secrets Production và Admin APIs.
     - Database riêng (SKU chọn theo `POC-09`: đối chứng Cloud SQL dedicated, shared-core và PostgreSQL scale-to-zero) và Object storage bucket riêng.
     - Managed Auth issuer, audience và signing keys riêng: token của Sandbox không thể được Production API xác thực.
     - Model Gateway Sandbox riêng với quota, ledger và egress allowlist riêng.
2. **Dữ liệu trong Sandbox (Zero Production Sync)**:
   - Chỉ nạp (a) tập con văn bản pháp luật công khai đã duyệt quyền (`public-approved`) đại diện các lĩnh vực để chạy thật Playground/temporal/graph/citation, và (b) dữ liệu giả lập (`synthetic`) cho hội thoại mẫu, feedback mẫu, evaluation/ablation mẫu và role mapping mẫu.
   - Tuyệt đối không đồng bộ hội thoại thật, PII người dùng, tập holdout nghiệm thu G5, hay production prompts/secrets vào Sandbox.
3. **Truy cập Reviewer, chống bot & kiểm soát chi phí**:
   - Truy cập bằng **tài khoản Technical Reviewer demo do chủ dự án cấp và đính kèm qua invite/CV**; không mở tự đăng ký tài khoản trên Studio Sandbox.
   - Bắt buộc lớp **anti-bot** tại trang đăng nhập/tác vụ nặng và **rate limit** theo IP + tài khoản.
   - Áp **quota 3 tầng** tại Model Gateway Sandbox: trần theo lượt (`max_tokens`, `step_cap`, `timeout`), trần theo ngày/tài khoản, và trần cứng theo tháng của toàn Sandbox.
   - Khi hết quota LLM: Sandbox giữ nguyên toàn bộ giao diện Studio, tra cứu, lineage, báo cáo benchmark/ablation có sẵn và trace mẫu đã che; chỉ tạm khóa các nút gọi LLM live kèm thông báo rõ.
4. **Ranh giới Đọc / Ghi & Guardrails**:
   - Đủ 7 nhóm chức năng Studio chạy được trong namespace demo (xem health/lineage, chạy lại ingestion demo từ fixture đóng gói sẵn, tạo/so sánh candidate config, chạy RAG Playground, xem Agent Visualizer, chạy mini-evaluation, mô phỏng gate/rollback, thử role mapping mẫu).
   - **Chặn cứng tại Sandbox API**: không cho crawl URL Internet tùy ý (chống SSRF), không cho egress ngoài allowlist, không gọi tích hợp ngoài, không sửa quyền/dữ liệu Production.
   - Mọi thao tác ghi do agent đề xuất trong Studio phải đi qua màn hình phê duyệt ghi rõ phạm vi, hash input, thời hạn và audit, chỉ có hiệu lực trong namespace demo.
5. **Cơ chế Reset (Hàng tuần + Nút Reset)**:
   - Chạy lịch **reset tự động hàng tuần** khôi phục DB/state Sandbox về *golden seed snapshot* đã pin.
   - Cung cấp **nút Reset Demo State** trong Studio Sandbox (có xác nhận, rate limit/cooldown ngắn để chống spam) để Reviewer tự đưa môi trường về trạng thái sạch ngay khi cần.
   - Áp giới hạn số bản ghi/kích thước candidate và hiển thị thông báo rõ trên UI rằng trạng thái demo sẽ được làm mới theo tuần hoặc qua nút Reset.

---

## 4. Tác động, đánh đổi và kiểm soát bù trừ (Consequences)

- **Lợi ích**: Giảm đáng kể overhead quản trị cloud/IaC/CI cho 1 người vận hành; ngăn bot/scraper đốt tiền LLM nhờ tài khoản invite/CV + anti-bot + rate limit; cơ chế reset hàng tuần + nút Reset đơn giản, dễ kiểm thử và đáng tin cậy cho V1.
- **Đánh đổi & biện pháp giảm thiểu**:
  - *Chung Cloud Project làm tăng nguy cơ cấp nhầm IAM rộng ở cấp project*: Giảm thiểu bằng IaC khai báo tường minh theo từng resource (không gán role mức project như `roles/editor` hay `roles/cloudsql.client` chung cho Service Account Sandbox), kiểm tự động IAM/isolation trong `POC-10` và `TST-10`.
  - *Tài khoản demo chia sẻ có thể có hai Reviewer thao tác cùng lúc trong tuần*: Giảm thiểu bằng giới hạn số lượng candidate/bản ghi, nút Reset nhanh một chạm và cảnh báo rõ trên UI về trạng thái chia sẻ demo.

---

## 5. Phương án đảo & điều kiện xem xét lại (Rollback & Revisit Triggers)

- **Phương án đảo khẩn cấp**: Có công tắc tắt riêng ingress hoặc route gọi LLM của Sandbox mà không ảnh hưởng Legal Web hay Production Admin; xoay vòng/thu hồi tức thì credential tài khoản demo nếu bị lộ rộng rãi.
- **Revisit triggers** (khi nào cần nâng cấp ADR-05):
  1. Trước **G8 (thương mại hóa)** hoặc khi có thêm thành viên vận hành/chuyên gia truy cập hạ tầng → tách sang **Cloud Project riêng** cho Sandbox.
  2. Nếu lưu lượng Reviewer đồng thời tăng cao khiến xung đột trạng thái demo thường xuyên → chuyển từ reset hàng tuần chung sang **per-session isolated namespace** với TTL ngắn.
  3. Nếu `POC-09` cho thấy chi phí DB Sandbox vượt ngưỡng duyệt → áp dụng phương án DB serverless/scale-to-zero hoặc shared-core theo kết quả đo thực tế.

---

## 6. Điều kiện nghiệm thu vận hành tại G6 (Verification Criteria)

ADR-05 chỉ đóng hoàn toàn sau khi vượt qua các bằng chứng thực chạy ở G6 (`TST-09`, `TST-10`, `TST-10.2`, `TST-11`):
- [ ] Token từ Managed Auth Sandbox gọi sang Production API bị từ chối (401/403).
- [ ] Service Account của Sandbox không thể đọc/ghi vào DB, Bucket và Secrets của Production (kiểm IAM audit + negative probe).
- [ ] Canary secret giả đặt ở Production không xuất hiện trên UI, API, logs hay trace của Sandbox (`T-05`).
- [ ] Chặn cứng hành vi crawl URL ngoài, ghi vượt phạm vi và indirect prompt injection từ fixture (`T-03`, `T-10`, `TST-10.2`).
- [ ] Anti-bot, rate limit và quota 3 tầng hoạt động đúng; khi chạm trần quota, Sandbox suy giảm an toàn sang chế độ chỉ xem/tra cứu.
- [ ] Cả **nút Reset** và **job reset hàng tuần** khôi phục chính xác về *golden seed snapshot* đã pin và ghi log kiểm chứng.
