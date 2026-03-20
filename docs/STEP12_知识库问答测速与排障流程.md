# Step 12 知识库问答测速与排障流程

版本：V1.1  
状态：可执行  
更新日期：2026-03-20

## 1. 目标
- 验证 Step 12（Dify Service API）问答链路是否满足：
  - 回答非空；
  - `retriever_resources` 非空（有依据回答）；
  - 响应耗时尽可能接近产品目标 `<= 2s`（见产品文档性能口径）。

## 2. 前置条件
| 项目 | 要求 |
| --- | --- |
| Dify 服务 | `infra/dify/docker/docker-compose.yaml` 已启动，`api/web/nginx/worker` 为 `Up` |
| 后端环境变量 | `VOLTIQ_DIFY_BASE_URL`、`VOLTIQ_DIFY_API_KEY` 已正确设置 |
| 执行目录 | `E:\git\VoltIQ\backend` |

## 3. 标准执行流程（PowerShell）

### 3.1 准备环境变量
```powershell
cd E:\git\VoltIQ\backend
Copy-Item .env.example .env -ErrorAction SilentlyContinue
$env:VOLTIQ_DIFY_BASE_URL = "http://localhost/v1"
$env:VOLTIQ_DIFY_API_KEY = "app-xxxxxxxxxxxxxxxx"
$env:VOLTIQ_DIFY_RESPONSE_MODE = "blocking"
```

### 3.2 准备中文问题集（与网页问答口径一致）
```powershell
@'
请基于知识库回答：售电合同中直接交易的定义是什么？并给出依据。
售电合同里“中长期交易”和“现货交易”有什么区别？请给出处。
请解释售电合同中的电量结算规则，并给出依据。
'@ | Set-Content ..\artifacts\step12_queries.txt -Encoding UTF8
```

### 3.3 单条连通性与依据验证（先过门禁）
```powershell
python scripts/verify_step12_dify.py --response-mode streaming --timeout-seconds 120 --retries 1 --query "请基于知识库回答：售电合同中直接交易的定义是什么？并给出依据。"
```

通过标准：
- 输出包含 `[PASS]`
- `sources > 0`

### 3.4 小样本测速（推荐先跑）
```powershell
python scripts/benchmark_step12_dify_latency.py --modes blocking,streaming --queries-file ..\artifacts\step12_queries.txt --sample-count 6 --warmup-count 1 --timeout-seconds 120 --retries 1 --threshold-seconds 2 --output-dir ..\artifacts --print-each
```

### 3.5 全量测速（基线）
```powershell
python scripts/benchmark_step12_dify_latency.py --modes blocking,streaming --queries-file ..\artifacts\step12_queries.txt --sample-count 10 --warmup-count 2 --timeout-seconds 120 --retries 1 --threshold-seconds 2 --output-dir ..\artifacts --print-each
```

## 4. 输出文件与判读
测速脚本默认输出到 `..\artifacts\`：
- `step12-latency-blocking.csv`
- `step12-latency-streaming.csv`
- `step12-latency-summary.md`

重点看 `step12-latency-summary.md`：
- `success/failed`：成功率和失败率；
- `avg/p50/p95`：完整返回延迟分布；
- `avg_ttft/p50_ttft/p95_ttft`：首字时间分布（仅 `streaming` 有值）；
- `<=threshold`：达标率（阈值默认 2 秒）；
- `slowest successful samples`：最慢样本；
- `failure distribution`：失败原因统计。

## 5. 常见异常与处理
| 现象 | 典型原因 | 处理动作 |
| --- | --- | --- |
| `Dify API key is not configured.` | 未设置 `VOLTIQ_DIFY_API_KEY` 或仍为 `replace_me` | 重新设置环境变量并重试 |
| `empty_retriever_resources` | 未命中知识库、问题与知识库语料偏离、应用未正确配置引用 | 优先使用中文业务问题；检查 Dify App 的知识库绑定与引用设置 |
| `Dify request timed out.` | 上游模型超时或响应慢 | 提高 `--timeout-seconds`，保留 `--retries 1`；检查 Dify `api` 日志 |
| 网页可对话但脚本失败 | Studio 预览链路与 Service API 配置不一致 | 用同一问题集复测；核对脚本 API Key 对应的 App 与模型配置 |

## 6. 快速排障命令
```powershell
cd E:\git\VoltIQ
docker compose -f infra/dify/docker/docker-compose.yaml ps
docker compose -f infra/dify/docker/docker-compose.yaml logs --tail 120 api
docker compose -f infra/dify/docker/docker-compose.yaml logs --tail 120 worker
```

若确认模型配置已更新，建议重建相关服务：
```powershell
docker compose -f infra/dify/docker/docker-compose.yaml up -d --force-recreate api worker
```
