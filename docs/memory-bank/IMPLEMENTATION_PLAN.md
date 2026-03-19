# 实施计划（面向 AI 开发者）

版本：V1.10  
状态：Step 1-10 已完成工程实现（Step 10 待用户测试验证）；Step 11 未启动  
更新日期：2026-03-18

本计划基于 `docs/memory-bank/tech-stack.md` 与 `docs/memory-bank/AI_售电_产品设计文档.md`，并吸收了产品负责人在 2026-03-18 的澄清结论。先交付基础功能，完整功能在“扩展阶段”追加。
执行门禁（2026-03-18）：Step 10 已完成工程实现并等待用户测试验证；在用户确认前不启动 Step 11。


## 一期范围（锁定）
- 仅交付基础功能，不包含数字人直播、智能外呼、电价预测。
- 内容生成支持三类任务：文案、图片、短视频脚本。
- 系统为单租户模式。

## 全局决策（锁定）
- 线索去重规则：
  - 主规则：手机号唯一。
  - 次规则：`企业名称 + 联系人姓名` 完全一致判重。
  - 命中去重时不新建线索，保留主记录 `source_channel` 不变，将来源载荷写入 `lead_merge_logs` 并记录审计。
- 角色与权限：
  - 角色：运营、销售、管理层。
  - 粒度：接口级 RBAC + 页面级菜单控制。
  - 一期不做字段级权限。
- 登录与鉴权：
  - 账号密码登录。
  - JWT：`access_token` 2 小时，`refresh_token` 7 天。
- 智能客服：
  - 基于 Dify 本地测试环境接入，后续可切阿里云模型。
  - 回答必须有依据（返回来源信息），表达需自然不僵硬。
- 指标口径：
  - 时区统一 `Asia/Shanghai`。
  - 基础看板默认按日聚合，可按时间范围筛选。
  - 转化率 = 成单客户数 / 有效线索数。
- 审计与安全：
  - 审计日志记录：操作者、动作、对象、变更前后、时间、IP、request_id。
  - 保留周期：180 天。
  - 手机号、邮箱等敏感信息必须脱敏后写日志。
- 质量门槛：
  - 一期验收以“功能可用 + 闭环跑通 + 基础可观测”为准。
  - 不将 99.9% SLA 和 100 路并发作为一期硬门槛。

## 分步实施（每步都要验证）

### 1. 明确版本边界与验收标准
- 指令：输出 MVP 验收清单（字段、接口、页面、指标、角色）。
- 验证：评审清单覆盖“获客→触达→成单”最小闭环，并经产品负责人确认。

### 2. 建立环境与依赖矩阵
- 指令：明确前端、后端、数据库、队列、知识库服务版本与运行方式（Docker Compose 优先）。
- 验证：本地可启动基础服务并通过健康检查。

### 3. 统一项目结构（已完成）
- 指令：确定 `frontend/`、`backend/`、`docs/`、`infra/` 目录职责。
- 验证：README 路径说明与实际目录一致。

### 4. 设计核心数据模型（第一版，已完成并通过用户验证）
- 指令：定义线索、客户、跟进记录、商机、成单、内容任务、知识条目、审计日志等实体字段。
- 验证：字段满足 MVP 页面与接口需求，并覆盖去重与状态流转规则。
- 当前产出：`docs/memory-bank/architecture.md` 已更新至 V1.5，补充实体关系与关键索引口径。
- 执行约束：Step 5 已在用户明确指令后启动并完成落地。

### 5. 建立数据库与迁移流程（已完成，待用户验证）
- 指令：配置 PostgreSQL 与迁移工具，创建核心表结构与索引（含线索去重索引）。
- 验证：迁移可反复执行且结构一致。
- 当前产出：`backend/` 已新增 SQLAlchemy + Alembic 基线与初始迁移 `20260318_0001_step5_initial_schema.py`。
- 本地验证：已执行 `upgrade head -> downgrade base -> upgrade head`，结果通过。

### 6. 建立基础权限模型（已完成，待用户验证）
- 指令：定义三角色访问范围，落地接口级 RBAC 与菜单级权限。
- 验证：接口可区分角色读写，菜单可按角色显示。
- 当前产出：
  - 已新增 `backend/app/rbac/` 策略层（与框架解耦），包含权限码、角色权限映射、接口策略注册表、菜单策略注册表。
  - 已落地 `sales` owner 强约束与 `manager` 审批权限（`opportunity.rollback`、`deal.correct`）。
  - 已新增 `backend/tests/test_rbac_policy.py`，本地 `pytest -q` 通过（7 passed）。

### 7. 后端基础框架搭建（已完成，待用户验证）
- 指令：初始化 FastAPI 项目，划分模块（`auth`、`leads`、`crm`、`content`、`kb`、`metrics`、`audit`）。
- 验证：基础路由可访问，健康检查成功。
- 当前产出：
  - 已新增 FastAPI 应用入口 `backend/app/main.py` 与 API 聚合路由 `backend/app/api/router.py`。
  - 已新增七大模块路由骨架（`backend/app/modules/*/router.py`）并统一挂载到 `/api/v1`。
  - 已新增全局 `/healthz` 与模块 `/api/v1/<module>/health` 健康检查接口。
  - 已新增 `backend/tests/test_api_health.py`，本地 `python -m pytest -q` 通过（9 passed）。

### 8. 线索管理接口（新增/查询/更新）
- 指令：实现线索创建、列表筛选、状态更新、分配与去重合并。
- 验证：API 可完成线索全流程，去重命中行为正确落库。
- 当前产出：
  - 已在 `backend/app/modules/leads/` 新增 `router.py`、`deps.py`、`schemas.py`、`repository.py`、`service.py`，完成 Step 8 接口分层落地。
  - 已实现 `POST /api/v1/leads`（创建+自动去重合并）、`GET /api/v1/leads`（筛选列表）、`GET /api/v1/leads/{lead_id}`、`PATCH /api/v1/leads/{lead_id}`、`POST /api/v1/leads/{lead_id}/assign`、`POST /api/v1/leads/{lead_id}/merge`。
  - 已接入 Header 模拟鉴权（`X-Actor-Role`、`X-Actor-User-Id`）并调用 Step 6 RBAC 策略层进行接口授权与 `sales` owner 约束。
  - 已新增 `backend/tests/test_leads_api.py`，覆盖去重、筛选、分配、更新、RBAC 与审计/合并日志落库断言。
  - 本地验证：`python -m pytest -q` 通过（16 passed）。

### 9. CRM 跟进记录接口（已完成，待用户验证）
- 指令：实现跟进记录增删改查，关联线索/客户。
- 验证：新增跟进后，线索最近跟进时间与负责人正确更新。
- 当前产出：
  - 已在 `backend/app/modules/crm/` 新增 `deps.py`、`schemas.py`、`repository.py`、`service.py`，并扩展 `router.py`，完成 Step 9 接口分层落地。
  - 已实现 `POST /api/v1/crm/follow-ups`、`GET /api/v1/crm/follow-ups`、`GET /api/v1/crm/follow-ups/{follow_up_id}`、`PATCH /api/v1/crm/follow-ups/{follow_up_id}`、`DELETE /api/v1/crm/follow-ups/{follow_up_id}`。
  - 已接入 Header 模拟鉴权（`X-Actor-Role`、`X-Actor-User-Id`）并复用 Step 6 RBAC 策略层，落地 `sales` owner 约束与 `manager` 只读。
  - 已落地 `follow_up.created`、`follow_up.updated`、`follow_up.deleted` 审计记录，并实现 `leads.latest_follow_up_at` 新增更新/删除重算。
  - 已新增 `backend/tests/test_crm_follow_ups_api.py`，覆盖 CRUD、RBAC、客户归属校验、审计落库与 `latest_follow_up_at` 更新规则。
  - 本地验证：`python -m pytest -q` 通过（22 passed，含 Step 6/7/8/9 回归）。

### 10. 商机与成单接口（已完成，待用户验证）
- 指令：实现商机阶段流转、成单记录与简要统计。
- 验证：阶段变更可追溯，成单数据可查询。
- 当前产出：
  - 已在 `backend/app/modules/crm/` 扩展 Step 10 接口，新增 `POST /api/v1/crm/opportunities`、`GET /api/v1/crm/opportunities`、`GET /api/v1/crm/opportunities/{opportunity_id}`、`PATCH /api/v1/crm/opportunities/{opportunity_id}/stage`、`POST /api/v1/crm/deals`、`GET /api/v1/crm/deals`、`GET /api/v1/crm/opportunities/stats`。
  - 已落地 `Deal 驱动 won` 规则：禁止通过阶段流转直接设置 `won`，仅允许在创建 `deal` 时自动将商机置为 `won`。
  - 已落地阶段流转规则与校验：`initial -> proposal -> negotiation -> lost`；`lost` 必须提供 `lost_reason` 并记录审计。
  - 已落地 `opportunity.created`、`opportunity.stage_changed`、`deal.created` 审计日志。
  - 已新增 `backend/tests/test_crm_opportunities_deals_api.py`，覆盖商机/成单 CRUD 查询、流转约束、RBAC owner 约束、统计与审计断言。
  - 已更新 `backend/app/main.py` 版本标识至 `0.1.0-step10`。
- 本地验证：
  - 当前执行环境 Python 解释器不可用，未能完成本地 `pytest` 执行，待用户侧执行验证。

### 11. 内容生成任务接口
- 指令：实现文案/图片/短视频脚本三类任务创建与状态查询，先用占位结果。
- 验证：任务提交后可查询状态与结果字段。

### 12. 知识库接入方案确认
- 指令：采用 Dify API 接入，明确认证、会话与知识库结构。
- 验证：测试账户可返回示例回答与来源信息。

### 13. 智能客服基础问答接口
- 指令：封装问答接口，支持上下文连续对话与来源回传。
- 验证：5 条典型问题均返回非空且有依据回答。

### 14. 后端指标接口（基础）
- 指令：提供线索数、成单数、转化率等指标接口，统一时区与口径。
- 验证：统计结果与数据库一致，时间过滤生效。

### 15. 前端框架初始化
- 指令：使用 React + TypeScript + Ant Design Pro 初始化前端工程。
- 验证：本地可启动并访问首页。

### 16. 登录与角色切换
- 指令：实现账号密码登录与角色权限渲染。
- 验证：不同角色可见菜单与可操作项不同。

### 17. 线索管理页面
- 指令：实现线索列表、筛选、编辑、分配与去重结果展示。
- 验证：页面操作可触发接口并正确展示结果。

### 18. CRM 跟进与商机页面
- 指令：实现跟进记录列表与商机阶段流转 UI。
- 验证：新增跟进实时刷新，阶段流转准确。

### 19. 内容生成页面
- 指令：实现三类内容任务提交与结果展示。
- 验证：提交后可看到任务状态变化与结果区域更新。

### 20. 智能客服页面
- 指令：实现问答对话框并展示回答依据。
- 验证：连续提问可得到上下文相关回答。

### 21. 基础数据看板
- 指令：实现基础指标看板（线索、转化、成单）。
- 验证：看板数据与后端接口一致。

### 22. 异常与审计日志（最小）
- 指令：记录关键操作（线索分配、阶段变更、成单、去重合并）。
- 验证：操作后可按对象与操作者检索日志。

### 23. 最小化安全检查
- 指令：限制接口暴露，确保敏感数据不出现在日志中。
- 验证：抽查日志与接口返回，无敏感字段泄露。

### 24. 端到端流程验证
- 指令：完成一次“线索→跟进→商机→成单”全链路演示。
- 验证：各节点数据一致，并在看板中反映。

## 测试与交付基线（一期）
- 后端：`pytest` 覆盖核心服务与接口集成测试。
- 前端：关键页面 smoke 测试。
- 端到端：至少 1 条完整闭环场景。
- 交付：本地 Docker Compose 可运行，并附生产部署草案（ECS/RDS/Redis）。

## 扩展阶段（完整功能后续追加）
- 数字人直播获客与多平台矩阵分发。
- 智能外呼系统与意向识别。
- 电价预测模型与可视化。
- 多省市电价抓取与自动播报。
- 内容自动发布与评论自动回复（openclaw）。
- 高级权限、审计与合规模块。

