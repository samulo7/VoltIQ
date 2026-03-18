# Backend Directory

该目录当前已完成 Step 5（数据库与迁移流程）基础搭建，范围仅包含数据库配置、数据模型基线与 Alembic 迁移，不包含 Step 6 权限模型与业务接口实现。

## 1. 本地准备

1. 复制环境变量模板：`Copy-Item .env.example .env`
2. 确保 PostgreSQL 可用（可复用 Step 2 的 `voltiq-postgres`）。
3. 安装依赖：`python -m pip install -e .`

## 2. 迁移命令

- 升级到最新版本：`alembic upgrade head`
- 回滚到初始状态：`alembic downgrade base`
- 查看当前版本：`alembic current`
- 查看迁移历史：`alembic history`

## 3. Step 5 验证流程

1. `alembic upgrade head`
2. `alembic downgrade base`
3. `alembic upgrade head`

通过标准：三条命令均成功执行，且数据库表结构与 `docs/memory-bank/architecture.md` 一致。
