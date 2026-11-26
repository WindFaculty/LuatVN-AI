# Ma trận truy vết yêu cầu

Phiên bản 0.2 · 26/11/2026 · Liên kết thiết kế và kế hoạch kiểm thử

Các định danh lấy từ [Requirements Baseline v1.0](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md). Cột UC dẫn đến use case trong [SRS](02-srs.md). Cột suite dẫn đến bằng chứng tối thiểu trong [Test Plan](14-acceptance-test-plan.md). Các suite triển khai ở trạng thái `NOT_RUN`. AC-16 chờ duyệt G0. Các mục LATER được xem lại khi mở phạm vi. Nghĩa của `—` là kiểm ở cấp hồ sơ, vận hành hoặc mục tiêu, chưa có use case riêng.

## Yêu cầu chức năng và kiến trúc

| Baseline ID | Yêu cầu theo dõi | Hồ sơ | Suite | Gate | UC |
|---|---|---|---|---|---|
| REQ-DATA-01 | Bao phủ dữ liệu và danh mục gốc | [05](05-data-engineering.md) | TST-02 | G1 | UC-01 |
| REQ-DATA-02 | Loại văn bản và phân loại giá trị | [05](05-data-engineering.md) | TST-02, TST-04 | G1/G3 | UC-01 |
| REQ-DATA-03 | Ưu tiên nguồn chính thức và quyền khai thác | [05](05-data-engineering.md) | TST-02, TST-10 | G1 | UC-04 |
| REQ-DATA-04 | Định dạng, OCR, layout, bảng và phụ lục | [05](05-data-engineering.md) | TST-02 | G1 | UC-04 |
| REQ-DATA-05 | Thu thập/cập nhật, checkpoint, retry, idempotency | [05](05-data-engineering.md) | TST-02 | G1 | UC-04 |
| REQ-DATA-06 | Validation, quarantine và điều kiện dùng làm căn cứ | [05](05-data-engineering.md) | TST-02, TST-06, TST-10 | G1/G3 | UC-04 |
| REQ-DATA-07 | Artifact bất biến và lineage phiên bản | [05](05-data-engineering.md), [06](06-database-design.md) | TST-02, TST-04 | G1/G3 | UC-04 |
| REQ-DATA-08 | Taxonomy revisions và coverage theo catalog | [05](05-data-engineering.md) | TST-02, TST-08 | G1/G5 | UC-01 |
| REQ-TEMP-01 | Hierarchy, stable IDs và hiệu lực từng phần | [06](06-database-design.md) | TST-04 | G3 | UC-02 |
| REQ-TEMP-02 | Valid/recorded times, snapshot và replay | [06](06-database-design.md) | TST-04, TST-06 | G3 | UC-02 |
| REQ-TEMP-03 | Loại nguồn, rule ưu tiên và applicability | [04](04-ai-rag.md), [06](06-database-design.md) | TST-04, TST-06 | G3 | UC-02 |
| REQ-GRAPH-01 | Ontology sâu cho quyền/nghĩa vụ/điều kiện/ngoại lệ | [06](06-database-design.md) | TST-05 | G3 | UC-02 |
| REQ-GRAPH-02 | Verified provenance, version, bounded multi-hop | [04](04-ai-rag.md), [06](06-database-design.md) | TST-05, TST-06 | G3/G5 | UC-02 |
| REQ-AI-01 | FastAPI, adapter modular và swap | [04](04-ai-rag.md) | TST-03, TST-07 | G2/G4 | UC-02 |
| REQ-AI-02 | Router, workflow và Agentic RAG, với luồng search độc lập LLM | [04](04-ai-rag.md) | TST-03, TST-07 | G2/G4 | UC-02, UC-03 |
| REQ-AI-03 | Chunk pháp lý, semantic, cha–con và IDs | [04](04-ai-rag.md) | TST-02, TST-03 | G2 | UC-02 |
| REQ-AI-04 | Dense/sparse/fusion/rerank, filters và graph | [04](04-ai-rag.md) | TST-03, TST-04, TST-05 | G2/G3 | UC-02 |
| REQ-AI-05 | Pipeline tình huống, verify, hỏi thêm/từ chối | [04](04-ai-rag.md) | TST-06, TST-07 | G3/G4 | UC-02, UC-03 |
| REQ-AI-06 | Căn cứ nội bộ đã xác minh và reformulation | [04](04-ai-rag.md) | TST-03, TST-06 | G2/G3 | UC-02 |
| REQ-AI-07 | Rule, citation/version/source verification và judge | [04](04-ai-rag.md), [06](06-database-design.md) | TST-04, TST-06, TST-08 | G3/G5 | UC-02 |
| REQ-AI-08 | Answer envelope và evidence fields | [04](04-ai-rag.md) | TST-06, TST-09 | G3 | UC-02 |
| REQ-AI-09 | VI/EN, thuật ngữ gốc và nguồn nguyên bản | [04](04-ai-rag.md), [09](09-ui-ux.md) | TST-06, TST-09 | G3/G6 | UC-02 |
| REQ-AI-10 | Tool ACL, caps, retry, cancellation và approval | [04](04-ai-rag.md), [08](08-security-threat-model.md) | TST-07, TST-10 | G4 | UC-03 |
| REQ-AI-11 | Memory và isolation theo tenant/private policy | [04](04-ai-rag.md), [08](08-security-threat-model.md) | TST-07, TST-10 | G4/G6 | UC-05 |
| REQ-AI-12 | Standard, Advanced và Expert Research LATER | [04](04-ai-rag.md), [12](12-roadmap-backlog.md) | TST-07, TST-08, TST-13 | G4/G5 | UC-03 |
| REQ-AI-13 | LLM API ngoài, adapter embedding/reranker | [04](04-ai-rag.md) | TST-07 | G4 | UC-03 |
| REQ-AI-14 | Gateway eligibility, routing, cost và fallback | [04](04-ai-rag.md), [08](08-security-threat-model.md) | TST-07, TST-10 | G4/G6 | UC-03 |
| REQ-AI-15 | Citation theo provision, quote, version/history | [04](04-ai-rag.md), [09](09-ui-ux.md) | TST-06, TST-09 | G3/G6 | UC-02 |
| REQ-AI-16 | AI hỗ trợ đầu cuối và validate từng adapter | [04](04-ai-rag.md), [05](05-data-engineering.md) | TST-02, TST-03, TST-06, TST-07 | G1/G4 | UC-02, UC-04 |
| REQ-AI-17 | Progress stream, final verification và redaction | [04](04-ai-rag.md), [09](09-ui-ux.md) | TST-07, TST-09, TST-10 | G4/G6 | UC-03 |
| REQ-AI-18 | Fallback an toàn và trace có trạng thái | [04](04-ai-rag.md) | TST-06, TST-07 | G3/G4 | UC-02, UC-03 |
| REQ-WEB-01 | React/Vite/TS, tra cứu, lọc và tài liệu gốc | [09](09-ui-ux.md) | TST-03, TST-09 | G2/G6 | UC-01 |
| REQ-WEB-02 | Chat, citation panel, lịch sử, quota và progress | [09](09-ui-ux.md) | TST-07, TST-09, TST-10 | G4/G6 | UC-02, UC-03, UC-05 |
| REQ-UI-01 | Themes, bilingual, accessibility và design system | [09](09-ui-ux.md) | TST-09 | G6 | UC-01, UC-02, UC-06 |
| REQ-UI-02 | OpenAPI typed clients, tokens, localization và SEO | [03](03-sad.md), [09](09-ui-ux.md) | TST-09 | G6 | UC-01 |
| REQ-STUDIO-01 | Data, config, playground, agent, eval, monitoring, feedback, roles | [09](09-ui-ux.md) | TST-08, TST-09, TST-11 | G6 | UC-06 |
| REQ-STUDIO-02 | Public full-feature sandbox và production MFA isolation | [08](08-security-threat-model.md), [09](09-ui-ux.md), [10](10-cloud-deployment.md) | TST-09, TST-10, TST-11 | G6 | UC-06 |
| REQ-MOBILE-01 | Android rồi iOS, offline, camera, share, push | [12](12-roadmap-backlog.md) | TST-13 | LATER | — |
| REQ-DOC-01 | Private Document Intelligence và multi-doc comparison | [12](12-roadmap-backlog.md) | TST-13 | LATER | — |
| REQ-USER-01 | Workspace riêng, consent, history, notification và community, gồm phụ thuộc V1 | [08](08-security-threat-model.md), [09](09-ui-ux.md), [12](12-roadmap-backlog.md) | TST-09, TST-10, TST-13 | G6/LATER | UC-05, UC-08 |
| REQ-ARCH-01 | Python/FastAPI và service boundaries | [03](03-sad.md) | TST-01, TST-03, TST-07 | G0/G4 | UC-02, UC-03 |
| REQ-ARCH-02 | Polyrepo private và đủ skeleton sau duyệt catalog | [03](03-sad.md) | TST-01 | G0 sau duyệt | — |
| REQ-ARCH-03 | Năm năng lực lưu trữ và alternatives có evidence | [06](06-database-design.md) | TST-02, TST-03, TST-05, TST-11 | G1/G3 | UC-02, UC-04 |
| REQ-ARCH-04 | Control repo, contract SDK/version và integration | [03](03-sad.md), [10](10-cloud-deployment.md) | TST-01, TST-03, TST-11 | G0/G6 | UC-07 |
| REQ-CLOUD-01 | Local + managed cloud và trial eligibility | [10](10-cloud-deployment.md), [11](11-cost-estimation.md) | TST-11 | G6 | UC-07 |
| REQ-CLOUD-02 | Availability, monitoring, quotas và cost caps | [10](10-cloud-deployment.md), [11](11-cost-estimation.md) | TST-11 | G6 | UC-07 |
| REQ-CLOUD-03 | Environment separation, CI/CD, release và rollback | [10](10-cloud-deployment.md) | TST-10, TST-11 | G6 | UC-07 |
| REQ-CLOUD-04 | Cloudflare/GCP candidates và vùng/SKU theo test | [10](10-cloud-deployment.md), [11](11-cost-estimation.md) | TST-11 | G6 | UC-07 |
| REQ-SEC-01 | Managed auth, RBAC/ABAC, OAuth/OTP và MFA | [08](08-security-threat-model.md) | TST-09, TST-10 | G6 | UC-05, UC-06 |
| REQ-SEC-02 | Tenant isolation, encryption, key management | [08](08-security-threat-model.md) | TST-10 | G6 | UC-05 |
| REQ-SEC-03 | Retention, consent và data rights | [08](08-security-threat-model.md) | TST-10 | G6 | UC-05 |
| REQ-SEC-04 | Region, redaction, approved provider và deny | [08](08-security-threat-model.md) | TST-07, TST-10 | G4/G6 | UC-03, UC-05 |
| REQ-SEC-05 | Tool/ingestion controls, authorization và quarantine | [08](08-security-threat-model.md) | TST-02, TST-07, TST-10 | G1/G4/G6 | UC-03, UC-04 |
| REQ-SEC-06 | Audit, secrets và trace redaction | [08](08-security-threat-model.md), [10](10-cloud-deployment.md) | TST-10, TST-11 | G6 | UC-05, UC-07 |
| REQ-SEC-07 | Rate/bot, quotas, anomaly detection và cancel | [08](08-security-threat-model.md), [10](10-cloud-deployment.md), [11](11-cost-estimation.md) | TST-07, TST-10, TST-11 | G4/G6 | UC-03, UC-05 |
| REQ-SEC-08 | High-risk/expert restrictions | [04](04-ai-rag.md), [08](08-security-threat-model.md) | TST-06, TST-08, TST-10 | G5/G6 | UC-02 |
| REQ-SEC-09 | Search public, age/PII gate | [08](08-security-threat-model.md), [09](09-ui-ux.md) | TST-09, TST-10 | G6 | UC-01, UC-05 |
| REQ-SEC-10 | Backup/PITR, scans, restore và đánh giá độc lập LATER | [08](08-security-threat-model.md), [10](10-cloud-deployment.md) | TST-10, TST-11 | G6/G8 | UC-07 |
| REQ-SEC-11 | Thẩm định quyền, privacy, AI, incident/correction | [05](05-data-engineering.md), [08](08-security-threat-model.md) | TST-02, TST-10 | G1/G6/G8 | UC-04, UC-08 |
| REQ-SEC-12 | Sandbox và production isolation | [08](08-security-threat-model.md), [10](10-cloud-deployment.md) | TST-09, TST-10, TST-11 | G6 | UC-06 |
| REQ-EVAL-01 | 1.000 case L2/L3 và strata | [07](07-benchmark-evaluation.md) | TST-08 | G5 | UC-07 |
| REQ-EVAL-02 | Review thực tế, adjudication và L3 pending | [07](07-benchmark-evaluation.md) | TST-08 | G5 | UC-07 |
| REQ-EVAL-03 | Leakage-safe split, holdout, rubric và reproducibility | [07](07-benchmark-evaluation.md) | TST-08 | G5 | UC-07 |
| REQ-EVAL-04 | Baselines, ablation, fairness giữa mode và metrics | [07](07-benchmark-evaluation.md) | TST-03, TST-05, TST-06, TST-07, TST-08 | G5 | UC-07 |
| REQ-EVAL-05 | Regression, tracking, registry và deployment gate | [07](07-benchmark-evaluation.md), [10](10-cloud-deployment.md) | TST-08, TST-11 | G5/G6 | UC-07 |
| REQ-EVAL-06 | Feedback, correction, regression và khóa phạm vi | [07](07-benchmark-evaluation.md), [08](08-security-threat-model.md), [09](09-ui-ux.md) | TST-08, TST-09, TST-10 | G6/G7 | UC-08 |
| REQ-EVAL-07 | Benchmark/report public và bảo vệ source private | [01](01-prd.md), [13](13-ai-coding-agent-guidelines.md) | TST-12 | G7 | — |
| REQ-EVAL-08 | So chất lượng Standard/Advanced, cost và gate premium | [04](04-ai-rag.md), [07](07-benchmark-evaluation.md) | TST-07, TST-08, TST-13 | G4/G5/LATER | UC-03 |

## Quy tắc nghiệp vụ

| Baseline ID | Yêu cầu theo dõi | Hồ sơ | Suite | Gate | UC |
|---|---|---|---|---|---|
| BR-LEGAL-01 | Phân biệt authentic, valid và applicable | [04](04-ai-rag.md), [05](05-data-engineering.md), [06](06-database-design.md) | TST-02, TST-04, TST-06 | G3 | UC-02, UC-04 |
| BR-LEGAL-02 | Cấm căn cứ draft hoặc chưa xác minh | [04](04-ai-rag.md), [05](05-data-engineering.md) | TST-02, TST-06 | G1/G3 | UC-02, UC-04 |
| BR-LEGAL-03 | Ngày, địa phương, thẩm quyền, facts và giới hạn | [04](04-ai-rag.md) | TST-04, TST-06 | G3 | UC-02 |
| BR-LEGAL-04 | Amendment, repeal, exception, transitional và conflict | [04](04-ai-rag.md), [06](06-database-design.md) | TST-04, TST-05 | G3 | UC-02 |
| BR-LEGAL-05 | Rule có version, evidence, tests và approval | [04](04-ai-rag.md), [06](06-database-design.md) | TST-04, TST-06 | G3 | UC-02 |
| BR-LEGAL-06 | EN giữ nguồn VI và nhãn dịch | [04](04-ai-rag.md), [09](09-ui-ux.md) | TST-06, TST-09 | G3/G6 | UC-02 |
| BR-LEGAL-07 | Partial hoặc abstain khi thiếu evidence | [04](04-ai-rag.md) | TST-06 | G3 | UC-02 |
| BR-LEGAL-08 | Hạn chế cá nhân hóa rủi ro cao và expert flag | [04](04-ai-rag.md), [08](08-security-threat-model.md) | TST-06, TST-08, TST-10 | G5/G6 | UC-02 |
| BR-RELEASE-01 | Release theo domain/task/risk, all-domain về G7 | [01](01-prd.md), [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-07, TST-08 | G7 | UC-02, UC-03 |
| BR-RELEASE-02 | Chuẩn an toàn chung mọi mode | [04](04-ai-rag.md), [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-07, TST-08, TST-13 | G4/G5/LATER | UC-03 |
| BR-SEC-01 | Không tái sử dụng dữ liệu riêng thiếu đồng ý | [08](08-security-threat-model.md) | TST-10 | G6 | UC-05 |

## Yêu cầu phi chức năng

| Baseline ID | Yêu cầu theo dõi | Hồ sơ | Suite | Gate | UC |
|---|---|---|---|---|---|
| NFR-01 | Availability và SLO theo service | [10](10-cloud-deployment.md) | TST-11 | G6 | UC-07 |
| NFR-02 | P50/P95/P99, TTFT, time-to-verified | [07](07-benchmark-evaluation.md), [10](10-cloud-deployment.md) | TST-07, TST-11 | G5/G6 | UC-03, UC-07 |
| NFR-03 | Tải đăng ký, concurrency và quota | [10](10-cloud-deployment.md), [11](11-cost-estimation.md) | TST-11 | G6 | UC-07 |
| NFR-04 | Dev/prod budgets, alerts và cost theo mode | [10](10-cloud-deployment.md), [11](11-cost-estimation.md) | TST-07, TST-11 | G6 | UC-07 |
| NFR-05 | Crawl, verify, index freshness | [05](05-data-engineering.md), [10](10-cloud-deployment.md) | TST-02, TST-11 | G1/G6 | UC-04, UC-07 |
| NFR-06 | RPO/RTO và restore drill | [08](08-security-threat-model.md), [10](10-cloud-deployment.md) | TST-10, TST-11 | G6 | UC-07 |
| NFR-07 | Privacy, age, consent, retention và provider policy | [08](08-security-threat-model.md) | TST-07, TST-10 | G6 | UC-05 |
| NFR-08 | Reproducibility và trace redaction | [07](07-benchmark-evaluation.md), [10](10-cloud-deployment.md), [13](13-ai-coding-agent-guidelines.md) | TST-08, TST-11, TST-12 | G5/G7 | UC-07 |
| NFR-09 | Accessibility | [09](09-ui-ux.md) | TST-09 | G6 | UC-06 |
| NFR-10 | OCR, metadata, dedup, graph và coverage | [05](05-data-engineering.md), [06](06-database-design.md) | TST-02, TST-05 | G1/G3 | UC-04 |
| NFR-11 | Tenant isolation và production credential control | [08](08-security-threat-model.md), [10](10-cloud-deployment.md) | TST-10, TST-11 | G6 | UC-05 |
| NFR-12 | Contracts, pinned versions và rollback | [03](03-sad.md), [10](10-cloud-deployment.md) | TST-03, TST-11 | G2/G6 | UC-07 |

## Nghiệm thu

| Baseline ID | Yêu cầu theo dõi | Hồ sơ | Suite | Gate | UC |
|---|---|---|---|---|---|
| AC-01 | Recall@20 ≥ 90% | [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-03, TST-08 | G2/G5 | UC-02, UC-07 |
| AC-02 | nDCG@10 ≥ 0,80 | [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-03, TST-08 | G2/G5 | UC-02, UC-07 |
| AC-03 | Correctness ≥ 90% | [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-06, TST-08 | G5 | UC-02, UC-07 |
| AC-04 | Faithfulness ≥ 95% | [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-06, TST-08 | G5 | UC-02, UC-07 |
| AC-05 | Citation precision ≥ 98% | [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-06, TST-08 | G5 | UC-02, UC-07 |
| AC-06 | Temporal accuracy ≥ 98% | [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-04, TST-08 | G5 | UC-02, UC-07 |
| AC-07 | Correct abstention ≥ 90% | [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-06, TST-08 | G5 | UC-02, UC-07 |
| AC-08 | 0 citation không tồn tại | [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-06, TST-08 | G5 | UC-02, UC-07 |
| AC-09 | 0 rò rỉ tài khoản trong nghiệm thu | [08](08-security-threat-model.md), [14](14-acceptance-test-plan.md) | TST-10 | G6 | UC-05 |
| AC-10 | ≥ 1.000 L2/L3 thực tế | [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-08 | G5 | UC-07 |
| AC-11 | Toàn bộ taxonomy có AI qua gate | [01](01-prd.md), [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-07, TST-08 | G7 | UC-02, UC-03 |
| AC-12 | Graph chuyên sâu, provenance và temporal | [06](06-database-design.md), [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-05 | G3/G5 | UC-02 |
| AC-13 | AI core end-to-end và regression | [04](04-ai-rag.md), [07](07-benchmark-evaluation.md), [14](14-acceptance-test-plan.md) | TST-03, TST-04, TST-05, TST-06, TST-07, TST-08 | G4/G5 | UC-02, UC-03, UC-07 |
| AC-14 | Cloud online và evidence vận hành | [10](10-cloud-deployment.md), [14](14-acceptance-test-plan.md) | TST-11 | G6 | UC-07 |
| AC-15 | Demo, Studio và portfolio evidence | [01](01-prd.md), [09](09-ui-ux.md), [13](13-ai-coding-agent-guidelines.md), [14](14-acceptance-test-plan.md) | TST-09, TST-12 | G6/G7 | UC-06 |
| AC-16 | 14 hồ sơ phê duyệt trước PoC | [12](12-roadmap-backlog.md), [14](14-acceptance-test-plan.md) | TST-01 | G0 | — |

## Quyết định và mục tiêu

| Baseline ID | Yêu cầu theo dõi | Hồ sơ | Suite | Gate | UC |
|---|---|---|---|---|---|
| DEC-01 | Technical Preview và hoãn mobile/thương mại | [01](01-prd.md), [12](12-roadmap-backlog.md) | TST-01, TST-13 | G0/G8 | — |
| DEC-02 | Mở AI mọi lĩnh vực theo release gate | [01](01-prd.md), [07](07-benchmark-evaluation.md) | TST-07, TST-08 | G7 | UC-02, UC-03 |
| DEC-03 | 1.000 case kiểm chứng và holdout | [07](07-benchmark-evaluation.md) | TST-08 | G5 | UC-07 |
| DEC-04 | Tự kiểm chứng và L3 blocker khi thiếu chuyên gia | [07](07-benchmark-evaluation.md), [12](12-roadmap-backlog.md) | TST-08 | G5 | UC-07 |
| DEC-05 | Knowledge Graph chuyên sâu V1 | [04](04-ai-rag.md), [06](06-database-design.md) | TST-05 | G3/G5 | UC-02 |
| DEC-06 | Standard và Advanced trong V1, Expert Research về sau | [04](04-ai-rag.md), [12](12-roadmap-backlog.md) | TST-07, TST-08, TST-13 | G4/G5 | UC-03 |
| DEC-07 | Skeleton private cho toàn bộ catalog sau duyệt | [03](03-sad.md) | TST-01 | G0 sau duyệt | — |
| DEC-08 | Năm khả năng lưu trữ logic | [06](06-database-design.md) | TST-02, TST-03, TST-05, TST-11 | G1/G3 | UC-02, UC-04 |
| DEC-09 | 100–500 đăng ký, concurrency TBD | [10](10-cloud-deployment.md), [11](11-cost-estimation.md) | TST-11 | G6 | UC-07 |
| DEC-10 | Versioning, bitemporal, provenance và rule đã kiểm | [04](04-ai-rag.md), [05](05-data-engineering.md), [06](06-database-design.md) | TST-02, TST-04, TST-05, TST-06 | G3 | UC-02, UC-04 |
| DEC-11 | Public full-feature Studio sandbox | [08](08-security-threat-model.md), [09](09-ui-ux.md) | TST-09, TST-10, TST-11 | G6 | UC-06 |
| DEC-12 | 14 hồ sơ trước PoC | [12](12-roadmap-backlog.md), [14](14-acceptance-test-plan.md) | TST-01 | G0 | — |
| OBJ-01 | Sản phẩm có ích và phát triển dài hạn | [01](01-prd.md), [12](12-roadmap-backlog.md) | TST-09, TST-13 | G7/G8 | UC-01 |
| OBJ-02 | Nghiên cứu Vietnamese AI/RAG có đo lường | [04](04-ai-rag.md), [07](07-benchmark-evaluation.md) | TST-03, TST-04, TST-05, TST-06, TST-07, TST-08 | G5 | UC-02, UC-03 |
| OBJ-03 | Portfolio và năng lực vận hành/debug | [01](01-prd.md), [13](13-ai-coding-agent-guidelines.md) | TST-12 | G7 | — |
| OBJ-04 | Mobile và doanh nghiệp theo roadmap | [01](01-prd.md), [12](12-roadmap-backlog.md) | TST-13 | LATER | — |
