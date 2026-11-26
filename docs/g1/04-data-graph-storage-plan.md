# G1-04 — Temporal model, Knowledge Graph và storage sizing

Phiên bản 0.1-draft · REQ-TEMP-01–03, REQ-GRAPH-01–02, REQ-ARCH-03, REQ-DATA-07 · AC-12; chuẩn bị TST-04/05, POC-04/05 G3, ADR-02

## 1. Mô hình nguồn sự thật

Tiếp nối [Database Design](../g0/06-database-design.md) và [SQL fixture đã kiểm G0](../g0/examples/temporal-example.sql). Legal Knowledge là writer duy nhất của document/provision versions, canonical identity, lineage, taxonomy, graph/rule assertions; Data Ingestion sở hữu jobs, source/artifacts/quarantine/candidates. Retrieval sở hữu index dẫn xuất, Evaluation sở hữu cases/reviews/runs; join giữa service qua IDs và contract đã pin, không ghi vào schema của service khác.

Mục tiêu G1 là migration candidate và test integrity với mẫu được phép/synthetic có label; G3 mới nghiệm thu semantic temporal/rule/graph engine. Ghi data model/schema revision và manifest. Version data phải cùng snapshot và recorded cutoff, giữ valid time khác recorded time (nửa mở, timezone timestamp); unknown được biểu diễn rõ; verified overlap bị từ chối theo cùng key + scope; candidate/conflict có thể tồn tại để review. Không dùng similarity để xác định giá trị pháp lý.

| Fixture case | G1 expected assertion |
|---|---|
| Effective date sớm hơn recorded time | Hai recorded cutoff khác nhau trả về revision tương ứng |
| Ngày đúng biên valid/recorded | Nửa mở, không chọn hai revision đồng thời |
| Điều 5a, khoản 2a, rename, partial repeal | Stable ID khác khi khác provision, label/history đúng revision |
| Sửa nhiều luật và sửa cụm từ | Các operation, target version, span/anchor riêng, ambiguous → review |
| Hợp nhất và địa giới cũ/mới | Lineage về source versions, nhiều cạnh split hợp lệ; unknown scope không tự đoán |
| Provenance hoặc review sai | Candidate không vào verified snapshot/index/graph; anchor phải cùng version |
| Update/rollback | Transaction + outbox, index projection replay, giữ manifest nhất quán |

Chạy fixture G0 trên database tạm và thêm case missing/ambiguous provenance nếu cần. Cấm tuyên bố fixture synthetic là legal correctness.

## 2. Graph hai tầng

| Tầng | Gold scope proposed | Đo trong G3 |
|---|---|---|
| Structural/citation | 18 families mục tiêu (2/domain) từ corpus đủ quyền; gồm 6 edge types modifies, replaces, repeals, guides, corrects, references, hierarchy/lineage và locality | Precision và coverage từng edge/node type trên gold audit; tỷ lệ processed corpus riêng |
| Deontic/normative | Cùng các family có quy tắc điều kiện/ngoại lệ đủ evidence, bổ sung family nếu thiếu. Subject, Right, Obligation, Condition, Exception; applies_to, grants, imposes, conditioned_by, excepted_by | Precision, coverage từng node/edge, evidence validity, temporal/scope constraints, multi-hop ablation |

Gold assertion gồm stable id, source provision version, source/target/type, canonical labels, exact quote/locator, valid/recorded ranges, scope, review status, reviewer/evidence ref, ambiguity/conflict. Gold tạo hoặc kiểm riêng bởi human; cạnh suy đoán tuyệt đối không làm căn cứ.

Quy tắc mẫu: báo cho mỗi type/domain số gold units độc lập, số predicted, TP/FP/FN và eligible corpus count. Precision = TP/predicted; coverage (recall) = TP/gold. Không coi edge count lớn là graph sâu. Mục tiêu proposed cho G3: structural precision ≥98%, coverage ≥90%; deontic precision ≥95%, coverage ≥85%; 100% verified assertions có version/anchor/time/scope hợp lệ. Báo các ngưỡng theo type, sample adequacy và confidence; nếu thiếu gold không PASS. Đây không phải sửa AC-12: owner khóa phạm vi, mẫu số và ngưỡng sau khảo sát, trước evaluation của graph; pipeline structural trên mọi corpus được nhận có quyền, deontic đủ ontology/pipeline sâu trên tập lõi được duyệt, không xóa domain để chạy kịp.

## 3. So sánh storage theo 5 năng lực logic

| Năng lực | A: baseline tối giản | B: khi A không đáp ứng |
|---|---|---|
| Relational | PostgreSQL schema/role ownership | Managed/tách cụm theo trust hoặc tải |
| Vector | pgvector | Qdrant hoặc managed vector |
| Keyword | exact-key + PostgreSQL FTS/simple, đối chứng trgm/unaccent | OpenSearch/BM25 hoặc tương đương |
| Graph | Relation tables + bounded traversal | Neo4j/managed graph |
| Object | S3-compatible local test | GCS/R2 hoặc object store phù hợp policy |

Đề xuất bắt đầu bằng A cho đo sizing/fixture, không phải lựa chọn final. So results query plans, filter temporal/ACL, index build/rebuild, restore, service isolation, backup, operational complexity và cost với B theo cùng corpus. G1 chỉ chốt baseline relational/object candidate và số đo khối lượng có evidence; search/vector phải POC-03, temporal/graph phải POC-04/05, cloud managed phải POC-09. ADR-02 được ghi từng phần / PROPOSED cho phần chưa có bằng chứng; không ép một DB vật lý cho tất cả vì monorepo.

## 4. Sizing report thực đo

Với authorized snapshot, ghi unique documents, versions, provisions, artifacts, raw bytes, normalized text bytes, pages, chunks theo chunker candidate (version), node/edge count, index bytes theo config, peak RAM/disk và thời gian parse/index. Báo mean/P50/P90, grouped by format/source/time; tách artifact duplicate raw vs logical revisions. Tránh ngoại suy từ một trang synthetic.

Projection:
- raw/year = sum(n_s × mean raw bytes_s) theo strata s; dự báo tăng revision và retention bằng low/base/high có assumptions.
- vector payload lower bound = chunks × dimension × bytes per scalar; đo overhead index/metadata/replica thực, không coi lower bound là tổng dung lượng.
- total = raw + normalized/relational + keyword + vector + graph + backup + logs; nếu dùng chung engine kiểm không double-count, thêm headroom có lý do.
- growth & time: bytes/day, artifacts/day, reviewer hours theo throughput; report P50/P90 và khoảng uncertainty, chi phí thực bằng metered usage ở G6, không dùng giá chưa xác minh.

Máy thử nghiệm reference của owner: i7-14650HX, RTX 5060 Laptop 8GB, RAM 32GB, Windows 11 (xác nhận cấu hình thực trước pin). Local PoC ưu tiên đủ tài nguyên trong môi trường cô lập; model LLM vẫn 100% API theo baseline và không cần dùng API cho G1 mặc định. 
