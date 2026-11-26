# Kiểm chứng cục bộ G1 ngày 26/11/2026

Run `G1-LOCAL-20261126-01` · Base commit `72218a681edf8de47d777825dc5fc9389077e6aa` và thay đổi G1 trong worktree · Owner Trần Xuân Khoa, chờ review · Dữ liệu tổng hợp

## Kết quả

| Task | Kỳ vọng và kết quả quan sát | Môi trường và thời gian lệnh |
|---|---|---|
| T01 · TST-01 | `PASS` 25/25 digest G0, 123 ID RTM, 10 component và contract pin `0.2.1-draft`; 19 Python tests và 2 frontend smoke scripts. OpenAPI lint, TypeScript strict và kiểm fixture Pydantic/JSON Schema/SSE đều exit 0. | Python 3.12.10, Node 24.19.0; workspace ~1,8 giây, lint ~3 giây, TS strict ~1,5 giây, validation Pydantic ~0,7 giây |
| T02 · TST-02 | `PASS` cho kiểm policy tổng hợp. 42/42 cặp nguồn/action thật đều trả `PENDING_RIGHTS`; fixture đúng scope được cho phép; sai action, thời gian, loại dữ liệu, size, URL hoặc policy thiếu/đúp bị chặn. | Python 3.12.10, chung lần chạy workspace |
| T06 · POC-02 | `SYNTHETIC_REPLAY` bốn cấu hình trên ba PDF dựng cùng nội dung. Kết quả ở bảng bên dưới. | pypdf 6.19.0, ReportLab 5.0.1, Pillow 13.0.0, Tesseract.js/core 7.0.0, `vie` 1.0.0, PSM `SPARSE_TEXT`; lệnh ~1,2 giây |
| T07 · TST-02.1 | `PASS` trên SQLite tổng hợp. Ngắt có chủ đích sau raw write rồi chạy lại đạt 1 object, 1 logical revision, 2 attempts truy vết được; khi chạy đồng thời đạt 2 provenance độc lập. Checkpoint chờ cursor thiếu; mismatch, UTF-8 lỗi, media sai và text đánh dấu đi quarantine. Ca quá byte/rate hoặc thiếu quyền bị từ chối. | SQLite 3.49.1, chung lần chạy workspace |
| T08 · TST-04 | `PASS` fixture G0 và migration ứng viên G1. Kiểm ngày ở biên, cutoff, anchor khác version, overlap verified, snapshot đã khóa, rollback và outbox replay. 4 snapshots tồn tại, 3 entries được thêm ở replay đầu, 0 entries ở replay hai. Snapshot rollback bị loại. | PostgreSQL 18.6 native, cụm tạm loopback; ~5,8 giây cả khởi tạo và dừng cụm |
| T09 · AC-12 | `PASS` cho schema dự thảo. 2 mẫu tổng hợp hợp lệ và 5 dòng không hợp lệ bị từ chối. | jsonschema 4.25.1, rfc3339-validator 0.1.4; ~0,2 giây |
| T11 · POC-11 | `PASS` 3 test methods cho validator trên record tổng hợp. Kiểm case pending, tier/chuyên môn, revision, thời lượng và rò rỉ group. Review thực tế chưa chạy. | Python 3.12.10, chung lần chạy workspace |

| PDF và cấu hình | Mốc đúng / gold | Mốc sai thêm | Hàng bảng đúng / gold | Sửa ký tự / gold | Raw / normalized bytes |
|---|---:|---:|---:|---:|---:|
| Text · pypdf plain | 6/6 | 0 | 0/3 | 0/256 | 46.791 / 348 |
| Cùng artifact · pypdf layout | 6/6 | 0 | 3/3 | 0/256 | 46.791 / 348 |
| Scan rõ · Tesseract `vie` | 6/6 | 0 | 0/3 | 4/256 | 31.069 / 348 |
| Scan suy giảm · Tesseract `vie` | 1/6 | 1 (`3a`) | 0/3 | 66/256 | 18.345 / 319 |

SHA-256 font Arial `edfbd22a3d088fc2f5d7c79b8c9c732df6dc878a60f0a80be0f92a3c7a634404`, model `2284f610f262a1b19ec8df9f196b9ff6ce38ddb4a66329e998941df4b8961c8d` và replay JSON cục bộ `build/g1-poc02-replay.json` là `561c99ae5a79f216a85c73e20e67cf355ef5ecdd6febf66b3d3e47686c286159`.

Máy đo chạy Windows 11 `10.0.26300`, i7-14650HX, RTX 5060 Laptop GPU, RAM khoảng 31,6 GiB, ổ D còn khoảng 4,88 GiB lúc kiểm. Docker Desktop engine chưa chạy nên replay dùng cụm PostgreSQL native tạm, khởi tạo với xác thực SCRAM và chỉ bind loopback. Fixture dừng và xóa cụm tạm khi kết thúc. Các lệnh trên không dùng API trả phí và không thu thập nguồn pháp luật. Thời gian bảng là elapsed từng lệnh, không dùng để tính throughput/cost corpus thật.

## Hosted CI

GitHub trả `[]` cho `gh run list --commit 72218a681edf8de47d777825dc5fc9389077e6aa` và `0` check-runs cho commit này. Workflow `ci.yml` chạy khi push `main` hoặc có pull request. Lượt gần nhất trên `main` lúc kiểm là `45816772853`, hai jobs báo `failure` với `steps=[]`. Annotation của GitHub ghi job chưa khởi động vì thanh toán gần đây thất bại hoặc giới hạn chi tiêu cần tăng. Trạng thái hosted của nhánh là `NOT_RUN`; điều kiện hosted hoặc kiểm tương đương vẫn chờ chủ dự án. [Lượt chạy trên main](https://github.com/WindFaculty/LuatVN-AI/actions/runs/45816772853) · [Workflow](../../../.github/workflows/ci.yml).

## Tái hiện

Chạy từ Git root. `build/` là thư mục cục bộ được ignore. Cài venv, npm packages và chạy replay PDF theo [POC-02](../poc02-parser-ocr.md#chạy-lại), dùng `--output build/g1-poc02-replay.json --run-id G1-POC02-20261126-SYNTH-REPLAY`.

```powershell
rtk proxy python -X utf8 scripts/verify-workspace.py --smoke
rtk proxy python -X utf8 experiments/g1/run_temporal_fixture.py
rtk proxy build/g1-venv/Scripts/python.exe -m pip install jsonschema==4.25.1 rfc3339-validator==0.1.4
rtk proxy build/g1-venv/Scripts/python.exe -X utf8 experiments/g1/check_graph_fixture.py
rtk proxy npx.cmd --yes --package=@redocly/cli@2.83.0 redocly lint --extends=spec packages/contracts/contracts/answers.openapi.yaml
rtk proxy npx.cmd --yes --package=openapi-typescript@7.13.0 openapi-typescript packages/contracts/contracts/answers.openapi.yaml --array-length -o build/g1-contracts/answer-types.ts
rtk proxy powershell -NoProfile -Command 'Copy-Item -LiteralPath packages/contracts/contracts/answer-types.test.ts -Destination build/g1-contracts/answer-types.test.ts'
rtk proxy npx.cmd --yes --package=typescript@5.9.3 tsc --noEmit --strict build/g1-contracts/answer-types.test.ts
rtk proxy build/g1-venv/Scripts/python.exe -m pip install datamodel-code-generator==0.102.0 jsonschema==4.25.1 PyYAML==6.0.3 pydantic==2.11.4
rtk proxy build/g1-venv/Scripts/datamodel-codegen.exe --input packages/contracts/contracts/answers.openapi.yaml --input-file-type openapi --output-model-type pydantic_v2.BaseModel --output build/g1-contracts/answer_models.py
rtk proxy build/g1-venv/Scripts/python.exe -X utf8 packages/contracts/contracts/verify-contracts.py build/g1-contracts
```

Pin đầu vào tại [digest manifest của lần chạy](local-inputs-2026-11-26.sha256). Audit manifest cho corpus thật và holdout chưa khóa.
