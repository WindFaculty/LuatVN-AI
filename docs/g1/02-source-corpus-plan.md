# G1-02 — Source rights, corpus và taxonomy

Phiên bản 1.0 · Quyết định G1-D01–06 đã được chủ dự án duyệt ngày 26/11/2026 · POC-01 · TST-02 · REQ-DATA-01–03, 05–08, REQ-SEC-11 · BLOCKER-01, RISK-07

## 1. Quyền nguồn là gate đầu tiên

Đối chiếu [discovery 26/11](poc01-sources.md) và [registry G0](../g0/registers.md#data-source-registry). HTTP 200, nhìn thấy tệp hoặc quyền đọc không đủ để suy ra quyền thu thập hàng loạt, lưu trữ, index, trích dẫn hoặc tái phân phối. Chủ dự án lưu căn cứ theo đúng hành động và không tự diễn giải đây là kết luận tuân thủ pháp lý.

Theo G1-D01, ưu tiên SRC-01/03; các nguồn khác tiếp tục khảo sát theo mức ưu tiên bên dưới, không có quyền tải/xử lý tự động nếu chưa xác minh từng hành động.

| Source | Ưu tiên đã duyệt cho pilot | Hành động tiếp theo | Khi bị chặn |
|---|---|---|---|
| SRC-01 Công báo | P0 | Xác nhận manual sample, signed PDF/DOC, quyền lưu nội bộ, index test, citation, redistribution riêng | Giữ PENDING_RIGHTS; không ingest |
| SRC-03 Văn bản Chính phủ | P0 | Xác nhận catalog và artifact, đối chiếu provenance với SRC-01 | Như trên; ghi overlap/gap |
| SRC-02 VBPL | P1 critical coverage | Hỏi kênh catalog/API/batch chính thức, điều kiện, rate | Không bypass 403; phương án nguồn giao nhau đã duyệt, mẫu số unknown nếu thiếu |
| SRC-04 án lệ / SRC-05 bản án | P1 | Xác nhận kênh, quyền, loại hồ sơ, anonymization | Không bỏ TLS verification; khi chưa duyệt chỉ synthetic hoặc nguồn tư pháp khác được phép |
| SRC-06 | P1 | Định danh các cổng bộ/ngành, Quốc hội, địa phương và lịch sử theo cấp | Lập danh mục thiếu, không tuyên bố coverage toàn quốc |
| SRC-07 | P2 | Chỉ nguồn đối chiếu bổ sung/đóng góp đã được phép | Quarantine và không dùng làm gold nếu provenance chưa đủ |

Registry mỗi source + action: source_id, source URL/owner/contact, policy URL/version/date, action (manual_download, automated_access, store, index, cite, redistribute), purpose, allowed data class, scope/region/type/time, rate/limits, expiry, evidence_ref, approval by owner, status PENDING_RIGHTS/APPROVED/DENIED/EXPIRED, revocation procedure. Một run cần mọi action sử dụng đã APPROVED; một action chưa duyệt không suy ra từ action khác. Không liên hệ nguồn thay chủ dự án nếu chưa được cấp quyền gửi.

Chủ dự án đã mở phạm vi tải từng mẫu công khai SRC-01/03 và xử lý nội bộ. Mỗi lô dùng registry URL cụ thể, tách khỏi registry mặc định. Adapter kiểm hiệu lực quyền tại lúc thao tác và dừng nếu nội dung registry thay đổi giữa lượt chạy. Cutoff giữ cố định để phân loại ngày ban hành trong snapshot. [Cập nhật G1-D01](evidence/owner-decision-g1-d01-2026-11-26.md)

## 2. Taxonomy revision

Giữ 9 nhóm pilot 0.1.0 làm lớp 1 trong khi chưa đo coverage: CIV, CRI, ADM, LAB, LND, BUS, TRA, EDU, ENV. Theo G1-D02, mở rộng sub-domain bằng catalog chính thức, không tự khẳng định 9 nhãn là đầy đủ hệ thống pháp luật. Đặc biệt rà soát hiến định/quản trị nhà nước, tố tụng, tài chính/ngân hàng/bảo hiểm, thuế, SHTT/công nghệ, y tế, an sinh, hôn nhân/gia đình, quốc phòng/an ninh, thương mại quốc tế và lĩnh vực chuyên ngành. Nếu chưa có nhóm phù hợp, gắn UNMAPPED và review để thêm hoặc đổi nhãn có migration, không ép vào nhóm gần nhất.

Tách taxonomy lĩnh vực khỏi document_type, issuer, authority level, jurisdiction lineage, language, binding class, temporal state. Cho phép nhiều nhãn; benchmark gán domain chính cho group để thống kê độc lập. Lưu mapping aliases/names per revision và nguồn đối chiếu. Hiến pháp, văn bản hết hiệu lực, dự thảo, văn bản hợp nhất, công văn, án lệ và bản án có loại và policy riêng; metadata quan sát không tự khẳng định hiệu lực.

## 3. Kế hoạch chọn mẫu đã duyệt (G1-D02; không phải corpus hiện có)

| Lô | Mục tiêu | Mẫu dự kiến |
|---|---|---:|
| A discovery | Đếm catalog theo snapshot, dedup identity/metadata | Toàn bộ catalog được phép trong scope xác định; không đặt quota tùy ý |
| B real pilot | 9 nhóm × 5 document families chính; ưu tiên text gốc, có revision/related sources | 45 families, giữ các version liên quan nếu có quyền |
| C extraction gold | Mẫu phủ format/condition, định danh điều khoản và bảng, nhiều trang | Tối thiểu mục tiêu 36 artifacts; có thể lấy từ B |
| D temporal/graph gold | Có sửa đổi từng phần, hợp nhất, viện dẫn, locality/lineage và normative conditions | Mục tiêu 18 families (2/domain), có thể lấy từ B |
| E review pilot | Query/case đại diện theo 9 nhóm | 27 cases mục tiêu (3/domain), tách holdout |

Số lượng 45/36/18/27 là mục tiêu pilot đã duyệt; thiếu mẫu phải báo gap và remediate, không tự giảm mục tiêu. Đây không phải điều kiện đủ đại diện toàn quốc hay số lượng benchmark 1.000. B/C/D là tập giao nhau được ghi manifest; không cộng thành ba corpus độc lập. Ưu tiên ca khó (scan kém, bảng qua trang, Điều 5a, sửa cụm từ, nhiều cơ quan hoặc local/time). Mỗi strata có mục tiêu, thực thu, lý do hụt, bias và owner remediation. Nếu quyền/format thiếu, synthetic dùng kiểm kỹ thuật và tách riêng số liệu.

## 4. Snapshot và phương pháp coverage

Manifest: corpus_id/version, catalog cutoff + recorded timestamp, source scopes and rights_ref, document_family_id, canonical identity (issuer/type/number/year/identity disambiguation), source record/artifact hash + MIME/size, source revision, legal status candidate, labels/revision, locality/cấp, historical/active/future/draft, verified status, split eligibility và source/anchor references. Không đưa raw document vào Git.

- Mẫu số = unique eligible records từ catalog hoặc scope được phép có cutoff rõ. Báo theo source, domain, sub-domain, loại, cấp, địa phương, thời kỳ. Đối chiếu cross-source và giữ provenance dù byte trùng.
- Tử số = unique record thuộc cùng denominator đã đối chiếu source/identity/version. Report numerator/denominator và coverage %. Không lấy số seed records hay số trang crawl làm mẫu số.
- Catalog không đếm được → unknown; catalog trung ương không đại diện địa phương. Nếu 2 sources có overlap, tổng dedup theo canonical identity và review conflict, không cộng thô.
- Báo riêng tỷ lệ artifacts được lấy/đối chiếu, verified/pending/conflict/quarantined, missing revisions, source gaps và sampling bias. Không coi coverage của lô pilot là coverage pháp luật Việt Nam.
- Với mỗi tài liệu chưa xác minh, chỉ search kèm cảnh báo khi quyền cho phép; excluded khỏi verified evidence.

## 5. Evidence chốt POC-01

Cần source/action registry có căn cứ đã duyệt; manifest catalog và sample; taxonomy revision + mapping; coverage by strata có counts hoặc explicit unknown/gap (scope trọng yếu chưa đếm giữ G1 open); nguồn đối chiếu conflict; raw/normalized sizing; danh sách quyền/chuyên ngành còn thiếu. Owner chốt phạm vi thực tế và đánh giá đường đến toàn bộ taxonomy V1, không xóa domain vì nguồn thiếu.

| Phạm vi | Điều kiện để ghi số đo | Hệ quả ở G1 |
|---|---|---|
| Lô thủ công SRC-01/03 | Tất cả URL trong danh sách mẫu có provenance, SHA-256 và quyền tương ứng. Đếm riêng trang, occurrences, họ và phiên bản. | Số đo của lô mẫu phục vụ kiểm thử. Coverage catalog vẫn `UNKNOWN`. |
| Catalog trọng yếu SRC-01/03 | Có catalog hoặc export đủ quyền trong khoảng 01/01/2020 đến cutoff đã pin, xác nhận đầy đủ theo nguồn × năm × loại và phạm vi cấp/địa bàn. Đối chiếu hai nguồn theo family và version, giữ conflict riêng. | G1-AC-A còn mở nếu thiếu mẫu số ở phạm vi đã chốt. |
| Phần lịch sử, địa phương, tư pháp và chuyên ngành chưa đủ catalog | Lập danh sách strata chưa kiểm, nguồn đối chứng khả dĩ, owner và gate xử lý. Dùng `UNKNOWN` kèm lý do ở strata thiếu. | Ghi rõ các khoảng trống trong G1-AC-B và trình chủ dự án chốt taxonomy. Chỉ công bố coverage trên phần đã đo. |
