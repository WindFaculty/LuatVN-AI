# G1-05 — Human review pilot & Benchmark feasibility

Phiên bản 0.1-draft · POC-11 · REQ-EVAL-01–03, REQ-SEC-08 · AC-10/11, BLOCKER-01/02 · ADR-06

## 1. Nguyên tắc

[Protocol pilot hiện hành](poc11-review-pilot.md) và [G0 Evaluation](../g0/07-benchmark-evaluation.md) là căn cứ. G1 chưa chạy pilot human review: 0/0 L2/L3. L0 draft, L1 automatic check, L2 người thật xác nhận căn cứ/đáp án/hiệu lực; L3 người có chuyên môn phù hợp review độc lập. AI sinh câu hỏi, kiểm schema, đề xuất source/answer và calibration judge được dùng hỗ trợ nhưng không thay L2/L3. Case required L3 chưa có chuyên gia = PENDING_L3, không tính AC-10. Không sử dụng hồ sơ người thật/PII nếu chưa có quyền.

## 2. Pilot và quy trình

Mục tiêu 27 cases (9 domain × 3; primary domain/group không trùng; 1 tra cứu, 1 hiệu lực, 1 ca rủi ro/thiếu dữ kiện nếu đủ). Có thể không đạt 27 độc lập khi thiếu data/source rights; báo số thực. Pilot riêng, không đưa sang holdout hoặc tính vào 1.000 case nghiệm thu.

1. Tạo case_id/revision/group_id; rights_ref, corpus snapshot/recorded cutoff, legal date, facts, expected state, required claims/gold version+anchor, risk, difficulty, language, task, required tier, source references, negative cases. Group theo họ văn bản và tình huống, liên kết biến thể/bản dịch; phép đo theo primary domain.
2. Chạy machine L1 (schema, evidence ID/version/quote, scope, duplication). Tách bug và revision; không tự bổ sung gold từ model answer.
3. Người review đọc original evidence và facts, ghi pass/reject/needs clarification, active minutes, wait minutes, adjudication minutes; ghi reviewer ID/role, level đủ điều kiện và evidence. Nếu không có L3, thống kê case L3 pending, không đánh giá expert time bằng LLM.
4. Recheck sample chấm chéo hoặc review lần 2 nếu có độc lập; disagreement ghi adjudication evidence, không tự vote theo số model. Báo count theo level/domain/task/risk, median/P90 thời gian, throughput, % required L3, % case pending; sample size và limits.
5. Project hours = preparation + N_L2 × mean reviewed minutes_L2/60 + N_L3 × mean reviewed minutes_L3/60 + adjudication/recheck. Median/P90 để lập range; L3 chưa đo → unknown/sensitivity assumptions có label. Phân biệt owner hours, expert hours và calendar waiting.

## 3. Kiểm tra tính khả thi của 1.000+ cases

G0 đề xuất domain floor 50 independent holdout groups, 20 groups đủ điều kiện/metric và ≥50 units cho citation/temporal; cell floor 10 independent groups và 0 S0/S1 cùng ca khó. 9 domains × 50 = tối thiểu 450 independent holdout groups với primary domain duy nhất; holdout 50% tương ứng ≥900 group toàn bộ, 40% tương ứng ≥1.125 group. Mỗi group có thể nhiều case, do đó 1.000 case chỉ là mức sàn, không cam kết đủ.

Đề xuất để đánh giá feasibility: 10% authoring/train, 20% dev, 20% tuning, 50% holdout theo connected group; phân chia actual chỉ chốt trước model selection khi biết số group và required tier. Ứng viên 50% giúp sàn domain nhưng giảm mẫu tuning; kiểm số group đủ điều kiện cho từng metric và cell theo Standard/Advanced. Nếu thiếu, tăng verified independent cases hoặc lập change request lịch, không dùng test để tuning. Không bắt buộc đủ mọi tổ hợp cell lý thuyết; đăng ký trước các cell V1 dự kiến mở, đảm bảo mọi domain có tối thiểu một cell AI đạt ở G7 và giữ high-risk restrictions.

Holdout manifest chứa case/group/revision, snapshot, taxonomy, rubric, eligibility, tier, split, hash và access roles. Tách authoring/dev/tuning/test theo connected components, kiểm near duplicate và false group merges, khóa manifest và access trước chọn model. Pilot dùng dev/pilot riêng. Raw gold và holdout không vào demo hoặc prompt công khai; reports phải redact và tuân quyền.

## 4. Kết luận ADR-06 cần owner duyệt

- Taxonomy revision, primary-domain/group rule, target cells và ca khó.
- Metric denominator, micro/macro, CI, severity, sample floors và split/hashes (giữ AC-01–10 nguyên vẹn).
- Số nhóm/case khả dụng, verified L2/L3 thực, review budget/time theo median/P90, tỷ lệ cần L3 và phương án chuyên gia phù hợp hoặc blocker/change request.
- Chốt policy và feasibility trước model selection; khóa test độc lập khi đủ dữ liệu trước G5. Nếu input thiếu, ADR-06 vẫn PROPOSED và G1 ghi blocker, không gọi holdout frozen.

G1 không nghiệm thu benchmark 1.000 hoặc chất lượng LLM. G5 phải chứng minh đủ 1.000+ verified cases, holdout độc lập và các ngưỡng AC; G7 phải chứng minh mọi domain có AI đạt. Nếu chủ dự án chọn tự review trước, chỉ L2 đủ điều kiện được đếm sau kiểm; phải ghi rõ các case cần L3 còn pending.
