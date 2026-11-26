# 12. Development Roadmap & Backlog

Phiên bản 0.2 · 26/11/2026 · Kế hoạch phụ thuộc gate

## Roadmap và effort

| Cửa sổ tham chiếu | Backlog và gate | Evidence chính | Agent-assisted engineering | Human review/approval |
|---|---|---|---:|---:|
| Tuần 1–2 | B01 hồ sơ, catalog và G0. Tạo skeleton private sau duyệt | Phiên bản duyệt, 16 repo inventory, cách sync contract và kiểm codegen ở commit đầu của contracts | 8–16 h | 18–28 h |
| Tuần 3–4 | B02 nguồn, parser/OCR, dữ liệu và pilot review G1 | POC-01/02/11, rights, quality, taxonomy, sizing, mô hình graph và fixture toàn vẹn migration | 12–24 h | 12–25 h |
| Tuần 5–6 | B03 search, dense/hybrid/rerank và API G2 | POC-03, manifest index, repeated metrics | 15–30 h | 8–16 h |
| Tuần 7–8 | B04 temporal, deep graph, rule và verification G3 | POC-04/05/07, gold set, citation/version E2E | 24–45 h | 18–34 h |
| Tuần 9–10 | B05 Standard/Advanced. B06 Web + Studio sandbox, G4 | POC-06/08, mode comparison, controls, progress và sandbox flows | 18–35 h | 10–20 h |
| Tuần 3–12, xen kẽ | B07 dataset, human review L2/L3, regression và G5 | Holdout đã khóa, report theo tầng, ≥1.000 case đủ level | 12–24 h | 160–280 h |
| Tuần 11–12 | B08 cloud, security và recovery G6 | POC-09/10, metered spend, public sandbox, isolation, rollback/restore | 24–45 h | 16–32 h |
| Sau G0–G6 PASS | B09 portfolio và release G7 | Replay/debug của chủ dự án, hồ sơ công khai, mọi domain có AI qua gate | 4–8 h | 12–22 h |
| Tổng | | | 117–227 h | 254–457 h |

Ước lượng v0.2 là 371–684 giờ công. Cột agent-assisted tính thời gian kỹ sư giao việc, tích hợp và sửa trực tiếp với agent, chưa tính thời gian agent chạy không cần giám sát. Cột human tính kiểm diff, quyết định kiến trúc, quyền nguồn, review dataset và ký gate. Khoảng 160–280 giờ review/approval cho B07 giả định 8–14 phút × 1.000 case và khoảng 27–47 giờ cho chuẩn bị, xử lý bất đồng và kiểm lại. Điểm tham chiếu 10 phút/case là khoảng 167 giờ trước khi cộng xử lý bất đồng. Khi có chuyên gia, tách giờ L3 do họ thực hiện khỏi capacity của chủ dự án và theo dõi lịch chờ riêng. POC-11 đo median/P90 và tỷ lệ case cần L3. Dùng 1 task triển khai chính và 1 luồng kiểm chứng đang chạy, ưu tiên throughput review trước khi tăng WIP.

Khung 8–12 tuần × 30–40 giờ là 240–480 giờ. Dự toán v0.2 đi qua trần khung này và chưa phản ánh thời gian chờ quyền nguồn/chuyên gia. Sau G1, tính lại bằng dữ liệu thực và quyết định lịch hoặc change request theo baseline nếu vượt capacity. Tuần 1–2 xác định kênh chính thức để hỏi quyền SRC-02/05 và tiêu chí tuyển reviewer L3. Chỉ liên hệ và lưu trao đổi theo phạm vi được chủ dự án cấp. PoC bắt đầu sau phê duyệt G0. [Theo dõi quyền nguồn và L3](registers.md#quyết-định-mở).

## Kế hoạch chạy PoC sau G0

Mỗi thử nghiệm có run ID, hypothesis, sample/version/dataset rights, controls và config, máy/region, expected evidence, observed results, failure/limits và ADR. POC-01/02/11 đi trước để chốt quyền, chất lượng và năng lực review. G1 khóa phạm vi và cách đo cho graph, G3 đo pipeline. POC-09/10 chạy khi staging có các thành phần và kiểm soát cần đo. Ngưỡng PoC dùng chọn kỹ thuật. AC V1 theo [Test Plan](14-acceptance-test-plan.md).

| Pha | PoC | Giả thuyết và cách kiểm | Bằng chứng cần lưu |
|---|---|---|---|
| G1 | POC-01 | Nguồn chính thức ưu tiên có thể khai thác đúng quyền và đo coverage. Đối chiếu catalog với 9 domain pilot và sub-domain | Source rights, coverage/catalog counts, khoảng trống taxonomy, format, sizing |
| G1 | POC-02 | Parser/OCR giữ cấu trúc trên gold samples văn bản và scan có bảng/phụ lục | Extraction metrics, diff theo định dạng và lỗi |
| G1 | POC-11 | Kế hoạch holdout theo domain, metric và cell khả thi với thời gian review đo trong pilot | Số group đủ điều kiện, split, median/P90, reviewer provenance, số L2/L3 thực tế và giờ review dự kiến |
| G2 | POC-03 | Hybrid/rerank đạt lợi ích so dense và keyword trên pilot/dev split | Recall/nDCG, latency/cost, config theo cùng queries |
| G3 | POC-04 | Bitemporal tái hiện snapshot, sửa ghi nhận muộn, hiệu lực từng phần và chuyển tiếp | Version assertions, replay và query plans |
| G3 | POC-05 | Graph structural và deontic có provenance và cải thiện multi-hop | Gold node/edge precision/coverage từng tầng và ablation |
| G3 | POC-07 | Verification chặn trích dẫn hỏng, claim ngoài căn cứ và sai hiệu lực | Confusion report, false positive/negative và cases. Kiểm judge thực trên route thử đã duyệt nếu dùng. Fixture chỉ chứng minh phần deterministic và contract |
| G4 | POC-06 | API LLM đáp ứng data class, chất lượng VI/EN, latency/cost. Đo cache trên prefix lặp và Batch cho eval offline | Provider terms, policy check, cache hit tokens, storage/TTL, thời gian và chi phí thực theo route |
| G4 | POC-08 | Bounded Advanced có lợi ích đo được so Standard cùng evidence | Paired results, tool budgets, timeout/cancel/recovery |
| G6 | POC-09 | Cloud đáp ứng tải, reliability, region policy và chi phí. So DB Sandbox dedicated, shared-core và scale-to-zero | Load, P95 sau idle, extensions, restore, tổng chi phí theo SKU và topology ADR |
| G6 | POC-10 | ACL, tool, egress, parser và tenant controls chặn vượt quyền | Isolation logs, privacy/egress tests, security report |

## Backlog sau V1

B10 Android rồi iOS, offline có timestamp, camera/share/push. B11 Document Intelligence, upload, OCR và so sánh/soạn. B12 workspace, consent memory, export và fully private mode theo policy. B13 monitoring và community moderation. B14 legal calculators và Expert Research, dựa trên benchmark. B15 billing, API, enterprise SSO/dedicated và G8. B16 fine-tuning khi có dữ liệu và bằng chứng cần thiết. Các task mới link change record, requirement và gate. Chi tiết effort ở thời điểm mở scope.

[Căn cứ baseline §§3, 14–16](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md)
