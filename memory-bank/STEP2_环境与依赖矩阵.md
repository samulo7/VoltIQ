# Step 2：环境与依赖矩阵（建立环境与依赖矩阵）

版本：V1.0  
状态：已落地，待用户本地验证  
更新日期：2026-03-18

## 1. 目标与边界
- 本文档仅对应 `IMPLEMENTATION_PLAN.md` 的 Step 2。
- 目标：明确前后端运行时、数据库、队列、知识库服务版本与运行方式，并给出最小健康检查口径。
- 非目标：不进入 Step 3（不做 `frontend/`、`backend/`、`docs/`、`infra/` 目录职责收敛）。

## 2. 依赖版本矩阵（锁定）

| 组件 | 版本基线 | 用途 | 运行方式 |
| --- | --- | --- | --- |
| Node.js | 22 LTS | 前端运行时（后续步骤使用） | 本机安装或容器 |
| Python | 3.12 | FastAPI/Celery 运行时（后续步骤使用） | 本机安装或容器 |
| PostgreSQL | 16（`16-alpine`） | 主业务库 | 本仓库 `docker-compose.step2.yml` |
| Redis | 7（`7-alpine`） | 缓存与队列 Broker | 本仓库 `docker-compose.step2.yml` |
| Dify | 0.15.x（默认 `0.15.3`） | RAG/智能客服基础服务 | 本仓库内 `.dify/docker` 官方 Compose |
| Docker Compose | v2+ | 本地一键启动与联调 | Docker Desktop / Linux Docker |

## 3. 启动方式（Docker Compose 优先）

### 3.1 准备环境变量
1. 在仓库根目录复制示例文件：  
   `Copy-Item .env.step2.example .env.step2`
2. 按本机环境修改 `.env.step2`（至少检查端口与密码）。

### 3.2 启动基础服务（PostgreSQL + Redis）
1. 启动命令：  
   `docker compose --env-file .env.step2 -f docker-compose.step2.yml up -d`
2. 查看状态：  
   `docker compose --env-file .env.step2 -f docker-compose.step2.yml ps`

### 3.3 在仓库内重建 Dify（官方 Compose）
1. 首次拉取到仓库目录 `.dify`：  
   `git clone --depth 1 --branch 0.15.3 https://github.com/langgenius/dify.git .dify`
2. 初始化 Dify 环境变量：  
   `Copy-Item .dify/docker/.env.example .dify/docker/.env`
3. 启动 Dify：  
   `docker compose -f .dify/docker/docker-compose.yaml up -d`
4. 查看状态：  
   `docker compose -f .dify/docker/docker-compose.yaml ps`

说明：若 `0.15.3` 标签在你的镜像源不可用，可改为同主版本的 `0.15.x` 可用标签；修改后需在 `progress.md` 记录实际版本。

## 4. 健康检查口径（仅基础服务）

### 4.1 PostgreSQL
- 命令：  
  `docker compose --env-file .env.step2 -f docker-compose.step2.yml exec postgres pg_isready -U voltiq -d voltiq`
- 通过标准：返回 `accepting connections`。

### 4.2 Redis
- 命令：  
  `docker compose --env-file .env.step2 -f docker-compose.step2.yml exec redis redis-cli ping`
- 通过标准：返回 `PONG`。

### 4.3 Dify
- 命令：  
  `docker compose -f .dify/docker/docker-compose.yaml ps`
- 通过标准：关键容器（`api`、`worker`、`web` 及其依赖）状态为 `Up`/`healthy`（以官方编排实际健康配置为准）。

## 5. Step 2 交付物清单
- `docker-compose.step2.yml`：PostgreSQL + Redis 本地编排。
- `.env.step2.example`：Step 2 变量模板。
- `memory-bank/STEP2_环境与依赖矩阵.md`：版本、启动方式、健康检查口径。

