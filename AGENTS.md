# Repository Guidelines

## 项目结构与模块组织
当前仓库已完成 Step 3 目录统一，采用以下顶层结构：

- `frontend/`：前端工程目录（React + TypeScript + Ant Design Pro，后续步骤落地）。
- `backend/`：后端工程目录（FastAPI 模块化，后续步骤落地）。
- `docs/`：业务与架构文档目录，`memory-bank` 位于 `docs/memory-bank/`。
- `infra/`：基础设施与环境编排目录（Step 2 Compose、Dify、环境模板）。

文档新增请优先放在 `docs/`；若新增子目录，请同步更新本指南。

## 构建、测试与开发命令
当前尚未开始业务代码开发；已提供 Step 2 环境编排命令：

- `Copy-Item infra/.env.step2.example .env.step2`：初始化 Step 2 环境变量。
- `docker compose --env-file .env.step2 -f infra/docker-compose.step2.yml up -d`：启动 PostgreSQL + Redis。
- `docker compose --env-file .env.step2 -f infra/docker-compose.step2.yml ps`：查看 PostgreSQL + Redis 状态。
- `docker compose -f infra/dify/docker/docker-compose.yaml up -d`：启动 Dify 官方编排。
- `docker compose -f infra/dify/docker/docker-compose.yaml ps`：查看 Dify 状态。

## 编码风格与命名规范
当前内容以 Markdown 为主，保持风格统一：

- 使用 `#`/`##` 标题与短段落。
- 结构化信息优先用表格。
- 控制单行长度，避免过长的表格行。
- 文件命名要描述清晰；中英混用时需在同一类文档内保持一致。

## 测试指南
当前无业务测试。若新增测试，请建立对应目录并明确：

- 测试框架（如 `pytest`、`vitest`）。
- 命名规则（如 `test_*.py`、`*.spec.ts`）。
- 运行命令（具体可执行命令）。

## 提交与 PR 指南
当前无法读取完整 Git 历史，提交规范未知。若建立约定，请在此说明（如 Conventional Commits）。PR 需包含：

- 变更摘要。
- 关联问题/决策链接。
- 影响 UI/UX 或规格变更时的截图或文档更新。

## 安全与配置提示
本仓库包含业务/产品文档与本地编排配置，请避免提交敏感客户数据、凭据或真实电价数据。若引入配置文件，务必将密钥排除在版本控制之外，并在此列出必要环境变量。

## Agent 使用说明
编辑文档时请保持原有结构与语气，若修改需求请同步更新版本/日期字段，并确保内容范围与 `docs/memory-bank/AI_售电_产品设计文档.md` 一致。
- 当前主线为 V1（in process）；`docs/memory-bank/frontend_productization_execution_plan_v1.md` 仅在 V1 全量验收后启动执行。
- 新会话默认先读取 `docs/memory-bank/IMPLEMENTATION_PLAN.md` 与 `docs/memory-bank/progress.md`，再判断是否进入产品化改造执行。

## AI 开发规则（强制）
以下规则面向 AI 开发者，必须严格遵守。

### Always（始终应用）
- 写任何代码前必须完整阅读 `docs/memory-bank/architecture.md`（包含完整数据库结构）。
- 写任何代码前必须完整阅读 `docs/memory-bank/AI_售电_产品设计文档.md`。
- 每完成一个重大功能或里程碑后，必须更新 `docs/memory-bank/architecture.md`。
- 必须坚持模块化与多文件拆分，禁止单体巨文件（monolith）。

### 其他规则（推荐但非 Always）
- 后端采用 FastAPI 模块化组织（路由、服务、数据访问分层），避免业务逻辑堆叠在路由层。
- 数据访问集中在仓储/DAO 层，禁止在控制器直接写复杂 SQL。
- 异步任务统一使用 Celery + Redis，并为任务添加幂等性与重试策略说明。
- 前端遵循 Ant Design Pro 约定，页面与组件分离，状态管理保持单一来源。
- 依赖接入（如 Dify）必须封装为独立模块，禁止散落调用。
