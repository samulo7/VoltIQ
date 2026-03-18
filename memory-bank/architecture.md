# 架构文档（Architecture）

版本：V1.0  
状态：一期基线已锁定  
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

### 4.6 opportunities（商机）
- `id` UUID PK
- `lead_id` UUID FK -> leads.id
- `customer_id` UUID FK -> customers.id null
- `stage` enum(`initial`,`proposal`,`negotiation`,`won`,`lost`)
- `amount_estimate` numeric(14,2) null
- `owner_user_id` UUID FK -> users.id
- `created_at` timestamptz
- `updated_at` timestamptz

### 4.7 deals（成单）
- `id` UUID PK
- `opportunity_id` UUID FK -> opportunities.id UNIQUE
- `deal_amount` numeric(14,2)
- `deal_date` date
- `created_by` UUID FK -> users.id
- `created_at` timestamptz

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
  - 记录审计日志 `lead.merged`。

## 7. 权限模型（RBAC）
- 角色：
  - `operator`（运营）
  - `sales`（销售）
  - `manager`（管理层）
- 一期控制粒度：接口级 + 菜单级。

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
- AI 开发前必读文档：`AI_售电_产品设计文档.md` 与本文件。
- 每完成重大里程碑必须更新本文件（数据模型、接口边界、部署策略至少一项）。
