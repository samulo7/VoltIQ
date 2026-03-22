# 开发进度记录（Progress）

更新时间：2026-03-22

## 2026-03-22
### 会话继承需求（长期约束）
- 当前项目仍处于 V1 版本实施阶段，整体进度为 in process。
- `frontend_productization_execution_plan_v1.md` 仅做计划沉淀与约束固化，不作为当前阶段主执行线。
- 前端产品化改造（dashboard/workbench 聚合、运营型客服台、管理层审批/校正入口、内容任务状态模型升级等）统一在 V1 阶段完成并验收后启动。
- 后续新会话默认先读取 `docs/memory-bank/IMPLEMENTATION_PLAN.md` 与本文件，再决定是否进入产品化改造执行。

## 2026-03-21
### 已完成事项（Step 20）
- 已按用户指令完整阅读 `docs/memory-bank/` 全部文件与 `docs/memory-bank/progress.md`。
- 已按用户指令实施计划 Step 20（智能客服页面）：
  - 新增前端服务层 `frontend/src/services/voltiq/kb.ts`，统一封装会话列表与问答接口（`listKbSessions`/`chatWithKb`）及类型。
  - 已替换 `frontend/src/pages/kb/sessions/index.tsx` 占位页，落地智能客服可用页面。
  - 已实现会话列表分页、刷新、会话切换与“新会话”入口。
  - 已实现问答对话框：首次提问自动建会话，后续提问自动携带 `session_key` 进行连续对话。
  - 已实现回答依据展示：assistant 消息展示 `sources`（知识库、文档、评分、片段内容）。
  - 已同步更新 `docs/memory-bank/architecture.md`（V1.31）与 `docs/memory-bank/IMPLEMENTATION_PLAN.md`（V1.28）。

### 产出文件（Step 20）
- `frontend/src/services/voltiq/kb.ts`。
- `frontend/src/pages/kb/sessions/index.tsx`。
- `docs/memory-bank/architecture.md`。
- `docs/memory-bank/IMPLEMENTATION_PLAN.md`。
- `docs/memory-bank/progress.md`。

### 本地验证（Step 20）
- 已执行：`pnpm -C frontend run tsc`。
- 结果：通过（`tsc --noEmit` 成功，无 TypeScript 错误，2026-03-21）。

### 验收状态（Step 20）
- Step 20 已完成工程实现，待用户测试确认。

### 执行约束记录（Step 20）
- Step 20 已按用户明确指令启动并完成工程实现。
- 在用户完成 Step 20 验证前，不启动 Step 21。

### 已完成事项（Step 19）
- 已按用户指令完整阅读 docs/memory-bank/ 全部文件与 docs/memory-bank/progress.md。
- 已按用户指令实施计划 Step 19（内容生成页面）：
  - 新增前端服务层 frontend/src/services/voltiq/content.ts，统一封装内容任务 create/list/detail 接口与类型。
  - 已替换 frontend/src/pages/content/tasks/index.tsx 占位页，落地内容任务真实页面。
  - 已实现任务列表分页与筛选（task_type、status、created_by、created_at 时间范围）。
  - 已实现三类任务提交（copywriting、image、video_script）与结果详情展示（result_text、result_meta）。
  - 已按确认口径落地前端过渡态：提交时显示“任务提交中”，成功后刷新并展示最新状态。
  - 已同步更新 docs/memory-bank/architecture.md（V1.30）与 docs/memory-bank/IMPLEMENTATION_PLAN.md（V1.27）。

### 产出文件（Step 19）
- frontend/src/services/voltiq/content.ts。
- frontend/src/pages/content/tasks/index.tsx。
- docs/memory-bank/architecture.md。
- docs/memory-bank/IMPLEMENTATION_PLAN.md。
- docs/memory-bank/progress.md。

### 本地验证（Step 19）
- 已执行：pnpm -C frontend run tsc。
- 结果：通过（tsc --noEmit 成功，无 TypeScript 错误，2026-03-21）。

### 验收状态（Step 19）
- Step 19 已完成工程实现，待用户测试确认。

### 执行约束记录（Step 19）
- Step 19 已按用户明确指令启动并完成工程实现。
- Step 20 已按用户明确指令启动并完成工程实现，待用户测试确认。

### 已完成事项（Step 18）
- 已按用户指令完整阅读 `docs/memory-bank/` 全部文件与 `docs/memory-bank/progress.md`。
- 已按用户指令实施计划 Step 18（CRM 跟进与商机页面，含成单联动）：
  - 新增前端服务层 `frontend/src/services/voltiq/crm.ts`，统一封装 `follow-ups`、`opportunities`、`deals` 接口与类型。
  - 已改造 `frontend/src/pages/crm/follow-ups/index.tsx`，实现跟进记录列表分页、筛选（线索/客户/创建人/时间）、新增、编辑、删除。
  - 已落地跟进新增“线索下拉选择”交互（可搜索），并兼容可选 `customer_id` 录入。
  - 已改造 `frontend/src/pages/crm/opportunities/index.tsx`，实现商机列表分页、筛选、阶段统计、阶段流转（含 `lost_reason` 校验）与商机页内联创建成单。
  - 已改造 `frontend/src/pages/crm/deals/index.tsx`，实现成单记录分页、按商机/日期筛选、基于谈判中商机下拉创建成单。
  - 已同步更新 `docs/memory-bank/architecture.md`（V1.29）与 `docs/memory-bank/IMPLEMENTATION_PLAN.md`（V1.26）。

### 产出文件（Step 18）
- `frontend/src/services/voltiq/crm.ts`。
- `frontend/src/pages/crm/follow-ups/index.tsx`。
- `frontend/src/pages/crm/opportunities/index.tsx`。
- `frontend/src/pages/crm/deals/index.tsx`。
- `docs/memory-bank/architecture.md`。
- `docs/memory-bank/IMPLEMENTATION_PLAN.md`。
- `docs/memory-bank/progress.md`。

### 本地验证（Step 18）
- 已执行：`pnpm -C frontend run tsc`。
- 结果：通过（`tsc --noEmit` 成功，无 TypeScript 错误，2026-03-21）。

### 验收状态（Step 18）
- Step 18 已完成并通过用户测试确认（确认日期：2026-03-21）。

### 执行约束记录（Step 18）
- Step 18 已按用户明确指令启动并完成工程实现。
- Step 18 用户验证已通过，Step 19 门禁已解除；是否启动 Step 19 以用户指令为准。

### 已完成事项（Step 17 验收）
- Step 17（线索管理页面）已完成用户验收（确认日期：2026-03-21）。
- 验收过程已修复并确认：
  - 前端默认 API 地址统一为 `http://127.0.0.1:9000/api/v1`。
  - 前端请求补齐 `X-Actor-Role` 与 `X-Actor-User-Id`，消除 `GET /api/v1/leads` 的 `422` 校验错误。
  - 手动合并增加页面常驻反馈（目标线索、原因、时间），提升操作可感知性。
- Step 18（CRM 跟进与商机页面）门禁已解除，可按用户指令启动。


## 2026-03-20

### 已完成事项（Step 16）
- 已按用户指令完整阅读 `docs/memory-bank/` 全部文件与 `docs/memory-bank/progress.md`。
- 已按用户指令实施计划 Step 16（登录与角色切换）：
  - 后端 `auth` 模块完成分层落地：新增 `deps.py`、`schemas.py`、`repository.py`、`security.py`、`service.py`，并扩展 `router.py`。
  - 已实现认证接口：`POST /api/v1/auth/login`、`POST /api/v1/auth/refresh`、`GET /api/v1/auth/me`。
  - 已落地 JWT（HS256）口径：`access_token=2h`、`refresh_token=7d`。
  - 已落地密码校验口径：`PBKDF2-SHA256`（兼容历史开发明文密码）。
  - 新增 CORS 与鉴权配置项（`VOLTIQ_JWT_*`、`VOLTIQ_CORS_ALLOW_ORIGINS`），`backend/app/main.py` 版本更新至 `0.1.0-step16`。
  - 新增账号初始化脚本：`backend/scripts/seed_step16_auth_users.py`（`operator_demo/sales_demo/manager_demo`，默认密码 `voltiq123`）。
  - 前端已接入 VoltIQ 认证链路：`frontend/src/services/voltiq/auth.ts`、`app.tsx`、`requestErrorConfig.ts`、登录页、头像退出登录。
  - 前端已按角色完成菜单与操作项渲染：更新 `routes.ts`、`access.ts`、`Welcome.tsx`，并新增 Step 17-22 的权限占位页骨架（仅渲染，不实现业务逻辑）。
  - 已更新 `backend/README.md`、`frontend/README.md`、`docs/memory-bank/architecture.md`（V1.26）、`docs/memory-bank/IMPLEMENTATION_PLAN.md`（V1.23）。

### 产出文件（Step 16）
- 后端：
  - `backend/app/modules/auth/router.py`、`backend/app/modules/auth/deps.py`、`backend/app/modules/auth/schemas.py`、`backend/app/modules/auth/repository.py`、`backend/app/modules/auth/security.py`、`backend/app/modules/auth/service.py`
  - `backend/tests/test_auth_api.py`
  - `backend/scripts/seed_step16_auth_users.py`
  - `backend/app/core/config.py`、`backend/app/main.py`、`backend/.env.example`、`backend/README.md`
- 前端：
  - `frontend/src/services/voltiq/auth.ts`
  - `frontend/src/app.tsx`、`frontend/src/requestErrorConfig.ts`、`frontend/src/access.ts`
  - `frontend/src/pages/user/login/index.tsx`、`frontend/src/pages/Welcome.tsx`
  - `frontend/src/components/RightContent/AvatarDropdown.tsx`
  - `frontend/config/routes.ts`、`frontend/config/defaultSettings.ts`
  - `frontend/src/pages/_components/StepPlaceholder.tsx` 与 `frontend/src/pages/leads|crm|content|kb|metrics|audit` 占位页
  - `frontend/README.md`
- 文档：
  - `docs/memory-bank/architecture.md`、`docs/memory-bank/IMPLEMENTATION_PLAN.md`、`docs/memory-bank/progress.md`

### 本地验证（Step 16）
- 后端：
  - 计划执行：`python -m pytest -q tests/test_auth_api.py`
  - 实际结果：当前环境缺少 `pytest` 模块（`No module named pytest`），未能执行 pytest。
  - 已执行替代校验：`python -m compileall app tests`（通过）。
- 前端：
  - 已执行：`pnpm -C frontend run tsc`
  - 结果：通过（`tsc --noEmit` 成功，无 TypeScript 错误）。

### 验收状态（Step 16）
- Step 16 已完成并通过用户测试确认（确认日期：2026-03-20）。

### 执行约束记录（Step 16）
- Step 16 已按用户明确指令启动并完成实现。
- Step 16 用户验证已通过，Step 17 门禁已解除；是否启动 Step 17 以用户指令为准。

### 已完成事项（Step 15）
- 已按用户指令完整阅读 `docs/memory-bank/` 全部文件与 `docs/memory-bank/progress.md`。
- 已按用户指令实施计划 Step 15（前端框架初始化）：
  - 使用 Ant Design Pro 官方脚手架初始化前端工程，落地 React + TypeScript + Ant Design Pro 模板。
  - 初始化目录为 `frontend/`，未触发 Step 16 登录与角色权限对接。
  - 更新 `frontend/README.md`，补充基于 `pnpm` 的启动与构建说明。
  - 补充依赖 `swagger-ui-dist`，修复 OpenAPI 插件在开发启动时的缺失报错。
  - 已更新 `docs/memory-bank/architecture.md` 至 V1.23，并更新 `docs/memory-bank/IMPLEMENTATION_PLAN.md` 至 V1.20。

### 产出文件（Step 15）
- `frontend/`：Ant Design Pro 模板工程（`src/`、`config/`、`public/` 等目录）。
- `frontend/package.json`：前端依赖与脚本。
- `frontend/README.md`：本地启动说明（pnpm）。
- `docs/memory-bank/architecture.md`、`docs/memory-bank/IMPLEMENTATION_PLAN.md`：Step 15 架构基线与实施状态同步。

### 验收状态（Step 15）
- Step 15 已完成并通过用户测试确认（确认日期：2026-03-20）。
- 用户验证结果：`pnpm install`、`pnpm start` 启动成功，访问 `http://localhost:8000/welcome` 页面正常。

### 执行约束记录（Step 15）
- Step 15 已按用户明确指令启动并完成工程初始化。
- Step 15 用户验证已通过，Step 16 门禁已解除（当前未启动）。

### 已完成事项（Step 14）
- 已按用户指令完整阅读 `docs/memory-bank/` 全部文件与 `docs/memory-bank/progress.md`。
- 已按用户指令实施计划 Step 14（后端指标接口）：
  - 在 `backend/app/modules/metrics/` 新增 `deps.py`、`schemas.py`、`repository.py`、`service.py`，并扩展 `router.py`，完成 Step 14 接口分层落地。
  - 已实现 `GET /api/v1/metrics/overview`，支持 `start_date/end_date` 日期过滤与默认“今日”统计。
  - 已落地统一指标口径：`lead_count`、`deal_count`、`effective_lead_count`、`conversion_rate`（分母为 0 返回 0）。
  - 已落地上海时区自然日统计（`Asia/Shanghai`），并返回按日序列 `daily`。
  - 已落地 RBAC 与作用域约束：复用 `metrics.overview`，`sales` 仅可查看本人数据，`manager` 全量可读，`operator` 拒绝访问。
  - 已更新 `backend/app/main.py` 版本标识至 `0.1.0-step14`。
  - 已更新 `docs/memory-bank/architecture.md` 至 V1.22，并更新 `docs/memory-bank/IMPLEMENTATION_PLAN.md` 至 V1.19。
- 已完成本地回归：
  - `python -m pytest -q tests/test_metrics_api.py` 通过（3 passed）。
  - `python -m pytest -q` 全量回归通过（56 passed）。

### 产出文件（Step 14）
- `backend/app/modules/metrics/router.py`、`backend/app/modules/metrics/deps.py`、`backend/app/modules/metrics/schemas.py`、`backend/app/modules/metrics/repository.py`、`backend/app/modules/metrics/service.py`：Step 14 指标接口与分层实现。
- `backend/tests/test_metrics_api.py`：Step 14 接口集成测试（角色权限/sales 作用域/时区边界/日期过滤/零分母/非法区间）。
- `backend/app/main.py`：版本标识更新至 `0.1.0-step14`。
- `docs/memory-bank/architecture.md`、`docs/memory-bank/IMPLEMENTATION_PLAN.md`：Step 14 架构基线与实施状态同步。

### 验收状态（Step 14）
- Step 14 已完成并通过用户测试确认（确认日期：2026-03-20）。
- 用户验证结果：`python -m pytest -q tests/test_metrics_api.py` 输出 `3 passed in 1.21s`。

### 执行约束记录（Step 14）
- Step 14 已按用户明确指令启动并完成工程实现。
- Step 14 用户验证已通过，Step 15 已完成并通过用户验证，Step 16 门禁已解除（当前未启动）。

### 已完成事项（Step 13）
- 已按用户指令完整阅读 `docs/memory-bank/` 全部文件与 `docs/memory-bank/progress.md`。
- 已按用户指令实施计划 Step 13（智能客服基础问答接口）：
  - 在 `backend/app/modules/kb/` 新增 `deps.py`、`schemas.py`、`repository.py`、`service.py`，并扩展 `router.py`，完成 Step 13 接口分层落地。
  - 已实现 `POST /api/v1/kb/sessions/chat`（支持自动建会话、`session_key` 续聊、来源回传）。
  - 已实现 `GET /api/v1/kb/sessions`（会话分页查询，当前按当前用户隔离）。
  - 已落地会话与消息持久化：`kb_sessions`、`kb_messages` 双写；`assistant` 消息强制写入 `source_refs`。
  - 已落地上游失败映射：Dify 超时映射 `504`，其他上游异常映射 `502`；来源为空返回失败且不落库。
  - 已落地 `kb.session.chatted` 审计日志。
  - 已新增 Step 13 验证脚本 `backend/scripts/verify_step13_kb_api.py`，用于“5 条典型问题”验收。
  - 已新增接口测试 `backend/tests/test_kb_chat_api.py`，覆盖自动建会话、续聊、越权拦截、来源缺失失败、超时映射与 RBAC。
  - 已更新 `backend/app/main.py` 版本标识至 `0.1.0-step13`。
  - 已更新 `docs/memory-bank/architecture.md` 至 V1.19，并更新 `docs/memory-bank/IMPLEMENTATION_PLAN.md` 至 V1.16。
- 已完成本地回归：
  - `python -m pytest -q tests/test_kb_chat_api.py tests/test_rbac_policy.py tests/test_api_health.py` 通过（15 passed）。
  - `python -m pytest -q` 全量回归通过（53 passed）。

### 产出文件（Step 13）
- `backend/app/modules/kb/router.py`、`backend/app/modules/kb/deps.py`、`backend/app/modules/kb/schemas.py`、`backend/app/modules/kb/repository.py`、`backend/app/modules/kb/service.py`：Step 13 智能客服问答接口与分层实现。
- `backend/tests/test_kb_chat_api.py`：Step 13 接口集成测试（会话续聊/来源回传/RBAC/异常映射/越权拦截）。
- `backend/scripts/verify_step13_kb_api.py`：Step 13 五问验收脚本（默认超时提升至 `120s`，新增网络异常友好输出）。
- `backend/app/db/models.py`：枚举绑定修复（统一按枚举 `.value` 写入，避免大小写不一致导致的数据库枚举报错）。
- `backend/app/main.py`：版本标识更新至 `0.1.0-step13`。
- `docs/memory-bank/architecture.md`、`docs/memory-bank/IMPLEMENTATION_PLAN.md`：Step 13 架构基线与实施状态同步。

### 验收状态（Step 13）
- Step 13 已完成工程实现并通过用户测试确认（确认日期：2026-03-20）。

### 执行约束记录（当前）
- Step 13 已按用户明确指令启动并完成工程实现。
- Step 13 用户验证已通过，Step 14 门禁已解除并已实施完成。

### 运行问题记录（Step 13 用户验证）
- 现象 1：执行 `python scripts/verify_step13_kb_api.py ...` 报错 `WinError 10061`，无法连接 `127.0.0.1:8000`。
- 原因 1：本地后端 API 服务未启动，验收脚本默认访问 `http://127.0.0.1:8000`。
- 现象 2：后端启动后，`POST /api/v1/kb/sessions/chat` 返回 `500`，日志报错 `invalid input value for enum user_role: "OPERATOR"`（同类 `ACTIVE` 问题同源）。
- 原因 2：`SQLAlchemy Enum` 默认按枚举名（大写）绑定，数据库枚举实际值为小写（如 `operator`、`active`）。
- 现象 3：接口修复后，验收脚本仍可能报 `httpx.ReadTimeout`。
- 原因 3：脚本默认超时 `30s`，在 Dify 慢响应 + 后端重试退避场景下可能超时。
- 处理：
  - 启动后端并完成健康检查：`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`、`GET /healthz` 返回 `200`。
  - 修复枚举绑定：`backend/app/db/models.py` 的 `SqlEnum` 统一使用 `values_callable` 按 `.value`（小写）读写。
  - 新建可用验证账号：`operator + active` 用户 `d77487b2-faed-411a-871e-0f761b045812`（仅用于 Step 13 验证）。
  - 优化验收脚本：`backend/scripts/verify_step13_kb_api.py` 默认超时改为 `120s`，并对 `httpx.HTTPError` 输出 `[FAIL]` 友好错误。
- 结果：`python scripts/verify_step13_kb_api.py --actor-user-id d77487b2-faed-411a-871e-0f761b045812 --actor-role operator --timeout-seconds 120` 已通过（Q1-Q5 全部 `[PASS]`）。

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
- 已完成 Step 12 性能加固改造：Dify Client 支持指数退避自动重试，`streaming` 模式支持事件流解析；用于降低超时导致的失败率并改善首字等待时延。
- 已完成输出清洗：统一剔除 `<details>...</details>` 以避免思考过程泄露。
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
