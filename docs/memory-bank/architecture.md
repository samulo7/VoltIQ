# 架构文档（Architecture）

版本：V1.26  
状态：一期基线已锁定（Step 1-16 已完成并通过用户验证；Step 12 测速能力含 TTFT 统计）  
更新日期：2026-03-20

## 1. 范围与边界
- 当前文档仅覆盖 MVP 一期基础功能。
- 一期不包含：数字人直播、智能外呼、电价预测。
- 一期包含：线索管理、CRM 跟进与商机成单、内容生成（文案/图片/短视频脚本）、RAG 智能客服、基础看板、账号密码登录与角色权限。
- 租户模式：单租户。

## 2. 总体架构
- 前端：React + TypeScript + Ant Design Pro。
- 后端：FastAPI 单体模块化。
- 数据库：PostgreSQL。
- 缓存与任务：Redis + Celery。
- AI 与知识库：Dify（本地测试接入，后续可切换阿里云模型）。
- 部署：Docker Compose（本地开发与联调）。

## 3. 后端模块划分
- `auth`：账号密码登录、JWT 签发与刷新、角色鉴权。
- `leads`：线索创建、查询、更新、分配、去重合并。
- `crm`：跟进记录、商机流转、成单记录。
- `content`：内容生成任务（文案/图片/短视频脚本）创建与查询。
- `kb`：Dify 问答封装、上下文对话、来源信息透传。
- `metrics`：线索、成单、转化率等基础指标聚合。
- `audit`：关键操作审计日志记录与检索。

## 4. 核心数据模型（第一版）

### 4.1 users（用户）
- `id` UUID PK
- `username` varchar(64) UNIQUE
- `password_hash` varchar(255)
- `role` enum(`operator`,`sales`,`manager`)
- `status` enum(`active`,`disabled`)
- `created_at` timestamptz
- `updated_at` timestamptz

### 4.2 leads（线索）
- `id` UUID PK
- `name` varchar(64)
- `phone` varchar(32)
- `company_name` varchar(128)
- `source_channel` varchar(64)
- `status` enum(`new`,`contacted`,`converted`,`invalid`)
- `owner_user_id` UUID FK -> users.id
- `latest_follow_up_at` timestamptz null
- `created_at` timestamptz
- `updated_at` timestamptz
- 约束与索引：
  - UNIQUE(`phone`)
  - INDEX(`company_name`,`name`)
  - INDEX(`owner_user_id`,`status`,`created_at`)

### 4.3 lead_merge_logs（线索合并日志）
- `id` UUID PK
- `target_lead_id` UUID FK -> leads.id
- `merged_payload` jsonb
- `merge_reason` varchar(64)
- `operator_user_id` UUID FK -> users.id
- `created_at` timestamptz

### 4.4 customers（客户）
- `id` UUID PK
- `lead_id` UUID FK -> leads.id UNIQUE
- `company_name` varchar(128)
- `contact_name` varchar(64)
- `contact_phone` varchar(32)
- `created_at` timestamptz
- `updated_at` timestamptz

### 4.5 follow_ups（跟进记录）
- `id` UUID PK
- `lead_id` UUID FK -> leads.id
- `customer_id` UUID FK -> customers.id null
- `content` text
- `next_action_at` timestamptz null
- `created_by` UUID FK -> users.id
- `created_at` timestamptz
- 约束与索引：
  - INDEX(`lead_id`,`created_at`)

### 4.6 opportunities（商机）
- `id` UUID PK
- `lead_id` UUID FK -> leads.id
- `customer_id` UUID FK -> customers.id null
- `stage` enum(`initial`,`proposal`,`negotiation`,`won`,`lost`)
- `amount_estimate` numeric(14,2) null
- `owner_user_id` UUID FK -> users.id
- `created_at` timestamptz
- `updated_at` timestamptz
- 约束与索引：
  - INDEX(`owner_user_id`,`stage`,`updated_at`)

### 4.7 deals（成单）
- `id` UUID PK
- `opportunity_id` UUID FK -> opportunities.id UNIQUE
- `deal_amount` numeric(14,2)
- `deal_date` date
- `created_by` UUID FK -> users.id
- `created_at` timestamptz
- 约束与索引：
  - INDEX(`deal_date`)

### 4.8 content_tasks（内容生成任务）
- `id` UUID PK
- `task_type` enum(`copywriting`,`image`,`video_script`)
- `prompt` text
- `status` enum(`pending`,`running`,`succeeded`,`failed`)
- `result_text` text null
- `result_meta` jsonb null
- `created_by` UUID FK -> users.id
- `created_at` timestamptz
- `updated_at` timestamptz
- 约束与索引：
  - INDEX(`created_by`,`status`,`created_at`)

### 4.9 kb_sessions（客服会话）
- `id` UUID PK
- `user_id` UUID FK -> users.id
- `session_key` varchar(128) UNIQUE
- `created_at` timestamptz
- `updated_at` timestamptz

### 4.10 kb_messages（客服消息）
- `id` UUID PK
- `session_id` UUID FK -> kb_sessions.id
- `role` enum(`user`,`assistant`)
- `content` text
- `source_refs` jsonb null
- `created_at` timestamptz
- 约束与索引：
  - INDEX(`session_id`,`created_at`)
  - 规则：`role=assistant` 时，`source_refs` 必须非空。

### 4.11 audit_logs（审计日志）
- `id` UUID PK
- `actor_user_id` UUID FK -> users.id
- `action` varchar(64)
- `target_type` varchar(64)
- `target_id` varchar(64)
- `before_data` jsonb null
- `after_data` jsonb null
- `ip_address` varchar(64)
- `request_id` varchar(64)
- `created_at` timestamptz
- 保留策略：180 天（到期归档或删除）。
- 约束与索引：
  - INDEX(`actor_user_id`,`created_at`)
  - INDEX(`action`,`created_at`)
  - INDEX(`request_id`)

### 4.12 实体关系基线（Step 4 定版）
- `users` 1 - N `leads`（负责人）。
- `leads` 1 - N `follow_ups`（线索跟进历史）。
- `leads` 1 - 1 `customers`（线索转客户）。
- `leads` 1 - N `opportunities`（同一线索可有多次商机尝试）。
- `opportunities` 1 - 1 `deals`（仅 `won` 阶段允许创建成单，且唯一）。
- `users` 1 - N `content_tasks`、`kb_sessions`、`audit_logs`（操作主体）。
- `kb_sessions` 1 - N `kb_messages`（会话消息流水）。

## 5. 状态流转规则

### 5.1 线索状态
- `new` -> `contacted` -> `converted`
- 任意状态可转 `invalid`（需记录原因）

### 5.2 商机阶段
- 阶段集合：`initial`、`proposal`、`negotiation`、`won`、`lost`
- Step 10 流转实现口径：
  - 通过阶段接口仅允许 `initial -> proposal -> negotiation -> lost`。
  - 不允许通过阶段接口直接设置 `won`（`won` 仅由成单创建触发）。
- `won` 时必须存在且仅存在 1 条 `deals` 记录（`opportunity_id` 唯一约束）。
- `lost` 时必须写入丢单原因（扩展字段或审计日志）。

## 6. 去重与合并规则
- 规则 1：手机号命中已有线索，判定为重复线索。
- 规则 2：`company_name + name` 完全一致时，判定为重复线索。
- 重复处理：
  - 不新建 leads 主记录。
  - 保留主记录 `source_channel` 不变，新来源信息写入 `lead_merge_logs`。
  - 写入 `merge_reason`，并保存来源载荷 `merged_payload`。
  - 记录审计日志 `lead.merged`。

## 7. 权限模型（RBAC）
- 角色：
  - `operator`（运营）
  - `sales`（销售）
  - `manager`（管理层）
- 一期控制粒度：接口级 + 菜单级。
- Step 6 落地形态：先落地框架无关的策略层（可测试）；Step 7 已完成后端路由骨架接入，Step 16 已完成前端菜单与操作项权限渲染接入。

### 7.1 权限矩阵（一期）
- 运营：
  - 可读写线索与内容任务。
  - 可查看客服会话。
  - 不可创建成单。
- 销售：
  - 可读写本人负责线索、跟进、商机。
  - 可创建成单。
  - 可查看基础看板。
- 管理层：
  - 全量只读 + 关键审批操作（阶段回退、成单校正）。
  - 可查看全量看板与审计日志。

### 7.2 Step 6 策略层约束（已落地）
- 权限编码：
  - 使用 `PermissionCode` 统一描述接口与菜单权限点（如 `lead.read`、`deal.create`、`audit_log.read`、`opportunity.rollback`、`deal.correct`）。
- 角色权限映射：
  - `operator`：线索读写/分配/合并、内容任务读写、客服会话查看。
  - `sales`：本人线索/跟进/商机读写、成单创建与查看、基础看板查看。
  - `manager`：全量读权限 + `opportunity.rollback`、`deal.correct` 两个审批权限。
- 所有权约束（sales）：
  - 对 `lead`、`follow_up`、`opportunity`、`deal` 相关权限强制 owner 校验。
  - owner 校验采用 fail-closed：缺少 owner 上下文默认拒绝。
- 注册表契约：
  - `ENDPOINT_POLICY_REGISTRY`：`<module>.<action>` -> 权限码 + `sales` 所有权策略。
  - `MENU_POLICY_REGISTRY`：菜单 key -> 访问所需权限码。
- 测试口径：
  - 覆盖角色矩阵、sales owner 约束、manager 审批特权、注册表完整性与菜单可见性。

## 8. 鉴权与安全
- 登录方式：账号密码。
- Token：JWT（access 2h，refresh 7d）。
- Step 8 过渡鉴权：在 JWT 完整落地前，线索接口使用 Header 鉴权（`X-Actor-Role`、`X-Actor-User-Id`）并复用 RBAC 策略层。
- 密码存储：`bcrypt/argon2` 哈希，禁止明文。
- 日志脱敏：手机号、邮箱、身份证等敏感字段禁止明文落日志。
- API 最小暴露：关闭未使用端点，生产环境禁用调试接口。

## 9. 指标口径
- 统一时区：`Asia/Shanghai`。
- 聚合粒度：默认按日，支持时间范围筛选。
- 核心指标：
  - `lead_count`：时间窗口内新建线索数。
  - `deal_count`：时间窗口内成单数。
  - `conversion_rate`：成单客户数 / 有效线索数。
- 有效线索定义：`status in (contacted, converted)` 的线索。

## 10. 审计与可观测性
- 必审计事件：
  - 线索分配
  - 线索去重合并
  - 商机阶段变更
  - 成单创建与修改
- 检索条件：按操作者、对象、时间范围、request_id。
- 一期性能目标：功能可用与基础可观测，不强制 99.9% SLA 和 100 并发压测。

## 11. 开发约束同步
- AI 开发前必读文档：`docs/memory-bank/AI_售电_产品设计文档.md` 与 `docs/memory-bank/architecture.md`。
- 每完成重大里程碑必须更新本文件（数据模型、接口边界、部署策略至少一项）。

## 12. memory-bank 文档职责映射（新增）
- `docs/memory-bank/AI_售电_产品设计文档.md`
  - 作用：产品原始需求与业务目标来源，定义全量业务蓝图（含一期与后续扩展）。
  - 使用方式：用于确认“做什么”，是范围判断的上游依据。
- `docs/memory-bank/tech-stack.md`
  - 作用：技术选型基线，约束前后端、数据层、AI 中台与部署方式。
  - 使用方式：用于确认“用什么做”，避免技术栈漂移。
- `docs/memory-bank/IMPLEMENTATION_PLAN.md`
  - 作用：分步实施路线图与每步验证标准，定义执行顺序与门禁。
  - 使用方式：用于确认“先做什么、如何验收”，开发按步骤推进。
- `docs/memory-bank/MVP_验收清单.md`
  - 作用：实施计划 Step 1 的交付物，沉淀一期 MVP 的字段、接口、页面、指标、角色验收口径。
  - 使用方式：作为后续步骤的共同验收基线；若超出清单即视为范围变更。
- `docs/memory-bank/progress.md`
  - 作用：开发日志与里程碑记录，面向后续开发者快速了解“已经做了什么、当前卡点是什么”。
  - 使用方式：每完成一个阶段或关键决策后更新，记录产出文件与验收状态。
- `docs/memory-bank/architecture.md`（本文件）
  - 作用：系统架构与核心数据模型的当前事实来源，承接每个里程碑后的结构性沉淀。
  - 使用方式：当实现引入新模块、边界变化或数据结构调整时，必须同步更新。

## 13. Step 2 运行时基线（新增）
- 版本基线：
  - 前端运行时：Node.js 22 LTS
  - 后端运行时：Python 3.12
  - PostgreSQL：16（`16-alpine`）
  - Redis：7（`7-alpine`）
  - Dify：0.15.x（默认 `0.15.3`）
- 运行方式：
  - `infra/docker-compose.step2.yml` 负责 PostgreSQL + Redis。
  - Dify 使用仓库内 `infra/dify/docker/docker-compose.yaml` 官方编排启动。
- 验证口径（Step 2）：
  - 仅验证基础服务健康检查（PostgreSQL、Redis、Dify），不包含业务接口联调。
- 执行边界：
  - Step 5（数据库与迁移流程）已完成工程落地。
  - Step 6（基础权限模型）已完成工程实现并通过本地单测。
  - Step 7（后端基础框架搭建）已按用户指令完成工程实现。
  - Step 8（线索管理接口）已按用户指令完成工程实现并通过本地回归测试。
  - Step 9（CRM 跟进记录接口）已按用户指令完成工程实现并通过用户门禁解除。
  - Step 10（商机与成单接口）已按用户指令完成工程实现。
  - Step 11（内容生成任务接口）已按用户指令完成工程实现。
  - Step 12（知识库接入方案确认）已按用户指令完成工程实现，并通过用户测试验证（2026-03-19）。
  - Step 13（智能客服基础问答接口）已完成并通过用户测试验证（2026-03-20）。
  - Step 14（后端指标接口）已完成并通过用户测试验证（2026-03-20）。
  - Step 15（前端框架初始化）已完成并通过用户测试验证（2026-03-20）。
  - Step 16（登录与角色切换）已完成并通过用户测试验证（2026-03-20）。

## 14. Step 3 目录基线（新增）
- `frontend/`：前端工程目录（后续步骤落地 React + TypeScript + Ant Design Pro）。
- `backend/`：后端工程目录（后续步骤落地 FastAPI 模块化服务）。
- `docs/`：文档目录，memory-bank 位于 `docs/memory-bank/`。
- `infra/`：基础设施目录，包含 Step 2 编排文件与 Dify 仓库副本。

## 15. Step 5 数据库与迁移基线（新增）
- 迁移工具：
  - `SQLAlchemy 2.x + Alembic`（位于 `backend/`）。
- 迁移版本：
  - 基线迁移：`20260318_0001_step5_initial_schema.py`。
- 落地范围：
  - 创建一期核心表：`users`、`leads`、`lead_merge_logs`、`customers`、`follow_ups`、`opportunities`、`deals`、`content_tasks`、`kb_sessions`、`kb_messages`、`audit_logs`。
  - 创建关键唯一约束与索引（含线索去重唯一索引 `leads.phone`）。
  - 落地 `kb_messages` 来源约束：`role=assistant` 时 `source_refs` 必须非空。
- UUID 策略：
  - 主键采用应用层 `uuid4` 生成，不依赖 PostgreSQL 扩展函数。

## 16. Step 6 基础权限模型基线（新增）
- 落地目录：
  - `backend/app/rbac/`（`types.py`、`policy.py`、`__init__.py`）。
- 核心接口：
  - `AccessRequest` + `is_allowed()`：统一权限判定入口。
  - `EndpointAccessRequest` + `authorize_endpoint()`：接口动作授权入口。
  - `can_view_menu()`：菜单可见性授权入口。
- 关键策略：
  - `sales` 的 owner 约束在策略层强制执行。
  - `manager` 仅保留只读 + `opportunity.rollback`、`deal.correct` 审批特权。
- 测试基线：
  - `backend/tests/test_rbac_policy.py`，本地 `pytest` 通过（7 passed）。

## 17. Step 7 后端基础框架基线（新增）
- 落地目录：
  - `backend/app/main.py`、`backend/app/api/`、`backend/app/modules/`。
- 模块骨架：
  - 已创建 `auth`、`leads`、`crm`、`content`、`kb`、`metrics`、`audit` 七个模块路由骨架。
  - 统一挂载到 `/api/v1/*` 前缀下。
- 健康检查：
  - 全局健康检查：`/healthz`。
  - 模块健康检查：`/api/v1/<module>/health`。
- 测试基线：
  - `backend/tests/test_api_health.py` 覆盖全局与模块健康检查、OpenAPI 可访问性。
  - 本地 `python -m pytest -q` 通过（9 passed，包含 Step 6 回归测试）。

## 18. Step 8 线索管理接口基线（新增）
- 落地目录：
  - `backend/app/modules/leads/`（`router.py`、`deps.py`、`schemas.py`、`repository.py`、`service.py`）。
- 接口基线：
  - `POST /api/v1/leads`：创建线索，命中去重规则时自动合并并写 `lead_merge_logs`。
  - `GET /api/v1/leads`：支持 `status`、`owner_user_id`、`source_channel`、`keyword`、`created_at` 时间范围筛选。
  - `GET /api/v1/leads/{lead_id}`、`PATCH /api/v1/leads/{lead_id}`、`POST /api/v1/leads/{lead_id}/assign`、`POST /api/v1/leads/{lead_id}/merge`。
- 权限与约束：
  - 接口授权复用 Step 6 RBAC 策略层，`sales` 按 owner 强约束（fail-closed）。
  - `manager` 保持线索读权限，写接口默认拒绝。
- 审计与脱敏：
  - 已落地 `lead.created`、`lead.updated`、`lead.assign`、`lead.merged` 审计写入。
  - 审计与合并载荷中的手机号按脱敏规则写入。
- 测试基线：
  - 新增 `backend/tests/test_leads_api.py`，覆盖去重、筛选、分配、更新、RBAC 与审计/合并日志落库。
  - 本地 `python -m pytest -q` 通过（16 passed，含 Step 6/7 回归）。

## 19. Step 9 CRM 跟进记录接口基线（新增）
- 落地目录：
  - `backend/app/modules/crm/`（`router.py`、`deps.py`、`schemas.py`、`repository.py`、`service.py`）。
- 接口基线：
  - `POST /api/v1/crm/follow-ups`：新增跟进，支持关联 `lead_id` 与可选 `customer_id`。
  - `GET /api/v1/crm/follow-ups`：支持 `lead_id`、`customer_id`、`created_by`、`created_at` 时间范围筛选与分页。
  - `GET /api/v1/crm/follow-ups/{follow_up_id}`、`PATCH /api/v1/crm/follow-ups/{follow_up_id}`、`DELETE /api/v1/crm/follow-ups/{follow_up_id}`。
- 业务规则与约束：
  - 新增跟进后同步更新 `leads.latest_follow_up_at`。
  - 删除跟进后按剩余记录重算 `leads.latest_follow_up_at`（无记录则置空）。
  - 传入 `customer_id` 时必须存在，且必须归属同一 `lead_id`。
- 权限与约束：
  - 接口授权复用 Step 6 RBAC 策略层与现有 `crm.follow_ups.*` endpoint key。
  - `sales` 按 owner 强约束，仅可操作本人负责线索的跟进记录。
  - `manager` 保持只读（可查不可写）。
- 审计基线：
  - 已落地 `follow_up.created`、`follow_up.updated`、`follow_up.deleted` 审计写入。
- 测试基线：
  - 新增 `backend/tests/test_crm_follow_ups_api.py`，覆盖创建/查询/更新/删除、owner 权限、客户归属校验、`latest_follow_up_at` 更新与重算、审计落库断言。
  - 本地 `python -m pytest -q` 通过（22 passed，含 Step 6/7/8 回归）。

## 20. Step 10 商机与成单接口基线（新增）
- 落地目录：
  - `backend/app/modules/crm/`（`router.py`、`service.py`；复用 `repository.py`、`schemas.py`）。
- 接口基线：
  - `POST /api/v1/crm/opportunities`、`GET /api/v1/crm/opportunities`、`GET /api/v1/crm/opportunities/{opportunity_id}`。
  - `PATCH /api/v1/crm/opportunities/{opportunity_id}/stage`（阶段流转）。
  - `POST /api/v1/crm/deals`、`GET /api/v1/crm/deals`。
  - `GET /api/v1/crm/opportunities/stats`（简要统计）。
- 业务规则与约束：
  - `Deal 驱动 won`：禁止通过阶段流转接口直接设置 `won`，仅在创建成单时自动将商机置为 `won`。
  - 阶段流转接口允许：`initial -> proposal -> negotiation -> lost`。
  - 切换至 `lost` 时必须提供 `lost_reason`（写入审计日志）。
  - 创建成单仅允许商机处于 `negotiation` 且商机尚无成单记录。
  - 创建商机时 `owner_user_id` 继承线索负责人；`customer_id`（若传入）必须归属同一线索。
- 权限与约束：
  - 接口授权复用 Step 6 RBAC 策略层与现有 `crm.opportunities.*`、`crm.deals.*` endpoint key。
  - `sales` 按 owner 强约束，仅可操作本人商机与成单。
  - `manager` 保持只读（可查不可写）。
- 审计基线：
  - 已落地 `opportunity.created`、`opportunity.stage_changed`、`deal.created`。
- 测试基线：
  - 新增 `backend/tests/test_crm_opportunities_deals_api.py`，覆盖创建/查询、流转约束、Deal 驱动 won、owner 权限、统计口径与审计落库断言。

## 21. Step 11 内容生成任务接口基线（新增）
- 落地目录：
  - `backend/app/modules/content/`（`router.py`、`deps.py`、`schemas.py`、`repository.py`、`service.py`）。
- 接口基线：
  - `POST /api/v1/content/tasks`：创建内容生成任务。
  - `GET /api/v1/content/tasks`：按任务类型、状态、创建人、时间范围筛选并分页查询。
  - `GET /api/v1/content/tasks/{task_id}`：查询任务详情。
- 业务规则与约束：
  - Step 11 占位执行口径为“立即成功”：创建任务即写入 `status=succeeded`。
  - 三类任务（`copywriting`、`image`、`video_script`）均返回占位 `result_text` 与 `result_meta`。
- 权限与约束：
  - 接口授权复用 Step 6 RBAC 策略层与现有 `content.tasks.create`、`content.tasks.list` endpoint key。
  - `operator` 可创建与查询内容任务。
  - `manager` 只读查询内容任务。
  - `sales` 默认拒绝访问内容任务接口。
- 审计基线：
  - 已落地 `content_task.created`、`content_task.queried`。
- 测试基线：
  - 新增 `backend/tests/test_content_tasks_api.py`，覆盖创建、查询、筛选分页、RBAC 与审计断言。

## 22. Step 12 知识库接入方案基线（新增）
- 接入方式：
  - 采用 Dify Service API（本地 Compose 环境）接入，默认走 `POST /chat-messages`，`response_mode=blocking`。
  - 鉴权使用 `Authorization: Bearer {API_KEY}`，API Key 仅后端持有。
- 落地目录：
  - `backend/app/integrations/dify/`（`client.py`、`schemas.py`、`exceptions.py`）。
  - `backend/scripts/verify_step12_dify.py`（连通性与来源回传验证脚本）。
- 配置基线：
  - 环境变量：`VOLTIQ_DIFY_BASE_URL`、`VOLTIQ_DIFY_API_KEY`、`VOLTIQ_DIFY_REQUEST_TIMEOUT_SECONDS`、`VOLTIQ_DIFY_RESPONSE_MODE`、`VOLTIQ_DIFY_REQUEST_MAX_RETRIES`、`VOLTIQ_DIFY_REQUEST_RETRY_BACKOFF_SECONDS`。
  - `VOLTIQ_DIFY_BASE_URL` 兼容 host 级输入；未带路径时按 `/v1` 规范化。
  - 支持 `blocking` 与 `streaming` 两种响应模式。
- 会话与来源结构约束：
  - Step 12 不新增数据库字段，不执行迁移。
  - 会话延续依赖 Dify `conversation_id`；Step 13 已按该约束落地会话与消息持久化。
  - 回答依据来自 Dify `metadata.retriever_resources`，作为“有依据回答”的统一来源载体。
- 验证口径：
  - 执行 `python scripts/verify_step12_dify.py` 成功返回。
  - 断言 `answer` 非空且 `retriever_resources` 非空。
  - 性能加固口径：请求超时后按指数退避自动重试；`streaming` 模式可用于降低首字等待时延。\n  - 输出清洗：统一剔除 `<details>...</details>` 以避免思考过程泄露。
  - Step 12 阶段不新增 `/api/v1/kb` 业务问答接口；该门禁已在 Step 13 实施时遵循并解除。

## 23. Step 12 延迟基准测试能力（新增）
- 目标口径：
  - 以“真实问答端到端耗时”评估 Step 12 速度表现，默认阈值 `<= 2s`（可通过参数覆盖）。
  - 支持 `blocking` 与 `streaming` 两种模式独立采样，支持预热样本与正式样本分离统计。
- 落地目录：
  - `backend/scripts/benchmark_step12_dify_latency.py`：Step 12 延迟基准脚本。
  - `backend/tests/test_step12_latency_benchmark.py`：统计逻辑与汇总输出单测。
- 输出产物：
  - `artifacts/step12-latency-blocking.csv`
  - `artifacts/step12-latency-streaming.csv`
  - `artifacts/step12-latency-summary.md`
- 统计口径：
  - 按模式输出 `avg/p50/p95`、`<= 阈值达标率`、`失败率`。
  - `streaming` 模式新增 `TTFT`（首字时间）统计：`avg_ttft/p50_ttft/p95_ttft`。
  - 输出慢样本 Top3 与失败原因分布，便于定位慢查询与异常类型。
- 实现说明：
  - `streaming` 延迟采样改为真实 SSE 事件流测量，不再依赖整包响应读取，避免“完整结束时间误代替首字时延”。
  - `backend/.env.example` 默认 `VOLTIQ_DIFY_RESPONSE_MODE=blocking`，作为当前稳定口径。
- 约束边界：
  - 本能力仅新增离线测速脚本与测试，不新增后端 API、不变更数据库结构、不触发迁移。

## 24. Step 13 智能客服基础问答接口基线（新增）
- 落地目录：
  - `backend/app/modules/kb/`（`router.py`、`deps.py`、`schemas.py`、`repository.py`、`service.py`）。
- 接口基线：
  - `POST /api/v1/kb/sessions/chat`：客服问答入口，支持 `session_key` 续聊与来源回传。
  - `GET /api/v1/kb/sessions`：客服会话分页查询（当前按当前用户隔离）。
- 会话与消息规则：
  - 首轮不传 `session_key` 时自动创建会话，`session_key` 对齐 Dify `conversation_id`。
  - 续聊时透传 `session_key` 到 Dify `conversation_id`，维持上下文连续。
  - 每次成功问答写入两条消息：`user` + `assistant`。
  - `assistant` 消息必须写入 `source_refs.retriever_resources`（来源非空约束）。
- 失败与一致性规则：
  - Dify 返回空回答或空来源时，接口返回上游错误且不写入会话消息。
  - Dify 超时映射为 `504`，其他上游失败映射为 `502`。
  - 会话归属校验：仅会话所有者可续聊该 `session_key`。
- 权限与审计：
  - 接口授权复用 Step 6 RBAC：`kb.sessions.chat`、`kb.sessions.list`。
  - `operator`、`manager` 允许访问；`sales` 默认拒绝。
  - 已落地 `kb.session.chatted` 审计日志。
- 测试与验证基线：
  - 新增 `backend/tests/test_kb_chat_api.py`，覆盖自动建会话、续聊、来源缺失失败、超时映射、越权拦截与 RBAC。
  - 新增 `backend/scripts/verify_step13_kb_api.py`，串行 5 条典型问题验收“回答非空 + 来源非空”。
  - 本地验证：`python -m pytest -q` 全量通过（53 passed）。
  - 用户验证：`python scripts/verify_step13_kb_api.py --actor-user-id d77487b2-faed-411a-871e-0f761b045812 --actor-role operator` 通过（Q1-Q5 全部 `[PASS]`）。
- 执行边界：
  - Step 13 用户验证已通过，Step 14 门禁已解除并已实施完成。

## 25. Step 14 后端指标接口基线（新增）
- 落地目录：
  - `backend/app/modules/metrics/`（`router.py`、`deps.py`、`schemas.py`、`repository.py`、`service.py`）。
- 接口基线：
  - `GET /api/v1/metrics/overview`：返回指标总览与按日序列（`daily`）。
  - 查询参数：`start_date`、`end_date`（`YYYY-MM-DD`，按 `Asia/Shanghai` 自然日）。
  - 参数缺省：`start_date/end_date` 同时缺省时统计“今日”；仅传一侧时按单日统计。
- 指标口径：
  - `lead_count`：时间窗口内新建线索数（按 `leads.created_at`）。
  - `deal_count`：时间窗口内成单数（按 `deals.deal_date`）。
  - `effective_lead_count`：时间窗口内 `status in (contacted, converted)` 的新建线索数。
  - `conversion_rate`：`deal_count / effective_lead_count`；分母为 `0` 时返回 `0`。
  - 汇总与按日序列均采用统一口径，时区固定 `Asia/Shanghai`。
- 权限与范围：
  - 接口授权复用 Step 6 RBAC：`metrics.overview`。
  - `sales` 仅可查看本人数据（按 `owner_user_id` 作用域过滤）。
  - `manager` 可查看全量数据；`operator` 默认拒绝访问。
- 测试基线：
  - 新增 `backend/tests/test_metrics_api.py`，覆盖角色权限、sales 作用域、上海时区跨日边界、时间过滤、零分母转化率与非法日期区间。
  - 本地验证：`python -m pytest -q tests/test_metrics_api.py` 通过（3 passed）。
  - 全量回归：`python -m pytest -q` 通过（56 passed）。
- 版本基线：
  - `backend/app/main.py` 版本标识更新至 `0.1.0-step14`。
- 执行边界：
  - Step 14 用户验证已通过，Step 15 已完成并通过用户验证；Step 16 已完成并通过用户验证，Step 17 门禁已解除。

## 26. Step 15 前端框架初始化基线（新增）
- 模板：Ant Design Pro 官方模板（React + TypeScript + Ant Design Pro，Umi Max）。
- 初始化目录：`frontend/`。
- 运行方式：使用 `pnpm` 安装与启动（具体命令见 `frontend/README.md`）。
- 执行边界：仅完成脚手架初始化，不包含登录与角色权限对接（Step 16 之后执行）。

## 27. Step 16 登录与角色切换基线（新增）
- 后端认证接口：
  - 已在 `backend/app/modules/auth/` 新增 `deps.py`、`schemas.py`、`repository.py`、`security.py`、`service.py` 并扩展 `router.py`。
  - 已实现 `POST /api/v1/auth/login`、`POST /api/v1/auth/refresh`、`GET /api/v1/auth/me`。
  - Token 口径：JWT（HS256）`access=2h`、`refresh=7d`，包含 `sub/role/username/typ/iat/exp`。
- 安全与运行基线：
  - 新增密码口径：`PBKDF2-SHA256`（兼容历史本地明文口径用于开发联调）。
  - 新增配置项：`VOLTIQ_JWT_SECRET_KEY`、`VOLTIQ_JWT_ISSUER`、`VOLTIQ_JWT_ACCESS_EXPIRES_MINUTES`、`VOLTIQ_JWT_REFRESH_EXPIRES_MINUTES`、`VOLTIQ_CORS_ALLOW_ORIGINS`。
  - `backend/app/main.py` 版本标识更新至 `0.1.0-step16`，并新增 CORS 中间件（前端跨域联调）。
  - 新增初始化脚本：`backend/scripts/seed_step16_auth_users.py`（`operator_demo`、`sales_demo`、`manager_demo`，默认密码 `voltiq123`）。
- 前端权限渲染基线：
  - 已新增 `frontend/src/services/voltiq/auth.ts`，落地 token 存储与认证请求封装。
  - 已改造 `frontend/src/app.tsx`、`frontend/src/requestErrorConfig.ts`、`frontend/src/pages/user/login/index.tsx`、`frontend/src/components/RightContent/AvatarDropdown.tsx`。
  - 已按 `operator/sales/manager` 在 `frontend/src/access.ts` 实现菜单与操作项权限渲染。
  - 已改造路由与占位页骨架（`/leads`、`/crm/*`、`/content/tasks`、`/kb/sessions`、`/metrics`、`/audit/logs`），用于 Step 16 角色可见性验证。
- 测试基线：
  - 新增 `backend/tests/test_auth_api.py`，覆盖登录成功、错误密码、禁用用户、refresh 与 `me` 鉴权。
  - 当前环境无法执行 `pytest`（缺少 `pytest` 模块）；已执行 `python -m compileall app tests` 语法校验通过。
- 执行边界：
  - Step 16 已按用户指令实施完成并通过用户测试验证（2026-03-20）。
  - Step 17 门禁已解除，可按用户指令启动线索管理页面实现。


