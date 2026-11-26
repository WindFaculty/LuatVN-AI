# ADR-02 Lưu trữ, chỉ mục và phân cỡ dữ liệu

| Thuộc tính | Giá trị |
|---|---|
| Trạng thái | `PROPOSED` (lát cắt G1 dựa trên đo thực trên lô `G1-REAL-20261127-01`; chưa chốt stack cuối cùng) |
| Yêu cầu liên quan | `DEC-08`, `REQ-ARCH-03`, `REQ-TEMP-01–03`, `REQ-GRAPH-01–02`, `REQ-DATA-07`, `NFR-06` |
| Căn cứ G0 | [Thiết kế cơ sở dữ liệu G0](../g0/06-database-design.md) · [Kế hoạch G1-04](../g1/04-data-graph-storage-plan.md) |

## 1. Phạm vi quyết định ở G1 vs các pha sau

| Năng lực logic (`REQ-ARCH-03`) | Baseline thử nghiệm G1 | Pha nghiệm thu & lựa chọn cuối |
|---|---|---|
| Object storage (raw gốc & artifact bất biến) | Khử trùng SHA-256 cục bộ trong `data/raw/` (chuẩn bị S3-compatible / GCS / R2) | G1 đo dung lượng thật; G6 chốt chính sách object cloud (`POC-09`) |
| Relational (bitemporal & provenance) | PostgreSQL 18.6 với schema ownership tách dịch vụ và `btree_gist` | G1 qua `TST-04` bitemporal; G3 nghiệm thu ngữ nghĩa (`POC-04`) |
| Keyword / Search | PostgreSQL FTS `GIN (to_tsvector('simple', content))` làm mốc đối chứng | G2 đối chứng BM25/OpenSearch/trgm/unaccent (`POC-03`) |
| Graph | Bảng quan hệ `g1_graph_node` + `g1_graph_edge` + recursive CTE có giới hạn độ sâu | G3 đối chứng với Neo4j/managed graph (`POC-05`) |
| Vector | Mới tính cận dưới kích thước payload (`chunks × dim × bytes`) | G2 đo HNSW/IVFFlat RAM/disk với `pgvector` vs Qdrant (`POC-03`) |

## 2. Số đo thực tế trên PostgreSQL 18.6 (`G1-REAL-20261127-01`)

Môi trường đo xác thực thực tế: Windows 11 (`10.0.26300`, AMD64, 24 luồng logic, 91,98 GiB đĩa trống), PostgreSQL `18.6` khởi tạo cô lập loopback với SCRAM-SHA-256. Toàn bộ dữ liệu văn bản thô lấy từ lô `45` họ / `70` tệp duy nhất theo SHA-256 (`SRC-01` & `SRC-03`) theo [kết quả kiểm toán G1](../g1/evidence/g1-real-audit-2026-11-27.md).

| Thành phần đo | Quy mô quan sát | Dung lượng thực đo | Thời gian / độ toàn vẹn |
|---|---:|---:|---|
| Object gốc (theo lượt / đã khử trùng SHA-256) | 82 lần xuất hiện / 70 tệp (`64` PDF, `5` DOC, `1` DOCX) | `186.754.814` B / `173.803.902` B (`165,75 MiB`) | P50 `1.009.447` B; P90 `6.176.759` B |
| Text chuẩn hóa (`chunks.jsonl`) | `4.436` chunks (`PENDING_REVIEW`) | `4.675.855` B nội dung UTF-8 | Unicode NFC giữ nguyên dấu tiếng Việt |
| Bảng PostgreSQL + B-tree PK | `4.436` dòng (`public.g1_chunk`) | Heap `5.931.008` B + Index `483.328` B (`6,12 MiB`) | Nạp `\copy` + tạo B-tree: `0,138 giây` |
| Chỉ mục từ khóa baseline (`FTS simple`) | `GIN` trên `4.436` chunks | `1.425.408` B (`1,36 MiB`) | Dựng GIN `0,51 giây`; truy vấn mẫu `40,46 ms` |
| Bảng Graph quan hệ (`18` họ thật) | `82` nodes, `105` edges (`structural` + `normative`) | `172.032` B (`0,16 MiB` gồm index) | Duyệt 2-hop CTE (`442` cặp): `40,54 ms` |
| Backup & Restore (`pg_dump -Fc` / `pg_restore`) | Toàn bảng `g1_chunk` | Dump nén `865.767` B (`0,83 MiB`) | Backup `0,371 giây`; restore `0,524 giây`; MD5 khớp 100% |

Cận dưới payload vector (chưa tính chi phí index HNSW/IVFFlat và lọc ACL ở G2) cho `4.436` chunks:

| Số chiều | `fp32` (byte) | `fp16` (byte) | `int8` (byte) |
|---:|---:|---:|---:|
| 768 | `13.627.392` (`13,00 MiB`) | `6.813.696` (`6,50 MiB`) | `3.406.848` (`3,25 MiB`) |
| 1024 | `18.169.856` (`17,33 MiB`) | `9.084.928` (`8,66 MiB`) | `4.542.464` (`4,33 MiB`) |
| 1536 | `27.254.784` (`25,99 MiB`) | `13.627.392` (`13,00 MiB`) | `6.813.696` (`6,50 MiB`) |

## 3. Dự báo theo mẫu catalog quan sát được (`Low / Base / High`)

Neo theo số liệu catalog cổng `SRC-03` (`48.101` bản ghi toàn thời kỳ, trong đó giai đoạn 2020–cutoff có chính xác `195` Luật/Pháp lệnh và `1.441` Nghị định; tổng mọi loại ≥ 3.500 bản ghi) và trung bình thực đo trên 45 họ mẫu (`~3,86 MiB` raw khử trùng/họ, `~98,6` chunk/họ):

| Kịch bản giả định | Số họ duy nhất giả định | Hệ số revision | Raw (GiB) | Relational + FTS (GiB) | Vector 1024-fp16 + HNSW ước tính (GiB) | Tổng gồm backup & headroom (GiB) |
|---|---:|---:|---:|---:|---:|---:|
| Low (hạt nhân 2020–2026) | `4.000` | `1,15` | `16,55` | `0,60` | `1,17` | `43,74` |
| Base (cận đại + mở rộng nguồn) | `18.000` | `1,30` | `84,17` | `3,40` | `5,94` | `354,98` |
| High (toàn catalog ~48k + đa nguồn) | `48.101` | `1,50` | `259,53` | `11,52` | `18,31` | `1.217,61` |

## 4. Ràng buộc chưa chốt và điều kiện mở khóa

- **Không chốt DB vật lý duy nhất tại G1**: Theo `DEC-08` và `REQ-ARCH-03`, giữ kiến trúc baseline PostgreSQL 18.6 (`pg_trgm`/`FTS`, bảng quan hệ graph) + Object store cho đến khi G2 (`POC-03` hybrid retrieval/vector) và G3 (`POC-04/05` temporal/graph) có số đo truy vấn thực tế.
- **Cần bổ sung ở G2/G6**: Đo RAM thực tế của index HNSW ở Qdrant vs `pgvector` trên tập chunk ≥100.000 dòng và kiểm chứng RPO/RTO trên cloud (`POC-09`).
