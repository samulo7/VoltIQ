# Infra Directory

基础设施与环境编排目录。

- `docker-compose.step2.yml`：PostgreSQL + Redis 本地编排。
- `.env.step2.example`：Step 2 环境变量模板。
- `dify/`：Dify 上游仓库副本（用于本地 RAG/客服基础服务）。

常用命令（仓库根目录执行）：
- `docker compose --env-file .env.step2 -f infra/docker-compose.step2.yml up -d`
- `docker compose -f infra/dify/docker/docker-compose.yaml up -d`
