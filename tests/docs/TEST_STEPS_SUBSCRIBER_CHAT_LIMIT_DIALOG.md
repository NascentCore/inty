# TEST_STEPS_SUBSCRIBER_CHAT_LIMIT_DIALOG

## 目标

验证 IntelliMate Android 在**订阅用户**达到聊天使用上限时，展示专属提示对话框，而不是引导订阅弹窗。

## 前置条件

1. 使用 Android Debug 构建并登录已订阅账号（`VipStatusHelper.isUserVip() == true`）。
2. 后端环境可稳定返回聊天额度限制（`/api/v1/chat/completions/{agent_id}` 返回 `code=10001001`）。
3. 已进入任意可聊天角色会话页。

## 测试步骤

1. 在聊天页输入消息并发送，直到服务端返回额度限制。
2. 观察限制弹窗文案。
3. 点击弹窗确认按钮。
4. 再次发送消息，确认可再次弹出相同限制提示。
5. 切换到非订阅账号，重复触发限制场景，确认展示原“升级订阅”弹窗。

## 预期结果

1. 订阅用户触发限制时，弹出标题为 **Daily Premium Chat Limit Reached** 的专属对话框。
2. 弹窗正文提示“当日 Premium 聊天额度已用完，次日刷新”。
3. 点击确认后仅关闭弹窗，不跳转订阅页面。
4. 非订阅用户触发限制时，仍展示升级订阅引导弹窗（原有行为不变）。
5. 埋点区分：
   - 非订阅用户：`free_limit_reached`
   - 订阅用户：`subscriber_limit_reached`
