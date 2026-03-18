# MVP 验收清单（Step 1：版本边界与验收标准）

版本：V1.1  
状态：已通过产品负责人评审确认  
更新日期：2026-03-18

## 1. 一期版本边界（锁定）

### 1.1 一期必须交付
- 线索管理：新增、查询、更新、分配、去重合并。
- CRM：跟进记录、商机阶段流转、成单记录。
- 内容生成：文案、图片、短视频脚本三类任务（占位结果可接受）。
- 智能客服：基于 Dify 的问答接口与上下文会话，返回来源信息。
- 基础看板：线索数、成单数、转化率（按日，支持时间范围）。
- 账号密码登录 + JWT 鉴权 + 三角色 RBAC。
- 关键操作审计日志与敏感信息脱敏。

### 1.2 一期明确不包含
- 数字人直播。
- 智能外呼。
- 电价预测。
- 多租户能力。

## 2. 字段验收清单（MVP 最小字段）

| 实体 | 必要字段 | 必要规则 |
| --- | --- | --- |
| `users` | `id`,`username`,`password_hash`,`role`,`status`,`created_at`,`updated_at` | `username` 唯一；`role` 仅 `operator/sales/manager` |
| `leads` | `id`,`name`,`phone`,`company_name`,`source_channel`,`status`,`owner_user_id`,`latest_follow_up_at`,`created_at`,`updated_at` | `phone` 唯一；`status` 支持 `new/contacted/converted/invalid` |
| `lead_merge_logs` | `id`,`target_lead_id`,`merged_payload`,`merge_reason`,`operator_user_id`,`created_at` | 命中去重时必须写入 |
| `customers` | `id`,`lead_id`,`company_name`,`contact_name`,`contact_phone`,`created_at`,`updated_at` | `lead_id` 唯一 |
| `follow_ups` | `id`,`lead_id`,`customer_id`,`content`,`next_action_at`,`created_by`,`created_at` | 新增后应刷新 `leads.latest_follow_up_at` |
| `opportunities` | `id`,`lead_id`,`customer_id`,`stage`,`amount_estimate`,`owner_user_id`,`created_at`,`updated_at` | 阶段仅 `initial/proposal/negotiation/won/lost` |
| `deals` | `id`,`opportunity_id`,`deal_amount`,`deal_date`,`created_by`,`created_at` | `opportunity_id` 唯一；商机 `won` 时必须有 `deals` |
| `content_tasks` | `id`,`task_type`,`prompt`,`status`,`result_text`,`result_meta`,`created_by`,`created_at`,`updated_at` | `task_type` 仅 `copywriting/image/video_script` |
| `kb_sessions` | `id`,`user_id`,`session_key`,`created_at`,`updated_at` | `session_key` 唯一 |
| `kb_messages` | `id`,`session_id`,`role`,`content`,`source_refs`,`created_at` | 回复消息必须包含可追溯来源（`source_refs` 非空） |
| `audit_logs` | `id`,`actor_user_id`,`action`,`target_type`,`target_id`,`before_data`,`after_data`,`ip_address`,`request_id`,`created_at` | 记录线索分配/去重合并/阶段变更/成单；敏感字段脱敏 |

## 3. 接口验收清单（MVP 最小接口集）

| 模块 | 接口能力 | 验收标准 |
| --- | --- | --- |
| `auth` | 登录、刷新 token、当前用户信息 | 登录成功返回 `access_token`（2h）与 `refresh_token`（7d） |
| `leads` | 新增、列表、详情、更新、分配、去重合并 | 手机号或企业+联系人命中去重时，不新增主线索且落 `lead_merge_logs` |
| `crm/follow_ups` | 跟进记录增删改查 | 新增跟进后可在查询中看到，线索最近跟进时间正确 |
| `crm/opportunities` | 商机创建、阶段流转、查询 | 流转轨迹可追溯；`won/lost` 规则生效 |
| `crm/deals` | 成单创建、查询 | 与商机关联正确，金额与日期可查询 |
| `content` | 三类内容任务创建、状态查询 | 可查询 `pending/running/succeeded/failed` 与结果字段 |
| `kb` | 会话问答、上下文续聊 | 返回答案 + 来源信息，连续提问保持上下文 |
| `metrics` | 线索数、成单数、转化率 | 口径正确，时区 `Asia/Shanghai`，时间过滤生效 |
| `audit` | 审计日志查询 | 可按操作者、对象、时间、`request_id` 检索 |

## 4. 页面验收清单（MVP）

| 页面 | 关键能力 | 验收标准 |
| --- | --- | --- |
| 登录页 | 账号密码登录 | 登录后按角色进入可访问菜单 |
| 线索管理页 | 列表、筛选、编辑、分配、去重提示 | 操作后页面与后端状态一致 |
| CRM 跟进页 | 跟进记录增查改删 | 新增后列表实时可见 |
| 商机/成单页 | 阶段流转、成单录入 | `won` 后可查看对应成单记录 |
| 内容生成页 | 三类任务提交与结果展示 | 状态变化可见，失败态可见 |
| 智能客服页 | 多轮对话 + 来源展示 | 连续问答有上下文，来源可展示 |
| 基础看板页 | 线索/成单/转化率 | 与指标接口一致 |
| 审计日志页（管理层） | 条件筛选与查看 | 能检索关键操作记录 |

## 5. 指标验收清单

| 指标 | 公式/口径 | 验收标准 |
| --- | --- | --- |
| `lead_count` | 时间窗口内新建线索数 | 与数据库统计一致 |
| `deal_count` | 时间窗口内成单数 | 与数据库统计一致 |
| `conversion_rate` | 成单客户数 / 有效线索数 | 有效线索 = `status in (contacted, converted)` |
| 时区与聚合 | `Asia/Shanghai`，默认按日 | 跨日边界统计正确 |

## 6. 角色验收清单（接口级 + 菜单级）

| 角色 | 一期权限 |
| --- | --- |
| 运营（`operator`） | 可读写线索与内容任务；可查看客服会话；不可创建成单 |
| 销售（`sales`） | 可读写本人线索/跟进/商机；可创建成单；可查看基础看板 |
| 管理层（`manager`） | 全量只读 + 关键审批操作（阶段回退、成单校正）；可看全量看板与审计 |

## 7. 最小闭环验收场景（获客 -> 触达 -> 成单）

1. 创建线索（获客），验证去重规则生效。
2. 对线索发起智能客服会话（触达），验证回答含来源且会话可续聊。
3. 新增跟进并推进商机至 `won`（成单前）。
4. 创建成单记录，验证看板指标与审计日志同步更新。

通过标准：以上 4 步均可在 UI + API + 数据层闭环验证，且角色权限与审计规则均满足本清单。

## 8. 评审结论（已确认）

- 产品负责人确认：`[x] 通过` / `[ ] 需调整`
- 评审日期：`2026-03-18`
- 调整项：
  - `无`
