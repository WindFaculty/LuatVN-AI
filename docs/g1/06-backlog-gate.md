# G1-06 — Backlog thực thi, acceptance gate và handoff

Phiên bản 0.1-draft · 26/11/2026 · Quyết định/threshold/scope trong bộ này chờ chủ dự án duyệt

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

Tasks engineering chưa thực hiện trong đợt viết plan ghi PLANNED; các runs đã có dẫn link riêng, không overwrite evidence cũ. T02/T07/T08 có thể chạy synthetic trước khi quyền nguồn thật; T03/T05/T06 real và T11 human bị chặn cho đến quyền/reviewer. Owner review diff/verification, ký merge và gate. Không tạo repo mới.

## 2. Gate G1

| Check | Điều kiện chấp nhận | Hiện trạng 26/11 |
|---|---|---|
| G1-AC-A | POC-01 rights per action confirmed cho in-scope pilot và kế hoạch nguồn trọng yếu; catalog/scope có denominator & gap rõ | BLOCKED — pending rights và denominator |
| G1-AC-B | Taxonomy version có mapping/source evidence, strata và plan phủ toàn bộ lĩnh vực; owner chốt | IN_PROGRESS — 9 nhóm pilot, chưa official |
| G1-AC-C | POC-02 real authorized gold samples, metrics by format/ngưỡng approved, failure policy + artifact/replay/quarantine tests | IN_PROGRESS — synthetic only |
| G1-AC-D | Data model/temporal migration candidate, integrity tests, graph gold scope/type denominators approved | IN_PROGRESS — fixture G0, thiếu gold & sizing thật |
| G1-AC-E | Sizing artifacts/corpus/resources thực, storage trade-offs và ADR evidence theo từng phần | NOT_RUN — chưa đo corpus thật |
| G1-AC-F | POC-11 người thật review, counts L2/L3/pending, effort và feasibility, ADR-06 policy đủ căn cứ | BLOCKED — pilot verified L2/L3 0/0 |
| G1-AC-G | Gate report tổng hợp, trace tests/ADRs, reproduction và owner sign-off; tình trạng CI ghi trung thực | NOT_RUN — chưa có gate report |

Không đổi AC V1. G1 PASS cần tất cả check của G1 có evidence đạt, không có blocker về scope bắt buộc chưa được xử lý, có quyết định chủ dự án. TST-02 phần pipeline sẽ tiếp tục kiểm hồi quy ở các pha; TST-03–08 chỉ được ghi PASS khi có evidence đúng pha. Các phần ADR-02/03 chưa tới PoC tương ứng giữ PROPOSED; ADR-06 khóa policy đủ căn cứ trước lựa chọn model. Hosted CI đang bị chặn: log local replay là evidence riêng, không coi CI PASS hoặc bypass security. Nếu formal gate cần hosted CI mà không có run thì ghi BLOCKED và trình owner phương án kiểm tương đương, không tự accept.

## 3. Quyết định chủ dự án (chưa duyệt)

| ID | Nội dung | Đề xuất mặc định để duyệt | Nếu không duyệt |
|---|---|---|---|
| G1-D01 | Phạm vi và phương thức pilot | SRC-01/03, manual + nội bộ sau xác minh action riêng; song song xác minh SRC-02/04/05/06; chưa crawl hàng loạt | Chọn nguồn khác hợp pháp hoặc synthetic; real evidence chờ |
| G1-D02 | Taxonomy và sizing mẫu | 9 nhóm tầng 1 pilot → subdomains/mapping, review UNMAPPED; mục tiêu 45 families/36 artifacts/18 graph families/27 review cases | Thay phân bổ theo catalog và năng lực, không giảm scope V1 tự động |
| G1-D03 | Review capacity | Owner làm L2; đo 27-case pilot, phân tầng L3 thật, tìm reviewer phù hợp trước G5 nếu required | L3 pending, không được tính; cập nhật blocker/lịch |
| G1-D04 | Ngưỡng parser & graph | Candidate tại G1-03 và G1-04; khóa scope/metric trước audit, không điều chỉnh sau khi thấy kết quả chỉ để pass | Owner chọn phương án trước run chính và ghi lý do |
| G1-D05 | Môi trường/budget | Local PoC, disposable DB/object, ưu tiên zero paid services, no API data egress mặc định. Confirm giờ/tuần và ngân sách cho real-source/expert/model PoC sau | Ghi giới hạn, tách chi phí; xin duyệt trước chi tiêu/external effects |
| G1-D06 | Split/cell policy | Group-based, 50% holdout candidate, sàn G0 giữ proposed cho tới POC-11/ADR-06 | Tái phân bổ trước model selection dựa trên evidence, AC giữ nguyên |

D01 là phê duyệt phạm vi nội bộ, không thay bằng chứng quyền của bên cung cấp nguồn. D02 là pilot, không phải taxonomy cuối cùng hay corpus release. D03 không sửa DEC-04 hay gán owner là L3. D04–06 là giả định đề xuất; chưa ghi ACCEPTED.

## 4. Mẫu báo cáo G1 exit (chưa có kết quả)

- Gate run ID, date, repo commit, contract/schema/rights/corpus/taxonomy revisions.
- Evidence link cho T01–T13, expected/actual/counts by strata, scripts/commands/resources và reproduction.
- Source rights scope và gaps; parser quality/critical failures; temporal/graph constraints; sizing/hardware/cost assumptions; review tiers/throughput; S0/S1 hoặc known issues.
- Quyết định ADR: 02 storage/index (phần G1), 03 parser/OCR (phần G1), 06 evaluation protocol; phần sau G1 ghi rõ dependency và không chốt sớm.
- RTM delta đối với requirement/test/ADR liên quan; không thay G0 hash. Re-estimate engineering/human hours/calendar wait của roadmap; blockers, owner, action/due.
- G1 verdict PLANNED/NOT_RUN/BLOCKED/FAIL/PASS phù hợp evidence, ký owner/date, next gate/rollback target. Hiện tại verdict chưa nghiệm thu.

## 5. Bàn giao sang G2

Chỉ chuyển sang G2 sau owner chốt G1 gate hoặc phê duyệt ngoại lệ bằng change control không hạ chuẩn. G2 nhận corpus authorized/verified dev snapshot, taxonomy IDs, canonical anchors và provenance, parser/quality policy, rights scope, storage sizing/ADR candidates, retrieval qrels/dev set (không holdout G5), manifest, TST-03 protocol và backlog POC-03. G2 so exact-key/keyword/dense/hybrid/rerank; G3 nhận temporal + graph migration/gold; G5 nhận split policy và review logs. Demo repo chỉ tham chiếu artifact và sample synthetic/approved, chưa cần đổi trong G1 documentation.
