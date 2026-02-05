# API 端点列表

本文档列出了 `app/` 目录下实现的所有 API 端点及其对应的实现文件。

## 根路径端点

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/` | GET | `app/main.py` |
| `/evaluation` | GET | `app/main.py` |
| `/evaluation/{path:path}` | GET | `app/main.py` |

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
| `/api/v1/ai/agents/generate_background` | POST | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/text-to-image` | POST | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/creator/{creator_id}/stats` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/import-character-card` | POST | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/import-character-card-file` | POST | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/export-character-card` | POST | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/{agent_id}/character-card` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/validate-character-card` | POST | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/character-card/features` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/models/openrouter` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/image-generation/config` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/prompts/available` | GET | `app/api/v1/endpoints/agents.py` |
| `/api/v1/ai/agents/image-generation/config` | PUT | `app/api/v1/endpoints/agents.py` |

> **关于 `/recommend` 端点的行为说明**：
>
> - 该端点只返回**超级用户**（`is_superuser=True`）创建的角色，不会返回普通用户创建的角色
> - **普通用户**调用时：只返回超级用户创建的**公开**（`visibility=PUBLIC`）角色
> - **超级用户**调用时：返回所有超级用户创建的**公开和私有**角色，包括其他超级用户创建的私有角色
> - 无论调用者身份如何，都不会返回普通用户创建的私有角色

### 聊天 (Chat)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/chat/completions/{agent_id}` | POST | `app/api/v1/endpoints/chat.py` |
| `/api/v1/chat/images/{agent_id}` | POST | `app/api/v1/endpoints/chat.py` |

### 聊天会话 (Chats)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/chats/` | GET | `app/api/v1/endpoints/chats.py` |
| `/api/v1/chats/` | POST | `app/api/v1/endpoints/chats.py` |
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
| `/api/v1/chats/agents/{agent_id}/generate-image` | POST | `app/api/v1/endpoints/chats.py` |

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

### 评测 (Evaluation)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/evaluation/sessions` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/sessions` | POST | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/start` | POST | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/results` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/cancel` | POST | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/questions/parse` | POST | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/models` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/scoring-criteria/validate` | POST | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/stats` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/monitor` | WebSocket | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/agents` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/agents` | POST | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}` | PUT | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}` | DELETE | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/check-background-aspect-ratio` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/upload-cropped-background` | POST | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/deploy` | POST | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/templates` | POST | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/templates` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/sessions/batch` | POST | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/results/export` | POST | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/sessions/compare` | POST | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/new-users` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-activity` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/conversation-rounds` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-rounds-distribution` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/popular-agents` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/users-hitting-limit` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/agent-analytics` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-sessions-detail` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/conversations-detail` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/stats` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/reports` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-daily-messages` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-today-stats` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-sessions` | GET | `app/api/v1/endpoints/evaluation.py` |
| `/api/v1/evaluation/user-analytics/session-messages` | GET | `app/api/v1/endpoints/evaluation.py` |

### 节日记忆（管理员，Evaluation Admin）

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/evaluation/admin/festival-memory-configs` | GET | `app/api/v1/endpoints/festival_memory.py` |
| `/api/v1/evaluation/admin/festival-memory-configs` | POST | `app/api/v1/endpoints/festival_memory.py` |
| `/api/v1/evaluation/admin/festival-memory-configs/{config_id}` | PUT | `app/api/v1/endpoints/festival_memory.py` |
| `/api/v1/evaluation/admin/festival-memory-configs/{config_id}` | DELETE | `app/api/v1/endpoints/festival_memory.py` |
| `/api/v1/evaluation/admin/festival-memory-extraction/run` | POST | `app/api/v1/endpoints/festival_memory.py` |

> 以上端点仅超级用户可访问。节日记忆通过角色详情 `GET /api/v1/ai/agents/{agent_id}` 的响应字段 `features.festival_memories` 返回。

## API v2 端点 (`/api/v2`)

### 聊天 (Chat)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v2/chat/completions/{agent_id}` | POST | `app/api/v2/endpoints/chat.py` |

### AI 角色 (Agents)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v2/ai/agents/recommend` | GET | `app/api/v2/endpoints/agents.py` |

> **关于 `/recommend` 端点的行为说明**：
>
> - 该端点只返回**超级用户**（`is_superuser=True`）创建的角色，不会返回普通用户创建的角色
> - **普通用户**调用时：只返回超级用户创建的**公开**（`visibility=PUBLIC`）角色
> - **超级用户**调用时：返回所有超级用户创建的**公开和私有**角色，包括其他超级用户创建的私有角色
> - 无论调用者身份如何，都不会返回普通用户创建的私有角色
