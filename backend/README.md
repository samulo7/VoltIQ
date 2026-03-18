# Backend Directory

当前目录已完成：
- Step 5：数据库模型与 Alembic 迁移基线。
- Step 6：框架无关 RBAC 策略层。
- Step 7：FastAPI 基础框架与模块化路由骨架（不含业务 CRUD）。

## 1. 本地准备

1. 复制环境变量模板：`Copy-Item .env.example .env`
2. 安装依赖：`python -m pip install -e .[dev]`
3. 确保 PostgreSQL 可用（可复用 Step 2 的 `voltiq-postgres`）

## 2. 运行 FastAPI（Step 7）

- 开发启动：
  `python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- 全局健康检查：
  `GET /healthz`
- 模块健康检查：
  - `GET /api/v1/auth/health`
  - `GET /api/v1/leads/health`
  - `GET /api/v1/crm/health`
  - `GET /api/v1/content/health`
  - `GET /api/v1/kb/health`
  - `GET /api/v1/metrics/health`
  - `GET /api/v1/audit/health`

## 3. 迁移命令（Step 5）

- 升级到最新版本：`alembic upgrade head`
- 回滚到初始状态：`alembic downgrade base`
- 查看当前版本：`alembic current`
- 查看迁移历史：`alembic history`

## 4. 测试命令

- 运行全部测试：`python -m pytest -q`

