# Frontend（Step 16 基线）

该目录基于 Ant Design Pro（React + TypeScript + Umi Max）。
当前已完成 Step 16：账号密码登录、JWT 前端接入、角色菜单/操作项渲染。

## 环境准备
- Node.js >= 20
- pnpm 10.x

## 常用命令
- 安装依赖：`pnpm install`
- 启动开发：`pnpm start`
- 类型检查：`pnpm run tsc`

## 联调配置
- 前端默认请求地址：`http://127.0.0.1:9000/api/v1`
- 可通过环境变量覆盖：
  - `VOLTIQ_API_BASE_URL=http://127.0.0.1:9000/api/v1`

## Step 16 演示账号
先在后端执行：

`python scripts/seed_step16_auth_users.py`

默认账号：
- `operator_demo / voltiq123`
- `sales_demo / voltiq123`
- `manager_demo / voltiq123`

## 当前边界
- Step 16 仅完成登录与权限渲染骨架。
- 线索管理业务页面将在 Step 17 按计划实现。
