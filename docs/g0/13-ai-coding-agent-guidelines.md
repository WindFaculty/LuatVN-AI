# 13. AI Coding Agent Development Guidelines

Phiên bản 0.2 · 26/11/2026 · Quy trình dự án đề xuất

## Task contract

Một task có mục tiêu quan sát được, requirement/ADR/gate ID, repo và module cho phép thay đổi, phiên bản contract và dữ liệu, hướng triển khai, lỗi phải xử lý, lệnh kiểm chứng và evidence cần bàn giao. Đọc baseline và RTM, repo guidelines, accepted ADR, contract và issue liên quan. Đối chiếu trạng thái Git trước sửa, bảo toàn thay đổi của chủ dự án. Tách task nếu thay đổi nhiều ranh giới. Version contract trước khi đổi caller/callee theo rollout tương thích.

| Bước | Đầu ra |
|---|---|
| 1. Kiểm hiện trạng | Đường vào thực tế, vấn đề tái hiện được, phạm vi và phụ thuộc |
| 2. Thực hiện | Diff tối thiểu theo contract, quyền hẹp, dữ liệu fixture hợp lệ và lỗi có trạng thái |
| 3. Kiểm chứng | Lệnh thật, commit/config/snapshot, kết quả unit/integration/contract hoặc gate phù hợp, log đã che và lý do cho bước bị chặn |
| 4. Review | Chủ dự án đọc diff, chạy lại đường chính, xác nhận quyền/rollback và duyệt merge/release |
| 5. Ghi nhận | RTM liên kết test/evidence, ADR/change request nếu đổi thiết kế/yêu cầu, bug và regression nếu có |

### Mẫu giao task

```yaml
title: Giữ đúng phiên bản điều khoản khi recorded cutoff thay đổi
requirements: [REQ-TEMP-02, AC-06]
gate: G3
repositories:
  read: [LuatVN-AI-control, LuatVN-AI-contracts]
  write: [LuatVN-AI-legal-knowledge]
pins:
  workspace_manifest: <reviewed revision>
  contracts: <released version>
  fixture: <synthetic snapshot and hash>
allowed_effects: [local tests in disposable database]
acceptance:
  - id: TST-04.1
    expected: Hai cutoff trả đúng phiên bản từ cùng ngày pháp lý
verification:
  commands: [<repo integration command>]
  artifacts: [redacted test log, snapshot digest, commit diff]
handoff:
  reviewer: Trần Xuân Khoa
  rollback: <revert or compatible migration path>
```

Task dùng manifest đã pin. Nếu phát hiện cần đổi hợp đồng hoặc repo ngoài scope, ghi dependency và tạo task liên quan để duyệt phạm vi. Trong bàn giao, checklist hoàn tất gồm đường vào thật, test thực theo task, kết quả có evidence, kiểm quyền và dữ liệu, tệp thay đổi khớp phạm vi, rollback và mục còn chặn. Chủ dự án xác nhận diff và tái hiện ít nhất một đường quan trọng trước khi merge.

## Thay đổi contract xuyên repo

1. Đồng bộ các repo V1 trong meta-workspace theo manifest của `LuatVN-AI-control`. Kiểm branch, revision và worktree ở từng repo. Gói contracts và SDK sinh tự động được pin theo cùng version. Ghi environment và các ref trong task.
2. Mở thay đổi contract tại `LuatVN-AI-contracts`, liên kết PR producer và từng consumer. Chạy validation OpenAPI/JSON Schema, compatibility check và sample fixtures. Với thay đổi phá tương thích, thêm version song song hoặc kế hoạch migration có rollback.
3. Chạy lệnh sync kiểm drift và sinh SDK theo flow đã duyệt. Chạy unit/contract ở mỗi repo và integration xuyên producer–consumer trên manifest ứng viên. Kiểm validator, SSE reconnect và điều kiện reject cho contract liên quan.
4. Review merge order theo chiến lược mở rộng → cập nhật producer/consumer → tháo đường cũ khi hết cửa sổ rollback. Cập nhật manifest sau các PR cần thiết. Ghi accepted version, diff, lệnh, kết quả, rollback target và người duyệt. Chặn promotion manifest nếu contract pin lệch hoặc integration fail. [SAD và meta-workspace](03-sad.md#meta-workspace-cho-polyrepo).

## Kiểm thử và quyền tác động

- Chạy luồng qua entrypoint thật, gồm happy path, phân quyền, dữ liệu cũ, retry, concurrency, cancel và recovery khi liên quan. Mock để kiểm branch khó điều khiển, thêm integration với dependency thật cho khẳng định end-to-end. Fixture và sandbox cần gắn nhãn.
- Giữ failing test và điều tra nguyên nhân. Báo rõ `PASS`, `FAIL`, `NOT_RUN` hoặc `BLOCKED` theo lệnh và evidence. Kết quả AI review là nhận xét. Evidence runtime cần run thực tế.
- Secrets chỉ qua policy của môi trường. Fixture dùng token giả, dữ liệu synthetic hoặc nguồn đã duyệt. Không chép chat/PII vào prompt, test hoặc trace. Trước gọi provider, kiểm allowlist và data class. Agent cần approval được cấp khi tự đề xuất mutation hoặc external effect.
- Thay đổi yêu cầu cần change request ghi lý do, baseline ID, tác động scope/cost/risk/acceptance, lựa chọn để chủ dự án duyệt, và cập nhật RTM, gates, test. Thay đổi thiết kế đã chốt dùng ADR mới hoặc revision có liên kết.
- Tạo task G0 và duyệt tài liệu trước PoC theo DEC-12. Khởi tạo polyrepo theo danh mục SAD đã phê duyệt. Mọi môi trường dùng credentials phù hợp phạm vi và quyền tối thiểu.

## Bằng chứng năng lực chủ dự án

Chủ dự án tự mô tả data lineage, chunking, sparse/dense, reranking, graph/temporal, citation/verifier, workflow/agent, MLOps, CI/CD, quyền và privacy. Thực hành chạy một pipeline từ manifest, đọc trace để xác định lỗi retrieval/citation/version/model, sửa một thành phần, thêm hoặc chạy regression và trình bày kết quả. Ghi lệnh, đầu vào, log đã che, commit/diff và xác nhận của chủ dự án. Dùng public architecture overview, case study và report công khai theo policy.

[Căn cứ baseline §16, RISK-06/08 và AC-15](../../Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md)
