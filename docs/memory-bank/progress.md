# 开发进度记录（Progress）

更新时间：2026-03-20

## 2026-03-20

### 运行问题记录（Dify / Step 12 联调）
- 现象：`nginx` 启动反复重启，日志报错 `host not found in upstream "api"`，导致 `/v1` 请求不可用。
- 排查：`api` 服务在 `voltiqdify_default` 网络内，DNS 解析正常；`nginx` 容器未正确挂载网络（启动时无法解析 `api`）。
- 处理：执行 `docker compose -f infra/dify/docker/docker-compose.yaml up -d --force-recreate nginx` 重新创建 `nginx`，恢复 `api` 上游解析与 80/443 端口监听。
- 结论：需确保 `nginx` 与 `api/web` 使用同一 Compose 项目启动，避免单独启动导致网络与 DNS 解析异常。

### 已完成事项（Step 12 速度测试能力）
- 已新增 Step 12 延迟基准脚本 `backend/scripts/benchmark_step12_dify_latency.py`：
  - 支持 `blocking`/`streaming` 双模式采样、预热样本剔除、固定题集循环采样。
  - 支持输出 `avg/p50/p95`、`<= 阈值达标率`、失败率、慢样本 Top3 与失败原因分布。
  - `streaming` 新增 `TTFT`（首字时间）统计：`avg_ttft/p50_ttft/p95_ttft`。
  - `streaming` 采样改为真实 SSE 事件流测量，避免整包读取导致的统计偏差。
  - 支持输出 CSV 明细与 Markdown 汇总（默认输出目录 `artifacts/`）。
- 已新增单测 `backend/tests/test_step12_latency_benchmark.py`，覆盖模式解析、分位数计算、汇总口径与报告渲染。
- 已更新 `backend/.env.example` 默认 `VOLTIQ_DIFY_RESPONSE_MODE=blocking`，对齐当前稳定测量口径。
- 已完成本地回归：
  - `python -m pytest -q tests/test_step12_latency_benchmark.py` 通过（4 passed）。
  - `python -m pytest -q tests/test_dify_client.py tests/test_step12_latency_benchmark.py` 通过（14 passed）。
- 已完成脚本烟测（当前环境未配置真实 Key）：
  - `python scripts/benchmark_step12_dify_latency.py --sample-count 1 --warmup-count 0 --modes blocking`
  - 输出 `[FAIL] mode=blocking Dify API key is not configured.`（错误信息符合预期，脚本失败路径可读）。

### 文档更新（Step 12 测试流程）
- 已新增 `docs/STEP12_知识库问答测速与排障流程.md`，沉淀可复制执行的测速命令、结果判读口径与常见异常排障路径。
- 已更新 `docs/README.md`，补充 Step 12 测试流程文档入口。

## 2026-03-19

### 已完成事项（Step 12）
- 已按用户指令完整阅读 `docs/memory-bank/` 全部文件与 `docs/memory-bank/progress.md`。
- 已按用户指令实施计划 Step 12（知识库接入方案确认）：
  - 在 `backend/app/integrations/dify/` 新增 `client.py`、`schemas.py`、`exceptions.py`，完成 Dify Service API 接入封装。
  - 已实现统一请求契约：`POST /chat-messages`、`Authorization: Bearer <API_KEY>`、默认 `response_mode=blocking`。
  - 已实现统一响应解析：提取 `answer`、`conversation_id`、`metadata.retriever_resources`，并映射超时/HTTP/载荷异常。
  - 已新增并更新验证脚本 `backend/scripts/verify_step12_dify.py`，用于连通性与“回答有依据”口径验证（支持响应模式、超时、重试与退避参数）。
  - 已新增单测 `backend/tests/test_dify_client.py`，覆盖请求构造、成功解析、超时与错误映射。
  - 已扩展配置项 `VOLTIQ_DIFY_BASE_URL`、`VOLTIQ_DIFY_API_KEY`、`VOLTIQ_DIFY_REQUEST_TIMEOUT_SECONDS`、`VOLTIQ_DIFY_RESPONSE_MODE`。
  - 已更新 `backend/app/main.py` 版本标识至 `0.1.0-step12`。
  - 已更新 `docs/memory-bank/architecture.md` 至 V1.16，并更新 `docs/memory-bank/IMPLEMENTATION_PLAN.md` 至 V1.15。
- 已完成 Step 12 性能加固改造：Dify Client 支持指数退避自动重试，`streaming` 模式支持事件流解析；用于降低超时导致的失败率并改善首字等待时延。\n- 已完成输出清洗：统一剔除 `<details>...</details>` 以避免思考过程泄露。
- Step 12 执行边界遵循门禁：未新增 kb 业务问答 API，仅保留 /api/v1/kb/health，未启动 Step 13。

### 产出文件（Step 12）
- `backend/app/integrations/dify/client.py`、`backend/app/integrations/dify/schemas.py`、`backend/app/integrations/dify/exceptions.py`、`backend/app/integrations/dify/__init__.py`、`backend/app/integrations/__init__.py`：Step 12 Dify 接入封装。
- `backend/scripts/verify_step12_dify.py`：Step 12 连通性与来源回传验证脚本。
- `backend/tests/test_dify_client.py`：Step 12 单元测试（请求契约/解析/异常映射）。
- `backend/app/core/config.py`、`backend/.env.example`、`backend/pyproject.toml`、`backend/app/main.py`：Step 12 运行时配置、依赖与版本标识更新。
- `docs/memory-bank/architecture.md`、`docs/memory-bank/IMPLEMENTATION_PLAN.md`：Step 12 架构基线与实施状态同步。

### 验收状态（Step 12）
- Step 12 已完成工程实现并通过用户测试确认（确认日期：2026-03-19）。
- Step 13 可按计划启动（当前尚未启动）。

### 执行约束记录（当前）
- Step 12 已按用户明确指令启动并完成工程实现。
- Step 12 用户验证已通过，Step 13 门禁已解除。
- 用户侧已完成真实 Dify 联调验证，命令输出为 `[PASS]` 且 `sources=4`。

### 已完成事项（Step 11，历史记录）
- 已按用户指令完整阅读 `docs/memory-bank/` 全部文件与 `docs/memory-bank/progress.md`。
- 已按用户指令实施计划 Step 11（内容生成任务接口）：
  - 在 `backend/app/modules/content/` 新增 `deps.py`、`schemas.py`、`repository.py`、`service.py`，并扩展 `router.py`，完成模块化分层。
  - 已实现 `POST /api/v1/content/tasks`、`GET /api/v1/content/tasks`、`GET /api/v1/content/tasks/{task_id}`。
  - 已落地“立即成功占位”策略：任务创建即写入 `status=succeeded`，并返回占位 `result_text` 与 `result_meta`。
  - 已接入 Header 模拟鉴权并复用 Step 6 RBAC 策略层，落地 `operator` 可写可读、`manager` 只读、`sales` 拒绝访问。
  - 已落地 `content_task.created`、`content_task.queried` 审计记录。
  - 已新增接口测试 `backend/tests/test_content_tasks_api.py`，覆盖创建/筛选分页/详情/RBAC/审计断言。
- 已更新 `backend/app/main.py` 版本标识至 `0.1.0-step11`。
- 已于 2026-03-19 完成本地测试验证：
  - `python -m pytest -q tests/test_content_tasks_api.py` 通过（4 passed）。
  - `python -m pytest -q` 全量回归通过（32 passed）。
  - `.pytest_cache` 写入受限（WinError 5）产生告警，但不影响测试通过结论。

### 产出文件
- `backend/app/modules/content/router.py`、`backend/app/modules/content/deps.py`、`backend/app/modules/content/schemas.py`、`backend/app/modules/content/repository.py`、`backend/app/modules/content/service.py`：Step 11 内容任务接口与分层实现。
- `backend/tests/test_content_tasks_api.py`：Step 11 接口集成测试（创建/查询/筛选分页/RBAC/审计）。
- `backend/app/main.py`：版本标识更新至 `0.1.0-step11`。
- `docs/memory-bank/architecture.md`：更新至 V1.12，同步 Step 11 接口基线与 Step 12 门禁。
- `docs/memory-bank/IMPLEMENTATION_PLAN.md`：更新至 V1.11，同步 Step 11 状态、产出与验证门禁。

### 验收状态
- Step 11 已完成工程实现；内容任务接口已落地，待用户测试确认（记录日期：2026-03-19）。

### 执行约束记录
- Step 11 已按用户明确指令启动并完成工程实现。
- 在用户完成 Step 11 测试验证前，不启动 Step 12（知识库接入方案确认）。
- 按分工约定，测试由用户侧执行，当前记录不包含测试执行结果。

## 2026-03-18

### 已完成事项
- 已完整阅读 `docs/memory-bank/architecture.md`、`docs/memory-bank/AI_售电_产品设计文档.md`、`docs/memory-bank/IMPLEMENTATION_PLAN.md`、`docs/memory-bank/tech-stack.md`、`docs/memory-bank/progress.md`。
- 已完成实施计划 Step 1（明确版本边界与验收标准）。
- 已新增 `docs/memory-bank/MVP_验收清单.md`，覆盖字段、接口、页面、指标、角色及“获客 -> 触达 -> 成单”最小闭环验收场景。
- 已完成实施计划 Step 2 的文档与编排落地（环境与依赖矩阵）。
- 已完成实施计划 Step 3（统一项目结构），目录职责收敛至 `frontend/`、`backend/`、`docs/`、`infra/`。
- 已按用户指令实施计划 Step 4（核心数据模型设计第一版），并完成文档定版更新（不包含 Step 5 的数据库迁移落地）。
- 已按用户指令实施计划 Step 5（数据库与迁移流程）：
  - 在 `backend/` 初始化 `SQLAlchemy + Alembic` 基线与数据库配置。
  - 新增基线迁移 `20260318_0001_step5_initial_schema.py`，落地 MVP 核心表、约束与索引。
  - 本地完成迁移链路验证：`upgrade head -> downgrade base -> upgrade head`。
- 已按用户指令实施计划 Step 6（基础权限模型）：
  - 新增框架无关 RBAC 策略层 `backend/app/rbac/`（权限码、角色映射、接口/菜单策略注册表）。
  - 落地 `sales` owner 强约束（fail-closed）与 `manager` 审批权限（`opportunity.rollback`、`deal.correct`）。
  - 新增权限单测 `backend/tests/test_rbac_policy.py`，本地执行 `python -m pytest -q` 通过（7 passed）。
- 已按用户指令实施计划 Step 7（后端基础框架搭建）：
  - 新增 FastAPI 应用入口 `backend/app/main.py` 与 API 聚合路由 `backend/app/api/router.py`。
  - 新增 `auth`、`leads`、`crm`、`content`、`kb`、`metrics`、`audit` 七个模块路由骨架（仅健康检查，占位无业务 CRUD）。
  - 新增 API 冒烟测试 `backend/tests/test_api_health.py`，并与 Step 6 回归测试一起通过（`python -m pytest -q`，9 passed）。
- 已按用户指令实施计划 Step 8（线索管理接口：新增/查询/更新）：
  - 在 `backend/app/modules/leads/` 新增 `deps.py`、`schemas.py`、`repository.py`、`service.py`，并重构 `router.py`，完成模块化分层。
  - 已实现 `POST /api/v1/leads`（创建+自动去重合并）、`GET /api/v1/leads`（筛选列表）、`GET /api/v1/leads/{lead_id}`、`PATCH /api/v1/leads/{lead_id}`、`POST /api/v1/leads/{lead_id}/assign`、`POST /api/v1/leads/{lead_id}/merge`。
  - 已接入 Header 模拟鉴权（`X-Actor-Role`、`X-Actor-User-Id`）并复用 Step 6 RBAC 策略层，落地 `sales` owner 约束与 `manager` 写入拒绝。
  - 已落地 `lead.created`、`lead.updated`、`lead.assign`、`lead.merged` 审计记录，且手机号按脱敏规则写入日志。
  - 新增接口测试 `backend/tests/test_leads_api.py`；本地执行 `python -m pytest -q` 通过（16 passed，含 Step 6/7 回归）。
- 已按用户指令实施计划 Step 9（CRM 跟进记录接口）：
  - 在 `backend/app/modules/crm/` 新增 `deps.py`、`schemas.py`、`repository.py`、`service.py`，并扩展 `router.py`，完成模块化分层。
  - 已实现 `POST /api/v1/crm/follow-ups`、`GET /api/v1/crm/follow-ups`、`GET /api/v1/crm/follow-ups/{follow_up_id}`、`PATCH /api/v1/crm/follow-ups/{follow_up_id}`、`DELETE /api/v1/crm/follow-ups/{follow_up_id}`。
  - 已接入 Header 模拟鉴权并复用 Step 6 RBAC 策略层，落地 `sales` owner 约束与 `manager` 只读。
  - 已实现新增跟进更新 `leads.latest_follow_up_at`，删除跟进后重算并回写该字段。
  - 已落地 `follow_up.created`、`follow_up.updated`、`follow_up.deleted` 审计记录。
  - 新增接口测试 `backend/tests/test_crm_follow_ups_api.py`；本地执行 `python -m pytest -q` 通过（22 passed，含 Step 6/7/8 回归）。
- 已按用户指令实施计划 Step 10（商机与成单接口）：
  - 在 `backend/app/modules/crm/` 扩展商机与成单接口，新增 `POST /api/v1/crm/opportunities`、`GET /api/v1/crm/opportunities`、`GET /api/v1/crm/opportunities/{opportunity_id}`、`PATCH /api/v1/crm/opportunities/{opportunity_id}/stage`、`POST /api/v1/crm/deals`、`GET /api/v1/crm/deals`、`GET /api/v1/crm/opportunities/stats`。
  - 已落地 `Deal 驱动 won`：禁止通过阶段接口直接设置 `won`，仅允许在创建 `deal` 时自动置 `won`。
  - 已落地阶段流转约束：`initial -> proposal -> negotiation -> lost`，并强制 `lost` 场景传入 `lost_reason`。
  - 已落地 `opportunity.created`、`opportunity.stage_changed`、`deal.created` 审计记录。
  - 已新增接口测试 `backend/tests/test_crm_opportunities_deals_api.py`，覆盖流转约束、RBAC owner、统计口径与审计断言。
  - 当前执行环境 Python 解释器不可用，未完成本地 `pytest` 执行，待用户侧验证。

### 产出文件
- `docs/memory-bank/MVP_验收清单.md`：Step 1 的正式验收基线与评审记录载体。
- `infra/docker-compose.step2.yml`：PostgreSQL + Redis 的本地 Compose 编排。
- `infra/.env.step2.example`：Step 2 环境变量模板。
- `docs/memory-bank/STEP2_环境与依赖矩阵.md`：Step 2 依赖矩阵、启动方式、健康检查口径。
- `README.md`、`frontend/README.md`、`backend/README.md`、`docs/README.md`、`infra/README.md`：Step 3 目录职责与入口说明。
- `docs/memory-bank/architecture.md`：更新至 V1.5，沉淀 Step 4 的实体关系基线、关键索引与规则约束。
- `docs/memory-bank/IMPLEMENTATION_PLAN.md`：更新至 V1.5，同步 Step 5 状态与 Step 6 门禁。
- `backend/pyproject.toml`、`backend/alembic.ini`、`backend/.env.example`、`backend/.gitignore`：Step 5 迁移工程基础配置。
- `backend/app/core/*`、`backend/app/db/*`：数据库配置、模型基类、枚举与核心模型定义。
- `backend/alembic/env.py`、`backend/alembic/script.py.mako`、`backend/alembic/versions/20260318_0001_step5_initial_schema.py`：迁移运行环境与基线迁移脚本。
- `docs/memory-bank/architecture.md`：更新至 V1.6，同步 Step 5 落地与执行门禁。
- `backend/app/rbac/types.py`、`backend/app/rbac/policy.py`、`backend/app/rbac/__init__.py`：Step 6 权限模型策略层与注册表。
- `backend/tests/test_rbac_policy.py`：Step 6 RBAC 单元测试。
- `backend/pyproject.toml`：新增 `pytest` 开发依赖与测试路径配置。
- `docs/memory-bank/architecture.md`：更新至 V1.7，同步 Step 6 策略层基线与 Step 7 门禁。
- `docs/memory-bank/IMPLEMENTATION_PLAN.md`：更新至 V1.6，同步 Step 6 状态与验证门禁。
- `backend/app/main.py`、`backend/app/api/router.py`、`backend/app/modules/*`：Step 7 FastAPI 应用入口、路由聚合与模块骨架。
- `backend/tests/test_api_health.py`：Step 7 API 健康检查与 OpenAPI 冒烟测试。
- `backend/pyproject.toml`：Step 7 新增 FastAPI/Uvicorn 运行依赖与 `httpx` 开发依赖。
- `backend/README.md`：修复编码并补充 Step 7 启动与健康检查说明。
- `docs/memory-bank/architecture.md`：更新至 V1.8，同步 Step 7 基线与 Step 8 门禁。
- `docs/memory-bank/IMPLEMENTATION_PLAN.md`：更新至 V1.7，同步 Step 7 状态与验证门禁。
- `backend/app/modules/leads/router.py`、`backend/app/modules/leads/deps.py`、`backend/app/modules/leads/schemas.py`、`backend/app/modules/leads/repository.py`、`backend/app/modules/leads/service.py`：Step 8 线索管理接口与分层实现。
- `backend/tests/test_leads_api.py`：Step 8 接口集成测试（去重/筛选/分配/更新/RBAC/审计落库）。
- `backend/app/main.py`：版本标识更新至 `0.1.0-step8`。
- `docs/memory-bank/architecture.md`：更新至 V1.9，同步 Step 8 接口基线与 Step 9 门禁。
- `docs/memory-bank/IMPLEMENTATION_PLAN.md`：更新至 V1.8，同步 Step 8 状态、产出与验证门禁。
- `backend/app/modules/crm/router.py`、`backend/app/modules/crm/deps.py`、`backend/app/modules/crm/schemas.py`、`backend/app/modules/crm/repository.py`、`backend/app/modules/crm/service.py`：Step 9 CRM 跟进记录接口与分层实现。
- `backend/tests/test_crm_follow_ups_api.py`：Step 9 接口集成测试（CRUD/RBAC/客户归属/最近跟进时间/审计落库）。
- `backend/app/main.py`：版本标识更新至 `0.1.0-step9`。
- `docs/memory-bank/architecture.md`：更新至 V1.10，同步 Step 9 接口基线与 Step 10 门禁。
- `docs/memory-bank/IMPLEMENTATION_PLAN.md`：更新至 V1.9，同步 Step 9 状态、产出与验证门禁。
- `backend/app/modules/crm/router.py`、`backend/app/modules/crm/service.py`：Step 10 商机与成单接口实现（商机 CRUD 查询、阶段流转、成单创建与统计）。
- `backend/tests/test_crm_opportunities_deals_api.py`：Step 10 接口集成测试（流转约束/RBAC/统计/审计）。
- `backend/app/main.py`：版本标识更新至 `0.1.0-step10`。
- `docs/memory-bank/architecture.md`：更新至 V1.11，同步 Step 10 接口基线与 Step 11 门禁。
- `docs/memory-bank/IMPLEMENTATION_PLAN.md`：更新至 V1.10，同步 Step 10 状态、产出与验证门禁。

### 验收状态
- 产品负责人已确认 Step 1 通过（确认日期：2026-03-18）。
- Step 2 已完成实现，用户已确认可进入 Step 3（确认日期：2026-03-18）。
- Step 3 已完成实施并通过用户验证（确认日期：2026-03-18）。
- Step 4 已通过用户验证（确认日期：2026-03-18）。
- Step 5 已完成工程实现；迁移链路已通过本地验证，待用户测试确认（记录日期：2026-03-18）。
- Step 6 已完成工程实现；权限单测已通过本地验证，待用户测试确认（记录日期：2026-03-18）。
- Step 7 已完成工程实现；基础路由与健康检查已通过本地测试，待用户测试确认（记录日期：2026-03-18）。
- Step 8 已完成工程实现；线索接口与去重/分配流程已通过本地测试，待用户测试确认（记录日期：2026-03-18）。
- Step 9 已完成工程实现；CRM 跟进接口与最近跟进时间回写规则已通过本地测试，待用户测试确认（记录日期：2026-03-18）。
- Step 10 已完成工程实现；商机/成单接口已落地，待用户测试确认（记录日期：2026-03-18）。

### 执行约束记录
- Step 3 门禁已解除，Step 4 已实施完成。
- Step 4 验证已完成，Step 5 已按用户明确指令启动并完成实现。
- Step 6 已按用户明确指令启动并完成工程实现。
- Step 7 已按用户明确指令启动并完成工程实现。
- Step 8 已按用户明确指令启动并完成工程实现。
- Step 9 已按用户明确指令启动并完成工程实现。
- Step 10 已按用户明确指令启动并完成工程实现。
- 在用户完成 Step 10 测试验证前，不启动 Step 11（内容生成任务接口）。
- 按分工约定，测试由用户侧执行，当前记录不包含测试执行结果。




