# 14. Acceptance Criteria & Test Plan

Phiên bản 0.2 · 26/11/2026 · Kế hoạch nghiệm thu, chưa chạy các suite

## Bộ kiểm thử và evidence

[RTM](rtm.md) nối từng yêu cầu với bộ kiểm thử dưới đây. Test case tạo sau G0 theo gói và dataset được phép. Dùng các trạng thái `PLANNED`, `NOT_RUN`, `BLOCKED`, `FAIL`, `PASS` với evidence thực. Gói chưa chạy hiện `NOT_RUN`.

| Suite | Kịch bản chính và kết quả mong đợi | Evidence tối thiểu |
|---|---|---|
| TST-01 Hồ sơ và repo | Đủ 14 bản versioned, RTM và giả định. Sau duyệt catalog, mỗi repo private có owner/contract/CI inventory | Chữ ký/approval, digests, repo inventory và checks |
| TST-02 Nguồn và ingestion | Quyền theo từng action. Chạy lô HTML/PDF/scan/DOC/bảng, retry/cursor/idempotency, mâu thuẫn và cách ly. Chỉ bản có quyền và review đi đúng kênh | Source registry, gold references, before/after count và extraction report |
| TST-03 Search và retrieval | Search số hiệu/điều khoản/date/locality, keyword/dense/hybrid/rerank, interface swappable. Filter verified/ACL và benchmark giữ corpus/split | Contract run, ranked output, Recall/nDCG, latency và parity |
| TST-04 Temporal và rules | Kiểm biên nửa mở, recorded-late, past/future, sửa/bãi bỏ/transition, khoanh scope, rule unknown và ưu tiên loại tài liệu | Snapshot replay, version assertions, rule registry và coverage |
| TST-05 Graph | Kiểm node/edge rights, obligations, conditions/exceptions, versioned provenance, review state, query multi-hop và giới hạn | Gold graphs, precision/coverage theo type, A/B report và path |
| TST-06 Answer verification | Trích dẫn sai ID/version/date/anchor và claim thiếu căn cứ bị chặn. Hỏi thiếu facts, trả partial, VI/EN và giữ nguyên bản | Structured answers, claim rubric, confusion matrix, evidence links |
| TST-07 Modes, gateway và agent | So Standard/Advanced cùng cases. Route/fallback deny, tool ACL, cap/cancel/retry và complete event sau verify | Traces đã che, tool outcomes, errors, token/cost, latency, release cell |
| TST-08 Evaluation | Kiểm dedup/group split, L2/L3, strata, metric/CI, ablation và chặn deploy khi regression fail | Signed dataset/reviewer evidence, holdout digest và gate/ablation report |
| TST-09 Web và Studio | Search/chat/citation/feedback/auth, progress/keyboard/screen reader/VI/EN. Reviewer thao tác tất cả module sandbox bằng dữ liệu mẫu | E2E runs, accessibility findings, screenshots/video và kiểm quota sandbox |
| TST-10 Security/privacy | Tenant control ở API/storage/index/cache/log/stream, dữ liệu tải lên, egress, roles, consent, quota race, privacy/age gates, redaction | Access matrix, isolation reports, scan results và security/compliance approvals |
| TST-11 Cloud, cost và recovery | Uptime/load, CI/CD canary, health monitoring, metered cost, quota, backup/restore, rollback cùng manifest đã pin | Deploy URLs, run logs, P50/P95/P99, billing/quotas, restore và rollback log |
| TST-12 Portfolio | Chủ dự án tái hiện pipeline, tự debug/sửa và regression. Demo và báo cáo public đúng quyền | Architecture overview, case study, benchmark report, video và replay evidence |
| TST-13 Roadmap LATER | Xem lại feature, scope và gate sau V1 khi được mở, giữ yêu cầu trong backlog | Backlog/change records và kế hoạch phiên bản tương ứng |

Mỗi run lưu ID, thời điểm, environment, actor, command/params, commit/image, corpus/index/rule/graph, model/prompt/policy, fixture/dataset và scope. Kết quả gồm expected/actual, count/denominator, logs đã che, bug, người duyệt và digest evidence. Quy ước metric và holdout ở [Evaluation Specification](07-benchmark-evaluation.md).

## Tình huống kiểm thử định trước

| Case | Thiết lập và thao tác | Kết quả cần quan sát |
|---|---|---|
| TST-02.1 | Dùng cùng response hợp lệ, ngắt job sau khi ghi raw object và chạy lại từ checkpoint | Một artifact theo hash, một revision cho cùng dữ liệu, hai lần thực thi truy vết được |
| TST-04.1 | Dùng fixture ghi nhận sửa đổi muộn trong Database Design và truy vấn cùng ngày pháp lý ở hai recorded cutoffs | Hai phiên bản đúng snapshot. Hiệu lực của khoản không liên quan giữ theo version riêng |
| TST-05.1 | Dùng bộ gold structural và bộ gold deontic riêng, gồm cạnh sửa đổi, nghĩa vụ có điều kiện và ngoại lệ chưa review | Tính precision/coverage theo mỗi tầng và loại cạnh. Loại cạnh chưa review khỏi đường dẫn dùng làm căn cứ |
| TST-06.1 | Đưa claim có source ID hợp lệ nhưng quote thuộc một version khác vào verifier | Claim bị chặn. Terminal event dùng partial hoặc insufficient evidence theo phần có căn cứ |
| TST-07.1 | Hủy Advanced sau khi đã mở một call và trước bước tool tiếp theo | Stream kết thúc canceled, call đã mở được kết toán, bước tool tiếp theo không chạy |
| TST-08.1 | Đưa hai biến thể từ cùng họ văn bản hoặc case gốc vào khác split | Validator báo leakage, manifest bị từ chối trước promotion |
| TST-10.1 | Đăng nhập tài khoản B và yêu cầu stream/replay của answer thuộc tài khoản A trên fixture riêng | API từ chối. Không lộ ID, nội dung, trace hoặc event qua cache hay replay |
| TST-11.1 | Candidate canary trỏ index snapshot khác manifest đã duyệt | Promotion bị chặn hoặc alias về bản đã duyệt. Evidence lưu snapshot sai và lần kiểm tra sau rollback |
| TST-08.2 | Global và domain đạt ngưỡng. Một cell đăng ký có 9 group độc lập, một cell đủ 10 nhưng có S1, và một cell đủ mẫu, ca khó, reviewer, không có lỗi nghiêm trọng | Hai cell đầu chỉ tra cứu với lý do riêng. Cell cuối đủ điều kiện xem xét mở trong mode đã đo và phạm vi policy |
| TST-09.1 | Guest chưa khai điều kiện tuổi và bấm Hỏi AI. Sau đó cập nhật khai báo theo policy. Mô phỏng verification chậm và reconnect | Quyền tra cứu công khai luôn khả dụng. AI chỉ được gửi khi server cho phép. Có progress, hủy và recovery. Kết luận do terminal result đã xác minh cung cấp |
| TST-10.2 | Source fixture chứa chỉ dẫn vô hại vượt scope. Agent end-user yêu cầu hành động ghi, Reviewer thao tác trên mẫu demo | Công cụ public từ chối ghi, egress giữ allowlist. Studio chỉ cho action đã duyệt trong namespace đúng quyền và môi trường |

## Acceptance matrix

| AC | Tiêu chí | Suite | Gate |
|---|---|---|---|
| AC-01 | Retrieval Recall@20 ≥ 90% | TST-03, TST-08 | G2, G5 |
| AC-02 | nDCG@10 ≥ 0,80 | TST-03, TST-08 | G2, G5 |
| AC-03 | Legal Answer Correctness ≥ 90% | TST-06, TST-08 | G5 |
| AC-04 | Faithfulness ≥ 95% | TST-06, TST-08 | G5 |
| AC-05 | Citation Precision ≥ 98% | TST-06, TST-08 | G5 |
| AC-06 | Temporal Validity Accuracy ≥ 98% | TST-04, TST-08 | G5 |
| AC-07 | Correct Abstention Rate ≥ 90% | TST-06, TST-08 | G5 |
| AC-08 | 0 trích dẫn không tồn tại trong nghiệm thu | TST-06, TST-08 | G5 |
| AC-09 | 0 rò rỉ tài khoản trong nghiệm thu | TST-10 | G6 |
| AC-10 | ≥ 1.000 case L2/L3 thực sự đạt required tier | TST-08 | G5 |
| AC-11 | Mọi lĩnh vực taxonomy có AI qua gate, giới hạn theo severity | TST-07, TST-08 | G7 |
| AC-12 | Structural trên corpus được phép, Deontic đủ ontology/pipeline trên tập lõi có gold evidence, đều có provenance, temporal và tests. Scope và ngưỡng precision/completeness chờ khóa | TST-05 | G3, G5 |
| AC-13 | Model/retriever swap, agent/citation/temporal/verification E2E và regression | TST-03–08 | G4, G5 |
| AC-14 | Cloud online, monitoring, quota/cost, release/rollback evidence | TST-11 | G6 |
| AC-15 | Demo public, Studio đầy đủ nhóm chức năng, portfolio evidence | TST-09, TST-12 | G6, G7 |
| AC-16 | 14 hồ sơ đủ phiên bản đã duyệt trước PoC, cập nhật theo bằng chứng | TST-01 | G0 |

## Gate, severity và rollback

| Gate | Điều kiện ký duyệt |
|---|---|
| G0 | Baseline, 14 hồ sơ versioned được chủ dự án duyệt, RTM, giả định/TBD, blocker và test plan. Ghi quyết định ADR-01/05 theo SAD. Sau phê duyệt G0 mới chạy PoC |
| G1 | Source/rights, taxonomy/quality, mô hình dữ liệu/graph và sizing có evidence. Chốt ADR phụ thuộc |
| G2 | Search/retrieval và metrics phát lại trên tập giai đoạn. G5 xác nhận lại trên holdout |
| G3 | Bitemporal, graph chuyên sâu, rule/citation/verification có test xuyên suốt và evidence |
| G4 | Standard, Advanced, bounded tools/iterations, progress, comparison và risk controls |
| G5 | ≥ 1.000 case L2/L3 thật và holdout độc lập. AC-01–07 áp ở cấp toàn tập/domain theo giao thức đã khóa. Cell có bằng chứng tối thiểu và 0 S0/S1. Thiếu L3 với case cần L3 giữ blocker |
| G6 | Studio sandbox public, production access isolated, demo online và test cost/load/security/restore/CI |
| G7 | G0–G6 PASS, reach theo AC-11, demo/portfolio/benchmark, không có lỗi nghiêm trọng đã biết trong phạm vi mở |
| G8 | LATER: SME và bảo mật độc lập, pháp lý, quyền nguồn/provider và thương mại |

S0 gồm rò rỉ dữ liệu/quyền quản trị, tác động ngoài trái quyền hoặc sự cố an toàn tức thời. S1 gồm căn cứ bịa, sai hiệu lực dẫn đến kết luận rủi ro cao hoặc sai nghiêm trọng có thể gây hại. S2 ảnh hưởng chức năng đáng kể có cách tránh. S3 là lỗi nhỏ. Với gate mở, S0/S1 chưa xử lý khóa phạm vi bị ảnh hưởng. Lỗi S2/S3 theo triage có owner và evidence. Điều kiện AC vẫn bắt buộc.

Gate report ghi các tầng global, domain và cell, cùng mode, quota, số group độc lập, denominator của từng metric, CI khi phù hợp, `s0_count` và `s1_count` theo scope, người duyệt và artifact digests. Event `GateReport.v1` liên kết báo cáo chi tiết qua `report_ref`. Giữ ngưỡng AC-01–07 ở global và domain. Với cell mục tiêu, dùng sàn đề xuất 10 group holdout độc lập, ca khó bắt buộc và 0 S0/S1 sau khi global và domain đạt. POC-11 và ADR-06 khóa sàn/mẫu số trước lựa chọn model. Cell thiếu evidence hoặc fail chỉ mở tra cứu. Không cấp PASS nhờ trung bình toàn tập nếu domain/cell chưa đủ điều kiện tương ứng. [Schema nội bộ](contracts/internal-v1.schema.json) · [Giao thức đo và sàn mẫu](07-benchmark-evaluation.md#báo-cáo-và-gate-theo-tầng).

Incident chạy quy trình khóa cell/route, rollback bản đã duyệt, lưu chứng cứ, sửa, chạy regression và duyệt mở lại. Nếu một lĩnh vực thiếu cell AI đủ điều kiện, G7 vẫn chờ đạt.

[Căn cứ baseline §§10, 12, 15–17](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md)
