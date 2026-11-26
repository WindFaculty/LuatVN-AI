# G1-01 — Kế hoạch thực thi Data & Proof of Concept

Phiên bản 0.1-draft · 26/11/2026 · Owner: Trần Xuân Khoa · G1 IN_PROGRESS

## 1. Căn cứ và phạm vi

Baseline hiện hành là [v1.1](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md), [ADR-07](../adr/ADR-07-monorepo-and-demo.md) và hồ sơ G0 v0.2.1 đã đóng. Giữ 25 hash của G0; không sửa tài liệu đã nghiệm thu để phản ánh kết quả mới. Ghi bằng chứng, ADR và phụ lục ở G1. Một Git root sản phẩm, không tái tạo repo cũ. Repo demo không chứa corpus thật hay gold holdout.

Mục tiêu G1: giảm bất định về nguồn có quyền, taxonomy/coverage, parser/OCR, dữ liệu bitemporal, graph và sizing, đồng thời chứng minh khả năng kiểm chứng bằng người thật. G1 không phải chứng nhận chất lượng AI pháp luật, không triển khai full retrieval/agent/cloud và không chọn sớm LLM. AC-01–15 của V1 vẫn giữ nguyên. Theo [roadmap G0](../g0/12-roadmap-backlog.md), POC-03 chạy G2, POC-04/05/07 G3, POC-06/08 G4, POC-09/10 G6. G1 chuẩn bị protocol, fixture và sizing cho các pha này; chỉ chốt kết luận có evidence đúng pha.

## 2. Entry và hiện trạng

| Điều kiện | Trạng thái |
|---|---|
| G0 / AC-16 | PASS, hồ sơ v0.2.1 đã phê duyệt |
| Tổ chức mã | ADR-07 ACCEPTED; monorepo + demo sandbox |
| POC-01 | Discovery đã chạy; 9 seed records; quyền và denominator chưa xác nhận |
| POC-02 | Synthetic pilot đã chạy; chưa đo real corpus, chưa có ngưỡng duyệt |
| POC-11 | Protocol đã có; L2 = 0, L3 = 0 ở pilot hiện tại |
| Temporal/graph | DDL fixture G0 có evidence; chưa có gold sample và sizing thật |
| CI | Theo thông báo chuyển đổi: local checks đã qua; hosted Actions bị chặn trước job. Cần CI run hoặc evidence thay thế được owner duyệt, không ghi hosted PASS |

## 3. Workstream và chuỗi phụ thuộc

| ID | Workstream | Trách nhiệm / đường dẫn | Đầu ra |
|---|---|---|---|
| G1-W01 | Source rights & catalog | Chủ dự án; services/data-ingestion | Registry theo hành động, snapshot catalog, phạm vi được phép |
| G1-W02 | Taxonomy & sampling | legal-knowledge + evaluation | taxonomy revision, counts, stratified manifests và coverage gaps |
| G1-W03 | Parser/OCR quality | data-ingestion | Gold extraction, định dạng, failure quarantine, replay/idempotency |
| G1-W04 | Temporal/graph & storage | legal-knowledge + retrieval + infra | Migration fixture, gold ontology protocol, sizing, ADR candidates |
| G1-W05 | Human review & eval design | evaluation + chủ dự án | Review effort, L2/L3, split feasibility, ADR-06 proposal |
| G1-W06 | Gate package | docs/g1 + owner | Báo cáo tổng hợp, ADR phụ thuộc, RTM delta, lịch cập nhật |

W01 → W02 → (W03, W04, W05) → W06. Song song chỉ khi độc lập; ưu tiên một task engineering và một task human review đang chạy. Chạy synthetic fixtures không cần chờ quyền nguồn thật; không dùng kết quả fixture làm evidence legal coverage.

## 4. Lịch đề xuất (10 ngày làm việc, không tính chờ bên ngoài)

| Ngày làm việc | Deliverable | Điểm kiểm |
|---|---|---|
| 1–2 | Kiểm G0, pin repo/contracts; rights matrix, source shortlist, taxonomy draft | Owner quyết định phạm vi pilot, không tự tải nguồn chưa rõ quyền |
| 3–4 | Snapshot catalog đủ quyền; sample manifest, dedup và phân tầng | Có denominator được ghi nguồn hoặc thiếu với lý do và hành động |
| 5–6 | Parse gold sample, audit anchor/table, retry và replay | Report riêng từng format, không gộp điểm che lỗi |
| 7–8 | Data/graph gold design, migration assertions, sizing; review pilot bắt đầu song song | Temporal, provenance, schema và review logs |
| 9 | Tổng hợp reviewer, holdout feasibility, phương án storage/OCR | ADR proposals và trách nhiệm giải quyết bất định |
| 10 | Review gate, đóng hoặc giữ BLOCKED/FAIL theo evidence | Owner sign-off, handoff G2 hoặc remediation |

G0 dự tính B02 là 12–24h engineering và 12–25h human review. Đây là khung tham chiếu, không phải cam kết. Ghi thời gian thao tác thực, thời gian chờ quyền/reviewer, số mẫu đã xử lý và tái ước lượng cuối G1. Nếu 10 ngày hết mà blocker còn mở, báo blocker và lịch mới; không giảm mục tiêu V1.

## 5. Quy tắc đối với AI Coding Agent

- Task scope theo component trong monorepo, đọc baseline, RTM, contract và ADR-07. Không sửa code outside allowed paths, không cài thêm framework production khi chưa có bằng chứng.
- Đổi contract phải cập nhật producer, consumer, validation và tests trong cùng PR; kiểm hợp đồng G0 vẫn nguyên vẹn.
- Harness thử nghiệm ở experiments/g1; bằng chứng có thể công bố nội bộ ở docs/g1/evidence nhưng raw artifacts, PII, credentials và holdout riêng nằm ngoài Git theo policy. Chỉ commit manifest/hash/log đã kiểm quyền và đã che.
- Trước chạy nguồn thật: kiểm action, mục đích, scope, thời hạn, rate, quyền lưu/chia sẻ. Không vòng qua 403, TLS hay giới hạn truy cập; không gửi dữ liệu ra provider chưa duyệt. Local/self-host trong PoC parser khi khả thi.
- Mỗi run chứa run_id, commit, env, version/hash công cụ, quyền/snapshot, inputs, command, expectation, actual/count/denominator, time/cost, failures, logs đã che, owner và linked test/ADR. Nếu chưa chạy, dùng NOT_RUN thay vì 0 hay PASS.
- Mọi threshold, scope hay budget mới dưới đây là PROPOSED cho đến owner chốt. Không xem phê duyệt dự thảo là phê duyệt quyền từ nguồn.

Tài liệu chi tiết: [Nguồn và corpus](02-source-corpus-plan.md), [Parser/OCR](03-parser-quality-plan.md), [Data/graph/sizing](04-data-graph-storage-plan.md), [Review/evaluation](05-review-evaluation-plan.md), [Backlog và gate](06-backlog-gate.md).
