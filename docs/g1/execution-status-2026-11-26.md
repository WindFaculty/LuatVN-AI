# Báo cáo thực thi G1

> **Bản mới hơn ngày 27/11/2026 (`G1-REAL-20261127-01`):** Xem **[Báo cáo nghiệm thu G1 (27/11)](g1-exit-report-2026-11-27.md)** và **[Bằng chứng kiểm toán 27/11](evidence/g1-real-audit-2026-11-27.md)** (đã mở public repo, đo snapshot catalog, audit 36 mẫu đa định dạng, 187 bản ghi graph 18 họ, PG 18.6 sizing và cập nhật `ADR-02/03/06/07`).

Cập nhật ngày 27/11/2026 · Run `G1-REAL-20261126-02` · Nhánh `docs/g1-execution-plan`, commit nền `72218a681edf8de47d777825dc5fc9389077e6aa` · Contract `0.2.1-draft` · Chủ dự án Trần Xuân Khoa

**Pilot thật đã chạy. Gate G1 vẫn `BLOCKED`.** Quyền tải mẫu và xử lý nội bộ đã được xác nhận theo G1-D01. Lô chọn trước có 45 họ, 48 phiên bản ứng viên, 70 tệp theo SHA-256 và 27 ca chờ review. Các điều kiện còn mở gồm mẫu số catalog, gold audit độc lập, kiểm chứng người thật và nghiệm thu của chủ dự án. [Quyết định G1-D01](evidence/owner-decision-g1-d01-2026-11-26.md) · [Kết quả và lệnh chạy lại](evidence/real-pilot-2026-11-26.md)

## G1-T01 đến T13

| Task | Trạng thái và bằng chứng | Điều kiện tiếp theo |
|---|---|---|
| T01 · TST-01 | `PASS_LOCAL`. 25 digest G0, 123 ID RTM, workspace smoke và contract pin. 51 kiểm thử Python, hai frontend smoke và validator hợp đồng thành công. | Xác nhận hosted CI hoặc phương án kiểm tương đương được chủ dự án duyệt. |
| T02 · Quyền nguồn | `PASS_LOCAL`. Adapter dùng thời gian hiện tại, kiểm lại sau mỗi lần chờ thử lại và dừng khi registry thay đổi. Lô nội bộ dùng registry theo đúng URL được pin. | Duy trì registry theo lô. Catalog tự động dùng quyết định riêng. |
| T03 · POC-01 | `PASS_SAMPLE`. 50 bản ghi nguồn, 45 họ, 48 phiên bản ứng viên, 70 tệp riêng theo SHA-256. 10 phân đoạn intake đã chạy. | Có catalog hoặc export được phép và mẫu số theo phạm vi cần nghiệm thu. |
| T04 · Taxonomy | `CANDIDATE`. Revision `g1-taxonomy-0.2.0-candidate` có 5 họ ở mỗi nhóm, mapping loại và cơ quan. | Chủ dự án duyệt taxonomy và xác định các strata chưa đo. |
| T05 · Gold extraction | `CANDIDATES_READY`. Bộ chọn có 36 tệp ứng viên từ 70 tệp đã lưu. Có PDF, DOC và DOCX. | Khóa gold thật, số mẫu audit độc lập theo format, mẫu bảng và nhánh lỗi. |
| T06 · POC-02 | `OBSERVED`. Đã parse 64 PDF, thử OCR 8 trang và trích một DOCX. Có đường chạy tái hiện và đo theo từng tệp. | Chạy audit có người duyệt gold và đo ngưỡng G1-03. Năm tệp DOC chưa có kết quả trích. |
| T07 · TST-02.1 | `PASS_LOCAL`. Fixture idempotency/retry/quarantine và kiểm hạn quyền qua. Intake thật có 82 occurrences khớp hash. Reconcile chạy lại khớp kết quả. | Kiểm parser isolation và lỗi định dạng ở audit thật. |
| T08 · Temporal | `PASS_FIXTURE`. PostgreSQL 18.6 qua kiểm biên thời gian, provenance, overlap, rollback và outbox replay. | Kiểm ngữ nghĩa temporal theo G3. |
| T09 · Graph | `CANDIDATES_READY`. 18 họ và 10 quan hệ ứng viên. Fixture schema đã qua. | Duyệt anchor, scope, rubric và mẫu số. Precision/recall pipeline đo ở G3. |
| T10 · Sizing | `OBSERVED`. Đo 173.803.902 byte raw duy nhất, 4.673.280 byte chuẩn hóa và 4.453 chunk. Khôi phục toàn bộ chunk ở PostgreSQL tạm và đối chiếu fingerprint. | Cập nhật ngoại suy theo mẫu số và tăng trưởng catalog. |
| T11 · POC-11 | `BLOCKED_HUMAN`. 27 ca trên 27 nhóm. Có phiếu review, 18 `PENDING_L2`, 9 `PENDING_L3`, 0 ca xác minh. | Ghi review thật theo phiếu. Dùng active minutes và công chuẩn bị để đo effort. |
| T12 · ADR-06 | `PROPOSED`. Đã xác minh cấu trúc nhóm của lô. Log người thật và effort còn trống. | Chốt feasibility và phương án chuyên gia sau POC-11. |
| T13 · Báo cáo gate | `REPORT_AVAILABLE`. Hồ sơ quyền, provenance, kết quả thật, replay và RTM delta đã tập hợp. | Chủ dự án xử lý các điều kiện A–G và ký gate. |

## Điều kiện nghiệm thu

| Check | Bằng chứng và trạng thái |
|---|---|
| G1-AC-A | `PARTIAL`. D01 mở lô nội bộ. Mẫu số catalog trong phạm vi nghiệm thu còn `UNKNOWN`. |
| G1-AC-B | `PARTIAL`. Đã có mapping và đủ 5 họ mỗi nhóm pilot. Taxonomy và độ phủ theo strata cần chủ dự án chốt. |
| G1-AC-C | `OBSERVED`. Parser/OCR và ingest có dữ liệu thật. Gold audit, ngưỡng theo format và review lỗi nghiêm trọng còn mở. |
| G1-AC-D | `PARTIAL`. Migration fixture đã qua. 18 họ graph đang chờ gold, locator và mẫu số theo loại. |
| G1-AC-E | `OBSERVED`. Sizing raw, text, PostgreSQL và restore đã đo trên lô. Ngoại suy toàn corpus chờ catalog. |
| G1-AC-F | `BLOCKED_HUMAN`. 0 L2 và 0 L3 xác minh. Effort và phân bổ thực vẫn chờ POC-11. |
| G1-AC-G | `IN_PROGRESS`. Báo cáo và local checks đã có. Hosted branch chưa có lượt cho commit nền, owner chưa sign-off. |

## Quyết định còn mở và lịch tiếp tục

- **ADR-02 `PROPOSED`.** Lô pilot đã đo raw trên filesystem, import/index PostgreSQL và backup/restore. Chốt relational/object sau khi duyệt bằng chứng và giả định tăng trưởng. Vector/search, temporal/graph và cloud theo PoC ở các pha tương ứng.
- **ADR-03 `PROPOSED`.** Dùng pypdf và PDFium/Tesseract `vie` làm đối chứng local. Duyệt gold và cấu hình audit trước khi quyết định đường tự động, review và quarantine theo format.
- **ADR-06 `PROPOSED`.** Đo người thật và chốt feasibility, sàn metric/cell, rubric và phân bổ thực. [Đề xuất ADR-06](../adr/ADR-06-evaluation-protocol.md)

GitHub chưa có workflow run cho commit nền nhánh. Lượt `45816772853` trên `main` bị chặn trước bước chạy job. Lưu kiểm chứng local làm đầu vào cho quyết định của chủ dự án về CI. [GitHub Actions](https://github.com/WindFaculty/LuatVN-AI/actions/runs/45816772853) · [Kiểm thử cục bộ trước lần mở quyền](evidence/local-verification-2026-11-26.md)

Bước review bắt đầu từ `build/g1/G1-REAL-20261126-02/poc11/review-worksheet.md`. Chủ dự án có thể bắt đầu với ca L2 tra cứu và hiệu lực để xác định effort thực, sau đó chốt lịch audit còn lại. Các ca L3 giữ pending. Chỉ bàn giao G2 sau quyết định gate cùng snapshot dev, qrels, canonical anchors và phạm vi quyền. [Handoff](06-backlog-gate.md#6-bàn-giao-sang-g2)
