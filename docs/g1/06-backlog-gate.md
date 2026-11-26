# G1-06 — Backlog thực thi, acceptance gate và handoff

Phiên bản 1.0 · Quyết định G1-D01–06 đã được chủ dự án duyệt ngày 26/11/2026 · 6/6 quyết định đã duyệt; G1 gate chưa nghiệm thu

## 1. Backlog cho Coding Agent

| ID | Task / acceptance quan sát được | Scope | Dependencies | Trace |
|---|---|---|---|---|
| G1-T01 | Verify repo/manifest/contract pin + G0 hashes; lưu output local và CI status thực | scripts, packages/contracts, docs/g1 | G0 | REQ-ARCH-02/04, TST-01 |
| G1-T02 | Thiết lập source/action registry + validator deny-by-default; synthetic allow/deny cases | data-ingestion, experiments/g1 | T01 | REQ-DATA-03/05, REQ-SEC-11, TST-02 |
| G1-T03 | Authorized catalog snapshot, canonical dedup và counts; dừng nếu quyền pending | data-ingestion, legal-knowledge | T02 + owner rights | REQ-DATA-01–03/08, POC-01 |
| G1-T04 | Taxonomy draft→candidate, mapping + coverage/strata/sample manifests | legal-knowledge, evaluation | T03 | REQ-DATA-08, BLOCKER-01 |
| G1-T05 | Real gold extraction set và format matrix; rights-checked | experiments/g1, docs/g1/evidence | T03/04 + reviewer | REQ-DATA-04/06, POC-02 |
| G1-T06 | Parser/OCR comparison, diff metrics, anchor/table/metadata and quarantine tests | experiments/g1, data-ingestion | T05 | REQ-DATA-04–07, TST-02 |
| G1-T07 | Idempotency/checkpoint/retry/immutable artifacts and security fixtures | data-ingestion | T02; synthetic trước | REQ-DATA-05–07, REQ-SEC-05, TST-02.1 |
| G1-T08 | Bitemporal migration candidate + integrity/replay on fixture, add provenance failure cases | legal-knowledge, experiments/g1 | T01 | REQ-TEMP-01–03, TST-04 |
| G1-T09 | Graph ontology gold schema/annotated examples by domain/type + review states | legal-knowledge, evaluation | T04/05 | REQ-GRAPH-01/02, AC-12 |
| G1-T10 | Measure raw/normalized/index candidates, resource profile and low/base/high sizing | data-ingestion, legal-knowledge, retrieval, infra | T06/08/09 | REQ-ARCH-03, ADR-02 proposed |
| G1-T11 | Validation of pilot case, group and review records; actual human review separately owned | evaluation | T04/05 + owner reviewer | REQ-EVAL-01–03, POC-11 |
| G1-T12 | Feasibility matrix/effort, split/policy and holdout plan; ADR-06 proposal | evaluation, docs/g1 | T11 | REQ-EVAL-01–03, AC-10/11 |
| G1-T13 | Aggregate evidence, unresolved ADR slices, roadmap/cost risk and acceptance report | docs/g1, docs/adr | T01–12 | TST-02, G1, G2 handoff |

Tasks engineering chưa thực hiện trong đợt viết plan ghi PLANNED; các runs đã có dẫn link riêng, không overwrite evidence cũ. T02/T07/T08 có thể chạy synthetic trước khi quyền nguồn thật; T03/T05/T06 real và T11 human bị chặn cho đến khi có quyền nguồn và dữ liệu hợp lệ; reviewer L2 đã xác định là chủ dự án, review thực vẫn chưa chạy. Owner review diff/verification, ký merge và gate. Không tạo repo mới.

## 2. Gate G1

Lô thực thi hiện hành và các điều kiện còn mở nằm trong [báo cáo thực thi G1](execution-status-2026-11-26.md#điều-kiện-nghiệm-thu).

| Check | Điều kiện chấp nhận | Tại thời điểm duyệt kế hoạch |
|---|---|---|
| G1-AC-A | POC-01 rights per action confirmed cho in-scope pilot và kế hoạch nguồn trọng yếu; catalog/scope có denominator & gap rõ | BLOCKED — pending rights và denominator |
| G1-AC-B | Taxonomy version có mapping/source evidence, strata và plan phủ toàn bộ lĩnh vực; owner chốt | IN_PROGRESS — 9 nhóm pilot, chưa official |
| G1-AC-C | POC-02 real authorized gold samples, metrics by format/ngưỡng đã duyệt và audit manifest đã khóa, failure policy + artifact/replay/quarantine tests | IN_PROGRESS — synthetic only |
| G1-AC-D | Data model/temporal migration candidate, integrity tests, graph gold scope/type denominators được khóa trước audit, ngưỡng đã duyệt | IN_PROGRESS — fixture G0, thiếu gold & sizing thật |
| G1-AC-E | Sizing artifacts/corpus/resources thực, storage trade-offs và ADR evidence theo từng phần | NOT_RUN — chưa đo corpus thật |
| G1-AC-F | POC-11 người thật review, counts L2/L3/pending, effort và feasibility, ADR-06 policy đủ căn cứ | BLOCKED — pilot verified L2/L3 0/0 |
| G1-AC-G | Gate report tổng hợp, trace tests/ADRs, reproduction và owner sign-off; tình trạng CI ghi trung thực | NOT_RUN — chưa có gate report |

Không đổi AC V1. G1 PASS cần tất cả check của G1 có evidence đạt, không có blocker về scope bắt buộc chưa được xử lý, có quyết định chủ dự án. TST-02 phần pipeline sẽ tiếp tục kiểm hồi quy ở các pha; TST-03–08 chỉ được ghi PASS khi có evidence đúng pha. Các phần ADR-02/03 chưa tới PoC tương ứng giữ PROPOSED; ADR-06 khóa policy đủ căn cứ trước lựa chọn model. Hosted CI đang bị chặn: log local replay là evidence riêng, không coi CI PASS hoặc bypass security. Nếu formal gate cần hosted CI mà không có run thì ghi BLOCKED và trình owner phương án kiểm tương đương, không tự accept.

## 3. Quyết định chủ dự án đã duyệt

| ID | Nội dung | Quyết định đã duyệt (ACCEPTED) | Điều kiện còn mở / guardrail |
|---|---|---|---|
| G1-D01 | Nguồn ban đầu | Ưu tiên SRC-01/03. Chủ dự án bổ sung quyền tải mẫu công khai theo URL chọn trước và xử lý nội bộ. [Phê duyệt bổ sung](evidence/owner-decision-g1-d01-2026-11-26.md) | Dẫn nguồn, pin quyền từng action của lô. Crawl catalog và phân phối toàn bộ cần phạm vi riêng. |
| G1-D02 | Taxonomy và quy mô pilot | Giữ 9 nhóm pilot, mở rộng sub-domain theo catalog; 45 families / 36 artifacts / 18 graph families / 27 review cases | Chưa phải taxonomy chính thức hay coverage toàn quốc. Báo thiếu mẫu, không tự giảm scope V1 |
| G1-D03 | Kiểm chứng pháp lý | Chủ dự án tự review L2, đo công sức và giữ case cần L3 ở PENDING_L3 cho đến khi có chuyên gia | Không tự gán L3, không đếm case thiếu required tier; blocker/lịch vẫn phải quản lý |
| G1-D04 | Ngưỡng parser & graph | Dùng các ngưỡng pilot trong [G1-03](03-parser-quality-plan.md) và [G1-04](04-data-graph-storage-plan.md), khóa trước audit | Manifest/rubric/scope/config phải pin trước audit; không chỉnh ngưỡng khi thấy kết quả để PASS |
| G1-D05 | Môi trường và ngân sách | Laptop hiện tại + Docker + database local; 30–40 giờ/tuần; ưu tiên miễn phí, không dùng API trả phí mặc định trong G1 | Xin duyệt trước phát sinh phí/external effects, không egress dữ liệu nếu chưa được phép |
| G1-D06 | Benchmark độc lập | Dự kiến 50% holdout theo group; khóa phân bổ thực sau POC-11 | Sàn/metric/cell policy và phân bổ thực qua ADR-06 trước model selection; không dùng holdout để tuning; AC giữ nguyên |

**Phê duyệt:** Trần Xuân Khoa, 26/11/2026, xác nhận trong cuộc trao đổi G1; 6/6 ACCEPTED, không có yêu cầu bổ sung. Kế hoạch G1 cập nhật từ v0.1-draft lên v1.0. D01 là phê duyệt phạm vi nội bộ, không thay bằng chứng quyền của bên cung cấp nguồn. D02 là pilot, không phải taxonomy cuối cùng hay corpus release. D03 không sửa DEC-04 hay gán owner là L3. D04 duyệt ngưỡng số nhưng audit manifest chưa khóa; D05 duyệt môi trường và ưu tiên ngân sách, không cấp phép chi tiêu; D06 duyệt tỷ lệ kế hoạch, không xác nhận holdout manifest đã freeze. Mọi ADR kỹ thuật chưa đủ evidence giữ PROPOSED; G1 vẫn IN_PROGRESS.

## 4. Checklist trước thực thi và audit

- [x] 6/6 quyết định G1 đã duyệt, capacity và ưu tiên ngân sách đã ghi nhận.
- [ ] T01: verify pin repo/contracts và G0 hashes; ghi tình trạng CI thực.
- [ ] T02: registry/action policy deny-by-default và các fixture allow/deny, trước mọi ingest thật.
- [ ] T03/T04: quyền thật theo từng action được xác nhận, catalog snapshot, mapping taxonomy, manifest mẫu và coverage gaps.
- [ ] T05/T06: pin gold extraction + group split, metric/mẫu số, ngưỡng G1-03, config và digest trước audit real sample.
- [ ] T08/T09: temporal fixture, graph gold scope/type/rubric và ngưỡng G1-04; pin trước graph audit G3.
- [ ] T11/T12: human review pilot 27 cases, log effort/tier; khóa phân bổ holdout thực sau POC-11 và trước model selection.
- [ ] T13: tổng hợp evidence, ADR theo pha, gate report, owner sign-off. Không đánh dấu PASS chỉ vì checklist kế hoạch đã duyệt.

## 5. Mẫu báo cáo G1 exit (chưa có kết quả)

- Gate run ID, date, repo commit, contract/schema/rights/corpus/taxonomy revisions.
- Evidence link cho T01–T13, expected/actual/counts by strata, scripts/commands/resources và reproduction.
- Source rights scope và gaps; parser quality/critical failures; temporal/graph constraints; sizing/hardware/cost assumptions; review tiers/throughput; S0/S1 hoặc known issues.
- Quyết định ADR: 02 storage/index (phần G1), 03 parser/OCR (phần G1), 06 evaluation protocol; phần sau G1 ghi rõ dependency và không chốt sớm.
- RTM delta đối với requirement/test/ADR liên quan; không thay G0 hash. Re-estimate engineering/human hours/calendar wait của roadmap; blockers, owner, action/due.
- G1 verdict PLANNED/NOT_RUN/BLOCKED/FAIL/PASS phù hợp evidence, ký owner/date, next gate/rollback target. Hiện tại verdict chưa nghiệm thu.

## 6. Bàn giao sang G2

Chỉ chuyển sang G2 sau owner chốt G1 gate hoặc phê duyệt ngoại lệ bằng change control không hạ chuẩn. G2 nhận corpus authorized/verified dev snapshot, taxonomy IDs, canonical anchors và provenance, parser/quality policy, rights scope, storage sizing/ADR candidates, retrieval qrels/dev set (không holdout G5), manifest, TST-03 protocol và backlog POC-03. G2 so exact-key/keyword/dense/hybrid/rerank; G3 nhận temporal + graph migration/gold; G5 nhận split policy và review logs. Demo repo chỉ tham chiếu artifact và sample synthetic/approved, chưa cần đổi trong G1 documentation.
