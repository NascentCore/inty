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
