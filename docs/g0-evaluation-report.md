# Báo cáo Đánh giá Bộ Hồ sơ Nền G0 — Luật Việt Nam AI

| Thuộc tính | Giá trị |
|---|---|
| Phạm vi đánh giá | 17 tệp trong `docs/g0/` đối chiếu với [Requirements Baseline v1.0](../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md) |
| Phiên bản hồ sơ được đánh giá | `0.1` (ngày 26/11/2026) |
| Ngày lập báo cáo | 26/11/2026 |
| SHA-256 của Requirements Baseline v1.0 | `d06b7ace9d5252c1e09ab5e79ad4d34198f8fc2bfd1ebe91b9b85d3d2e4e4a03` |
| Bối cảnh triển khai | Chủ dự án solo điều phối **AI Coding Agents** thực thi kỹ thuật; con người giữ vai trò thiết kế, duyệt diff, review L2, quản trị gate và điều phối chuyên gia L3 |

---

## 1. Kết luận tổng quan

Bộ hồ sơ G0 hiện tại là một **khung quản trị dự án (G0 Governance Baseline) rất kỷ luật, nhất quán và trung thực**. Toàn bộ yêu cầu từ Baseline đã được truy vết khép kín, không bịa số liệu PoC, không che giấu blocker.

Khi xét đúng bối cảnh **chủ dự án dùng AI Coding Agents để triển khai** (thay vì tính theo giờ code thủ công truyền thống), phần khối lượng kỹ thuật (scaffolding, services, parser adapters, test suites, UI, CI/CD) **khả thi hơn đáng kể**. Tuy nhiên, bộ hồ sơ vẫn cần một vòng nâng cấp lên **`v0.2`** trước khi ký duyệt G0 vì còn:
1. **5 điểm lệch chéo trực tiếp** giữa các tài liệu;
2. **Nghịch lý thống kê** giữa 1.000 test case và release gate cấp cell (`domain × task × risk`);
3. **Mô hình dự toán chi phí quá lạc quan** (thiếu 2 môi trường cloud, dùng đơn giá Flash-Lite cho legal reasoning, thiếu chi phí eval/ingestion LLM);
4. **Chưa tách rạch ròi nút thắt phi-coding** (review con người L2/L3, quyền cổng nguồn, human debug ownership) khỏi tốc độ thực thi của AI Coding Agent;
5. **Độ sâu đặc tả còn mỏng** (29–78 dòng/tệp), chưa có contract/schema cụ thể để AI Coding Agent thực thi ngay mà không bị lệch thiết kế.

### Kết quả kiểm tra tự động bộ hồ sơ

| Hạng mục kiểm tra | Kết quả | Chi tiết |
|---|---|---|
| Số tệp hồ sơ G0 | **PASS** | Đủ 14 hồ sơ (`01`–`14`) + `README.md` + `registers.md` + `rtm.md` |
| Độ phủ truy vết RTM | **PASS** | Khớp **123/123 mã** (`REQ`, `BR`, `NFR`, `AC`, `DEC`, `OBJ`), 0 thiếu, 0 thừa |
| Liên kết nội bộ & anchor | **PASS** | 0 liên kết hỏng, 0 anchor sai |
| Số học chi phí (`11`) | **PASS** | Khớp từng xu (kể cả làm tròn trần Class A/B của R2 và độ nhạy 2x LLM) |
| Số học effort (`12`) | **PASS** | Tổng bảng khớp `505–860 h` |
| Sơ đồ Mermaid | **PASS (cú pháp) / WARN (đồng bộ)** | Đủ 4 sơ đồ hợp lệ, nhưng sơ đồ `03-sad.md` lệch topology với `08-security-threat-model.md` |
| Bằng chứng SHA-256 Baseline | **WARN** | `README.md` khẳng định đã khớp nhưng chưa ghi chuỗi hash thực tế để đối chiếu lại |

### Bảng chấm điểm tổng hợp (theo mô hình Solo + AI Coding Agents)

| Tiêu chí | Điểm | Nhận xét chính |
|---|:---:|---|
| Quản trị yêu cầu & Truy vết | **9,0 / 10** | Truy vết 100% (123/123), rạch ròi `MUST/SHOULD/LATER/TBD/BLOCKER`, không tự làm đẹp trạng thái. |
| Tư duy AI/RAG & Evaluation | **8,0 / 10** | Bitemporal, deterministic-first verification, group split chống leakage và ablation rất chặt; cần sửa nghịch lý cỡ mẫu theo cell. |
| Bảo mật & Kiến trúc môi trường | **7,5 / 10** | Ý tưởng tách **Public Studio Sandbox** (`ADR-05`) khỏi Production Admin MFA rất chuẩn; cần đồng bộ sơ đồ giữa `03` và `08`. |
| Khả thi kỹ thuật / Coding (với AI Agent) | **8,0 / 10** | Khi dùng AI Coding Agents cho scaffolding, CRUD/FastAPI, adapters, UI, CI và PoC scripts, khối lượng code hoàn toàn có thể nén rất nhanh nếu contract rõ. |
| Khả thi nút thắt phi-coding (8–12 tuần) | **5,5 / 10** | Review con người L2/L3 cho 1.000 case (~167h không được thay bằng LLM theo `REQ-EVAL-02`), tìm chuyên gia L3, quyền truy cập `vbpl.vn`/`toaan.gov.vn` và human diff review (`AC-15`) vẫn là giới hạn vật lý. |
| Độ sâu kiến trúc & Đặc thù luật VN | **6,5 / 10** | Khung logic đúng hướng, nhưng quá cô đọng (30–67 dòng/tệp), thiếu JSON/OpenAPI/DDL mẫu và các edge case văn bản VN. |
| Dự toán chi phí | **5,5 / 10** | Phép tính đúng nhưng giả định đầu vào thấp xa thực tế vận hành 3 môi trường cloud và model legal chất lượng cao. |

---

## 2. Điểm mạnh nổi bật

1. **Kỷ luật quản trị yêu cầu xuất sắc**: Không "bịa" kết quả thực nghiệm; ghi nhận trung thực các điểm nghẽn khó (`BLOCKER-01` đến `BLOCKER-04`) và khảo sát thực tế cổng nguồn Nhà nước ngay ở G0 (`vbpl.vn` trả 403, `congbobanan.toaan.gov.vn` timeout, `anle.toaan.gov.vn` chưa xác nhận tại [registers.md](g0/registers.md#L35-L43)).
2. **Mô hình dữ liệu thời gian và kiểm chứng trúng lõi Legal AI**:
   - Bitemporal `[valid_from, valid_to)` × `[recorded_from, recorded_to)` ([06-database-design.md](g0/06-database-design.md#L27-L33)) giải quyết đúng bài toán sửa đổi ghi nhận muộn, hiệu lực từng phần và truy xuất snapshot quá khứ.
   - Quy tắc *"Model judge không thể cho qua lỗi deterministic"* ([04-ai-rag.md](g0/04-ai-rag.md#L11)), cấm dùng draft/nguồn chưa xác minh làm căn cứ, giữ nguyên văn tiếng Việt khi trả lời tiếng Anh.
3. **Thiết kế Benchmark & Evaluation bài bản**: Group-based split theo họ văn bản/tình huống gốc/bản dịch để chống leakage, báo cáo micro + macro theo strata kèm Wilson CI / group bootstrap, bổ sung `citation coverage`, `false abstention`, `useful answer rate` ([07-benchmark-evaluation.md](g0/07-benchmark-evaluation.md#L18-L42)).
4. **Giải pháp bảo mật thực tế cho Studio công khai**: Tách hoàn toàn Public Studio Sandbox (dữ liệu public/synthetic, project/identity/quota/storage riêng, reset được) khỏi Production Admin có MFA (`ADR-05`, [registers.md](g0/registers.md#L26), [10-cloud-deployment.md](g0/10-cloud-deployment.md#L12-L13)).

---

## 3. Sáu nhóm vấn đề trọng tâm cần xử lý trước khi ký duyệt G0

### Vấn đề 1: Nghịch lý thống kê giữa 1.000 test case và Release Gate cấp `domain × task × risk`
- **Bằng chứng**: [05-data-engineering.md](g0/05-data-engineering.md#L9) khởi tạo **9 lĩnh vực**, [04-ai-rag.md](g0/04-ai-rag.md#L7) có **5–6 loại tác vụ**, nhân với **2–3 mức rủi ro** → tối thiểu **90–135 cell**. Trong khi đó, [07-benchmark-evaluation.md](g0/07-benchmark-evaluation.md#L21) chia 1.000 case thành 4 split (`train / dev / tuning / test`).
- **Phân tích toán học**: Giả sử tập holdout `test` chiếm 40–50% (~400–500 case), chia cho 90 cell thì mỗi cell trung bình chỉ còn **4–5 case**.
  - Với $n = 5$: ngay cả khi đúng 5/5 (100%), cận dưới Wilson CI 95% chỉ là **56,6%**; sai đúng 1 case tụt ngay xuống **80%** (rớt toàn bộ ngưỡng 90%–98%).
  - Để kiểm định ngưỡng `AC-05/06 ≥ 98%`, một lát cắt cần tối thiểu $n \ge 50$ mới cho phép sai 1 trường hợp.
- **Hệ quả**: Phần lớn cell sẽ rơi vào `INSUFFICIENT_EVIDENCE` ([07-benchmark-evaluation.md](g0/07-benchmark-evaluation.md#L42)) và làm treo G5/G7.
- **Hướng xử lý**: Phân tầng quy tắc gate trong `07` và `14`:
  - **Cấp Global & Cấp Domain** ($n$ đủ lớn): Áp toàn bộ ngưỡng định lượng `AC-01–07` kèm Wilson CI / bootstrap.
  - **Cấp Cell (`domain × task × risk`)**: Áp **0 lỗi S0/S1 + minimum floor thực tế** (ví dụ $n \ge 5–10$ trên holdout cho các cell mục tiêu, không đòi hỏi đơn lẻ từng cell nhỏ phải đạt ngưỡng thống kê 98%).

---

### Vấn đề 2: Dự toán chi phí chưa phản ánh đúng kiến trúc thực tế ([11-cost-estimation.md](g0/11-cost-estimation.md))
- **Model tham chiếu quá thấp so với yêu cầu chất lượng**: Dùng `Gemini 2.5 Flash-Lite` (\$0,10/\$0,40 mỗi triệu token) với `8.000 in + 1.200 out` cho Standard ([11-cost-estimation.md](g0/11-cost-estimation.md#L9-L14)). Pipeline 6 bước có claim generation + LLM Judge verification + re-verify ([04-ai-rag.md](g0/04-ai-rag.md#L7-L12)) muốn đạt `Correctness ≥ 90%`, `Faithfulness ≥ 95%`, `Temporal ≥ 98%` trên luật Việt Nam nhiều khả năng phải dùng model hạng trung/cao (**đắt gấp 10x–30x** Flash-Lite). Độ nhạy ở [L29](g0/11-cost-estimation.md#L29) mới thử **2x** là quá hẹp.
- **Bỏ quên chi phí 2 môi trường cloud tách biệt**: [10-cloud-deployment.md](g0/10-cloud-deployment.md#L11-L13) thiết kế **3 môi trường cloud độc lập** (`Staging`, `Production`, `Public Studio sandbox` có DB/storage/API riêng), nhưng bảng 3 kịch bản ([11-cost-estimation.md](g0/11-cost-estimation.md#L18-L27)) chỉ tính tiền **1 cụm Cloud SQL**. Riêng thêm DB cho Sandbox và Staging đã nhân chi phí DB lên **2x–3x** trừ khi có cơ chế tắt/scale-to-zero hoặc dùng DB serverless cho môi trường phụ.
- **Thiếu 2 khoản chi lớn ở giai đoạn dev/V1**:
  1. Chi phí LLM chạy **Benchmark, Ablation và Regression** (nhiều cấu hình × 1.000 case × Standard/Advanced/Judge);
  2. Chi phí LLM/OCR cho **Ingestion và trích xuất Deep Graph** trên toàn corpus.
- **Hướng xử lý**: Bổ sung trong `11-cost-estimation.md` 3 dòng rõ ràng: (a) kịch bản độ nhạy **5x–20x** đơn giá LLM (model hạng trung/reasoning), (b) tách cột chi phí **Prod + Sandbox + Staging** (kèm chính sách tắt Staging ngoài giờ test), (c) ngân sách một lần/định kỳ cho **Dev/Eval/Ingestion**.

---

### Vấn đề 3: Hiệu chỉnh lộ trình theo mô hình Solo + AI Coding Agents & phân pha lại PoC
- **Đánh giá lại năng lực triển khai với AI Coding Agents**:
  - Bảng effort `505–860 giờ` trong [12-roadmap-backlog.md](g0/12-roadmap-backlog.md#L7-L17) hiện đang gộp chung công việc lập trình truyền thống với công việc con người bắt buộc làm. Khi dùng AI Coding Agents, thời gian **viết code, tạo skeleton 16 repo, viết adapter, dựng UI, sinh test harness và chạy PoC scripts** giảm rất mạnh — biến phần kỹ thuật thành **khả thi tốt (~8,0/10)**.
  - **Tuy nhiên**, có **3 nút thắt phi-coding mà AI Coding Agent không thể thay thế** (theo chính Baseline):
    1. **Review con người cho 1.000 case L2/L3** (`REQ-EVAL-02`, `BLOCKER-02`): Baseline cấm dùng LLM tự gắn L2/L3; chỉ riêng con người thẩm định (~10 phút/case ≈ 167 giờ) và tìm chuyên gia L3 vẫn là nút thắt thời gian thực.
    2. **Con người đọc diff, hiểu sâu & tự debug (`RISK-08`, `AC-15`)**: Khi agent sinh code nhanh trên nhiều repo, băng thông review và kiểm soát chất lượng của chủ dự án mới là điểm giới hạn thực sự.
    3. **Nút thắt ngoại sinh về nguồn dữ liệu**: `SRC-02 (vbpl.vn)` đang trả `403`, `SRC-05 (congbobanan.toaan.gov.vn)` timeout — xử lý quyền khai thác/chặn bot không phụ thuộc tốc độ code.
- **Hai điểm cần sửa ngay trong [12-roadmap-backlog.md](g0/12-roadmap-backlog.md) và [03-sad.md](g0/03-sad.md)**:
  1. **Phân pha lại `POC-01–11`**: Hiện bảng roadmap ([12-roadmap-backlog.md](g0/12-roadmap-backlog.md#L10)) dồn **toàn bộ 11 PoC vào Tuần 3–4**, mâu thuẫn với chính [L21](g0/12-roadmap-backlog.md#L21) (nói `POC-09/10` chỉ chạy ở staging sau khi có prototype tối thiểu). Cần xếp lại theo đúng phụ thuộc gate:
     - *Pha G1*: `POC-01`, `POC-02`, `POC-11` (nguồn, parser/OCR, đo throughput review thực tế).
     - *Pha G2*: `POC-03` (retrieval/embedding/rerank).
     - *Pha G3*: `POC-04`, `POC-05`, `POC-07` (bitemporal, graph, verification).
     - *Pha G4*: `POC-06`, `POC-08` (model gateway, Standard vs Advanced).
     - *Pha G6*: `POC-09`, `POC-10` (cloud load/cost/restore, security/tenant isolation).
  2. **Tối ưu 16 polyrepo cho AI Coding Agent**: Nếu giữ `DEC-07` (16 repo private riêng), AI Coding Agent sẽ giảm hiệu quả khi thiếu ngữ cảnh liên repo và tốn công đồng bộ `lvn-law-contracts`. Cần bổ sung quy chuẩn **local meta-workspace** (checkout các repo V1 cùng cấp thư mục + script sync OpenAPI/event contracts tự động) vào `03-sad.md` và `13-ai-coding-agent-guidelines.md`.

---

### Vấn đề 4: Chưa tách tầng "Deep Graph" và "Rule Engine"
- **Knowledge Graph ([06-database-design.md](g0/06-database-design.md#L37))**: Đang gộp chung 2 loại đồ thị có độ khó và chi phí kiểm duyệt hoàn toàn khác nhau:
  - *Tầng 1 — Structural / Citation Graph* (`modifies`, `replaces`, `repeals`, `guides`, `corrects`, `references`): trích xuất deterministic / bán tự động chính xác cao, làm được toàn corpus.
  - *Tầng 2 — Deontic / Normative Graph* (`Subject`, `Right`, `Obligation`, `Condition`, `Exception`): trích xuất ngữ nghĩa phức tạp, dễ nhiễu, đòi hỏi chi phí LLM & duyệt thủ công lớn.
  - **Khuyến nghị**: Tách rõ tiêu chí `AC-12` theo 2 tầng ở G1 (Tầng 1 phủ toàn corpus; Tầng 2 triển khai đầy đủ ontology + pipeline + kiểm thử chuẩn hóa trên tập văn bản lõi có gold-set đo precision/coverage, sau đó mở rộng dần).
- **Rule Engine ([04-ai-rag.md](g0/04-ai-rag.md#L10-L11), [registers.md](g0/registers.md#L68-L70))**: Chưa phân biệt giữa **Meta-legal Rule Engine** (quy tắc hiệu lực, thứ bậc văn bản, nguyên tắc áp dụng văn bản chuyên ngành/ban hành sau theo Luật 64/2025/QH15 — khả thi cao cho V1) và **Substantive Legal Rule Engine** (mã hóa điều kiện pháp lý nội dung cho từng ngành luật), cũng chưa định hướng format biểu diễn rule (JSONLogic, OPA/Rego, Datalog hay Python DSL).

---

### Vấn đề 5: Độ sâu đặc tả còn mỏng và thiếu các edge case đặc thù của pháp luật Việt Nam
- Cả 14 tệp hiện chỉ dài **29–78 dòng**, thiên về tóm tắt quản trị; để AI Coding Agent triển khai chính xác theo đúng [13-ai-coding-agent-guidelines.md](g0/13-ai-coding-agent-guidelines.md#L7) (tránh agent tự suy diễn lệch hợp đồng giữa các repo), cần bổ sung trước/ngay sau G0:
  - **Contract mẫu cốt lõi**: JSON schema cho `POST /v1/answers`, SSE events (`GET /v1/answers/{id}/events`), error payload chuẩn, và 5 event nội bộ (`CandidateVerified.v1`, `SnapshotReady.v1`, `EvidenceQuery.v1`, `ModelRequest.v1`, `GateReport.v1`), kèm danh mục API của Studio/Account/Ingestion.
  - **Đặc thù cấu trúc pháp luật Việt Nam trong [06-database-design.md](g0/06-database-design.md)**:
    - Chèn điều/khoản khi sửa đổi (`Điều 5a`, `Khoản 2a`), **1 luật sửa nhiều luật** (omnibus amendment), và sửa/bãi bỏ một cụm từ trong khoản → cần thực thể `AMENDMENT_OPERATION` / `CONSOLIDATION_LINEAGE` nối văn bản sửa đổi với phiên bản điều khoản bị sửa.
    - **Ràng buộc bitemporal cụ thể**: Ghi rõ thiết kế `EXCLUDE USING gist` trên `(canonical_key, scope, valid_range WITH &&, recorded_range WITH &&)` thay vì chỉ mô tả bằng văn xuôi.
    - **Lịch sử địa giới hành chính**: Thiết kế bảng `jurisdiction_lineage` theo `valid_time` (sáp nhập, chia tách, đổi tên tỉnh/huyện/xã) thay vì chỉ ghi "ánh xạ tên cũ".
    - **Tìm kiếm tiếng Việt trên PostgreSQL FTS** ([06-database-design.md](g0/06-database-design.md#L45)): PostgreSQL mặc định **không có bộ tách từ tiếng Việt**; cần nêu rõ ứng viên kỹ thuật cụ thể (`unaccent` + `pg_trgm` / tiền xử lý word segmentation / ParadeDB BM25 vs OpenSearch + `analysis-vi`).
  - **Trade-off UX về độ trễ**: Quy định *"Chỉ event cuối mới mang nội dung kết luận"* ([04-ai-rag.md](g0/04-ai-rag.md#L27)) bảo đảm an toàn tuyệt đối, nhưng khiến thời gian chờ hiển thị câu trả lời dài (15–60+ giây). Cần phản ánh rõ trong [09-ui-ux.md](g0/09-ui-ux.md#L17) (tách metric `time-to-first-progress-event` và `time-to-verified-answer`, thiết kế progress UX giữ chân người dùng và nút hủy rõ ràng).

---

### Vấn đề 6: Năm điểm không nhất quán trực tiếp giữa các tài liệu

| # | Mâu thuẫn / Điểm lệch | Vị trí cụ thể | Cách sửa |
|---|---|---|---|
| 1 | **Số lượng ADR lệch nhau** | [03-sad.md](g0/03-sad.md#L65) chỉ liệt kê `ADR-01`–`04`, bỏ sót `ADR-05 (Studio sandbox)` và `ADR-06 (Evaluation policy)` có trong [registers.md](g0/registers.md#L18-L27) | Cập nhật `03-sad.md` đủ `ADR-01`–`06` (nhấn mạnh `ADR-01` và `ADR-05` chốt tại G0). |
| 2 | **Topology sơ đồ kiến trúc lệch nhau** | [03-sad.md](g0/03-sad.md#L10-L21) vẽ `Web/Studio` gọi thẳng 3 service (thiếu Edge, Auth, Evaluation, Studio Prod); [08-security-threat-model.md](g0/08-security-threat-model.md#L8-L17) vẽ qua `Edge/Auth -> API ứng dụng` và tách 2 nhánh Studio | Thống nhất một sơ đồ container chuẩn (rõ Edge/Gateway/BFF, 2 nhánh Studio, Evaluation, Storage). |
| 3 | **Khẳng định SHA-256 nhưng không ghi mã băm** | [README.md](g0/README.md#L30) nói SHA-256 Baseline khớp bản đầu vào nhưng không lưu giá trị | Ghi trực tiếp chuỗi `d06b7ace9d5252c1e09ab5e79ad4d34198f8fc2bfd1ebe91b9b85d3d2e4e4a03` vào `README.md`. |
| 4 | **Thiếu Age Gate trên giao diện** | [02-srs.md](g0/02-srs.md#L9) và `REQ-SEC-09` áp giới hạn tuổi cho Guest/AI, nhưng [09-ui-ux.md](g0/09-ui-ux.md#L7-L13) không có luồng khai báo/chặn tuổi | Bổ sung luồng age gate / consent notice cho Guest và `/account` trong `09-ui-ux.md`. |
| 5 | **Phạm vi Agent Mutation ở V1 chưa rõ** | [02-srs.md](g0/02-srs.md#L22) và [04-ai-rag.md](g0/04-ai-rag.md#L25) nói về approval cho mutation của agent, nhưng chưa nói V1 có cho phép mutation ở luồng nào không | Khẳng định rõ: người dùng cuối V1 **read-only**; cơ chế mutation + approval chỉ áp dụng cho công cụ quản trị/sandbox hoặc tác vụ ghi tương lai. |

---

## 4. Đánh giá chi tiết từng tệp (17/17 tệp)

| Tệp | Kích thước | Mức sẵn sàng G0 | Đề xuất cải thiện cụ thể |
|---|---:|---|---|
| [README.md](g0/README.md) | 42 dòng · 3,8 KB | Rất tốt | Ghi rõ chuỗi SHA-256 của Baseline và bảng ký duyệt `v0.2`. |
| [01-prd.md](g0/01-prd.md) | 39 dòng · 4,5 KB | Khá ổn | Bổ sung tiêu chí hoàn tất tối thiểu cho bản internal preview khi `BLOCKER-01/02` chưa đóng. |
| [02-srs.md](g0/02-srs.md) | 39 dòng · 4,8 KB | Cần bổ sung | Bổ sung nhóm endpoint cho Studio/Account/Ingestion, cấu trúc lỗi chuẩn, và làm rõ Agent V1 read-only cho end-user. |
| [03-sad.md](g0/03-sad.md) | 67 dòng · 5,6 KB | Cần sửa | Đồng bộ sơ đồ với `08`, thêm `ADR-05/06`, rõ API Gateway/BFF, transport/outbox, và chiến lược meta-workspace cho 16 repo. |
| [04-ai-rag.md](g0/04-ai-rag.md) | 42 dòng · 5,9 KB | Khá tốt | Phân tách Meta-legal vs Substantive Rule Engine; ghi rõ trade-off latency của verification gate. |
| [05-data-engineering.md](g0/05-data-engineering.md) | 42 dòng · 5,0 KB | Khá tốt | Thêm phương án dự phòng khi `SRC-02` trả 403 / `SRC-05` timeout; làm rõ xử lý công văn hướng dẫn & lịch sử địa giới. |
| [06-database-design.md](g0/06-database-design.md) | 51 dòng · 5,3 KB | Cần làm sâu | Bổ sung `AMENDMENT_OPERATION`, `jurisdiction_lineage`, constraint `EXCLUDE USING gist`, xử lý `Điều 5a`, tokenizer tiếng Việt cho FTS, tách 2 tầng Graph. |
| [07-benchmark-evaluation.md](g0/07-benchmark-evaluation.md) | 50 dòng · 7,5 KB | Rất tốt (sửa 1 điểm lớn) | Sửa quy tắc thống kê cấp cell để không bị kẹt `INSUFFICIENT_EVIDENCE` khi chia 1.000 case cho 90+ cell. |
| [08-security-threat-model.md](g0/08-security-threat-model.md) | 52 dòng · 6,1 KB | Tốt | Đồng bộ sơ đồ với `03`; bổ sung kịch bản indirect prompt injection từ văn bản nguồn công khai/bản án. |
| [09-ui-ux.md](g0/09-ui-ux.md) | 48 dòng · 4,5 KB | Cơ bản | Thêm luồng Age Gate, UX chờ xác minh lâu, và định nghĩa rõ giới hạn thao tác write trên Studio sandbox. |
| [10-cloud-deployment.md](g0/10-cloud-deployment.md) | 34 dòng · 4,6 KB | Tốt | Quy định rõ chính sách tắt/scale-to-zero cho Staging & Sandbox để kiểm soát chi phí. |
| [11-cost-estimation.md](g0/11-cost-estimation.md) | 37 dòng · 4,2 KB | Cần làm lại mô hình giá | Cộng chi phí Staging + Sandbox, độ nhạy model 5x–20x, và dự toán riêng chi phí Eval/Ablation + Ingestion/Graph LLM. |
| [12-roadmap-backlog.md](g0/12-roadmap-backlog.md) | 41 dòng · 5,0 KB | Cần sửa | Tách rõ **effort Agent-assisted engineering** vs **effort Human review/approval**; phân pha lại `POC-01–11` theo từng gate thay vì dồn hết vào Tuần 3–4. |
| [13-ai-coding-agent-guidelines.md](g0/13-ai-coding-agent-guidelines.md) | 29 dòng · 3,5 KB | Khá ổn | Bổ sung mẫu Task Contract chuẩn, DoD checklist và quy trình đồng bộ contract/PR xuyên nhiều repo. |
| [14-acceptance-test-plan.md](g0/14-acceptance-test-plan.md) | 78 dòng · 9,1 KB | Rất tốt | Các tình huống `TST-02.1`–`11.1` rất sắc nét; cập nhật quy tắc cell gate khớp với chỉnh sửa của `07`. |
| [registers.md](g0/registers.md) | 89 dòng · 10,0 KB | Xuất sắc | Nâng rủi ro chặn kỹ thuật từ cổng nguồn (`SRC-02/05`) thành rủi ro theo dõi ưu tiên riêng. |
| [rtm.md](g0/rtm.md) | 153 dòng · 19,1 KB | Xuất sắc | Đạt chuẩn G0, chỉ cần giữ đồng bộ nếu có change request sau G0. |

---

## 5. Kế hoạch hành động nâng cấp G0 lên `v0.2`

### P0 — Sửa ngay trước khi ký duyệt G0 (ưu tiên cao nhất)
- [ ] Khắc phục đủ **5 điểm lệch chéo** (mục 3 — Vấn đề 6): `ADR-05/06` trong `03-sad.md`, đồng bộ sơ đồ `03` vs `08`, ghi chuỗi SHA-256 vào `README.md`, thêm Age Gate vào `09-ui-ux.md`, làm rõ phạm vi Agent mutation V1.
- [ ] Phân pha lại **`POC-01–11`** theo đúng gate và tách cột **Agent-assisted engineering** vs **Human review/approval** trong `12-roadmap-backlog.md`.
- [ ] Sửa quy tắc thống kê **Global/Domain vs Cell** trong `07-benchmark-evaluation.md` và `14-acceptance-test-plan.md` để tháo gỡ nghịch lý cỡ mẫu.
- [ ] Cập nhật **`11-cost-estimation.md`** bổ sung Staging + Sandbox, độ nhạy đơn giá LLM 5x–20x, và dự toán chi phí Eval/Ablation + Ingestion LLM.

### P1 — Chốt quyết định kiến trúc & phạm vi để tránh sa lầy ở G1–G3
- [ ] Chốt tách 2 tầng **Graph** (Structural toàn corpus vs Deontic trên tập văn bản lõi) và **Rule Engine** (Meta-legal ưu tiên V1) vào `04-ai-rag.md` & `06-database-design.md`.
- [ ] Chốt chiến lược **meta-workspace** (nếu giữ 16 polyrepo theo `DEC-07`) để AI Coding Agent có đủ ngữ cảnh xuyên repo và tự động kiểm tra tương thích contract.
- [ ] Lên phương án giải quyết sớm 2 nút thắt phi-coding ngay từ Tuần 1–2: kênh truy cập hợp lệ cho `SRC-02/05` và nguồn lực chuyên gia cho `L3` (`BLOCKER-02`).

### P2 — Bổ sung độ sâu đặc tả để AI Coding Agent thực thi chính xác ngay sau G0
- [ ] Bổ sung JSON schema mẫu cho API/SSE/Event contracts trong `02-srs.md` và `03-sad.md` (làm đầu vào trực tiếp cho `lvn-law-contracts`).
- [ ] Bổ sung DDL/constraint mẫu cho bitemporal (`EXCLUDE USING gist`), `AMENDMENT_OPERATION`, `jurisdiction_lineage` và chiến lược phân tích tiếng Việt trong `06-database-design.md`.
- [ ] Bổ sung **Task Contract Template** và **Cross-repo PR Checklist** vào `13-ai-coding-agent-guidelines.md`.
