# 10. Cloud Infrastructure & Deployment Plan

Phiên bản 0.2 · 26/11/2026 · Topology ứng viên, chờ POC-09

## Môi trường và topology

| Môi trường | Dữ liệu | Tổ chức triển khai |
|---|---|---|
| Dev | Synthetic fixtures và nguồn công khai đã duyệt | Local reproducible containers, PostgreSQL và object store local, adapter theo POC |
| Testing | Fixtures, dev split, test secrets | CI cô lập. Contract, integration, scan và offline regression |
| Staging | Candidate corpus snapshot và dataset đúng quyền | Cloud gần production, benchmark tải, fault recovery, restore và release gate |
| Production | Corpus đã duyệt và dữ liệu người dùng theo policy | API public, Studio production có MFA, managed state và quotas |
| Public Studio sandbox | Public-approved/synthetic | Chung cloud project, tách cứng IAM/service accounts, credentials, DB, storage, managed auth, APIs và Model Gateway theo [ADR-05](adr/ADR-05-studio-sandbox.md). Tài khoản demo invite/CV kèm anti-bot/rate limit, reset hàng tuần + nút reset, quota và egress riêng |

Ứng viên Cloudflare edge/DNS/WAF và static Web/Studio, Cloud Run service cho FastAPI, jobs theo lịch/hàng đợi, Cloud SQL PostgreSQL, GCS hoặc R2 object storage. Broker, region, auth, secrets, networking, physical indexes và SKU chờ ADR. Lựa chọn dựa trên hỗ trợ extension, quota/egress, quyền dữ liệu, SLO, migration và chi phí. Production sử dụng managed infrastructure phù hợp. Worker ingestion và benchmark có lịch và scale theo tải. Demo public bảo đảm service health và đường tra cứu được giám sát.

Tách secrets, workload identity, network namespace, DB/object accounts, logs và data policies. Chỉ edge và entrypoints cần thiết public. Egress nguồn và provider theo policy. Private state thuộc từng owner. Repo control giữ manifests và deploy permissions. [Cloud Run](https://cloud.google.com/run/pricing) · [Cloud SQL PostgreSQL extensions](https://docs.cloud.google.com/sql/docs/postgres/extensions) · [Cloud Storage](https://cloud.google.com/storage/pricing) · [R2](https://developers.cloudflare.com/r2/pricing/).

Staging chỉ bật trong cửa sổ CI, benchmark, canary hoặc restore. Kết thúc cửa sổ, lưu evidence/log theo retention, drain job, scale API/worker về 0 khi không dính yêu cầu sẵn sàng, dừng DB compute nếu SKU và cấu hình hỗ trợ. Storage/backup vẫn nằm trong dự toán. Trước phiên test, restore hoặc bật lại và kiểm snapshot/index khớp. Sandbox giữ URL public, issuer và state riêng. Cho API/worker scale-to-zero khi nhàn rỗi nếu đo cold start đạt yêu cầu, giữ DB chạy hoặc chọn phương án managed có khả năng đánh thức đã kiểm. Khi quota AI hết, UI vẫn mở demo an toàn và tra cứu trong phạm vi được phép. [Đơn giá theo môi trường](11-cost-estimation.md#ba-kịch-bản-sau-trial) · [Cloud Run autoscaling](https://docs.cloud.google.com/run/docs/about-instance-autoscaling) · [Cloud SQL start/stop](https://docs.cloud.google.com/sql/docs/postgres/start-stop-restart-instance).

## Build, release và rollback

1. Per-repo CI chạy lint/type/unit, integration và contract compatibility. Scan dependencies, secrets và image. Pin dependencies và image digests. Build image/SBOM versioned.
2. Deploy staging bằng workload identity. Migrate theo expand → compatibility → contract chỉ sau khi rollback window kết thúc. Build và validate index candidate trong namespace riêng.
3. Chạy smoke, permission isolation, AI regressions, quality/cost/load gate, restore drill và kiểm manifest. Chủ dự án approve promotion manifest pin image, migrations, contract, corpus/index, graph/rule, model/prompt và policy.
4. Canary có threshold đã duyệt cho error, latency, cost, verification và release cell leakage. Fail → khóa cell hoặc đưa traffic về release/snapshot cùng bộ đã xác minh. Có runbook cho DB restore hoặc forward fix nếu migration không thể rollback trực tiếp.
5. Ghi deploy/start/end, health, owner, config diff, bằng chứng phê duyệt và rollback/restore. Chỉ public release report đã che dữ liệu.

## Quan sát, capacity và recovery

- Ghi RED metrics theo service, queue lag, freshness, index/snapshot parity, auth deny, verification fail, time to first progress event, time to verified answer, TTFT ở tầng model khi có, model tokens/cost và tỷ lệ retry/cancel. Báo distribution theo mode và môi trường. Trace không chứa thông tin vượt policy. Dashboard tách người xem và environment.
- Dùng health check và synthetic uptime probe từ ngoài, cảnh báo service/AI/cost theo severity. Tải test từ search-only, Standard, Advanced và ingestion đồng thời. Đo cold/hot, P50/P95/P99, DB pool, quota, backpressure, peak traffic và chi phí. Giữ 100–500 đăng ký là dự báo tài khoản. POC-09 đo concurrency, throughput và SLO đề xuất.
- Kiểm backup, retention và PITR khi hỗ trợ. Khôi phục DB + object vào môi trường cô lập, rebuild projections, verify hash/ACL/deletion policy, kiểm vài câu truy vấn theo snapshot rồi ghi thời gian và mất dữ liệu quan sát được. Chốt RPO/RTO theo owner trước G6.
- Quota theo request, user, account và platform. Reserve token/cost trước call, limit jobs, log retention và batch size, reconcile usage, alert và có công tắc dừng Advanced/ingestion/AI theo scope. Duy trì tra cứu khi policy và hạ tầng cho phép. [Cloud Billing budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets).

[Căn cứ baseline §8, REQ-SEC-10/12, POC-09 và G6](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md)
