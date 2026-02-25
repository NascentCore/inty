# 聊天页面 Firebase 事件

## 消息点赞 / 点踩（like / dislike）

- 触发位置：
  - `android_app/app/src/main/kotlin/com/ai/intellimate/chat/viewmodel/ChatViewModel.kt`
  - `setMessageVote(msgId, userVote)`（由 `likeMessage` / `dislikeMessage` 调用）
- 事件名：`chat_page_click`（代码常量：`FirebaseManager.Events.CHAT_PAGE_CLICK`）
- 区分方式：通过参数 `click_type` 区分 like/dislike，而不是使用单独事件名
  - 点赞：`message_like`
  - 点踩：`message_dislike`

### 上报参数（`setMessageVote`）

| 参数名 | 说明 |
| --- | --- |
| `click_type` | `message_like` 或 `message_dislike` |
| `agent_id` | 角色 ID |
| `agent_name` | 角色名称 |
| `message_id` | 消息 ID |
| `message_length` | 消息内容长度 |
| `message` | 消息内容 |
| `has_generated_image` | 是否包含生图（`generatedImage.imageUrl` 非空） |
| `is_opening` | 是否为 opening 消息 |
| `user_type` | 用户类型（`vip` / `free`） |
| `timestamp` | 上报时间戳（毫秒） |

### Firebase 侧查看方式

- 事件筛选：`event_name = chat_page_click`
- 参数筛选：
  - `click_type = message_like`（点赞）
  - `click_type = message_dislike`（点踩）

---

## For Moment（秘密时刻）相关事件

所有 For Moment 相关埋点均以 ChatPage 为上下文，使用 `FirebaseManager.Events.CHAT_PAGE_CLICK`（事件名 `chat_page_click`）或 `FirebaseManager.Events.FOR_MOMENT_MESSAGE_EXPOSURE`（事件名 `for_moment_message_exposure`）。通过参数 `click_type` 或事件名区分具体行为。

### 1. 消息曝光（每 ChatPage 周期上报一次）

- 触发位置：`android_app/app/src/main/kotlin/com/ai/intellimate/chat/ChatItem.kt`，`item.type == "surprise_snap"` 时由 `LaunchedEffect` 调用 `chatViewModel.reportForMomentExposureIfNeeded`
- 事件名：`for_moment_message_exposure`（代码常量：`FirebaseManager.Events.FOR_MOMENT_MESSAGE_EXPOSURE`）
- 说明：以 ChatPage 为周期，每条 For Moment 消息在周期内首次展示时上报一次；离开 ChatPage 后再次进入视为新周期，可再次上报。

| 参数名 | 说明 |
| --- | --- |
| `agent_id` | 角色 ID |
| `message_key` | 消息唯一标识（优先 `message.id`，否则 `agentId-indexId`） |

### 2. 点击「Go Premium」按钮

- 触发位置：`ChatItem.kt` → `ChatItemForMoment`（带 navController）中 `unlockByVip` 回调
- 事件名：`chat_page_click`
- 参数 `click_type`：`for_moment_go_premium`

| 参数名 | 说明 |
| --- | --- |
| `click_type` | `for_moment_go_premium` |
| `agent_id` | 角色 ID |

### 3. 点击「Unlock with Credits」按钮

- 触发位置：`ChatItem.kt` → `ChatItemForMoment`（带 navController）中 `unlockByCredits` 回调
- 事件名：`chat_page_click`
- 参数 `click_type`：`for_moment_unlock_credits`

| 参数名 | 说明 |
| --- | --- |
| `click_type` | `for_moment_unlock_credits` |
| `agent_id` | 角色 ID |

### 4. 查看图片详情（点击已解锁的 moment 图片进入全屏）

- 触发位置：`ChatItem.kt` → `ChatItemForMoment`（image/text/isLocked…）中未锁定状态下图片的 `Modifier.clickable`
- 事件名：`chat_page_click`
- 参数 `click_type`：`for_moment_view_image`

| 参数名 | 说明 |
| --- | --- |
| `click_type` | `for_moment_view_image` |
| `agent_id` | 角色 ID |

### 5. 积分支付确认弹窗 - 取消

- 触发位置：`ChatItem.kt` → `PurchaseForMomentDialog` 内「取消」按钮
- 事件名：`chat_page_click`
- 参数 `click_type`：`for_moment_purchase_dialog_cancel`

| 参数名 | 说明 |
| --- | --- |
| `click_type` | `for_moment_purchase_dialog_cancel` |
| `agent_id` | 角色 ID |

### 6. 积分支付确认弹窗 - 确认解锁

- 触发位置：`ChatItem.kt` → `PurchaseForMomentDialog` 内「解锁」确认按钮
- 事件名：`chat_page_click`
- 参数 `click_type`：`for_moment_purchase_dialog_confirm`

| 参数名 | 说明 |
| --- | --- |
| `click_type` | `for_moment_purchase_dialog_confirm` |
| `agent_id` | 角色 ID |
| `price` | 所需积分数量 |

### Firebase 侧查看方式（For Moment）

- 曝光：事件筛选 `event_name = for_moment_message_exposure`，可按 `agent_id`、`message_key` 筛选。
- 点击类：事件筛选 `event_name = chat_page_click`，参数筛选 `click_type` 为上述各值（如 `for_moment_go_premium`、`for_moment_unlock_credits`、`for_moment_view_image`、`for_moment_purchase_dialog_cancel`、`for_moment_purchase_dialog_confirm`）。
