# 04. AI/RAG Architecture Specification

Phiên bản 0.2 · 26/11/2026 · Thiết kế đề xuất

## Luồng yêu cầu

1. Xác thực policy theo actor, tenant, tuổi, data class, tác vụ và mức rủi ro. Xác định ngày pháp lý, thời điểm hệ thống biết và snapshot. Phân loại search, QA, explanation, synthesis, scenario hoặc rebuttal. Search số hiệu và cấu trúc có đường đi không cần LLM.
2. Bảo toàn truy vấn gốc và thuật ngữ. Với EN, tạo truy vấn VI để truy xuất. Thiếu dữ kiện ảnh hưởng áp dụng thì ưu tiên hỏi lại. Trường hợp cần nêu giả định, ghi chúng vào envelope.
3. Retrieve candidate theo dense, sparse, exact/keyword, phân cấp cha–con và graph. Áp lọc ACL, tenant, nguồn, verification, jurisdiction, valid/recorded time trước khi xếp hạng. Ghép bằng Reciprocal Rank Fusion làm ứng viên, rerank, mở rộng ngữ cảnh cha–con có kiểm tra lại filter. Benchmark từng nhánh và ngưỡng. Khi evidence thiếu, thử reformulation hữu hạn trong kho nội bộ.
4. Tạo claims từ evidence đã chọn. Mỗi claim mang một hoặc nhiều evidence IDs. Legal Knowledge cung cấp rule đã duyệt, phạm vi áp dụng và trạng thái `applicable`, `not_applicable` hoặc `unknown`. Luật chuyển tiếp, ngoại lệ và bất đồng phải được kiểm tra trước khi kết luận.
5. Verify tồn tại và quyền đọc của evidence ID, nguồn, snapshot, version, khoảng hiệu lực, anchor và quote. Đối chiếu claim với căn cứ, điều kiện và ngoại lệ bằng rule engine và model đánh giá có cấu hình versioned. Model judge không thể cho qua lỗi deterministic. Nếu còn bằng chứng chưa đủ, chặn claim tương ứng hoặc chuyển trạng thái. Phiên bản cuối phải qua kiểm tra lại khi bỏ claim.
6. Phát kết quả cuối bằng ngôn ngữ yêu cầu. Trích dẫn giữ bản tiếng Việt, URL, lịch sử hiệu lực và vị trí. Hiển thị giới hạn, thông tin thiếu và cờ cần chuyên gia. V1 chỉ dùng kho đã xác minh làm căn cứ.

## Index và graph

Đơn vị evidence là provision version tại snapshot. Chunk ranh giới pháp lý mang heading/level, version ID, offsets hoặc tọa độ trang, source revision, validity và metadata lọc. Chunk ngữ nghĩa nằm trong hoặc trỏ về cùng version. Cache key chứa scope và snapshot, chỉ mục private tách tenant. Chunker, embedder, retriever, reranker, evaluator và provider là các adapter thay thế được theo config. Mỗi update rebuild hoặc update chỉ mục với manifest và kiểm tra parity trước promotion.

Graph tách tầng structural/citation và deontic/normative. Duyệt node và edge versioned theo danh sách relation được phép, ngân sách hops/nodes, valid/recorded time và provenance ở từng cạnh. Mất graph có thể đưa request về loại tác vụ có đường đạt gate riêng. Câu cần graph/temporal mà dependency thiếu trả trạng thái giới hạn phù hợp. [Phạm vi và bằng chứng từng tầng](06-database-design.md#hai-tầng-graph-và-quyền-ghi).

## Standard và Advanced

| Mode | Điều phối | Điều kiện kết thúc |
|---|---|---|
| Standard | Workflow có bước phân loại → truy xuất → tạo claim → verify | Verified, partial, needs facts, insufficient evidence, policy denied, canceled hoặc failed |
| Advanced | Planner tạo các subquestion, gọi tool tra cứu evidence/version, graph traversal và rule check, tự kiểm tra và chỉnh plan hữu hạn | Cùng terminal states và chuẩn verification. Tool dành cho end-user V1 là read-only, không có quyền ghi, publish hoặc tác động ngoài |

Prototype quy định deadline tổng, token cap, step cap, số retry, hop cap và cancellation token. Giá trị từng cap chốt ở POC-08 và POC-09. Retry chỉ với lỗi có thể phục hồi và trong phần ngân sách còn lại. Worker kiểm cancellation trước mọi bước, gateway kết toán call đã mở kể cả khi kết quả không trả cho UI. Tool output là dữ liệu. Agent đề xuất thao tác quản trị hoặc sandbox qua luồng Studio riêng. API theo role chỉ thực hiện action đã duyệt, cùng môi trường, hash input, expiry và audit.

Progress chỉ gồm stage, trạng thái tài liệu, verification status và mã lỗi đã lọc. Reconnect dựa event ID với quyền owner và retention. Kết luận qua kiểm chứng rồi mới trả trong terminal result, nên thời gian có kết luận phụ thuộc retrieval, generation và verification. Đo riêng time to first progress event và time to verified answer. Deadline hết thì kết thúc bằng trạng thái phù hợp hoặc trả phần đã qua xác minh. [UX khi chờ](09-ui-ux.md#chờ-kết-quả-xác-minh) · [OpenAPI Answer/SSE](contracts/answers.openapi.yaml).

## Gateway và Answer Envelope

Gateway kiểm data class, chính sách provider, region/retention, purpose, eligibility và quota trước khi reserve. Route theo chất lượng, độ khó, giá và quyền của provider đã phê duyệt. Fallback phải qua cùng eligibility. Local/self-host có thể dùng cho OCR, embedding, rerank và redaction. Mọi inference LLM dùng API bên ngoài. Request hoặc case cần xử lý riêng tư mà không khớp policy sẽ dừng trước egress.

| Nhóm | Trường bắt buộc của contract đề xuất |
|---|---|
| Nhận diện | `answer_id`, `request_id`, `status`, `mode`, `language`, `legal_as_of`, `recorded_as_of`, `snapshot_id` |
| Nội dung | `summary`, `facts`, `assumptions`, `missing_facts`, `claims[]`, `risks`, `limitations`, `expert_review_required` |
| Claim và evidence | `claim_id`, `verification`, `evidence_ids[]`. Mỗi evidence có `evidence_id`, `provision_id`, `version_id`, `quote`, `url`, `anchor`, `validity`, `source_revision` |
| Replay nội bộ | Trace đã che, `config_id`, `model_id`, `prompt_revision`, `rule_revision`, `index_digest`, mã nhánh, token/cost/latency |

## Rule Engine và hai lớp quy tắc

| Lớp | Phạm vi V1 | Ràng buộc xác minh |
|---|---|---|
| Meta-legal | Ưu tiên temporal, loại/hiệu lực/phạm vi văn bản, thứ bậc, quan hệ sửa đổi, chuyển tiếp và xung đột | Mỗi bộ quy tắc có căn cứ đã duyệt, revision, snapshot, scope và expected verdict. Khi điều kiện áp dụng hoặc căn cứ chưa rõ, trả `unknown` |
| Substantive | Mã hóa các điều kiện, ngoại lệ, quyền/nghĩa vụ có thể biểu diễn và kiểm chứng trên tập lõi dùng ở V1 | Mỗi rule gắn provenance đến provision version đã xác minh, facts bắt buộc, test dương/âm/thiếu facts. Coverage đánh giá riêng theo domain và tăng theo roadmap |

Ứng viên cho POC-07 là AST JSON có schema kiểu dữ liệu rõ, gồm `all`, `any`, fact predicate và kết quả ba trạng thái `applicable`, `not_applicable`, `unknown`. Rule family và revision thuộc Legal Knowledge. Không cho thực thi mã tùy ý trong rule. So sánh AST giới hạn với JSONLogic, OPA/Rego hoặc DSL Python bị giới hạn dựa trên tái lập, giải thích và handling khi thiếu dữ kiện. Chọn qua ADR-03 sau PoC. Graph cung cấp quan hệ đã xác minh. Rule engine áp điều kiện, tầm thời gian và ngữ cảnh để quyết định applicability trước verifier. [Hai tầng graph](06-database-design.md#hai-tầng-graph-và-quyền-ghi).

POC-03 đo retrieval, POC-04/05 đo temporal/graph, POC-06 đo model/gateway, POC-07 kiểm verification và POC-08 đối chứng mode. [Thiết kế đối chứng và metric](07-benchmark-evaluation.md).

[Căn cứ baseline §§5.2–6, 10 và 14](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md)
