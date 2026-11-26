# Kiểm tra hợp đồng G0

`answers.openapi.yaml` và `internal-v1.schema.json` là bản thiết kế đầu vào của `LuatVN-AI-contracts`. Khi khởi tạo repo sau duyệt G0, chạy các lệnh dưới tại thư mục chứa schema, khóa phiên bản phụ thuộc và dùng các kiểm tra này trong CI commit đầu. Sinh vào thư mục tạm hoặc build của CI.

```powershell
$ContractBuild = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $ContractBuild
python -m pip install datamodel-code-generator==0.102.0 jsonschema==4.25.1 PyYAML==6.0.3
npx.cmd --yes --package=@redocly/cli@2.83.0 redocly lint --extends=spec answers.openapi.yaml
npx.cmd --yes --package=openapi-typescript@7.13.0 openapi-typescript answers.openapi.yaml --array-length -o "$ContractBuild/answer-types.ts"
datamodel-codegen --input answers.openapi.yaml --input-file-type openapi --output-model-type pydantic_v2.BaseModel --output "$ContractBuild/answer_models.py"
Copy-Item answer-types.test.ts $ContractBuild
npx.cmd --yes --package=typescript@5.9.3 tsc --noEmit --strict "$ContractBuild/answer-types.test.ts"
python -X utf8 verify-contracts.py $ContractBuild
```

Chạy lệnh cài Python trong môi trường ảo. Kiểm OpenAPI 3.1 bằng linter và kiểm tương thích khi phát hành contract đã có consumer. Producer và consumer cần kiểm theo schema gốc tại runtime với dữ liệu đi qua ranh giới. TypeScript kiểm kiểu và số phần tử theo fixture. Pydantic kiểm payload Answer và JSON của SSE theo fixture. SSE dùng `text/event-stream`, parse frame rồi kiểm JSON `data` theo `SseData`. Client theo dõi `id`/replay theo SRS. `x-frame-data-schema` trỏ tới schema của `data` để tra cứu.

`GateReport.v1` bản dự thảo 0.2.1 yêu cầu hai trường `s0_count` và `s1_count`. Chuyển fixture hoặc consumer dùng `critical_failures` trước khi pin bản này. `EvidenceQuery.v1` giữ `query_vi` bắt buộc và nhận cặp trường nguyên văn/ngôn ngữ tùy chọn khi Retrieval cần dữ liệu đó. Tránh ghi nguyên văn truy vấn vào log theo policy của dự án.
