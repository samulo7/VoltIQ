# 架构文档（Architecture）

版本：V1.8  
状态：一期基线已锁定（Step 1-7 已完成工程实现；Step 7 待用户测试验证；Step 8 未启动）  
更新日期：2026-03-18

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
- `initial` -> `proposal` -> `negotiation` -> `won/lost`
- `won` 时必须创建 `deals` 记录。
- `lost` 时必须写入丢单原因（扩展字段或审计日志）。

## 6. 去重与合并规则
- 规则 1：手机号命中已有线索，判定为重复线索。
- 规则 2：`company_name + name` 完全一致时，判定为重复线索。
- 重复处理：
  - 不新建 leads 主记录。
  - 新来源信息写入 `lead_merge_logs`。
  - 写入 `merge_reason`，并保存来源载荷 `merged_payload`。
  - 记录审计日志 `lead.merged`。

## 7. 权限模型（RBAC）
- 角色：
  - `operator`（运营）
  - `sales`（销售）
  - `manager`（管理层）
- 一期控制粒度：接口级 + 菜单级。
- Step 6 落地形态：先落地框架无关的策略层（可测试）；Step 7 已完成后端路由骨架接入，后续在 Step 15 接入前端菜单渲染。

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
  - Step 7（后端基础框架搭建）已按用户指令完成工程实现，待用户测试验证。
  - 在用户完成 Step 7 验证前，不启动 Step 8（线索管理接口）。

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
