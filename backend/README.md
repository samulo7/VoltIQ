# Backend（Step 16 基线）

当前后端已完成：
- Step 5：数据库模型与 Alembic 迁移基线
- Step 6：框架无关 RBAC 策略层
- Step 7-14：核心业务 API（线索/CRM/内容/KB/指标）
- Step 16：登录认证接口（JWT）与当前用户接口

## 本地准备
1. 复制环境变量模板：`Copy-Item .env.example .env`
2. 安装依赖：`python -m pip install -e .[dev]`
3. 执行迁移：`alembic upgrade head`

## 运行服务
- 启动命令（建议供前端联调使用 9000 端口）：
  `python -m uvicorn app.main:app --host 127.0.0.1 --port 9000`

## Step 16 账号初始化
- 执行脚本：`python scripts/seed_step16_auth_users.py`
- 默认密码：`voltiq123`
- 账号：`operator_demo`、`sales_demo`、`manager_demo`

## 关键接口（Step 16）
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`

## 测试命令
- 全量：`python -m pytest -q`
- Step 16：`python -m pytest -q tests/test_auth_api.py`
