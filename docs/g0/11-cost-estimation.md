# 11. Cost Estimation

Phiên bản 0.2 · 26/11/2026 · USD, giả định mô phỏng, chờ duyệt ngân sách

## Đơn giá và phạm vi

| Hạng mục | Đơn giá, công thức và phạm vi |
|---|---|
| API LLM | Mốc chuẩn Gemini 2.5 Flash-Lite Standard paid USD 0,10/triệu token đầu vào văn bản và USD 0,40/triệu token đầu ra. Nhân hệ số 5x/10x/20x để thử độ nhạy giá cho route chất lượng cao hơn. Model, số call, replay, khả năng đáp ứng AC và điều kiện dữ liệu chờ POC-06/08. [Bảng giá Gemini](https://aistudio.google.com/docs/pricing#gemini-2.5-flash-lite) |
| DB compute | Cloud SQL Enterprise non-HA giả định USD 0,0413/vCPU-giờ + USD 0,007/GiB RAM-giờ. Nhân số giờ instance chạy theo từng môi trường, kể cả chạy idle. Kiểm tier/machine/region/HA trước báo giá. [Cloud SQL pricing](https://cloud.google.com/sql/pricing) |
| Object | R2 Standard gross ở mức USD 0,015/GB-tháng, USD 4,50/triệu Class A và USD 0,36/triệu Class B. Mô hình dự phòng làm tròn lên đơn vị triệu cho từng loại operation trên mỗi môi trường. Đối chiếu hóa đơn theo phạm vi tài khoản lúc PoC, chưa trừ free tier. [R2 pricing](https://developers.cloudflare.com/r2/pricing/) |
| Hạ tầng còn lại | Khoảng dự phòng giả định cho API compute, DB storage/backup, logs, queue và network. Tính riêng theo môi trường, kể cả storage/backup staging còn giữ khi DB dừng. [Cloud Run pricing](https://cloud.google.com/run/pricing) |

Tổng token theo answer bao gồm các call pipeline của một lượt. Mốc Standard là 8.000 input + 1.200 output (USD 0,00128 ở 1x), Advanced là 25.000 + 4.000 (USD 0,00410 ở 1x). Nhân hệ số giá và hệ số chi phí retry của từng kịch bản. Tách quota và ledger theo môi trường. Chi phí của benchmark và ingestion tính ở các dòng riêng.

## Ba kịch bản sau trial

| Đầu vào mỗi tháng | Thấp | Cơ sở | Cao |
|---|---:|---:|---:|
| Tài khoản đăng ký | 100 | 250 | 500 |
| Hệ số LLM / retry cho lượt hỏi | 5x / 1,10 | 10x / 1,15 | 20x / 1,25 |
| Production Standard / Advanced | 950 / 50 | 4.500 / 500 | 16.000 / 4.000 |
| Sandbox Standard / Advanced | 70 / 30 | 300 / 200 | 1.200 / 800 |
| Production DB vCPU / GiB / giờ | 1 / 3,75 / 730 | 2 / 7,5 / 730 | 4 / 15 / 730 |
| Sandbox DB vCPU / GiB / giờ | 1 / 3,75 / 730 | 1 / 3,75 / 730 | 2 / 7,5 / 730 |
| Staging DB vCPU / GiB / giờ | 1 / 3,75 / 80 | 1 / 3,75 / 160 | 2 / 7,5 / 320 |
| Production object GB-tháng / triệu A / triệu B | 20 / 0,05 / 0,5 | 100 / 0,2 / 3 | 500 / 2,2 / 12,4 |
| Sandbox object GB-tháng / triệu A / triệu B | 5 / 0,02 / 0,1 | 20 / 0,05 / 0,5 | 50 / 0,2 / 2 |
| Staging object GB-tháng / triệu A / triệu B | 10 / 0,05 / 0,25 | 50 / 0,1 / 1 | 200 / 0,5 / 3 |
| Dự phòng hạ tầng khác theo Production / Sandbox / Staging, USD | 10–35 / 5–15 / 5–15 | 25–80 / 10–30 / 10–35 | 60–240 / 20–75 / 25–100 |
| Eval case × cấu hình × lượt chạy | 300 × 3 × 1 | 600 × 6 × 2 | 1.000 × 8 × 4 |
| Ingest lần đầu trang OCR / đoạn Graph cần LLM | 2.500 / 1.000 | 15.000 / 6.000 | 90.000 / 30.000 |
| Tỷ lệ ingest bổ sung hàng tháng so với lần đầu | 5% | 10% | 15% |
| Dev tools/CI bổ sung, USD/tháng | 5–20 | 10–40 | 25–100 |

Eval/ablation và regression dự toán 12.000 input + 2.000 output token cho mỗi case × cấu hình × lượt, gồm tổng inference/judge và phần gọi lại ước lượng trong token. Đơn giá là USD 0,002 ở 1x. Chi phí smoke test LLM ở staging lấy trong budget này. Ingestion đầu kỳ dự toán USD 0,0025/trang OCR (giả định, chưa chọn SKU), cộng USD 0,00054 ở 1x cho mỗi đoạn Graph gọi LLM (3.000 input + 600 output). Áp hệ số giá cho phần LLM, đo chi phí OCR/extraction có retry riêng tại POC-02/05/06. Cập nhật tháng tính theo tỷ lệ tương ứng của lần đầu. Review con người lập dự toán riêng theo giờ và người phù hợp.

| Chi phí, USD | Thấp | Cơ sở | Cao |
|---|---:|---:|---:|
| Production, gồm LLM lượt hỏi | 72,29–97,29 | 220,52–275,52 | 1204,93–1384,93 |
| Public Studio Sandbox, gồm LLM demo | 60,42–70,42 | 78,32–98,32 | 244,99–299,99 |
| Staging, phần hạ tầng | 15,41–25,41 | 26,42–51,42 | 76,81–151,81 |
| Tổng 3 môi trường trước Eval/Ingestion/Dev | 148,12–193,12 | 325,25–425,25 | 1526,73–1836,73 |
| Eval/Ablation/Regression, tháng giả định | 9,00 | 144,00 | 1280,00 |
| Ingestion/OCR/Graph lần đầu, một lần | 8,95 | 69,90 | 549,00 |
| Ingestion/OCR/Graph cập nhật tháng | 0,45 | 6,99 | 82,35 |
| Tổng định kỳ đã mô phỏng, gồm Dev tools/CI | **162,56–222,56** | **486,24–616,24** | **2914,08–3299,08** |

Làm tròn sau khi cộng chi phí chưa làm tròn. Tháng nạp corpus cộng chi phí lần đầu. Các khoản cần báo giá riêng gồm thuế, công sức L2/L3 và kỹ sư, auth/OTP, embedding/reranker trả phí, dịch vụ search/vector/graph phụ, edge trả phí và HA. Quyết định mua cần thêm sizing, quote và billing export.

## Độ nhạy LLM với cùng tải cơ sở

| Khoản LLM, USD | 1x | 5x | 10x | 20x |
|---|---:|---:|---:|---:|
| Lượt hỏi Production và Sandbox, mỗi tháng | 10,37 | 51,83 | 103,66 | 207,32 |
| Eval/Ablation/Regression, mỗi tháng | 14,40 | 72,00 | 144,00 | 288,00 |
| Trích xuất Graph bằng LLM, lần đầu | 3,24 | 16,20 | 32,40 | 64,80 |

## Đối chứng giảm chi phí

- **POC-06.** Chạy cùng model/route, snapshot và bộ case, so lượt không có cached tokens với lượt có cache hit trên prefix đã duyệt, ưu tiên văn bản luật công khai lặp lại. Ghi token input thường, token cache hit, output, retry, phí tạo/lưu cache nếu có, TTL, latency và kết quả theo rubric. Báo tỷ lệ token hit và chi phí trên lượt đạt rubric. Trong kịch bản 10×, phần input trước caching là khoảng 64,29 USD cho lượt hỏi và 86,40 USD cho eval mỗi tháng. Với eval offline, đo thêm Batch khi route hỗ trợ bằng cùng cấu hình và tập đánh giá, ghi thời gian hoàn tất và chi phí thực trả. [Context caching](https://aistudio.google.com/docs/caching) · [Giá Gemini theo chế độ](https://aistudio.google.com/docs/pricing#gemini-2.5-flash-lite).
- **POC-09.** Dùng Sandbox compute 49,31 USD/tháng trong kịch bản cơ sở làm mốc. So Cloud SQL dedicated đang dự toán với shared-core chạy liên tục và PostgreSQL scale-to-zero trên cùng tải, region được phép và dữ liệu Sandbox. Ghi tiền compute, storage, backup/restore và egress. Đo P95 lượt demo đầu sau idle, tải đồng thời, giới hạn pool và khả năng dùng migration/extensions cần thiết. Kiểm điều kiện SLA của SKU và đo restore trước khi chọn. [Cloud SQL pricing](https://cloud.google.com/sql/pricing) · [PostgreSQL scale-to-zero](https://neon.com/docs/introduction/scale-to-zero).

Khoản tiết kiệm vào dự toán sau khi đối chiếu usage hoặc hóa đơn theo route/SKU trong PoC.

## Trial, lịch môi trường và phê duyệt

Google Cloud công bố free trial 300 USD trong 90 ngày theo điều kiện đủ tiêu chuẩn. Kiểm eligibility, SKU, hạn và phạm vi credit. Dự toán trên thể hiện chi phí sau trial và chưa trừ credit. Theo dõi gross/net, chi phí API ngoài credit và ngày hết trial. [Google Cloud Free Program](https://docs.cloud.google.com/free/docs/free-cloud-features).

Staging chạy theo lịch benchmark/restore/canary, dừng DB khi hết cửa sổ thử nghiệm nếu SKU hỗ trợ, giữ chi phí storage/backup. Sandbox ưu tiên API/worker scale-to-zero khi idle, vẫn dự phòng DB chạy đủ tháng để demo khả dụng. Kiểm tương thích SKU, cold-start và SLA trước quyết định. [Kế hoạch cloud](10-cloud-deployment.md#môi-trường-và-topology) · [Dừng Cloud SQL](https://docs.cloud.google.com/sql/docs/postgres/start-stop-restart-instance).

Chủ dự án duyệt hạn mức riêng môi trường, tuần benchmark, ingestion một lần, quota tài khoản và ngưỡng tạm dừng. POC-06/09/11 phải cung cấp token/call thực, billed hours, storage, log, network, chi phí reviewer và ngân sách ngoài trial. Dùng reservation và kết toán usage ở cấp ứng dụng, báo động billing và dừng route tốn phí khi hết hạn mức đã duyệt. [Cloud Billing budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets).

[Căn cứ baseline REQ-CLOUD-01/02, NFR-04 và POC-06/09/11](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md)
