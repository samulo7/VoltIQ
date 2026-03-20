# Frontend (Ant Design Pro)

该目录在 Step 15 初始化为 Ant Design Pro 官方模板（React + TypeScript + Ant Design Pro）。
当前仅完成前端脚手架落地，未进行登录与角色权限对接（Step 16 之后再做）。

## 环境准备
- Node.js >= 20（见 `package.json#engines`）
- pnpm 10.x

## 常用命令

| 目的 | 命令 |
| --- | --- |
| 安装依赖 | `pnpm install` |
| 启动开发 | `pnpm start` |
| 构建产物 | `pnpm run build` |
| 代码检查 | `pnpm run lint` |
| 运行测试 | `pnpm test` |

## 启动说明
- 默认开发服务由 `pnpm start` 启动。
- 端口以 Umi Max 默认配置为准（如需修改可在后续步骤调整）。
