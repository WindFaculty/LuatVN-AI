# Sổ đăng ký dự án

Phiên bản 0.2 · 26/11/2026 · Trạng thái kế hoạch G0

## Quyết định mở

| Vấn đề | Người phụ trách | Exit criterion |
|---|---|---|
| Catalog và Studio sandbox | Chủ dự án | ĐÃ ĐẠT G0 (26/11/2026): chốt [ADR-01](adr/ADR-01-polyrepo-catalog.md) (`WindFaculty/LuatVN-AI-*`, PRIVATE) và thiết kế [ADR-05](adr/ADR-05-studio-sandbox.md) |
| Nguồn, quyền, taxonomy, sizing, freshness | Chủ dự án kiêm data owner | POC-01/02, signed usage quyết định theo source, catalog denominator, format/quality, scope và freshness SLO trước G1 |
| Graph, temporal, indexing và rule engine | Chủ dự án kiêm technical owner | POC-03/04/05/07: edge precision/coverage/mẫu số, replay, conflict/transition, rule approvals và cấu hình trước G3 |
| Model, provider và policy | Chủ dự án | POC-06/08/10, terms/region/retention theo data class, routing thresholds, token/step/hop/timeout và chi phí trước G4/G6 |
| Benchmark splits, review, strata và rubric | Chủ dự án và reviewer phù hợp | POC-11 và review pilot, eligibility reviewer, L3 resource, split frozen, minimum per cell và metric bổ sung trước G5 |
| Ngân sách/cloud/load/recovery | Chủ dự án | POC-09, metered usage 3 kịch bản, DB/storage/egress, concurrency, latency/SLO, RPO/RTO và budget cap trước G6 |
| Age, consent, retention, accessibility, release compliance | Chủ dự án và người thẩm định phù hợp | Policy và test scope theo data flow, data rights, thời hạn, đánh giá pháp lý và accessibility test trước G6/G7 |
| Tiến độ | Chủ dự án | Tái ước lượng theo số giờ PoC và throughput đo được. Duyệt lịch cập nhật hoặc change request |
| Kênh nguồn SRC-02/05 | Chủ dự án kiêm data owner | Tuần 1–2 xác định đầu mối chính thức, đường API/feed/batch và quyền cần xin. Trước ingest, lưu evidence quyền, phương án thay thế đã duyệt và lỗ hổng coverage |
| Reviewer L3 | Chủ dự án | Tuần 1–2 lập hồ sơ năng lực và phạm vi chuyên môn theo risk/domain, kế hoạch lịch và dự toán. Trước G5, case cần L3 có reviewer phù hợp, bằng chứng review, kiểm bất đồng và đủ level |

## ADR

| ADR | Lựa chọn cần cân nhắc | Trạng thái và bằng chứng quyết định |
|---|---|---|
| ADR-01 Service/repo catalog | 16 repo `WindFaculty/LuatVN-AI-*` (PRIVATE, nhánh `main`), registry GitHub Packages/GHCR, tách control/contracts và các ranh giới LATER | ACCEPTED tại G0 (26/11/2026) theo [ADR-01](adr/ADR-01-polyrepo-catalog.md). Ghi repo inventory sau khi tạo skeleton |
| ADR-02 Storage/index | PostgreSQL + extensions và object store, hoặc tách vector/search/graph theo tải | PROPOSED. POC-01–05 với correctness, cost, restore, index rebuild và reliability |
| ADR-03 AI stack | OCR, chunker, sparse/dense, reranker, Rule Engine meta-legal/substantive, evaluator và API LLM | PROPOSED. Đối chứng POC-02/03/05–08. Chọn định dạng rule có kiểm kiểu và provenance, so với phương án thay thế và kiểm privacy allowlist |
| ADR-04 Cloud/auth | Cloudflare/GCP và dịch vụ managed phù hợp khác | PROPOSED. POC-09/10, data location, auth flows, blast radius, latency, post-trial costs |
| ADR-05 Studio sandbox | Chung project tách cứng IAM/DB/bucket/secrets/Auth/Gateway; tài khoản demo invite/CV có anti-bot + rate limit; reset hàng tuần + nút Reset | ACCEPTED thiết kế tại G0 (26/11/2026) theo [ADR-05](adr/ADR-05-studio-sandbox.md). G6 kiểm bằng chứng isolation, anti-bot/quota, reset và phạm vi tính năng public |
| ADR-06 Evaluation phase policy | Holdout, strata, L2/L3, adjudication và gate ba tầng | PROPOSED. POC-11 đo công sức review, khóa metric, sàn mẫu và cell mục tiêu trước chọn model, kiểm nghiệm thu tại G5 |

Mỗi quyết định ghi ngày, chủ trì, context, options, evidence IDs, lựa chọn, tác động, phương án đảo, trạng thái và revisit triggers. Change request ghi các ID thay đổi, effort, risk, ảnh hưởng acceptance và người phê duyệt.

## Data Source Registry

Khảo sát ở mức nhận diện cổng ngày 26/11/2026. Mỗi dòng có trạng thái `PENDING_RIGHTS`. Với từng nguồn, trước nhập dữ liệu cần ghi owner, access/action, terms/version/contact, rate, hình thức, scope/cấp/thời kỳ, độ tin cậy, quyền storage/index/cite/download/redistribution, verified date, policy confirmer và cách thu hồi.

| ID | Cổng và ưu tiên | Phạm vi ứng viên và việc xác minh trước ingest |
|---|---|---|
| SRC-01 | [Công báo điện tử](https://congbao.chinhphu.vn/) · Ưu tiên đối chiếu | Cổng mở khi kiểm. Cần xác minh phạm vi số Công báo, bản PDF, lịch truy cập và checksum |
| SRC-02 | [Cơ sở dữ liệu quốc gia về VBPL](https://vbpl.vn/) · Ưu tiên catalog | Lần kiểm G0 v0.1 trả 403. Xác minh đầu mối API/batch hợp lệ, quyền tra cứu và phân phối, coverage trung ương/địa phương. Tạm đối chiếu nguồn Công báo hoặc cơ quan có quyền |
| SRC-03 | [Văn bản Chính phủ](https://vanban.chinhphu.vn/) · Ưu tiên metadata/artifacts | Cổng mở khi kiểm. Xác minh bản đính kèm, ký số, diff với Công báo, giới hạn tự động |
| SRC-04 | [Cổng án lệ](https://anle.toaan.gov.vn/) · Theo chuyên mục tư pháp | Kiểm truy cập qua kênh chính thức, tình trạng áp dụng án lệ và quyền trích dẫn/phân phối. Tra cứu trực tiếp chưa xác nhận trong lượt này |
| SRC-05 | [Cổng công bố bản án, quyết định](https://congbobanan.toaan.gov.vn/) · Theo chuyên mục tư pháp | Lần kiểm G0 v0.1 timeout. Xác minh kênh chính thức, phạm vi công bố, PII và quyền tái sử dụng. Tạm dùng nguồn tư pháp khác đã duyệt hoặc synthetic fixtures theo scope |
| SRC-06 | Cổng bộ/ngành, địa phương, Quốc hội và nguồn lưu trữ lịch sử | Định danh từng cổng ở G1, chốt taxonomy/cấp/địa bàn cũ và đo denominator trước công bố |
| SRC-07 | Nguồn đối chiếu khác hoặc đóng góp | Chỉ dùng theo quyền source. Cách ly file đóng góp. Ưu tiên đối chiếu provenance với nguồn chính thức |

Đầu mối kiểm chứng loại văn bản, đối chiếu sửa đổi và xác định phạm vi áp dụng cho nghiệp vụ. [Luật 64/2025/QH15](https://vanban.chinhphu.vn/?docid=213327&orggroupid=1&pageid=27160) · [Luật 87/2025/QH15](https://vanban.chinhphu.vn/?classid=1&docid=214592&pageid=27160). Các trang này được dùng để đặt đầu việc thẩm định quyền và Rule Engine.

## Risk Register

| ID | Tình trạng | Owner và điều kiện xử lý |
|---|---|---|
| BLOCKER-01 | OPEN. AI mọi lĩnh vực và gate từng lĩnh vực | Chủ dự án chốt taxonomy ở G1, khóa sample floor trước G5, chứng minh mỗi miền có AI hợp lệ tại G7 |
| BLOCKER-02 | OPEN. Review L3 và kế hoạch solo Technical Preview | Chủ dự án đo L2 và nhu cầu L3 qua POC-11, rồi bố trí chuyên gia phù hợp hoặc trình change request. Giữ case cần L3 ở pending khi thiếu evidence |
| BLOCKER-03 | Đã chốt thiết kế qua [ADR-05](adr/ADR-05-studio-sandbox.md) (26/11/2026), chờ nghiệm thu G6 | Chủ dự án đã duyệt thiết kế cô lập Sandbox (chung project tách cứng tài nguyên/IAM/Auth, tài khoản invite/CV + anti-bot/rate limit, reset tuần + nút Reset). G6 kiểm đủ tính năng và isolation/guardrails thực tế |
| BLOCKER-04 | Chủ dự án đã duyệt bộ hồ sơ v0.2.1 với assumptions/TBD ngày 26/11/2026 | Cập nhật theo bằng chứng sau PoC và giữ điều kiện đóng G0 trước PoC |
| RISK-01 | OPEN. Graph chuyên sâu và coverage lịch sử | Chốt gold sample, nghĩa completeness, đo pipeline, precision/coverage và temporal G1/G3 |
| RISK-02 | OPEN. Effort solo và 1.000 review | Sau khi POC-11 đo throughput, chủ dự án tái ước lượng và cập nhật lịch hoặc trình change request |
| RISK-03 | OPEN. Vận hành nhiều repo | ADR-01, reusable CI/contracts và inventory trước khi triển khai |
| RISK-04 | OPEN. API ngoài và dữ liệu nhạy cảm | Provider eligibility/egress, redaction và no-call khi vi phạm policy |
| RISK-05 | OPEN. Demo online và chi phí | App caps, giám sát metered spend, dự toán sau trial và POC-09 |
| RISK-06 | OPEN. Mã nguồn private và bằng chứng portfolio | Report/case study/demo đúng quyền, trace đã che và replay minh chứng |
| RISK-07 | OPEN. Quyền khai thác và quy tắc áp dụng | Duyệt nguồn, xác minh rule và quản lý revisions có evidence |
| RISK-08 | OPEN. Tích hợp và khả năng debug của chủ dự án | Task nhỏ, kiểm thử thực, review diff, reproducible logs và diễn tập AC-15 |

**Ưu tiên trước G1.** SRC-02/05 có hạn chế truy cập đã quan sát ở v0.1. Kết quả ảnh hưởng denominator coverage, mẫu bản án và thời điểm chạy ingestion. Chủ dự án theo dõi riêng mức xác nhận quyền theo từng nguồn, kênh đã được phép và ảnh hưởng scope. Agent hỗ trợ chuẩn bị checklist quyền và test adapter trên fixture. Nếu thiếu nguồn, báo rõ nhóm chưa đo và đề xuất phương án hợp lệ, kèm điều kiện cần để xem xét lại.

## Model and Prompt Registry

Chưa có cấu hình đã duyệt. Record gồm config ID, task, provider, model/version, prompt hash, input schema, allowed classes/regions, retention, token limits, approved fallback, cost/latency evidence, status, approver và rollback revision. Trạng thái bắt đầu `PROPOSED`, chuyển `APPROVED` sau POC-06/08, kiểm policy và regression, sau đó `RETIRED` khi ngừng dùng. Baseline không RAG chỉ chạy ở evaluation có label.

## Legal Rule Registry

Chưa có quy tắc nghiệp vụ đã phê duyệt. Record gồm rule ID/family, rule layer meta-legal hoặc substantive, version, authority type, provision version, source/quote/anchor, temporal ranges, scope, condition/exception/transitional clauses, precedence, status/review evidence, test IDs và supersedes. Publication yêu cầu status approved, evidence verified, snapshot pin và test qua. Trường hợp xung đột hoặc dữ kiện thiếu trả `unknown`. [Đặc tả Rule Engine](04-ai-rag.md#rule-engine-và-hai-lớp-quy-tắc).

## Experiment Log

POC-01–11 đều `NOT_RUN`. Record khi chạy gồm run ID, hypothesis, protocol, dataset/snapshot và quyền, code/config/model, env, expected outcome, counters/timing/cost, findings, limits, artifact links, linked ADR và reviewer. [Danh mục POC-01–11](12-roadmap-backlog.md#kế-hoạch-chạy-poc-sau-g0).

## Release Gate Reports

Bộ hồ sơ v0.2.1 đã được chủ dự án duyệt ngày 26/11/2026, đồng thời chốt [ADR-01](adr/ADR-01-polyrepo-catalog.md) và thiết kế [ADR-05](adr/ADR-05-studio-sandbox.md) → **G0 PASS (26/11/2026)**. G1–G7 chờ bằng chứng, G8 thuộc phạm vi LATER. Mỗi report có gate/manifest, tầng global/domain/cell, domain/task/risk/mode tương ứng, test run IDs, group/denominator/metrics/CI, S0/S1, ngoại lệ còn mở, trạng thái, người duyệt và rollback target. [Ghi nhận phê duyệt](README.md#phê-duyệt-và-theo-dõi) · [Gate và acceptance matrix](14-acceptance-test-plan.md).

## Known Issues and Limitations

| ID | Trạng thái ảnh hưởng |
|---|---|
| KI-01 | Thiếu denominator taxonomy và corpus. Chưa công bố coverage |
| KI-02 | Chưa có reviewer L3, reviewed case count và holdout evidence. Chưa đánh giá readiness |
| KI-03 | Chưa có model/provider/db/cloud được duyệt theo PoC. Số dự toán là mô phỏng |
| KI-04 | G0 đã đóng (26/11/2026) kèm ADR-01 và ADR-05. Bằng chứng triển khai cloud/Studio chờ G6 |

[Căn cứ baseline §§12–15](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md)
