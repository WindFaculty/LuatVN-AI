# Báo cáo nghiệm thu G1 (G1 Exit Report)

- **Gate Run ID**: `G1-REAL-20261127-01`
- **Ngày cập nhật**: `2026-11-27` (Cutoff `2026-11-27T00:23:31.340392+07:00`)
- **Nhánh / Commit nền**: `docs/g1-execution-plan` (nền `72218a681edf8de47d777825dc5fc9389077e6aa`)
- **Chủ dự án**: Trần Xuân Khoa
- **Phiên bản ghim**: Contract `0.2.1-draft` · Taxonomy `g1-taxonomy-0.2.0-candidate` · Schema graph `graph-gold-draft.schema.json` · Quyền nguồn `G1-D01-20261127-STATUTORY-R01` (registry mặc định repo vẫn `g1-rights-pending-v1` fail-closed)
- **Hosted GitHub Actions CI**: **`PASS`** (`workspace` + `contracts` đều `success` tại lượt [Run 45869534740](https://github.com/WindFaculty/LuatVN-AI/actions/runs/45869534740) trên [PR #1](https://github.com/WindFaculty/LuatVN-AI/pull/1), commit `4976a6fe019d452b08b0bd2014b2af1878bd4aa5`; repo `WindFaculty/LuatVN-AI` đã chuyển `PUBLIC` ngày 27/11/2026)

> **KẾT LUẬN GATE G1 (`VERDICT`): `BLOCKED` (Chờ kiểm chứng người thật L2 và ký duyệt của chủ dự án).**  
> Toàn bộ hạng mục kỹ thuật, chuẩn hóa dữ liệu thật đa định dạng, kiểm thử bitemporal trên PostgreSQL 18.6, 187 bản ghi graph 18 họ hợp lệ schema, đo dung lượng 5 năng lực và chuẩn bị 27 ca `POC-11` đã hoàn thành trung thực; **không** tự bịa đặt kết quả review L2/L3 hoặc tự ký thay chủ dự án.

---

## 1. Bảng tổng hợp nhiệm vụ `G1-T01` đến `G1-T13`

| ID | Nội dung | Trạng thái | Bằng chứng chính | Còn lại (nếu có) |
|---|---|---|---|---|
| `G1-T01` | Verify repo/contracts/G0 hashes + public CI | `PASS` | `verify-workspace.py --smoke` (`25` G0 digests, `123` RTM IDs, `10` component, `49` Python + `2` TS tests), kiểm contract cục bộ, `WindFaculty/LuatVN-AI` chuyển `PUBLIC` và [CI Run 45869534740](https://github.com/WindFaculty/LuatVN-AI/actions/runs/45869534740) (`workspace` + `contracts` `success`) | Hoàn tất |
| `G1-T02` | Source/action registry deny-by-default & quyền G1 | `PASS` | `source_rights.py` per-operation scope + SQLite cross-process rate limiter; [quyết định quyền luật định](evidence/owner-decision-g1-d01-2026-11-27.md) | Mở rộng nguồn `SRC-02`, `SRC-04..07` ở G2 |
| `G1-T03` | Catalog snapshot & dedup trên nguồn thật | `PASS_SAMPLE_AND_PARTIAL_CATALOG` | `50` bản ghi nguồn, `45` họ, `48` version, `70` tệp duy nhất; `SRC-03` (`48.101` all-time, `195` Luật + `1.441` Nghị định 2020–cutoff), `SRC-01` (`2.673` trang) | Đếm khử trùng toàn bộ 2020–cutoff trên `SRC-01`/`SRC-03` thực hiện tại G2 bulk ingest |
| `G1-T04` | Taxonomy revision, sub-domain & gap register | `CANDIDATE_READY` | `g1-taxonomy-0.2.0-candidate` với sub-domain đủ `45` họ (`9` lĩnh vực × `5`) và `9` khoảng trống V1 | Chủ dự án duyệt chính thức |
| `G1-T05` | Bộ mẫu trích xuất thật & ma trận đa định dạng | `LOCKED_AND_AUDITED` | Manifest `poc02-audit-manifest.json` khóa trước cho `36` mẫu thật (`10 pdf_text`, `8 pdf_scan`, `6 html`, `6 doc_docx`, `6 table_appendix`), `7 tuning / 29 audit` | Chủ dự án đối chiếu gold trên `gold-review-sheet.md` |
| `G1-T06` | Đối chứng Parser/OCR, anchor/table & quarantine | `OBSERVED_PASS` | [Kiểm toán đa định dạng](evidence/g1-real-audit-2026-11-27.md#3-kiểm-toán-đa-định-dạng--ocr-poc-02--36-mẫu-thật-tách-tuningaudit): `pdfplumber` (`360` bảng/`9.153` ô), Tesseract `vie` (`16` trang/`32` ảnh, conf `91,19`), DOCX parity `31/31`, `6/6` quarantine tests PASS | Gold human xác nhận CER/precision/recall chính thức & bộ chuyển đổi `.doc` cô lập ở G2 |
| `G1-T07` | Idempotency, checkpoint, retry & security fixtures | `PASS` | `TST-02.1` SQLite retry/concurrency + `6/6` security/quarantine tests (injection, oversize, malformed container, anomaly `1900-01-01`) PASS | Duy trì hồi quy G2+ |
| `G1-T08` | Bitemporal migration candidate & PG18 replay | `PASS` | PostgreSQL `18.6` PASS `temporal-example.test.sql` + `temporal-fixture.sql` + nạp & restore MD5 `4.436` chunks | Kiểm thử ngữ nghĩa ở G3 (`POC-04`) |
| `G1-T09` | Graph ontology gold candidate 18 họ (2 tầng) | `CANDIDATES_READY` | **`187` bản ghi hợp lệ `100%` schema** (`186 candidate`, `1 conflict`) phủ `18` họ / `9` lĩnh vực (`90` normative + `97` structural) | Chủ dự án duyệt rubric & anchor trước audit G3 |
| `G1-T10` | Storage sizing thực đo 5 năng lực & Low/Base/High | `MEASURED_ON_PG18` | PG `18.6` đo thật raw (`165,75 MiB`), chunks (`4.436`), heap+Btree (`6,12 MiB`), FTS GIN (`1,36 MiB`), Graph tables (`0,16 MiB`, 2-hop `40,54ms`), vector payload bounds & `43,74 / 354,98 / 1.217,61 GiB` projections | Bổ sung ANN RAM & cloud sizing ở G2/G6 |
| `G1-T11` | Chuẩn hóa 27 ca `POC-11` (chờ người thật) | `BLOCKED_HUMAN` | `27` cases / `27` groups (`9×3`) kèm locator & trích đoạn thật; `18 PENDING_L2`, `9 PENDING_L3`, `0` fabricated | **Chủ dự án tự review 18 ca L2** theo phiếu tại `build/g1/G1-REAL-20261127-01/poc11/review-worksheet.md` |
| `G1-T12` | Feasibility matrix, effort & ADR-06 proposal | `PROPOSED_WITH_SENSITIVITY` | [ADR-06](../adr/ADR-06-evaluation-protocol.md) tính toán rõ sàn `900+` groups & bảng độ nhạy `5–20 phút/ca` trên quỹ `30–40h/tuần` | Cập nhật `median/P90` sau khi chủ dự án chấm L2 |
| `G1-T13` | Tổng hợp Gate G1 Exit Package | `PUBLISHED_PENDING_SIGNOFF` | Hồ sơ này + [Audit 27/11](evidence/g1-real-audit-2026-11-27.md) + `ADR-02/03/06/07` | Chủ dự án review và ký Gate G1 |

---

## 2. Trạng thái Điều kiện Nghiệm thu `G1-AC-A` đến `G1-AC-G`

| Check | Điều kiện | Trạng thái | Tóm tắt căn cứ |
|---|---|---|---|
| `G1-AC-A` | Quyền từng action & catalog denominator | `PARTIAL_READY` | Quyền luật định G1 cho `SRC-01`/`SRC-03` đã xác nhận; số liệu `SRC-03` (`48.101`; Luật/Nghị định 2020–2026 chính xác) và `SRC-01` (`2.673` trang) đã đo; mẫu số khử trùng toàn bộ 2 nguồn giữ `UNKNOWN_PENDING_G2` |
| `G1-AC-B` | Taxonomy revision, mapping & strata gaps | `CANDIDATE_READY` | `g1-taxonomy-0.2.0-candidate` phủ 9 lĩnh vực × 5 họ + sub-domain + 9 gaps; chờ chủ dự án chốt |
| `G1-AC-C` | `POC-02` mẫu thật, đa định dạng & quarantine | `OBSERVED_PASS` | 36 mẫu thật trên cả 5 tầng định dạng, khóa manifest trước khi chạy, `6/6` quarantine tests PASS; chờ gold người thật |
| `G1-AC-D` | Temporal migration + Graph 18 họ đủ 2 tầng | `CANDIDATE_READY` | PG 18.6 temporal PASS; `187` bản ghi graph 18 họ (đủ structural & normative) hợp lệ 100% JSON Schema; chờ duyệt gold & rubric G3 |
| `G1-AC-E` | Storage sizing thực đo & ADR từng phần | `PASS` | Đã đo PG 18.6 thực tế + dự báo Low/Base/High trong [ADR-02](../adr/ADR-02-storage-and-indexing.md) |
| `G1-AC-F` | `POC-11` human review, effort & ADR-06 | `BLOCKED_HUMAN` | Dữ liệu & phiếu 27 ca sẵn sàng (`0` bịa đặt); còn chờ 18 review L2 thật của chủ dự án |
| `G1-AC-G` | Báo cáo Gate, RTM/ADRs & CI trung thực | `READY_FOR_OWNER_SIGNOFF` | Hồ sơ Gate + `ADR-02/03/06/07` + local checks + [GitHub Actions CI Run 45869534740](https://github.com/WindFaculty/LuatVN-AI/actions/runs/45869534740) (`workspace` & `contracts` `PASS`); chỉ còn chữ ký gate của chủ dự án |

---

## 3. Quyết định ADR, RTM Delta và S0/S1 Known Issues

- **Trạng thái ADR**: [ADR-02](../adr/ADR-02-storage-and-indexing.md) (`PROPOSED` phần relational/object/FTS/projections), [ADR-03](../adr/ADR-03-parser-ocr-pipeline.md) (`PROPOSED` phần parser/OCR/quarantine), [ADR-06](../adr/ADR-06-evaluation-protocol.md) (`PROPOSED` chờ log L2 thật), [ADR-07](../adr/ADR-07-monorepo-and-demo.md) (`ACCEPTED` + bổ sung chuyển `WindFaculty/LuatVN-AI` sang `PUBLIC` ngày 27/11/2026).
- **RTM & G0 Hash Integrity**: **`0` thay đổi** trên toàn bộ `25` tệp G0 v0.2.1 khóa SHA-256 (`docs/g0/g0-v0.2.1.sha256` & Baseline v1.0) và toàn bộ `packages/contracts/contracts/*`; `123/123` ID RTM khớp tuyệt đối giữa Baseline v1.0, [Baseline v1.1](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.1.md) và [RTM G0](../g0/rtm.md).
- **Known Issues (`S0/S1` = `0` trên verified channel)**:
  1. Legacy `.doc` (`5` tệp) chưa có converter cục bộ (`LibreOffice`/`antiword`), được định tuyến an toàn sang `NEEDS_CONVERTER_OR_REVIEW` ở G2.
  2. DOM `SRC-01` cần extractor metadata riêng ở G2 (hiện đạt `0,83` trường/trang do phần lớn mẫu HTML là `SRC-01`).
  3. Lô 50 văn bản mẫu chưa gặp tệp `.xlsx` thật (`0` native `.xlsx`, đã xác minh `openpyxl` bằng fixture kỹ thuật).
  4. `59/2020/QH14` trên `SRC-01` ghi `01/01/1900` vs `01-01-2021` trên `SRC-03` (đã cách ly sang `conflict`).

---

## 4. Hành động của Chủ dự án để đóng Gate G1 và chuyển sang G2

1. **Chấm 18 ca L2 trong `POC-11`** bằng `build/g1/G1-REAL-20261127-01/poc11/review-worksheet.md` → ghi vào `human-reviews.json` và chạy lại `review_pilot.py` để lấy `median/P90` thời gian thực (giữ 9 ca L3 ở `PENDING_L3`).
2. **Duyệt `g1-taxonomy-0.2.0-candidate`**, xác nhận phạm vi gold extraction (`poc02/gold-review-sheet.md`) và graph rubric (`graph-audit-scope-manifest.json`).
3. **Ký duyệt Gate G1** (chấp nhận hoàn tất G1 hoặc mở G2 song song có kiểm soát ngoại lệ cho `.doc` converter & `L3` expert timeline).

| Hạng mục | Ký / Xác nhận | Ngày |
|---|---|---|
| Phê duyệt Gate G1 (Trần Xuân Khoa) | `PENDING_OWNER_SIGN_OFF` | — |
