# API 端点列表

本文档列出了 `app/` 目录下实现的所有 API 端点及其对应的实现文件。

## 双应用说明

- **backend/inty**（主后端）：面向 Android 的 `/api/v1`。
- **backend/ops**（运营平台）：提供 evaluation Web UI 与完整 `/api/v1`（含 evaluation、festival_memory 与所有 shared 端点）。部署后通过 ops.inty.cc / dev.ops.inty.cc 访问。

## 根路径端点

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/` | GET | `backend/inty/main.py` 或 `app/api/evaluation_web.py`（ops 评测页入口） |
| `/metrics` | GET | `backend/inty/main.py` |
| `/health` | GET | `backend/ops/main.py` |
| `/evaluation` | GET | `app/api/evaluation_web.py` |
| `/evaluation/{path:path}` | GET | `app/api/evaluation_web.py` |

## API v1 端点 (`/api/v1`)

### 认证 (Auth)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/auth/guest` | POST | `app/api/v1/endpoints/auth.py` |
| `/api/v1/auth/google/login` | POST | `app/api/v1/endpoints/auth.py` |

### 用户 (Users)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/users/profile` | GET | `app/api/v1/endpoints/users.py` |
| `/api/v1/users/me` | GET | `app/api/v1/endpoints/users.py` |
| `/api/v1/users/profile` | PUT | `app/api/v1/endpoints/users.py` |
| `/api/v1/users/device/register` | POST | `app/api/v1/endpoints/users.py` |
| `/api/v1/users/deletion/check` | GET | `app/api/v1/endpoints/users.py` |
| `/api/v1/users/delete-account` | POST | `app/api/v1/endpoints/users.py` |
| `/api/v1/users` | GET | `app/api/v1/endpoints/users.py` |

### AI 角色 (Agents)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/ai/agents/` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/me` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/search` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/recommend` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents` | POST | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/{agent_id}` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/{agent_id}` | PUT | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/{agent_id}` | DELETE | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/{agent_id}/generate-background-animated` | POST | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/text-to-image` | POST | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/creator/{creator_id}/stats` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/models/openrouter` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/image-generation/config` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/prompts/available` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/image-generation/config` | PUT | `app/api/v1/endpoints/agents.py` |

> **关于 `/recommend` 端点的行为说明**：
>
> - 该端点只返回**超级用户**（`is_superuser=True`）创建的**公开**（`visibility=PUBLIC`）角色
> - 不返回私有角色，也不返回普通用户创建的角色；调用者身份不影响结果
> - `sort=text_match_image_description`：按客户端文本与图片侧文案的模糊相似度对**图片**排序；必填 `match_description`（文本 D），`match_top_n`（N，默认 50，上限 500）表示参与排序的前 N 张图；分页在 N 条结果上切片；`data.matched_image_items` 为当前页的匹配条目（含 `similarity_score`、CDN `image_url`），`data.list` 为对应 agent（按首次出现顺序，去重；**前 N 张图请看 `matched_image_items` 而非 `list` 长度**）；同一 agent 下按规范化 URL 去重；`exclusive_photos` 无 caption 时回退 `resources` 的 `generation_prompt`；匹配 `resources` 时同时尝试 `url` 与 `resource_metadata.gcs_url`（应对 CDN/GCS 主键不一致）

### 聊天 (Chat)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/chat/completions/{agent_id}` | POST | `app/api/v1/endpoints/chat.py` |
| `/api/v1/chat/ws` | WebSocket | `app/api/v1/endpoints/chat.py` |
| `/api/v1/chat/ws/verify` | WebSocket | `app/api/v1/endpoints/chat.py` |
| `/api/v1/chat/images/{agent_id}` | POST | `app/api/v1/endpoints/chat.py` |
| `/api/v1/chat/music/{agent_id}` | POST | `app/api/v1/endpoints/chat.py` |

> **`/api/v1/chat/completions/{agent_id}` 多模态输入约定**：
>
> - `messages[].content` 兼容两种格式：
>   1. 纯文本字符串（向后兼容）
>   2. OpenAI-style content parts 数组（当前支持 `text` 与 `image_url`）
> - 示例：
>   - 文本：`{"role":"user","content":"hello"}`
>   - 图文：`{"role":"user","content":[{"type":"text","text":"describe this"},{"type":"image_url","image_url":{"url":"https://..."}}]}`
> - **客户端本地消息 ID（乐观 UI 对齐）**：请求体可选 `localId`（camelCase，与 Pydantic `local_id` 对应）；若未传则回退使用已有可选字段 `message_id`。服务端将值写入该条用户消息的 `chat_history.meta_data.localId`。**GET** `/api/v1/chats/agents/{agent_id}/messages` 返回的用户消息中，除 `meta_data.localId` 外，另提供顶层 `local_id`（snake_case）便于解析。**POST** `/api/v1/chat/completions/{agent_id}` 与 **WebSocket** `/api/v1/chat/ws` 成功时，`data` 内回显 `local_id`（与请求一致，便于客户端确认）；订阅/游客限额等业务错误时，`data` 内亦可含 `local_id`（与 `used_count` 等并列）。

> **`/api/v1/chat/ws/verify`**：仅用于验证 WebSocket 对话效果；协议与 `/api/v1/chat/ws` 一致，但**不写入 chat_history**（不落库）。实现上 verify 使用 `generate_message_without_user_save`，生产 `/ws` 使用 `agent_chat_completions`；接入 agentic v2 时需统一调度或显式记录差异（见 `docs/FR_INTY_V2_CHAT_WS_INTEGRATION_PLAN.md`）。
>
> **Evaluation assume user（与 live_chat WS 一致）**：`/api/v1/chat/ws` 与 `/api/v1/chat/ws/verify` 握手 URL 可带 `assume_user_id=<user id>`；仅当 token 对应用户为 **superuser** 时生效，否则忽略。对齐 HTTP `X-Assume-User-Id`（`get_effective_user_for_eval`）。
>
> **`/api/v1/chat/ws` 与 `/api/v1/chat/ws/verify` 上行扩展**：除 `{"type":"ping"}` 与既有 `ChatWebSocketRequest` JSON 外，可发送 `{"type":"client_context","time_context":{...}}`，字段与 HTTP `time_context`（`UserTimeContext`：`local_time`、`timezone`、`utc_offset_minutes`）一致。服务端回 `{"type":"client_context_ack","ok":true|false}`；该连接上若后续 chat 帧未带 `time_context`，则沿用最近一次成功写入的 `client_context`。
>
> **Chat WebSocket idle**：`app.features.chat_ws_idle_timeout_seconds`（默认 60）秒内无上行文本帧则关闭连接；`ping`/`pong` 计入上行。

### 聊天会话 (Chats)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/chats/` | GET | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/` | POST | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/modes` | GET | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/{chat_id}` | DELETE | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/status` | GET | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/initialize` | POST | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/cleanup` | DELETE | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/{chat_id}/detail` | GET | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/{agent_id}/detail` | GET | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/{agent_id}/messages` | GET | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/messages/vote` | POST | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/{agent_id}/chat/completions` | POST | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/{agent_id}/messages/{message_id}/voice` | POST | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/voices/{voice_id}` | GET | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/{agent_id}/settings` | PUT | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/{agent_id}/settings` | GET | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/{agent_id}/chats` | DELETE | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/{agent_id}/debug-messages` | GET | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/agents/{agent_id}/clear-messages` | POST | `app/api/v1/endpoints/chats.py` |

> **节日记忆提示消息（与 Android App 的接口约定）**：
>
> 类型为 `festival_memory_prompt` 的消息在以下响应中返回：
> - **POST** `/api/v1/chat/completions/{agent_id}` 的 `data.choices[].message`
> - **GET** `/api/v1/chats/agents/{agent_id}/messages` 的 `messages[]`
>
> 同一条消息可能同时包含：
> - **顶层** `festival_memory_id`（snake_case，整型）：对应 memory 表主键，**客户端应以该字段为准**，与普通 AI 消息的 `id` 用法一致。
> - **meta_data 内** `festivalMemoryId`（camelCase）：来自写入 chat_history 时存储的 meta_data，透传未改，仅作兼容。
>
> Android App 解析时请优先使用顶层 `festival_memory_id`。

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
| `/api/v1/report/upload-image` | POST | `app/api/v1/endpoints/report.py` |
| `/api/v1/report/` | POST | `app/api/v1/endpoints/report.py` |
| `/api/v1/report/` | GET | `app/api/v1/endpoints/report.py` |
| `/api/v1/report/{report_id}` | GET | `app/api/v1/endpoints/report.py` |
| `/api/v1/report/{report_id}/conversation-groups` | GET | `app/api/v1/endpoints/report.py` |
| `/api/v1/report/{report_id}/conversation-messages` | GET | `app/api/v1/endpoints/report.py` |
| `/api/v1/report/{report_id}` | DELETE | `app/api/v1/endpoints/report.py` |
| `/api/v1/report/{report_id}/github-issue` | PUT | `app/api/v1/endpoints/report.py` |

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
| `/api/v1/live-chat/{agent_id}` | WebSocket | `app/api/v1/endpoints/live_chat.py` |

> **注意**：WebSocket 端点不会出现在 Swagger 文档中。关于消息协议和错误码的详细说明，请参考 [`docs/FR_LIVE_VOICE_CHAT.md`](../../docs/FR_LIVE_VOICE_CHAT.md)。
> **Live Chat WS 可选 query**：`speech_language_code`（BCP-47）、`response_language_name`（英文可读语言名，用于 system instruction）。非法参数关闭码 `4000`。
> **Live Chat status**：响应 `data` 含 `default_speech_language_code`、`default_response_language_name`（服务端 `gemini_live` 默认，未传 query 时使用）。

### 评测 (Evaluation)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/evaluation/sessions` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/start` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/results` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/cancel` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/questions/parse` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/models` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/scoring-criteria/validate` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/stats` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/monitor` | WebSocket | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}` | PUT | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}` | DELETE | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/check-background-aspect-ratio` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/upload-cropped-background` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/deploy` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/templates` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/templates` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/batch` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/results/export` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/compare` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/new-users` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-activity` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/conversation-rounds` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-rounds-distribution` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/popular-agents` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/users-hitting-limit` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/agent-analytics` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-sessions-detail` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/conversations-detail` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/stats` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/reports` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/image-generation-failures` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-daily-messages` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-today-stats` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-sessions` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/session-messages` | GET | `backend/ops/api/v1/evaluation.py` |

