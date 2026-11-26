# LUẬT VIỆT NAM AI
## Requirements Baseline v1.0 — Hồ sơ yêu cầu tổng hợp

| Thuộc tính | Giá trị |
|---|---|
| Chủ dự án | Trần Xuân Khoa |
| Tên sản phẩm | Luật Việt Nam AI |
| Tên mô tả tiếng Anh | Vietnamese Legal Intelligence Platform |
| Ngày lập baseline | 26/11/2026 |
| Căn cứ | 11 giai đoạn khai thác yêu cầu và 12 quyết định cuối cùng của chủ dự án |
| Phiên bản đích đầu tiên | V1 — Technical Preview |
| Trạng thái | Đã ghi nhận yêu cầu; còn xung đột và điều kiện nghiệm thu mở |
| Mục đích | Tài liệu nguồn chung để soạn 14 hồ sơ thiết kế, ADR, backlog và acceptance gate |

### Quy ước
- **MUST**: yêu cầu đã được chủ dự án chọn, bắt buộc đối với phạm vi ghi rõ.
- **SHOULD**: đề xuất kỹ thuật, chưa phải quyết định công nghệ đã phê duyệt.
- **LATER**: phạm vi dài hạn, không bắt buộc trong V1.
- **TBD**: cần dữ liệu thực nghiệm hoặc quyết định bổ sung; không được giả định là đã xác định.
- **BLOCKER**: xung đột hoặc điều kiện thiếu khiến không thể xác nhận nghiệm thu.
- Mọi mã REQ, BR, NFR, AC, RISK, ADR, POC và G trong hồ sơ là định danh quản lý đề xuất. Những lựa chọn mới nhất của chủ dự án có ưu tiên; các tiêu chuẩn an toàn đã chọn trước đó vẫn có hiệu lực. Không hợp thức hóa một điều kiện chưa đạt bằng cách đổi nhãn hay tự giảm ngưỡng.

# 1. Product vision và mục tiêu

Xây dựng một nền tảng Legal Intelligence phục vụ người Việt Nam, học sinh/sinh viên, người tra cứu hành chính/pháp luật, cá nhân và doanh nghiệp; kết hợp công cụ tra cứu văn bản, AI giải thích pháp luật và hệ thống AI phân tích tình huống dựa trên căn cứ có thể truy xuất.

- OBJ-01: Sản phẩm thực tế cho cộng đồng, hướng tới thương mại hóa.
- OBJ-02: Nghiên cứu AI/RAG tiếng Việt chuyên biệt: dữ liệu, retrieval, temporal, graph, agents, verification.
- OBJ-03: Portfolio Junior AI Engineer với demo thực tế, benchmark, báo cáo kỹ thuật, MLOps và khả năng giải thích/debug độc lập.
- OBJ-04: Nền tảng dài hạn web + mobile và dịch vụ AI cho doanh nghiệp.
- Chủ dự án là người phát triển duy nhất, có AI Coding Agent hỗ trợ; cộng tác viên/chuyên gia có thể thực hiện kiểm chứng pháp lý và bảo mật sau V1 theo quyết định mới nhất. Không coi cộng tác viên là đội phát triển.
- Thời gian đích 2–3 tháng, 30–40 giờ/tuần (khoảng 240–480 giờ với quy ước 8–12 tuần). Đây là mục tiêu tiến độ, không phải cam kết đã chứng minh khả thi. Ngân sách và dung lượng lưu trữ chưa chốt.

# 2. Quyết định cuối cùng — khóa ưu tiên

| ID | Quyết định |
|---|---|
| DEC-01 | Chấp nhận phạm vi V1; hoãn mobile và thương mại. |
| DEC-02 | Bắt buộc mở AI ở toàn bộ lĩnh vực ngay trong Technical Preview. |
| DEC-03 | Tối thiểu 1.000 test case đã kiểm chứng, phân tầng L2/L3, tập test độc lập. |
| DEC-04 | Tự kiểm chứng toàn bộ trong Technical Preview, tìm chuyên gia sau. |
| DEC-05 | Knowledge Graph chuyên sâu bắt buộc hoàn thành trong V1. |
| DEC-06 | Standard hoàn chỉnh; Advanced đủ chứng minh Agentic RAG; Expert Research sau V1. |
| DEC-07 | Tạo đầy đủ repository cho mọi service ngay từ đầu. |
| DEC-08 | Đủ năm khả năng lưu trữ logic; chọn số database vật lý theo PoC. |
| DEC-09 | 100–500 là tổng tài khoản đăng ký dự kiến; concurrency TBD theo benchmark. |
| DEC-10 | Quản lý phiên bản đầy đủ, bitemporal, provenance, mở rộng loại văn bản, Rule Engine có kiểm chứng. |
| DEC-11 | Demo công khai toàn bộ chức năng AI Studio. |
| DEC-12 | Hoàn thiện đủ 14 tài liệu trước khi thực hiện PoC. |

# 3. Phạm vi và phân kỳ

## V1 — Technical Preview (MUST)
- Legal Data Pipeline, kho tri thức chuẩn hóa, tra cứu từ khóa/số hiệu/điều khoản/ngữ nghĩa, bộ lọc, đọc và tải văn bản gốc nếu được phép.
- Legal RAG và AI Chat: hỏi đáp nhiều lượt, giải thích, tổng hợp, phân tích tình huống trong giới hạn rủi ro, hỏi thêm, căn cứ, rủi ro và phương án tham khảo, phản biện lập luận.
- AI mở trên toàn bộ lĩnh vực theo taxonomy đã xác định; phải vượt release gate theo lĩnh vực và loại tác vụ. Không đồng nhất mở AI với cấp phép mọi tác vụ rủi ro.
- Temporal Legal Retrieval, Legal Rule Engine, Legal Knowledge Graph chuyên sâu: văn bản, điều khoản, chủ thể, quyền, nghĩa vụ, điều kiện, ngoại lệ, quan hệ và phiên bản; mọi dữ kiện/quan hệ sử dụng làm căn cứ phải có provenance và trạng thái xác minh.
- Hybrid Retrieval, hierarchical, temporal, graph, multi-hop; controlled workflow + Agentic RAG; Standard hoàn chỉnh, Advanced có khả năng lập kế hoạch và gọi công cụ được giới hạn.
- Model Gateway, Answer Verification, Benchmark tối thiểu 1.000 test case, AI Evaluation, regression, MLOps/LLMOps.
- Legal Web, Legal AI Studio với quản trị dữ liệu, RAG Playground, Agent Workflow Visualizer, đánh giá, trace, monitoring, model/prompt/config, báo cáo sai sót, quản lý quyền.
- Demo cloud có khả năng phục vụ liên tục, monitoring, quota, kiểm soát chi phí, CI/CD. Tài khoản Technical Reviewer; demo toàn bộ chức năng Studio, không công khai bí mật hoặc quyền production.
- 14 tài liệu nền tảng hoàn chỉnh trước PoC; hoàn thiện bằng chứng cá nhân và hồ sơ kỹ thuật.

## LATER — các phiên bản sau (giữ trong product backlog)
- Android React Native/Expo trước, iOS sau khi ổn định; mobile thiên AI chat, camera OCR, chia sẻ tài liệu, push notification, offline có cảnh báo phiên bản; website thiên nghiên cứu sâu.
- Document Intelligence cá nhân: upload hợp đồng, trích xuất ảnh/scan, phát hiện điều khoản có dấu hiệu bất lợi, đối chiếu pháp luật, so sánh nhiều tài liệu, đề xuất sửa đổi, soạn biểu mẫu/văn bản, báo cáo phân tích có trích dẫn. Không thay thế luật sư.
- Legal Workspace theo vụ việc, lưu yêu thích, lịch sử, xuất/chia sẻ, bộ nhớ có đồng ý, chế độ riêng tư; V1 cần tối thiểu cách ly hội thoại, quyền truy cập và lịch sử theo phạm vi được triển khai.
- Legal Monitoring: bản tin mới, văn bản sắp hiệu lực/hết hiệu lực, theo dõi lĩnh vực/văn bản, cá nhân hóa theo nhu cầu/nghề nghiệp.
- Community: đóng góp tài liệu có kiểm duyệt, bình luận/thảo luận, đánh giá, report lỗi (report lỗi cần có sớm trong V1), cộng đồng chuyên gia.
- Tính toán pháp lý chuyên biệt chưa triển khai.
- Expert Research: nhiều AI chuyên biệt phối hợp/đối chiếu/phản biện, chỉ phát hành khi có bằng chứng vượt Standard và giới hạn an toàn chung.
- Freemium, thuê bao cá nhân/doanh nghiệp, Legal AI API, SSO, dedicated deployment, triển khai riêng doanh nghiệp; iOS; fine-tuning embedding, reranker, LLM chỉ khi benchmark và dữ liệu chứng minh cần thiết.
- Thương mại hóa phải qua gate độc lập về nghiệp vụ, chất lượng, pháp lý, bảo mật; không dùng V1 để đánh đồng với hệ thống đã được thẩm định.

# 4. Actors và quyền

| Actor | Phạm vi |
|---|---|
| Khách | Tra cứu công khai, Standard có giới hạn phù hợp về tuổi/rủi ro |
| Registered User | Tra cứu, AI được cấp phép, lịch sử/tuỳ chọn theo tính năng |
| Premium User (LATER) | Advanced/Expert theo entitlement, không hạ chuẩn an toàn cho Free |
| Technical Reviewer | Demo Studio đầy đủ chức năng trong môi trường sandbox hoặc tài khoản giới hạn; xem dữ liệu công khai/giả lập, benchmark, trace đã che dữ liệu |
| System Admin | Quản trị production tách biệt, MFA bắt buộc |
| Legal Expert (LATER) | Kiểm chứng chuyên môn, hồ sơ được phân công và có quyền; MFA bắt buộc |
| Enterprise Account (LATER) | Tenant, roles, policy, SSO, dedicated deployment khi phù hợp |
| AI Agent / Worker | Danh tính service, quyền tối thiểu; phê duyệt mọi thay đổi dữ liệu hoặc tác động bên ngoài do agent tự đề xuất |

# 5. Data và nghiệp vụ pháp lý

## 5.1 Phạm vi
REQ-DATA-01 MUST: Bao phủ dài hạn toàn bộ hệ thống pháp luật, tất cả cấp ban hành và đơn vị hành chính cũ; đa lĩnh vực, lịch sử, hiện hành, tương lai đã ban hành, hết hiệu lực và dự thảo tách biệt; không đặt trước số văn bản tối thiểu.
REQ-DATA-02 MUST: Hiến pháp, bộ luật, luật, nghị quyết, nghị định, thông tư, quyết định; văn bản hợp nhất, án lệ, bản án được phép công bố, công văn hướng dẫn nghiệp vụ. Danh mục mở rộng cho pháp lệnh, loại lịch sử/liên tịch, điều ước liên quan, đính chính và loại mới theo khảo sát.
REQ-DATA-03 MUST: Ưu tiên nguồn Nhà nước; nguồn khác chỉ đối chiếu/khai thác khi có quyền. Crawler/API/dữ liệu mở/tài liệu batch/đóng góp người dùng có kiểm duyệt. Inventory phải có nguồn, điều kiện khai thác, độ bao phủ, cấp độ tin cậy, quyền sử dụng và hạn chế.
REQ-DATA-04 MUST: HTML, PDF text, PDF scan, ảnh, DOC/DOCX, bảng tính, bảng biểu, phụ lục, biểu mẫu, công thức. OCR/layout/table extraction thích ứng có validation.
REQ-DATA-05 MUST: Thu thập mọi nguồn có thể tiếp cận hợp pháp theo mục tiêu; triển khai adapter có thứ tự thực tế; cập nhật tự động thích ứng theo nguồn, phát hiện thay đổi, xử lý lại và lập chỉ mục; lưu lỗi, retry, dedup, idempotency, checkpoint và lịch sử.
REQ-DATA-06 MUST: Tự động kiểm chứng; duyệt thủ công trường hợp bất thường. Tài liệu chưa xác minh hoặc mâu thuẫn vẫn có thể tra cứu kèm cảnh báo khi được phép; không dùng làm căn cứ. Tài liệu đóng góp phải cách ly, kiểm tra bảo mật và quyền trước nhập kho.
REQ-DATA-07 MUST: Lưu bản gốc bất biến theo phiên bản (hash, URL, thời điểm truy xuất), nội dung chuẩn hóa, metadata, trạng thái, lịch sử kiểm chứng và phiên bản parser/OCR/embedding. Lưu bản dịch chính thức nếu có; dịch AI phải gắn nhãn.
REQ-DATA-08 MUST: Taxonomy lĩnh vực, cơ quan, đơn vị hành chính và loại văn bản có phiên bản; công bố độ bao phủ đo theo danh mục đối chiếu, không tuyên bố tuyệt đối nếu chưa có đối chứng. Taxonomy chính thức và danh mục nguồn là TBD trước G1.

## 5.2 Temporal, provenance và graph
REQ-TEMP-01 MUST: Cấu trúc phần/chương/mục/điều/khoản/điểm, định danh ổn định, phiên bản riêng, trạng thái hiệu lực toàn bộ/từng phần.
REQ-TEMP-02 MUST: Bitemporal: valid time (khi nào có hiệu lực pháp lý) và transaction/recorded time (khi nào hệ thống biết/ghi nhận/xác minh); thời điểm tham chiếu của câu hỏi và snapshot dữ liệu của câu trả lời phải truy vết được.
REQ-GRAPH-01 MUST: Ontology chuyên sâu (Document, Provision, ProvisionVersion, Authority, Jurisdiction, Subject, Right, Obligation, Condition, Exception; thêm loại khi cần), quan hệ sửa đổi, thay thế, bãi bỏ, hướng dẫn, đính chính, viện dẫn, áp dụng, quyền/nghĩa vụ và ngoại lệ.
REQ-GRAPH-02 MUST: Quan hệ có nguồn chứng minh, phiên bản/thời gian, loại pháp lý, trạng thái kiểm chứng; truy xuất multi-hop có giới hạn. Không sử dụng cạnh suy đoán/chưa xác minh để kết luận. Cần thước đo độ chính xác/độ bao phủ theo loại node/edge; ngưỡng và phạm vi trích xuất TBD theo PoC. "Chuyên sâu hoàn thành V1" là yêu cầu bắt buộc, nhưng chưa có định nghĩa định lượng về hoàn thành graph.
REQ-TEMP-03 MUST: Không coi văn bản hợp nhất, án lệ, công văn, bản án, bản dịch hoặc dự thảo là cùng một loại giá trị pháp lý; thứ tự ưu tiên phải theo quy tắc được xác minh, không chỉ theo độ mới hoặc similarity.

## 5.3 Business rules
| ID | Rule |
|---|---|
| BR-LEGAL-01 | Phân biệt tính xác thực, hiệu lực tại thời điểm và khả năng áp dụng cho tình huống. |
| BR-LEGAL-02 | Dự thảo không được dùng như quy định hiện hành; nguồn chưa xác minh không được dùng làm căn cứ. |
| BR-LEGAL-03 | Xác định địa phương, thẩm quyền, đối tượng, điều kiện, thời điểm sự kiện; nếu thiếu thì hỏi thêm hoặc nêu giới hạn. |
| BR-LEGAL-04 | Xử lý sửa đổi/bãi bỏ/thay thế/đính chính, hiệu lực từng phần, ngoại lệ và điều khoản chuyển tiếp; đánh dấu bất đồng chưa giải quyết. |
| BR-LEGAL-05 | Rule Engine quyết định phần có thể biểu diễn và kiểm thử bằng quy tắc; quy tắc phải có căn cứ, phiên bản, test và phê duyệt; trường hợp chưa xác minh không suy đoán. |
| BR-LEGAL-06 | Câu trả lời tiếng Anh giữ căn cứ gốc tiếng Việt, ưu tiên nguyên bản; ghi rõ bản dịch AI. |
| BR-LEGAL-07 | Trả lời phần có căn cứ khi thiếu dữ liệu; không dùng kiến thức LLM như bằng chứng pháp lý. |
| BR-LEGAL-08 | Trường hợp rủi ro cao: chỉ thông tin đã kiểm chứng, hạn chế kết luận cá nhân hóa; nếu cần chuyên gia mà chưa có, thông báo giới hạn thay vì giả lập thẩm định. |
| BR-RELEASE-01 | Bật AI theo lĩnh vực × loại tác vụ × mức rủi ro khi đạt gate; phạm vi chưa đạt chỉ tra cứu. V1 hoàn chỉnh đòi mọi lĩnh vực định danh đều có AI đạt gate; không gọi bản giới hạn là V1 đã nghiệm thu. |
| BR-RELEASE-02 | Standard, Advanced, Expert có chuẩn an toàn tối thiểu chung; trả phí không mua quyền bỏ qua verification. |
| BR-SEC-01 | Không đưa dữ liệu cá nhân/tài liệu khách hàng vào kho chung hoặc huấn luyện nếu thiếu đồng ý rõ và biện pháp phù hợp. |

Nội dung này là yêu cầu thiết kế, không phải kết luận tư vấn pháp lý hoặc thẩm định quy định hiện hành. Cần nghiên cứu nguồn chính thống và thẩm định điều kiện thực tế trước phát hành.

# 6. AI/RAG requirements

| ID | Yêu cầu (MUST V1 trừ ghi chú) |
|---|---|
| REQ-AI-01 | RAG Engine modular: thay thế được model, retriever, reranker, chunker, strategy, evaluator; Python/FastAPI. |
| REQ-AI-02 | Hybrid controlled workflow + Agentic RAG; router phân loại tra cứu/hỏi đáp/phân tích; Search không bắt buộc gọi LLM. |
| REQ-AI-03 | Hybrid legal structure + semantic + parent-child chunking, giữ provision/version ID, metadata, nguồn trích dẫn. |
| REQ-AI-04 | Dense + sparse/keyword, fusion, reranking, hierarchical, temporal, graph, multi-hop; filter xác minh, hiệu lực, địa phương và quyền. |
| REQ-AI-05 | Pipeline phân tích dữ kiện → lập kế hoạch → truy xuất → đối chiếu/suy luận → kiểm chứng → trả lời/hỏi thêm/từ chối một phần. |
| REQ-AI-06 | Chỉ sử dụng kho tri thức nội bộ đã xác minh làm căn cứ; tìm lại với truy vấn khác khi thiếu. Không tự động mở rộng sang web để trả lời trong V1. |
| REQ-AI-07 | Answer verification dùng Rule Engine, kiểm tra citation ID/source/version, đối chiếu nguồn, model đánh giá; chuyên gia cho tình huống bắt buộc khi có; không mô phỏng thẩm định. |
| REQ-AI-08 | Kết quả dạng có cấu trúc: answer_id, legal_as_of, snapshot, summary, facts, assumptions, missing_facts, claims, evidence, version_id, quote, URL, validity, verification, risks, limitations, expert-review flag. |
| REQ-AI-09 | Tiếng Việt + tiếng Anh; dịch truy vấn Anh sang Việt, bảo lưu truy vấn gốc và thuật ngữ; trả lời ngôn ngữ yêu cầu với căn cứ gốc. |
| REQ-AI-10 | Agents giới hạn quyền tool, step budget, token, timeout, cancellation, retries; có kế hoạch, tự kiểm tra, điều chỉnh hữu hạn; cần phê duyệt thao tác thay đổi dữ liệu/tác động ngoài. |
| REQ-AI-11 | Phân tầng memory, tenant/workspace context; không truy xuất ngoài quyền; không chia sẻ embeddings/log/cache giữa tenant; Private Chat không lưu lịch sử lâu dài, policy provider phải phù hợp. |
| REQ-AI-12 | Standard hoàn chỉnh; Advanced có Agentic RAG và benchmark; Expert Research nhiều vai trò chuyên biệt LATER; không đánh đồng nhiều agent với độ chính xác. |
| REQ-AI-13 | 100% inference LLM qua API bên ngoài; embedding/reranking có local/self-host/API theo benchmark. Fine-tuned LLM tương lai phải có endpoint API tương thích nếu thực hiện. |
| REQ-AI-14 | Model Gateway routing theo nhiệm vụ/độ khó/chất lượng/chi phí/quyền; privacy eligibility check trước routing, danh sách provider được phê duyệt, retry/fallback giới hạn, không fallback sang provider không phù hợp. |
| REQ-AI-15 | Trích dẫn tương tác chính xác đến điều/khoản/điểm, quote, nguồn, hiệu lực, phiên bản và lịch sử; câu không có căn cứ phải gắn trạng thái. |
| REQ-AI-16 | AI hỗ trợ toàn pipeline với validation; mô hình OCR, parser, embedding, reranker, LLM, verifier và framework chọn theo PoC. |
| REQ-AI-17 | Progress streaming hiển thị trạng thái thực thi, tài liệu và kết quả kiểm chứng; không xuất kết luận pháp lý chưa qua gate; không hiển thị suy luận nội bộ, secrets, log nhạy cảm. |
| REQ-AI-18 | Fallback có kiểm soát: nếu thiếu graph/temporal/verification thì hạ chức năng hoặc từ chối, không hạ chuẩn an toàn; request có trace và trạng thái lỗi rõ. |

# 7. App và giao diện

- REQ-WEB-01 MUST: React + Vite + TypeScript, trang chủ kết hợp AI search, danh mục, văn bản mới; tìm từ khóa/số hiệu/ngữ nghĩa, điều khoản, lĩnh vực, hiệu lực, thời gian, địa phương; đọc/tải văn bản gốc nếu được phép.
- REQ-WEB-02 MUST: Chat nhiều lượt, bố cục đóng/mở panel; interactive citation viewer highlight, version/history; giao diện tiến trình Agent và kiểm chứng. Tính năng Standard cho khách có giới hạn; đăng nhập cho lịch sử/tính năng cấp quyền. Không public tài liệu riêng tư.
- REQ-UI-01 MUST: Phong cách AI hiện đại + nghiên cứu chuyên nghiệp, bản sắc Việt Nam; light/dark/system; Design System kết hợp component library, hỗ trợ bàn phím, screen reader, cỡ chữ, ngôn ngữ đơn giản; VI/EN.
- REQ-UI-02 SHOULD: Chia sẻ types/API client từ OpenAPI, design tokens, localization; SEO phù hợp cho trang pháp luật công khai; chiến lược SSR/pre-render TBD không mặc định đổi framework.
- REQ-STUDIO-01 MUST: Dashboard quản trị, crawler/source, data validation, model/prompt/config, RAG Playground/traces, Agent visualizer, evaluation/ablation, release gate, token/cost/latency/error/data quality, quyền, review phản hồi.
- REQ-STUDIO-02 MUST: Toàn bộ nhóm chức năng có demo công khai. Diễn giải kỹ thuật đề xuất: demo đầy đủ chức năng trên sandbox dữ liệu công khai/giả lập, thao tác write/chạy tác vụ giới hạn quota; quản trị production vẫn riêng và yêu cầu MFA. Không công khai credentials, prompt bí mật, dữ liệu người dùng, quyền điều khiển production; nếu yêu cầu là mở trực tiếp production admin thì mâu thuẫn bảo mật (BLOCKER-03).
- REQ-MOBILE-01 LATER: React Native + Expo Android trước/iOS sau, backend chung, giao diện riêng, offline có timestamp và cảnh báo hiệu lực, camera/upload/share/push.
- REQ-DOC-01 LATER: Workspace nhiều tài liệu, extraction/OCR, clause-level comparison, adverse vs possibly unlawful distinction, đề xuất sửa/soạn nháp có trích dẫn, bảo mật từng tenant.
- REQ-USER-01 LATER: Saved items, workspace vụ việc, consent memory, export/share, fully private chat, notification, contribution/moderation/community; kiểm soát quyền và retention. Tính năng phụ thuộc V1 (auth, lịch sử, feedback, report) triển khai tối thiểu.

# 8. Kiến trúc phần mềm, repo, cloud

REQ-ARCH-01 MUST: Python + FastAPI cho backend, coarse-to-fine microservices; phạm vi service thiết kế đầy đủ, triển khai theo roadmap; không đồng nhất service boundary với một DB/máy chủ riêng.
REQ-ARCH-02 MUST: Polyrepo, mã nguồn private; tạo đủ repository cho mọi service ngay từ đầu sau khi danh mục service được phê duyệt trong SAD. Tạo skeleton không đồng nghĩa tất cả service code/deploy đồng thời. Đây là yêu cầu kế hoạch, chưa thực hiện thao tác tạo repo.
REQ-ARCH-03 MUST: Năm năng lực lưu trữ logic: relational PostgreSQL, vector, keyword/search, graph và object storage. Lựa chọn số lượng database vật lý theo PoC; pgvector, FTS, relationship tables, Qdrant, OpenSearch, Neo4j, S3-compatible chỉ là ứng viên. Source of truth, quyền ownership/schema, consistency, index versioning, reindex/recovery và API contract cần thiết kế.
REQ-ARCH-04 SHOULD: Một repo quản lý trung tâm docs/ADR/contract/infra/integration tests/release manifest, sinh SDK từ OpenAPI, pin version, shared package có version, trace xuyên service. Không dùng chung schema write tùy ý.
REQ-CLOUD-01 MUST: Local + Cloud; Managed Services cho production; ưu tiên kết hợp Cloudflare/GCP/provider khác dựa giá, năng lực và quyền bảo mật. Trial GCP 300 USD/3 tháng theo kế hoạch của người dùng, xác minh điều kiện hiện hành trước dùng; local trước rồi cloud benchmark. Không giả định giá/quota/trial còn hiệu lực hoặc đủ trả LLM.
REQ-CLOUD-02 MUST: Cloud demo khả năng phục vụ liên tục, monitoring, quota, cost cap cấp request/account/platform; scale theo tải, không yêu cầu worker idle chạy 24/7. Chi phí sau trial phải dự toán.
REQ-CLOUD-03 MUST: Dev/Testing/Staging/Production tách dữ liệu và credential; CI/CD, security scan, test, AI gate, phê duyệt, canary, rollback; versioned images và manifest dữ liệu/model/prompt/rule.
REQ-CLOUD-04 SHOULD: Cloudflare edge/DNS/WAF/bot; GCP container application workloads và managed infrastructure; region, runtime, queue, secrets, object và database chọn sau PoC. Không chốt SKU hoặc giá chưa kiểm chứng.

### Danh mục ranh giới service — đề xuất đầu vào SAD, không phải repo đã tạo

| Service boundary | Nhiệm vụ |
|---|---|
| Account & Workspace | Identity integration, permissions, tenants, chat/workspace |
| Legal Knowledge | Văn bản, version, taxonomy, provenance, rule/graph ownership |
| Data Ingestion | Source adapters, parser/OCR, validation, jobs |
| Retrieval Engine | Search, indexes, temporal/graph/multi-hop, reranking |
| AI Orchestrator | Routing workflow, Agent, reason/verify |
| Model Gateway | Provider, routing policy, quota, cost |
| Document Intelligence | Private documents, extraction, analysis (LATER) |
| Evaluation Service | Benchmark, regression, release gate |
| Legal Monitoring | Subscriptions/notifications (LATER) |
| Billing/Enterprise | Entitlement, billing, enterprise features (LATER; phân rã TBD) |
| Community | Contribution/discussion/moderation (LATER; ingestion interface) |

Repo web, AI Studio, mobile, system-control/docs/infra và shared contracts cũng cần hoạch định. Số service/repository chính thức được chốt trong SAD trước tạo skeleton; không tạo repo GitHub hoặc cloud resources trong lần tổng hợp yêu cầu này.

# 9. Security, privacy và compliance

- REQ-SEC-01 MUST: Managed Auth, email/password, Google OAuth, phone OTP; Enterprise SSO LATER; RBAC+ABAC theo tài nguyên/tổ chức/điều kiện; MFA tùy chọn người dùng, bắt buộc admin/expert.
- REQ-SEC-02 MUST: Tenant isolation mọi lớp, kiểm tra access tại service, DB/query/index/object/cache/log; dedicated enterprise LATER; encryption in transit/at rest, trường nhạy cảm, centralized key management và rotation.
- REQ-SEC-03 MUST: Retention theo loại dữ liệu/chế độ/gói; user consent rõ nếu dùng dữ liệu cải thiện AI, privacy-preserving; hỗ trợ yêu cầu truy cập/chỉnh sửa/xóa theo chính sách được thẩm định; private mode không quảng cáo no-retention nếu chưa kiểm soát provider/trace/backup/cache.
- REQ-SEC-04 MUST: Ưu tiên Việt Nam khi khả thi, kiểm soát dữ liệu ra nước ngoài; ẩn/thay thế thông tin nhạy cảm, approved provider, từ chối khi không có phương án an toàn; local/self-host cho tiền xử lý, không gửi LLM tự động ngoài policy.
- REQ-SEC-05 MUST: Agent tool ACL, least privilege, không cấp quyền DB admin, approval trước external effect/mutation; parser sandbox, malware scan, injection defense/quarantine, tách dữ liệu truy xuất khỏi chỉ dẫn.
- REQ-SEC-06 MUST: Audit log sự kiện admin, data change, sensitive access, tool calls, redact, integrity; secrets manager, no API key frontend, no sensitive trace public.
- REQ-SEC-07 MUST: Rate limiting, anti-bot, anomaly detection, quota token và request/account/platform budget; cancel runaway agent; giới hạn khách/Technical Reviewer; test cost failure.
- REQ-SEC-08 MUST: Câu hỏi rủi ro cao chỉ thông tin đã xác minh, giới hạn cá nhân hóa, chuyển chuyên gia khi có quy trình; không giả mạo dịch vụ chuyên gia.
- REQ-SEC-09 MUST: Tra cứu công khai mọi người; giới hạn AI/xử lý dữ liệu cá nhân theo tuổi và quy định; chính sách chi tiết TBD.
- REQ-SEC-10 MUST: Backup, PITR khi khả dụng, RPO/RTO theo service, thử phục hồi; SAST/DAST/dependency scan, AI red-team, API isolation tests, độc lập trước thương mại.
- REQ-SEC-11 MUST: Source rights, tư pháp/data protection, cross-border, AI risk classification, điều khoản và privacy notice, incident response và correction procedure cần được xác minh theo quy định thực tế trước release thích hợp. Không có xác nhận tuân thủ ở thời điểm lập baseline.
- REQ-SEC-12 MUST: Tách production admin khỏi public sandbox, synthetic/public approved demo data, hạn chế resettable mutations, redacted trace, không truy cập hội thoại thật.

# 10. Benchmark và MLOps

REQ-EVAL-01 MUST: Tối thiểu 1.000 test case đã kiểm chứng. Phân tầng theo lĩnh vực, loại tác vụ, độ khó, thời điểm, rủi ro, ngôn ngữ; nhãn L0 AI draft, L1 machine evidence check, L2 human source/answer check, L3 competent legal expert review. Chỉ L2/L3 thực sự đạt cấp tương ứng được tính vào tập đã kiểm chứng. Việc phân tầng nhu cầu L3 không tự biến case thành L3.
REQ-EVAL-02 MUST: AI hỗ trợ sinh + con người kiểm chứng, tình huống ẩn danh hợp lệ; thuật toán + nhiều model judge + manual; cộng đồng/chuyên gia sau V1 theo DEC-04. L3 và yêu cầu expert review là blocker nếu chưa có người đủ chuyên môn; không tự gắn L3 hoặc coi nhiều LLM là chuyên gia.
REQ-EVAL-03 MUST: Tập train/dev/tuning/test tách biệt; cố định test trước việc lựa chọn model, tránh leakage theo họ văn bản/tình huống; lưu snapshot nguồn, phân phối test, rubric, evidence, phiên bản config, timestamp, đánh giá bất đồng, confidence intervals và error categories; tỷ lệ split, số mẫu tối thiểu per domain TBD.
REQ-EVAL-04 MUST: So sánh baseline LLM không RAG, dense, hybrid, rerank, legal structure/temporal, graph/multi-hop, verification, agent; ablation có kiểm soát biến; đánh giá recall/nDCG/correctness/faithfulness/citations/temporal/abstention, safety, latency, cost; so sánh các mode cùng dữ liệu/test. Không bắt buộc fine-tune V1. Nếu một kỹ thuật V1 đã được chọn không cải thiện chất lượng, ghi rõ kết quả; không tự loại khỏi scope mà không có change control.
REQ-EVAL-05 MUST: Regression tự động khi đổi model, prompt, retrieval, data, graph, rules; chặn deploy khi gate fail; tracking, versioned dataset/model/prompt/config, trace, model registry, monitoring, phê duyệt model mới.
REQ-EVAL-06 MUST: Sau phát hành lấy mẫu/feedback, kiểm duyệt, root-cause, fix, bổ sung regression, rerun gate; bảo vệ privacy; có cơ chế khóa/tạm dừng chức năng lỗi và đính chính phù hợp.
REQ-EVAL-07 MUST: Công khai báo cáo benchmark, Architecture Overview, Technical Case Study, demo/video; private production source và kho dữ liệu; công bố mẫu dữ liệu khi có quyền, không mặc định công khai toàn bộ dataset/code.
REQ-EVAL-08 MUST: Không phát hành chế độ trả phí trước khi chứng minh lợi ích so Standard; Standard và Advanced chung chuẩn an toàn; P95 và cost per mode TBD theo benchmark; streaming progress được kiểm chứng.

## 10.1 AC V1 — ngưỡng đã chọn
| ID | Metric | Ngưỡng |
|---|---|---|
| AC-01 | Retrieval Recall@20 | ≥ 90% |
| AC-02 | nDCG@10 | ≥ 0,80 |
| AC-03 | Legal Answer Correctness | ≥ 90% |
| AC-04 | Faithfulness | ≥ 95% |
| AC-05 | Citation Precision | ≥ 98% |
| AC-06 | Temporal Validity Accuracy | ≥ 98% |
| AC-07 | Correct Abstention Rate | ≥ 90% |
| AC-08 | Trích dẫn không tồn tại | 0 trong bộ test nghiệm thu |
| AC-09 | Rò rỉ giữa tài khoản | 0 trong bộ test nghiệm thu |
| AC-10 | Benchmark đã kiểm chứng | ≥ 1.000 case L2/L3 thực tế |
| AC-11 | Phạm vi lĩnh vực | Mọi lĩnh vực theo taxonomy có ít nhất chức năng AI đã vượt gate; severity-specific restriction nhất quán |
| AC-12 | Graph chuyên sâu | Ontology và pipeline quyền/nghĩa vụ/điều kiện/ngoại lệ + provenance, temporal và kiểm thử; thước đo completeness/precision TBD |
| AC-13 | AI Core | Model/retrieval swap, agent/citation/temporal/verification end-to-end, regression tự động |
| AC-14 | Deployment | Cloud online, monitoring, quota/cost, build/test/release/rollback evidence |
| AC-15 | Portfolio | Demo công khai, Studio sandbox đủ chức năng, báo cáo, bằng chứng chủ dự án tự giải thích/sửa/debug |
| AC-16 | 14 tài liệu | Đầy đủ phiên bản phê duyệt trước PoC, ghi assumption/TBD rõ; revision theo bằng chứng sau PoC |

Các ngưỡng AC-01–07 phải có denominator, rubric, đơn vị đánh giá và tập holdout cố định; báo cáo macro/micro và từng strata, không dùng trung bình che lỗi nghiêm trọng. Mục tiêu bổ sung Citation Coverage, false abstention/useful answer rate, critical-severity failure, graph accuracy, extraction accuracy và confidence intervals phải xác định trong Evaluation Specification trước nghiệm thu. 0 lỗi trong mẫu không có nghĩa bằng chứng an toàn tuyệt đối. Không có lỗi nghiêm trọng đã biết ở phạm vi được mở.

## 10.2 Commercial (LATER)
Mục tiêu nghiên cứu trước đó: Recall@20 ≥95%, Correctness ≥95%, Faithfulness ≥98%, Citation Precision ≥99%, Temporal Validity Accuracy ≥99%, Correct Abstention ≥95%, không còn lỗi pháp lý nghiêm trọng đã biết, thẩm định chuyên môn rủi ro cao, đánh giá bảo mật độc lập, release gate theo lĩnh vực/rủi ro/tác vụ. Không áp dụng như tuyên bố kết quả thực tế hoặc điều kiện đủ pháp lý.

# 11. NFR và tham số chưa xác định

| ID | NFR | Yêu cầu / TBD |
|---|---|---|
| NFR-01 | Availability | Demo cloud truy cập được liên tục; SLO đo theo service TBD, không yêu cầu mọi worker chạy 24/7 |
| NFR-02 | Latency | P50/P95/P99, TTFT và time-to-verified-answer theo mode; target sau benchmark |
| NFR-03 | Load | 100–500 đăng ký; DAU, peak concurrency, throughput, request size, quota TBD |
| NFR-04 | Cost | Ngân sách dev/prod/tháng, hard cap ứng dụng, cảnh báo hóa đơn, cost per mode, chi phí sau trial TBD |
| NFR-05 | Data freshness | Độ trễ crawl → verify → index, reliability theo nguồn TBD |
| NFR-06 | Recovery | RPO/RTO theo service, error budget, backup/restore thử nghiệm; ngưỡng TBD |
| NFR-07 | Privacy | Retention/deletion theo loại dữ liệu, region/provider, age, consent; policy TBD |
| NFR-08 | Reproducibility | Snapshot, experiment manifest, logs/trace redacted, dependency versions |
| NFR-09 | Accessibility | Keyboard, screen reader, text size; tiêu chuẩn/test mức mục tiêu TBD |
| NFR-10 | Data quality | OCR, structure accuracy, metadata completeness, dedup, link/graph precision, coverage; ngưỡng TBD |
| NFR-11 | Security | Tenant isolation, deny by default, security testing, production credential isolation |
| NFR-12 | Maintainability | API versioning, contracts, integration tests, rollback, dependency pin |

Không mặc định ngân sách tối đa hoặc vendor fee. Dự toán = cloud compute + database/search/vector/graph + object/storage/backup/network + LLM tokens/calls/retry + embeddings/OCR + logging + chuyên gia/kiểm thử + chi phí khác; lập ba kịch bản sử dụng và kiểm soát khi hết trial.

# 12. Mâu thuẫn và quy tắc xử lý

| ID | Vấn đề | Trạng thái và cách diễn giải đề xuất |
|---|---|---|
| BLOCKER-01 | AI mọi lĩnh vực V1 vs từng lĩnh vực phải đạt gate, 2–3 tháng | Giữ nguyên cả hai; tổng thể V1 chỉ hoàn thành khi mọi lĩnh vực taxonomy có AI đạt gate. Một lĩnh vực fail => chỉ search, bản giới hạn là internal/preview thử nghiệm, không ghi nhận V1 hoàn tất. Taxonomy và minimum sample chưa chốt. |
| BLOCKER-02 | L2/L3 benchmark vs tự kiểm chứng rồi mới tìm chuyên gia | L2 được tự kiểm tra bằng nguồn; L3 đòi người đủ chuyên môn. Nếu không có bằng chứng L3, các case cần L3 phải gắn pending, không tính verified L3; không tuyên bố nghiệm thu L3/rủi ro cao. Giữ 1.000, không lặng lẽ giảm; cần giải quyết bằng chuyên gia hoặc thay đổi requirement được phê duyệt. |
| BLOCKER-03 | Demo toàn bộ AI Studio vs secrets, admin MFA, private code/data | Đề xuất public full-feature sandbox với dữ liệu công khai/giả lập, limit và reset; prod admin riêng. Nếu chủ dự án muốn public production admin, xung đột với yêu cầu security, không đạt gate. |
| BLOCKER-04 | Hoàn thiện 14 tài liệu trước PoC vs model/db/cost/sizing chưa đo | Hoàn chỉnh nội dung bản v1 kế hoạch và yêu cầu trước PoC với assumptions/TBD/exit criteria; không thể chứng minh số liệu thực nghiệm trước chạy. ADR và revision sau PoC không bị coi là bỏ tài liệu. Nếu 'hoàn thiện' yêu cầu mọi thông số final từ đầu thì không khả thi. |
| RISK-01 | Deep graph toàn bộ lĩnh vực và phạm vi dữ liệu lịch sử | Hoàn thành ontology + pipeline + kiểm thử graph chuyên sâu trong V1 là MUST. Độ bao phủ/chất lượng cần chuẩn hóa và đo trước G1/G3; không coi graph schema rỗng là hoàn thành. |
| RISK-02 | 2–3 tháng, 30–40h/tuần, 1000 cases, solo | 240–480h, 10 phút/case ~167h chỉ review; còn các nhiệm vụ khác. Ưu tiên chất lượng; nếu trễ báo cáo chưa đạt, không hạ ngưỡng tự động. |
| RISK-03 | Tạo tất cả polyrepos sớm | Chốt catalog trong SAD rồi tạo skeleton/contract; deploy theo milestone. CI templates và repo control đề xuất. |
| RISK-04 | 100% API và tài liệu nhạy cảm | Privacy-first allowlist và redaction; không có provider phù hợp thì từ chối, không fallback. |
| RISK-05 | Demo online, chi phí mở | App caps + quota, dự toán measured; không dùng trial như mô hình tài chính lâu dài. |
| RISK-06 | Mã nguồn private và bằng chứng cá nhân | Công khai report/case study/demo, trace sanitized; review code riêng theo quyền, không tự public. |
| RISK-07 | Độ bao phủ corpus/graph, quyền khai thác, độ đúng Rule Engine | Khảo sát và kiểm chứng trước sử dụng; không mẫu hóa thành kết luận nghiệp vụ chưa thẩm định. |
| RISK-08 | Khả năng tự debug, tích hợp do coding agents | Task nhỏ, tests thật/integration, evidence, review thủ công, không bỏ qua failing tests hoặc tuyên bố pass nếu không chạy. |

# 13. 14 tài liệu nền bắt buộc trước PoC

DEC-12: tạo và hoàn thiện cả 14 tài liệu trước khi thực hiện PoC, với phạm vi đã thống nhất, giả định, nguồn bằng chứng, TBD/exit criterion rõ. Các chỉ số chưa có dữ liệu được mô tả cách kiểm chứng; không bịa thông số. Sau PoC phải cập nhật theo ADR/changelog; không coi bản thiết kế giả định là kết quả thực nghiệm. Baseline này không thay thế 14 tài liệu và chưa tuyên bố chúng đã hoàn thành.

| # | Hồ sơ | Nội dung/đầu ra tối thiểu |
|---|---|---|
| 01 | Product Requirements Document (PRD) | Product vision, personas, scope V1/LATER, priorities, business outcomes, gates |
| 02 | Software Requirements Specification (SRS) | Actors, functional/NFR, business rules, interfaces, use cases, RTM |
| 03 | System Architecture Document (SAD) | Context/container/service, boundaries, repo catalog, contracts, data ownership, ADR |
| 04 | AI/RAG Architecture Specification | Routing, indexing/retrieval/graph/temporal, model gateway, verification, agents, failure policies |
| 05 | Data Engineering Specification | Source register, data model/lineage, adapters, OCR/parse, quality, update, validation |
| 06 | Database Design | ERD, provision/version, bitemporal, ontology mapping, indexes, persistence/ownership, alternatives |
| 07 | Benchmark & Evaluation Specification | Dataset design, L2/L3, splits, metrics/rubrics, tests, ablation, release gates |
| 08 | Security Architecture & Threat Model | DFD, trust boundaries, auth, tenant, privacy, provider policy, threat mitigations |
| 09 | UI/UX Specification | Sitemap, screen flows, design tokens, accessibility, citations, demo roles |
| 10 | Cloud Infrastructure & Deployment Plan | Dev/test/staging/prod, topology, monitoring, CI/CD, rollout, recovery, cost controls |
| 11 | Cost Estimation | Assumptions, vendor candidates, range/scenarios, trial/post-trial, budget approval |
| 12 | Development Roadmap & Backlog | 8–12 weeks target, milestones, dependencies, effort, scope/change trade-offs |
| 13 | AI Coding Agent Development Guidelines | Task contract, context, tests, review, security, evidence, no unverified pass, human understanding |
| 14 | Acceptance Criteria & Test Plan | Requirement-to-test-to-evidence matrix, gate conditions, severity, release/rollback |

Supporting records: RTM, ADR, Risk Register, Data Source Registry, Model and Prompt Registry, Legal Rule Registry, Experiment Log, Release Gate Reports, Known Issues and Limitations.

# 14. PoC kế hoạch (chỉ bắt đầu sau 14 hồ sơ)

| POC ID | Câu hỏi cần giải quyết | Bằng chứng đầu ra |
|---|---|---|
| 01 | Nguồn nào có quyền khai thác và độ bao phủ đo được? | source inventory/taxonomy/format/rights, sizing |
| 02 | Parser/OCR có giữ đúng cấu trúc? | gold samples, extraction error report |
| 03 | Retriever/embedding/reranker nào hiệu quả? | held-out recall/nDCG, latency, cost |
| 04 | Temporal có truy xuất đúng phiên bản tại ngày yêu cầu? | bitemporal tests, partial validity, transition cases |
| 05 | Graph chuyên sâu có chính xác và hữu ích? | node/edge precision/coverage, evidence, multi-hop ablation |
| 06 | API LLM nào đáp ứng chất lượng/privacy/cost? | provider allowlist, benchmark, token and cost |
| 07 | Verification phát hiện sai trích dẫn/hiệu lực/claim? | claim-evidence test, false positive/negative |
| 08 | Agentic tăng chất lượng xứng chi phí? | controlled comparison, limits, failure/recovery |
| 09 | Hosting nào phù hợp ngân sách và tải? | cloud configuration, load, reliability, actual metered cost |
| 10 | Bảo mật AI/tenant có pass? | threat tests, injection, permissions, leakage, upload isolation |
| 11 | Kiểm chứng 1.000 case khả thi? | measured time per case, reviewer provenance, L2/L3 counts |

Mỗi PoC có hypothesis, test design, dataset/version, expected evidence, measured results, failure/limits và ADR. Không coi PoC chưa chạy là thành công.

# 15. Milestones và acceptance gates

| Gate | Điều kiện và sản phẩm |
|---|---|
| G0 — Requirements | Baseline, các blocker được nhận diện, đủ 14 tài liệu versioned trước PoC; giả định/TBD và test plan rõ |
| G1 — Data / PoC | Kiểm tra nguồn, chất lượng, taxonomy, quyền khai thác, data/graph model và sizing; ADR công nghệ |
| G2 — Retrieval | Search, dense/sparse/hybrid/rerank, repeatable metrics |
| G3 — Legal Core | Temporal, full deep graph, Rule Engine, legal citation/verification, tested end-to-end |
| G4 — Agentic | Standard + Advanced, bounded tools/iterations, comparison, risk controls |
| G5 — Evaluation | 1.000 case verified, genuine L2/L3 evidence, held-out test and thresholds per strata, release gate; nếu L3 chưa đáp ứng thì chưa PASS hạng mục |
| G6 — Cloud/Studio | Public full-feature safe sandbox, production role isolation, CI/CD, monitoring/cost/security/load/restore evidence |
| G7 — Technical Preview | G0–G6 PASS, all-domain AI per BR-RELEASE-01, required metrics, demo, reports, portfolio competence; features/risk scopes chưa đạt không bật; bản thiếu MUST không được gọi hoàn thành |
| G8 — Commercial (LATER) | Legal review, security independent assessment, release gates by risk/domain, business readiness, expert verification, provider/data rights |

Mục tiêu 12 tuần tham chiếu: 1–2 nền tảng tài liệu/khảo sát chuẩn bị; 3–4 PoC/dữ liệu; 5–6 retrieval/baseline; 7–8 temporal/graph/rules; 9–10 agent/Studio; 11–12 evaluation/cloud/portfolio. Đây là khung kế hoạch ban đầu cần dự toán effort thực tế sau hồ sơ và PoC. Nếu không đủ thời gian, báo cáo trạng thái và đề nghị thay đổi phạm vi/tiến độ; tuyệt đối không giả lập acceptance.

# 16. Portfolio và quy trình AI Coding Agent

- Công khai demo, tài khoản Technical Reviewer, report benchmark, Architecture Overview, Technical Case Study, báo cáo nghiên cứu kỹ thuật và kết quả ablation. Không tự public mã nguồn production.
- Evidence của chủ dự án: tự giải thích RAG lifecycle, chunking, sparse/dense, embedding/reranking, graph/temporal, nguồn và citation, MLOps, API/CI/CD, bảo mật; tự reproduce một pipeline, debug lỗi retrieval/citation/version/model, đọc trace, sửa component và chứng minh regression.
- Task AI Agent: mục tiêu nhỏ + requirement ID + input/contract + acceptance tests + phạm vi thay đổi; review trước merge; real integration tests, không mock che lỗi; không tự ý đổi requirement, xóa test hoặc dùng fake dữ liệu như production proof; ghi lệnh chạy, kết quả và limitations.
- Quản lý Agile/milestone/ADR/acceptance gates. Mọi thay đổi baseline có change request, lý do và ảnh hưởng đến scope/cost/risk/acceptance; chủ dự án phê duyệt. Cập nhật RTM, tài liệu và test plan tương ứng.

# 17. Trạng thái và điều kiện tiếp theo

Đã hoàn thành khai thác yêu cầu 11/11 và ghi nhận 12/12 lựa chọn cuối cùng. Phạm vi/tầm nhìn và công nghệ nền đã được baseline; các xung đột BLOCKER-01–04 không được coi là giải quyết bằng cách ghi nhận. Model/database/vendor, taxonomy/coverage, graph acceptance, split/rubric, budget/storage/load/latency/RPO/RTO, pháp lý/privacy/retention chi tiết và nguồn lực reviewer đều chưa có bằng chứng đủ để chốt thông số cuối.

Hồ sơ này không phải toàn bộ PRD/SRS/SAD hay 14 tài liệu đã hoàn tất; không có PoC, deployment, benchmark hoặc repo GitHub mới được chạy/tạo ở bước này. Bước được phép tiếp theo theo DEC-12 là xây dựng đủ 14 tài liệu trước PoC, giữ rõ điểm chưa xác minh; sau đó mới triển khai nghiên cứu/PoC và hoàn thiện thiết kế bằng ADR, không bắt đầu lập trình production hàng loạt.
