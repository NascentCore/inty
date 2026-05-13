# Inty 后端 API 服务端点

- 后台管理用的 API 只能开放给超级用户（superuser）
- 增加新的 API endpoint(s)、迁移实现文件、或改动已登记路径的行为时，须同步更新下文「API 端点列表」章节（表格与块引用注记）

## API 端点列表

下列内容列出当前代码中注册的 HTTP 与 WebSocket 路径及实现文件。表格中的路径除 `{...}` 占位段外为字面量。

WebSocket 在 OpenAPI 中不可见；下表方法列写 `WS`。

Inty 不提供 `/health`；Ops 根路径 `/` 在关闭 API-only 时为评测页，与 Inty 的 JSON 健康根路径不同。

## API v1 共有端点（Inty 与 Ops）

### 认证 (Auth)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/auth/guest` | POST | `app/api/v1/endpoints/auth.py` |
| `/api/v1/auth/google/login` | POST | `app/api/v1/endpoints/auth.py` |

### 用户 (Users)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/users/profile` | GET | `app/api/v1/endpoints/users.py`（deprecated，兼容 v1.0.3） |
| `/api/v1/users/me` | GET | `app/api/v1/endpoints/users.py` |
| `/api/v1/users/profile` | PUT | `app/api/v1/endpoints/users.py` |
| `/api/v1/users/device/register` | POST | `app/api/v1/endpoints/users.py` |
| `/api/v1/users/deletion/check` | GET | `app/api/v1/endpoints/users.py`（deprecated） |
| `/api/v1/users/delete-account` | POST | `app/api/v1/endpoints/users.py` |
| `/api/v1/users` | GET | `app/api/v1/endpoints/users.py`（评测 / 内部用；`include_in_schema=False`；handler 未挂鉴权依赖，见代码 TODO） |

### AI 角色 (Agents)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/ai/agents/me` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/admin/list` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/search` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/recommend` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents` | POST | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/{agent_id}` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/{agent_id}` | PUT | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/{agent_id}` | DELETE | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/{agent_id}/generate-background-animated` | POST | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/text-to-image` | POST | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/models/openrouter` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/image-generation/config` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/image-generation/config` | PUT | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/prompts/available` | GET | `app/api/v1/endpoints/agents.py` |

### 聊天 (Chat)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/chat/completions/{agent_id}` | POST | `app/api/v1/endpoints/chat.py` |
| `/api/v1/chat/ws` | WS | `app/api/v1/endpoints/chat.py` |
| `/api/v1/chat/ws/verify` | WS | `app/api/v1/endpoints/chat.py` |
| `/api/v1/chat/images/{agent_id}` | POST | `app/api/v1/endpoints/chat.py` |
| `/api/v1/chat/music/{agent_id}` | POST | `app/api/v1/endpoints/chat.py` |

### 聊天会话 (Chats)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/chats/modes` | GET | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/` | GET | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/` | POST | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/{chat_id}` | DELETE | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/status` | GET | `app/api/v1/endpoints/chats.py`（deprecated） |
| `/api/v1/chats/agents/{agent_id}/messages` | GET | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/surprise-snap/unlock` | POST | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/messages/vote` | POST | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/{agent_id}/messages/{message_id}/voice` | POST | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/voices/{voice_id}` | GET | `app/api/v1/endpoints/chats.py`（deprecated） |
| `/api/v1/chats/agents/{agent_id}/settings` | PUT | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/{agent_id}/settings` | GET | `app/api/v1/endpoints/chats.py`（deprecated 说明见代码 docstring） |
| `/api/v1/chats/agents/{agent_id}/chats` | DELETE | `app/api/v1/endpoints/chats.py`（deprecated） |
| `/api/v1/chats/agents/{agent_id}/clear-messages` | POST | `app/api/v1/endpoints/chats.py` |

### 图片 (Images)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/images` | POST | `app/api/v1/endpoints/images.py` |

### 通知 (Notifications)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/notifications/` | POST | `app/api/v1/endpoints/notification.py` |
| `/api/v1/notifications/` | GET | `app/api/v1/endpoints/notification.py` |
| `/api/v1/notifications/templates/types` | GET | `app/api/v1/endpoints/notification.py` |
| `/api/v1/notifications/templates` | POST | `app/api/v1/endpoints/notification.py` |
| `/api/v1/notifications/templates` | GET | `app/api/v1/endpoints/notification.py` |

### 举报 (Report)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/report/` | GET | `app/api/v1/endpoints/report.py` |
| `/api/v1/report/{report_id}` | GET | `app/api/v1/endpoints/report.py` |
| `/api/v1/report/{report_id}/conversation-groups` | GET | `app/api/v1/endpoints/report.py` |
| `/api/v1/report/{report_id}/conversation-messages` | GET | `app/api/v1/endpoints/report.py` |
| `/api/v1/report/{report_id}/github-issue` | PUT | `app/api/v1/endpoints/report.py` |
| `/api/v1/report/` | POST | `app/api/v1/endpoints/report.py` |
| `/api/v1/report/{report_id}` | DELETE | `app/api/v1/endpoints/report.py` |

### 设置 (Settings)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/settings/` | GET | `app/api/v1/endpoints/settings.py` |
| `/api/v1/settings/` | PUT | `app/api/v1/endpoints/settings.py` |

### 订阅 (Subscription)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/subscription/plans` | GET | `app/api/v1/endpoints/subscription.py` |
| `/api/v1/subscription/status` | GET | `app/api/v1/endpoints/subscription.py` |
| `/api/v1/subscription/usage` | GET | `app/api/v1/endpoints/subscription.py` |
| `/api/v1/subscription/verify` | POST | `app/api/v1/endpoints/subscription.py` |
| `/api/v1/subscription/webhook` | POST | `app/api/v1/endpoints/subscription.py` |
| `/api/v1/subscription/admin/plans` | POST | `app/api/v1/endpoints/subscription.py` |
| `/api/v1/subscription/admin/plans` | GET | `app/api/v1/endpoints/subscription.py` |
| `/api/v1/subscription/admin/users/{user_id}/subscription` | GET | `app/api/v1/endpoints/subscription.py` |
| `/api/v1/subscription/admin/users/{user_id}/usage` | GET | `app/api/v1/endpoints/subscription.py` |
| `/api/v1/subscription/admin/refund` | POST | `app/api/v1/endpoints/subscription.py` |

### 文本转语音 (Text-to-Speech)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/text-to-speech/list-voices` | GET | `app/api/v1/endpoints/text_to_speech.py` |

### 版本 (Version)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/version/check` | POST | `app/api/v1/endpoints/version.py` |

> **`/api/v1/version/check` 行为说明**：该端点会将客户端上报的 Android 应用版本代码（Header `appVersionCode`）写入 `users.last_android_app_version_code`，用于 **push worker 的 feature gating**（worker 可根据该值决定是否发送或如何构造 push）。字段命名为 Android 专用，因后端未来可能服务 iOS 应用。

### 角色主题 (Character Themes)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/character-themes/` | POST | `app/api/v1/endpoints/character_themes.py` |
| `/api/v1/character-themes/` | GET | `app/api/v1/endpoints/character_themes.py` |
| `/api/v1/character-themes/{theme_id}` | GET | `app/api/v1/endpoints/character_themes.py` |
| `/api/v1/character-themes/{theme_id}` | PUT | `app/api/v1/endpoints/character_themes.py` |
| `/api/v1/character-themes/{theme_id}` | DELETE | `app/api/v1/endpoints/character_themes.py` |
| `/api/v1/character-themes/{theme_id}/agents` | POST | `app/api/v1/endpoints/character_themes.py` |
| `/api/v1/character-themes/{theme_id}/agents/{agent_id}` | DELETE | `app/api/v1/endpoints/character_themes.py` |
| `/api/v1/character-themes/{theme_id}/agents/reorder` | PUT | `app/api/v1/endpoints/character_themes.py` |

### 实时语音通话 (Live Chat)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/live-chat/status` | GET | `app/api/v1/endpoints/live_chat.py` |
| `/api/v1/live-chat/{agent_id}` | WS | `app/api/v1/endpoints/live_chat.py` |

> **注意**：WebSocket 端点不会出现在 Swagger 文档中。关于消息协议和错误码的详细说明，请参考 [`docs/FR_LIVE_VOICE_CHAT.md`](/docs/FR_LIVE_VOICE_CHAT.md)。
> **Live Chat WS 可选 query**：`speech_language_code`（BCP-47）、`response_language_name`（英文可读语言名，用于 system instruction）。非法参数关闭码 `4000`。
> **Live Chat status**：响应 `data` 含 `default_speech_language_code`、`default_response_language_name`（服务端 `gemini_live` 默认，未传 query 时使用）。

### 电话通话 (Phone Calls)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/phone-calls/status` | GET | `app/api/v1/endpoints/phone_call.py` |
| `/api/v1/phone-calls/{agent_id}` | POST | `app/api/v1/endpoints/phone_call.py` |
| `/api/v1/phone-calls/twilio/inbound` | POST | `app/api/v1/endpoints/phone_call.py` |
| `/api/v1/phone-calls/twilio-media` | WS | `app/api/v1/endpoints/phone_call.py` |

> **Phone Calls**：`POST /api/v1/phone-calls/{agent_id}` 由已登录用户显式传入手机号触发 Twilio 外呼；`POST /api/v1/phone-calls/twilio/inbound` 是 Twilio Voice webhook，用来把已绑定来电号码接入指定 agent；`WS /api/v1/phone-calls/twilio-media` 是 Twilio Media Streams 桥，使用短期签名 token，不接受用户 JWT。功能开关默认开启，但 `GET /status` 的 `available` 只有在 Gemini Live、Twilio 凭据、Twilio from number 与公网 WSS bridge 都配置完成时才为 true。手机号不写入 `users.phone`；来电识别仅保存 HMAC 与脱敏展示。
> **Chat message trigger**：生产 companion WebSocket 聊天中，用户当前轮明确发送 `Call me at <number>` 会走确定性触发；工具路径也暴露 `phone_call_user`，但仅允许当前用户显式要求立刻拨打且当前消息含号码时使用，禁止 proactive/implicit greeting 自动打电话。
