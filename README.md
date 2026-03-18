# VoltIQ

AI + 售电 MVP 项目仓库。

## 目录结构
- `frontend/`：前端工程目录（后续步骤初始化）。
- `backend/`：后端工程目录（后续步骤初始化）。
- `docs/`：文档目录，核心文档位于 `docs/memory-bank/`。
- `infra/`：基础设施目录，包含 Step 2 的 Compose 编排与 Dify 依赖目录。

## Step 2 快速启动（基础服务）
1. 复制环境变量模板：`Copy-Item infra/.env.step2.example .env.step2`
2. 启动 PostgreSQL + Redis：`docker compose --env-file .env.step2 -f infra/docker-compose.step2.yml up -d`
3. 启动 Dify：`docker compose -f infra/dify/docker/docker-compose.yaml up -d`

## 说明
- 当前已完成 Step 3（目录统一）。
- 根据执行门禁：在用户完成 Step 3 验证前，不启动 Step 4。
