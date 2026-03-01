# 免费用户 Premium 预览商业化触达 - 测试计划

## 概述

本测试计划覆盖 `POST /api/v1/chat/completions/{agent_id}` 的商业化触达能力：

- 对未订阅用户按配置频率触发一条 `premium_preview`；
- 预览内容标记为 **Premium-only** 并附订阅引导文案；
- 同时返回 `business_actions.subscription_popup` 供客户端触发订阅弹窗。

## 测试目标

1. 功能正确性：只在符合条件时返回 `premium_preview` 与 `subscription_popup`。
2. 行为安全性：预览生成不污染正常聊天历史。
3. 回归安全性：不影响既有额度限制返回（`GUEST_LOGIN_REQUIRED`、`SUBSCRIPTION_REQUIRED`）。

## 前置条件

1. 后端已启动（测试配置）：

   - `cp devops/config.yaml.test config.yaml`
   - `source .venv/bin/activate`
   - `./backend/inty/start.sh --test`

2. 数据库可用（本地 PostgreSQL）。
3. 测试用户可通过 `tests/app/api/test_client.py` 正常创建并发起聊天。

## 配置矩阵

重点关注以下配置组合（`app.agent.*`）：

1. `enable_free_user_premium_preview = true`
2. `free_user_premium_preview_every_n_messages = N`（例如 5）
3. `free_user_premium_preview_max_chars = M`（例如 280）

边界值：

- `enable_free_user_premium_preview = false`：永不触发。
- `free_user_premium_preview_every_n_messages <= 0`：永不触发。
- `free_user_premium_preview_max_chars <= 0`：不截断内容。

## 自动化测试

### 已覆盖用例（当前仓库）

- `tests/app/api/v1/endpoints/test_chat.py::test_v1_chat_completions_adds_premium_preview_and_popup_action`
  - 断言返回 `business_actions[0].action_type == "subscription_popup"`；
  - 断言 `choices` 中包含一条 `message.type == "premium_preview"`；
  - 断言预览文案包含 `Premium-only preview:` 与 `Subscribe to Premium`。

- `tests/app/api/v1/endpoints/test_chat.py::test_v1_chat_completions_guest_requires_login`
- `tests/app/api/v1/endpoints/test_chat.py::test_v1_chat_completions_subscription_required`
  - 用于验证本次改动未破坏既有限制分支。

### 推荐补充用例（后续）

1. 未到触发轮次时，不返回 `premium_preview`，`business_actions` 保持默认 `none`。
2. 已订阅用户时，不返回 `premium_preview`。
3. 预览生成异常时，主聊天响应仍成功返回，且不中断流程。
4. `max_chars` 生效：超长预览被截断并追加 `...`。
5. 历史消息验证：`premium_preview` 不应写入 `chat_history`。

## 手工/接口测试步骤

1. 使用未订阅用户连续发消息直到第 `N` 条。
2. 调用 `POST /api/v1/chat/completions/{agent_id}`。
3. 校验响应：
   - `code == 200`
   - `data.business_actions` 至少包含一项 `subscription_popup`
   - `data.choices` 中存在 `type=premium_preview` 的消息
   - 预览消息中含 Premium-only 标识与订阅引导文案
4. 在非触发轮次重复调用，确认不返回 `premium_preview`。

## 通过标准

满足以下条件即视为通过：

1. 自动化用例全部通过；
2. 手工接口验证与预期一致；
3. 无回归：游客/未订阅额度限制响应保持原有行为。
