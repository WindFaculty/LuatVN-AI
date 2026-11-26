# G1-01 — Kế hoạch thực thi Data & Proof of Concept

Phiên bản 1.0 · Quyết định G1-D01–06 đã được chủ dự án duyệt ngày 26/11/2026 · Owner: Trần Xuân Khoa · G1 IN_PROGRESS (chưa nghiệm thu)

## 1. Căn cứ và phạm vi

Baseline hiện hành là [v1.1](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md), [ADR-07](../adr/ADR-07-monorepo-and-demo.md) và hồ sơ G0 v0.2.1 đã đóng. Giữ 25 hash của G0; không sửa tài liệu đã nghiệm thu để phản ánh kết quả mới. Ghi bằng chứng, ADR và phụ lục ở G1. Một Git root sản phẩm, không tái tạo repo cũ. Repo demo không chứa corpus thật hay gold holdout.

Mục tiêu G1: giảm bất định về nguồn có quyền, taxonomy/coverage, parser/OCR, dữ liệu bitemporal, graph và sizing, đồng thời chứng minh khả năng kiểm chứng bằng người thật. G1 không phải chứng nhận chất lượng AI pháp luật, không triển khai full retrieval/agent/cloud và không chọn sớm LLM. AC-01–15 của V1 vẫn giữ nguyên. Theo [roadmap G0](../g0/12-roadmap-backlog.md), POC-03 chạy G2, POC-04/05/07 G3, POC-06/08 G4, POC-09/10 G6. G1 chuẩn bị protocol, fixture và sizing cho các pha này; chỉ chốt kết luận có evidence đúng pha.

## 2. Entry và hiện trạng

| Điều kiện | Trạng thái |
|---|---|
| G0 / AC-16 | PASS, hồ sơ v0.2.1 đã phê duyệt |
| Tổ chức mã | ADR-07 ACCEPTED; monorepo + demo sandbox |
| POC-01 | Discovery đã chạy; 9 seed records; quyền và denominator chưa xác nhận |
| POC-02 | Synthetic pilot đã chạy; chưa đo real corpus; ngưỡng pilot đã duyệt theo G1-D04, chưa khóa audit manifest |
| POC-11 | Protocol đã có; L2 = 0, L3 = 0 ở pilot hiện tại |
| Temporal/graph | DDL fixture G0 có evidence; chưa có gold sample và sizing thật |
| CI | Theo thông báo chuyển đổi: local checks đã qua; hosted Actions bị chặn trước job. Cần CI run hoặc evidence thay thế được owner duyệt, không ghi hosted PASS |

## 3. Quyết định được duyệt và giới hạn thực thi

Chủ dự án đã xác nhận cả 6 quyết định tại [G1-06](06-backlog-gate.md#3-quyết-định-chủ-dự-án-đã-duyệt). Ưu tiên SRC-01/03 và xác minh quyền theo từng hành động trước tải/xử lý; giữ 9 nhóm pilot, mở rộng sub-domain theo catalog; 45 families / 36 artifacts / 18 graph families / 27 case review; owner tự review L2, case cần L3 vẫn PENDING_L3; dùng các ngưỡng G1-03/G1-04 và khóa trước audit. Local-first trên laptop hiện tại, Docker và database local; ưu tiên miễn phí, không dùng API trả phí mặc định. Holdout theo group dự kiến 50%, khóa phân bổ thực sau POC-11. Không có yêu cầu bổ sung.

Chỉ các quyết định kế hoạch này đã được duyệt, không đồng nghĩa quyền nguồn, ADR công nghệ hay kết quả gate đã được xác nhận.

## 4. Workstream và chuỗi phụ thuộc

| ID | Workstream | Trách nhiệm / đường dẫn | Đầu ra |
|---|---|---|---|
| G1-W01 | Source rights & catalog | Chủ dự án; services/data-ingestion | Registry theo hành động, snapshot catalog, phạm vi được phép |
| G1-W02 | Taxonomy & sampling | legal-knowledge + evaluation | taxonomy revision, counts, stratified manifests và coverage gaps |
| G1-W03 | Parser/OCR quality | data-ingestion | Gold extraction, định dạng, failure quarantine, replay/idempotency |
| G1-W04 | Temporal/graph & storage | legal-knowledge + retrieval + infra | Migration fixture, gold ontology protocol, sizing, ADR candidates |
| G1-W05 | Human review & eval design | evaluation + chủ dự án | Review effort, L2/L3, split feasibility, ADR-06 proposal |
| G1-W06 | Gate package | docs/g1 + owner | Báo cáo tổng hợp, ADR phụ thuộc, RTM delta, lịch cập nhật |

W01 → W02 → (W03, W04, W05) → W06. Song song chỉ khi độc lập; ưu tiên một task engineering và một task human review đang chạy. Chạy synthetic fixtures không cần chờ quyền nguồn thật; không dùng kết quả fixture làm evidence legal coverage.

## 5. Lịch mục tiêu (10 ngày làm việc, không tính chờ bên ngoài)

| Ngày làm việc | Deliverable | Điểm kiểm |
|---|---|---|
| 1–2 | Kiểm G0, pin repo/contracts; rights matrix, source shortlist, taxonomy draft | Phạm vi pilot đã duyệt; xác minh quyền từng action, không tải nguồn chưa rõ quyền |
| 3–4 | Snapshot catalog đủ quyền; sample manifest, dedup và phân tầng | Có denominator được ghi nguồn hoặc thiếu với lý do và hành động |
| 5–6 | Parse gold sample, audit anchor/table, retry và replay | Report riêng từng format, không gộp điểm che lỗi |
| 7–8 | Data/graph gold design, migration assertions, sizing; review pilot bắt đầu song song | Temporal, provenance, schema và review logs |
| 9 | Tổng hợp reviewer, holdout feasibility, phương án storage/OCR | ADR proposals và trách nhiệm giải quyết bất định |
| 10 | Review gate, đóng hoặc giữ BLOCKED/FAIL theo evidence | Owner sign-off, handoff G2 hoặc remediation |

Owner xác nhận capacity 30–40 giờ/tuần (60–80 giờ trong hai tuần). G0 dự tính B02 là 12–24h engineering và 12–25h human review, tổng 24–49h; đây là khung tham chiếu, không phải cam kết hoặc số giờ thực đo. Dành phần capacity còn lại cho rework, review, integration và uncertainty; không coi thời gian chờ quyền nguồn/chuyên gia là giờ làm việc hay bảo đảm hoàn thành trong 10 ngày. Ghi thời gian thao tác thực, thời gian chờ quyền/reviewer, số mẫu đã xử lý và tái ước lượng cuối G1. Nếu 10 ngày hết mà blocker còn mở, báo blocker và lịch mới; không giảm mục tiêu V1.

## 6. Quy tắc đối với AI Coding Agent

- Task scope theo component trong monorepo, đọc baseline, RTM, contract và ADR-07. Không sửa code outside allowed paths, không cài thêm framework production khi chưa có bằng chứng.
- Đổi contract phải cập nhật producer, consumer, validation và tests trong cùng PR; kiểm hợp đồng G0 vẫn nguyên vẹn.
- Harness thử nghiệm ở experiments/g1; bằng chứng có thể công bố nội bộ ở docs/g1/evidence nhưng raw artifacts, PII, credentials và holdout riêng nằm ngoài Git theo policy. Chỉ commit manifest/hash/log đã kiểm quyền và đã che.
- Trước chạy nguồn thật: kiểm action, mục đích, scope, thời hạn, rate, quyền lưu/chia sẻ. Không vòng qua 403, TLS hay giới hạn truy cập; không gửi dữ liệu ra provider chưa duyệt. Local/self-host trong PoC parser khi khả thi.
- Mỗi run chứa run_id, commit, env, version/hash công cụ, quyền/snapshot, inputs, command, expectation, actual/count/denominator, time/cost, failures, logs đã che, owner và linked test/ADR. Nếu chưa chạy, dùng NOT_RUN thay vì 0 hay PASS.
- Tuân thủ G1-D01–06 đã duyệt; trước audit pin manifest, rubric/mẫu số, split, config và threshold theo G1-03/G1-04. Không hạ ngưỡng sau khi xem kết quả. Thay đổi yêu cầu/scope đã duyệt phải có change control; các ADR công nghệ, thông số chưa đo và phân bổ thực vẫn theo quy trình PoC.
- Ngân sách G1 ưu tiên miễn phí: không bật dịch vụ có tính phí, mua API credits hay dùng API trả phí mặc định. Nếu cần chi tiêu, báo lý do, lựa chọn miễn phí, dự toán và xin phê duyệt riêng trước khi phát sinh phí; không gửi dữ liệu ra ngoài nếu policy chưa cho phép.

Tài liệu chi tiết: [Nguồn và corpus](02-source-corpus-plan.md), [Parser/OCR](03-parser-quality-plan.md), [Data/graph/sizing](04-data-graph-storage-plan.md), [Review/evaluation](05-review-evaluation-plan.md), [Backlog và gate](06-backlog-gate.md).
