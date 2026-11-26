# 07. Benchmark & Evaluation Specification

Phiên bản 0.2 · 26/11/2026 · Rubric đề xuất, chờ khóa trước holdout

## Tập dữ liệu và chứng cứ review

| Cấp | Điều kiện | Được tính AC-10 |
|---|---|---|
| L0 | AI draft hoặc case do người soạn chưa qua evidence check | Không |
| L1 | Kiểm schema, anchors, versions, policy và trùng lặp bằng máy | Không |
| L2 | Người review xác nhận facts, đáp án hoặc lý do từ chối, căn cứ nguyên bản và ngày hiệu lực | Có khi review hoàn tất |
| L3 | Người có năng lực chuyên môn phù hợp review độc lập, ghi căn cứ, phạm vi và kết luận | Có khi review hoàn tất |

Record gồm case ID, revision, group ID, origin/rights, domain, task, difficulty, language, risk, legal/recorded time, snapshot, facts, expected state, mandatory claims, gold evidence/relevance, hard negatives, severity flags, required review level, achieved review level, reviewer reference, timestamp, review evidence và adjudication status. Bản dịch hoặc biến thể dùng cùng group. Trường hợp cần L3 mà thiếu reviewer có trạng thái pending. Chỉ đếm mỗi case một lần khi bằng chứng review xác nhận mức yêu cầu. Loại revision đã thay thế và case chưa phân xử. Mẫu giả định gắn nhãn và giữ riêng khỏi kết quả nghiệm thu.

Corpus benchmark gồm ca trực tiếp, điều khoản nhiều phiên bản, hiệu lực một phần, mâu thuẫn nguồn, ngoại lệ/chuyển tiếp, quan hệ nhiều bước, thiếu sự kiện, EN, lỗi đầu vào, scope đáng rủi ro, quyền và điều kiện từ chối. Phân phối khóa theo taxonomy được duyệt × task × risk, đồng thời báo theo difficulty/time/language. POC-11 ước lượng cỡ mẫu, nhu cầu L3 và công sức review. Trước khi chọn model, đăng ký các cell mục tiêu theo mode, unit đủ điều kiện cho từng chỉ số, cỡ mẫu và các ca khó bắt buộc. Không mở rộng cell bằng cách suy từ kết quả của cell khác.

## Chia split và tái lập

1. Nhóm connected theo họ văn bản liên quan, tình huống gốc, bản dịch và biến thể gần trùng. Đối soát leakage bằng hash, tương đồng và review thủ công.
2. Tách train/dev/tuning/test theo group. Tỷ lệ và minimum per stratum chờ số lượng sau POC-11. Khóa test ID/snapshot/gold manifest trước lựa chọn model. PoC dùng development hoặc tập pilot riêng, test nghiệm thu giữ quyền riêng.
3. Chạy so sánh với cùng items, corpus, corpus cutoff, config đã pin, seeds nếu hỗ trợ và rubric. Ghi model/provider version, prompt, retriever/index/chunker, rule, graph, tool budget, chi phí, latency và code/image version.
4. Ghi bất đồng reviewer/judge, xử lý theo adjudication và phân loại nguyên nhân. Model judge và kiểm bằng máy hỗ trợ chấm, level review theo bằng chứng con người. Ghi case thiếu đầu ra trong denominator đã định trước.
5. Báo micro, macro theo strata, số mẫu và CI 95%. Với tỷ lệ nhị phân dùng Wilson nếu đơn vị độc lập. Với nhiều claim/case và so cặp ablation dùng bootstrap theo group/case. Mỗi báo cáo ghi quy ước sample/CI, missing, ties và known errors.

## Báo cáo và gate theo tầng

AC-10 yêu cầu ≥ 1.000 case L2/L3 duy nhất trong tập benchmark đã kiểm chứng. Holdout là phần độc lập, được khóa trước lựa chọn model và dùng nghiệm thu AC-01–08. AC-09 dùng suite cách ly riêng. Pilot dùng tập riêng. Với 9 domain, 5–6 task và 2–3 mức rủi ro, tích Descartes lý thuyết là 90–162 cell. Nhiều tập con nhỏ khó ước lượng các chỉ số 98%. Chẳng hạn, quan sát 5/5 chỉ cho cận dưới Wilson hai phía 95% khoảng 56,6%. Quy hoạch mẫu theo cell dự kiến mở và theo đơn vị đo, có thể cần hơn 1.000 case.

| Tầng | Điều kiện đánh giá đề xuất cho ADR-06 | Kết quả khi dữ liệu thiếu |
|---|---|---|
| Toàn tập và từng domain | Áp giữ nguyên ngưỡng AC-01–07 trên mẫu đủ điều kiện. Báo micro/macro, theo mode và CI 95% phù hợp. Đăng ký trước các metric phù hợp, mẫu số và độc lập theo group. Sàn đề xuất ở mỗi domain là 50 group holdout độc lập tổng cộng, mỗi metric có từ 20 group đủ điều kiện. AC-05/06 có thêm sàn 50 đơn vị đủ điều kiện theo rubric. Các sàn là mức tối thiểu để xem xét, CI cho biết độ bất định. Ghi riêng các metric không áp dụng cùng lý do đã duyệt | Denominator rỗng hoặc thấp hơn sàn đã khóa với metric áp dụng thì báo `INSUFFICIENT_EVIDENCE`. Thiếu dữ liệu toàn tập giữ G5, thiếu ở domain giữ AI trong domain ở tra cứu |
| Cell domain × task × risk theo từng mode | Chỉ xem xét cell đăng ký trước nếu tầng toàn tập và domain liên quan đạt, holdout có ít nhất 10 group độc lập theo sàn đề xuất, có ca khó bắt buộc cho cell và 0 lỗi S0/S1. Báo count, mẫu số, lỗi và point estimate khi có. Sàn và ca bắt buộc được khóa qua POC-11/ADR-06 trước chọn model. Cell rủi ro cao vẫn cần L3 nếu yêu cầu và giữ giới hạn chức năng | Cell thiếu mẫu hoặc reviewer, có lỗi nghiêm trọng hay chưa được đánh giá chỉ được tra cứu. Kết quả ít mẫu không chứng minh đạt 98% tại cell |

AC-08 và AC-09 giữ nguyên yêu cầu 0 lỗi trong phạm vi suite nghiệm thu của từng AC. Một lỗi nghiêm trọng đã biết chặn phạm vi bị ảnh hưởng. G5 ghi rõ tập strata bắt buộc đã khóa và chỉ nghiệm thu khi lượng mẫu, review và ngưỡng của phạm vi đó đủ. G7 yêu cầu mọi domain trong taxonomy có ít nhất một cell AI qua gate. Nếu pilot cho thấy sàn không khả thi với lịch, lập lại phân bổ trước freeze hoặc xử lý bằng change control. Giữ ngưỡng, review level và tính độc lập của holdout. [Điều kiện quyết định G5/G7](14-acceptance-test-plan.md#gate-severity-và-rollback).

Trong pilot G1, phân bổ tối thiểu theo domain chính của từng group. Giữ nhãn phụ phục vụ phân tích và báo số group duy nhất khi tổng hợp nhiều domain. Với một domain chính cho mỗi group, 8–10 domain cần 400–500 group holdout, còn 15–20 domain cần 750–1.000. Nếu holdout chiếm 40–50% số group thì phương án 15–20 domain cần khoảng 1.500–2.500 group toàn tập. Số case phụ thuộc số biến thể trong group. POC-11 lập ma trận group đủ điều kiện theo metric/cell/mode, nhu cầu L3 và giờ review. Khóa với ADR-06 trước chọn model, đồng thời giữ sàn ≥ 1.000 case L2/L3 của AC-10.

## Định nghĩa đo lường

Reviewer chấm answer theo từng claim bắt buộc và điều kiện áp dụng. Nhãn claim gồm đúng, sai, thiếu hoặc ngoài phạm vi cần trả lời. Với faithfulness, chấm từng claim đã phát ra theo nhãn được hỗ trợ, mâu thuẫn hoặc chưa đủ căn cứ. Với citation, kiểm lần lượt ID, version, anchor/quote và mức hỗ trợ claim. Với abstention, đối chiếu phạm vi phần giữ lại/phần từ chối và lý do truy xuất, policy hoặc dữ kiện theo gold. Mọi bất đồng ảnh hưởng verdict đi vào adjudication, kèm căn cứ và người duyệt.

| AC | Đơn vị và mẫu số | Quy tắc đạt |
|---|---|---|
| AC-01 | Trên query có gold evidence, lấy số gold version IDs trong top 20 chia tổng gold IDs của query | Mean ≥ 90%, tính cả query trả rỗng |
| AC-02 | Trên query có ít nhất một item relevant, DCG@10 chia ideal DCG@10 với grade 0/1/2/3 | Mean ≥ 0,80. Grade từ không liên quan đến căn cứ trực tiếp, pin theo snapshot |
| AC-03 | Case cần câu trả lời, gồm case cho partial nếu expected | ≥ 90% case đúng toàn bộ kết luận bắt buộc trong phạm vi, có đánh giá áp dụng và không có sai sót trọng yếu |
| AC-04 | Toàn bộ factual/legal claims cần bằng chứng đã phát ra | ≥ 95% claim được nguồn hỗ trợ về nội dung và điều kiện. Claim thiếu căn cứ là fail |
| AC-05 | Từng liên kết claim–citation đã phát ra | ≥ 98% liên kết đúng claim, version, nguồn, quote và anchor theo rubric |
| AC-06 | Từng target application theo case (provision × legal/recorded time × scope) | ≥ 98% target chọn đúng version/trạng thái. Thiếu target bắt buộc tính fail |
| AC-07 | Case gold yêu cầu từ chối toàn bộ hoặc từng phần | ≥ 90% case từ chối đúng phạm vi và đúng lý do. Chặn quá mức đo thêm trên tập có thể trả lời |
| AC-08–09 | Lượt nghiệm thu với citation và bộ kiểm tra tenant, bao gồm probes hợp lệ ở mọi lớp | 0 citation không tồn tại và 0 leak quan sát được |
| AC-10–12 | Case review, gate cell taxonomy, graph gold node/edge | ≥ 1.000 L2/L3. Mọi domain có AI đạt gate. Graph có ontology, pipeline và test sâu. Ngưỡng graph cần khóa trước nghiệm thu |

Mẫu số bằng 0 hoặc thiếu strata quan trọng được báo `INSUFFICIENT_EVIDENCE`. Citation coverage = claims cần căn cứ có citation hợp lệ / claims cần căn cứ. False abstention = case answerable bị từ chối sai / case answerable. Useful answer rate = case answerable đáp ứng expected state và nội dung / case answerable. Báo `s0_count`, `s1_count` và danh sách case theo từng scope. `GateReport.v1` ghi ID metric, denominator, số group, numerator khi áp dụng và CI khi phù hợp. CI gồm `ci_low`, `ci_high`, `ci_method`. Evaluator kiểm thứ tự cận và tính nhất quán với rubric. Chi tiết reviewer, quota, metric không áp dụng hoặc thiếu bằng chứng và danh sách case nằm trong báo cáo theo `report_ref`. POC-02 khóa extraction CER và các chỉ số cấu trúc với gold audit. POC-05 khóa graph precision/coverage. POC-11 khóa mức tối thiểu strata, coverage, false abstention và useful answer trước G5. Giữ các ngưỡng baseline.

## Ma trận đối chứng và khóa phát hành

Chạy baseline LLM không RAG trong evaluation cô lập, sau đó dense, hybrid, hybrid + rerank, cấu trúc + temporal, graph/multi-hop, verification và Standard/Advanced. Giữ các biến khác cố định trong từng phép đối chứng, chạy từng thành phần và so cặp cùng case. Ghi chất lượng, sai lỗi nghiêm trọng, P50/P95/P99, TTFT, time-to-verified-answer và cost per answer/case cho từng mode. Luồng không RAG không được mở cho người dùng dưới dạng căn cứ pháp lý.

Mỗi thay đổi corpus, index, graph, rule, model, prompt hoặc policy chạy regression theo phạm vi và suite bắt buộc. Gate report khóa manifest và trạng thái từng lĩnh vực/tác vụ/rủi ro. Khi lỗi, lưu root cause, thêm regression, rerun và phục hồi/tạm dừng theo [Test Plan](14-acceptance-test-plan.md). Báo cáo công khai dùng kết quả đã che dữ liệu và chỉ công bố mẫu có quyền.

[Căn cứ baseline §§10–11, POC-03–08 và POC-11](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md)
