# AI+售电 技术栈推荐（最简单但最健壮版）

## 1. 目标
- 组件最少、交付最快，同时满足核心稳定性与可扩展性要求。
- 以“单体后端 + AI中台”为主，避免过早引入微服务。

## 2. 最简核心技术栈

### 2.1 前端
- React + TypeScript + Ant Design Pro
- 移动端（可选）：Taro（小程序 + H5 复用）

### 2.2 后端
- Python + FastAPI（单体后端，模块化拆分）
- 异步任务：Celery + Redis（定时抓电价、批量外呼队列）

### 2.3 AI 与知识库
- 知识库/RAG：Dify（对接阿里云百炼 / 通义千问）
- 文案/图片生成：通义千问（文生文）+ 通义万象（文生图）
- 预测：Python（Prophet / XGBoost / TFT）

### 2.4 数据层
- 业务数据库：PostgreSQL（主库，统一持久化）
- 缓存与队列：Redis（缓存 + Celery Broker）

### 2.5 基础设施
- 部署：Docker Compose（最简）
- 上云：阿里云 ECS + SLB + RDS for PostgreSQL + Redis
- 监控：阿里云 ARMS（或 Prometheus，二选一）

## 3. 为什么这样最简单但仍健壮
- 数据与队列统一：PostgreSQL + Redis，避免多组件运维。
- 后端单体：减少服务治理成本，依然可通过模块化支持扩展。
- AI 中台独立：Dify 降低 RAG 研发成本，接口稳定。

## 4. 何时需要升级（触发条件）
- 并发显著上升：引入消息中间件（RocketMQ）替代 Redis Broker。
- 数据分析复杂：新增 ClickHouse。
- 多团队并行开发：拆分微服务（或引入 API Gateway）。
- 可用性要求提升：容器化上 ACK + 多可用区。
