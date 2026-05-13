# Inty 后端 API 服务端点

- 后台管理用的 API 只能开放给超级用户（superuser）
- 增加新的 API endpoint(s)、迁移实现文件、或改动已登记路径的行为时，须同步更新下文「API 端点列表」章节（表格与块引用注记）

## API 端点列表

下列内容列出当前代码中注册的 HTTP 与 WebSocket 路径及实现文件。表格中的路径除 `{...}` 占位段外为字面量。

WebSocket 在 OpenAPI 中不可见；下表方法列写 `WS`。

Inty 不提供 `/health`；Ops 根路径 `/` 在关闭 API-only 时为评测页，与 Inty 的 JSON 健康根路径不同。

## API v1 共有端点（Inty 与 Ops）

下列路由由 `app/api/v1/router.py` 注册；Ops 通过 `backend/ops/api/v1/shared.py` 中的 `shared_router` 再导出同一套处理器。

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

> **关于 `/recommend` 端点的行为说明**：
>
> - 该端点只返回**超级用户**（`is_superuser=True`）创建的**公开**（`visibility=PUBLIC`）角色
> - 不返回私有角色，也不返回普通用户创建的角色；调用者身份不影响结果
> - `sort=text_match_image_description`：按客户端文本与图片侧文案的模糊相似度对**图片**排序；必填 `match_description`（文本 D），`match_top_n`（N，默认 50，上限 500）表示参与排序的前 N 张图；分页在 N 条结果上切片；`data.matched_image_items` 为当前页的匹配条目（含 `similarity_score`、CDN `image_url`），`data.list` 为对应 agent（按首次出现顺序，去重；**前 N 张图请看 `matched_image_items` 而非 `list` 长度**）；同一 agent 下按规范化 URL 去重；`exclusive_photos` 无 caption 时回退 `resources` 的 `generation_prompt`；匹配 `resources` 时同时尝试 `url` 与 `resource_metadata.gcs_url`（应对 CDN/GCS 主键不一致）

### 聊天 (Chat)

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/chat/completions/{agent_id}` | POST | `app/api/v1/endpoints/chat.py` |
| `/api/v1/chat/ws` | WS | `app/api/v1/endpoints/chat.py` |
| `/api/v1/chat/ws/verify` | WS | `app/api/v1/endpoints/chat.py` |
| `/api/v1/chat/images/{agent_id}` | POST | `app/api/v1/endpoints/chat.py` |
| `/api/v1/chat/music/{agent_id}` | POST | `app/api/v1/endpoints/chat.py` |

> **Companion Harness (inty v2 REPL same stack)**：**`WS /api/v1/chat/ws`** 通过 `_agent_chat_completions_impl(..., chat_route="websocket")` 始终使用 `CompanionManager` + `app/core/companion_harness/turn.run_turn` 生成回复，并写入 `chat_history`。**`POST /api/v1/chat/completions/{agent_id}`** 始终走既有 legacy `Agent` 栈（同一请求/响应契约，不切换 companion）。LLM 网关与 companion 使用与主聊天一致的 `select_chat_model` 结果（`model_override`）以及 `agent.chat_llm_api_key`（若配置）否则 `agent.api_key`，`agent.chat_llm_base_url` 否则 `agent.base_url`。可选：`app.features.companion_default_context_mode`、`app.features.companion_memory_bootstrap_type`（字符串枚举，默认 `USER_INTERACTIVE`：session 创建写入五件套种子，始终在 `run_turn` 中对话，由模型调用 `companion_update_prompt_slice` 与 `companion_bootstrap_user_interactive_complete`（见 `app/core/companion_harness/experience/bootstrap_user_interactive.py`）；交互式 bootstrap 以初始化 **SOUL** 为主，调用 `companion_bootstrap_user_interactive_complete` 且 `context.json` 显式记录完成后 **SOUL.md 不可再改**（含 `memory_store_write_document` 与记忆管线 SOUL 策展），IDENTITY / USER / MEMORY 等切片仍可更新；在交互式 bootstrap 尚未结束且 `context.json` 中 `companion_ws_session_system_written` 仍为 `false` 时，首轮成功 companion 轮会先向 `chat_history` 与 companion `transcript.jsonl` 各写入一条持久化 `system`（文案可选 `app.features.companion_ws_session_system_text`），再进入 `run_turn`；**WebSocket URL 可带 query `agent_id`**（如 REPL）：服务端不在 `accept` 后推送 connect-time 开场；由客户端发 **user_signed_on** 控制帧并设 **implicit_greeting: true** 与 RFC4122 **message_id** 触发问候为 **产品约定**（合法的 **`messageType: IMPLICIT_USER_SIGNED_ON`** 聊天帧与内部 synthetic 等价，服务端不做 wire 层额外拒绝）；文案见 [`/app/core/companion_harness/environment/implicit_signal_messages.py`](/app/core/companion_harness/environment/implicit_signal_messages.py)。`context.json` 或含 legacy 键 `companion_ws_interactive_kickoff_sent`（旧版；新 `USER_INTERACTIVE` 种子不再写 `false`）。`NONE`：仅最小文档种子，每轮 `run_turn`，无交互式 bootstrap。默认启用：`app.features.companion_transcript_compaction` 缺省时使用与 `app.utils.companion_feature_defaults.DEFAULT_COMPANION_FEATURE_COMPACTION` 相同的 dict，在单轮 LLM 请求前对 transcript 窗口做确定性压缩；在 YAML 中设为 `null` 可关闭。可覆盖各字段（同 `CompactionConfig`）。`app.features.companion_transcript_llm_window_max_messages` 可放大载入 transcript 行数再压缩。状态持久化在 workspace 的 `{state_file_prefix}_context_compaction_state.json`（默认 `.companion_context_compaction_state.json`）。实现见 `app/services/companion_chat_service.py`。
>
> **Dual-LLM async（`/api/v1/chat/ws` production）**（不含维护 inner tick 带工具；该路径无前台 chat）：每轮先 **await** 前台 chat（`response_format` JSON envelope：`user_facing_reply` + 三条 `importance_*` + `output_to_user`，前台须 `output_to_user=true`）；若 `user_facing_reply` **非空**，将其作为 **`assistant`** 消息追加进后台 tool 路径的 `messages` 后再 **dispatch** 后台线程跑完整 tool loop（无同步 tool loop），且后台首轮为 **自动** `tool_choice`（不先发 `required`），模型据前台口径自决是否出工具。若 `user_facing_reply` **为空**（envelope 显式让位给工具路），则不注入该 assistant 行，后台首轮仍可对非空 tools 尝试 **`tool_choice=required`**（上游拒绝时回退自动）。工具环 **收尾** 使用 **同一** envelope（`user_facing_reply` + significance + `output_to_user`；静默收尾可 `output_to_user=false`）。后台 LLM 模型 id 由 **`app.agent.companion_tool_call_model`**（默认 `google/gemini-3-flash-preview`，空字符串则与前台 chat 模型相同）经 `app/services/companion_chat_service.py` 写入 `CompanionLLMConfig.tool_model`。适用时前台助手 `choices[].message.meta_data` 含 **`tool_background_started`: true**（与 `CompanionTurnResult.tool_background_started` 同名），表示后台 tool loop 已启动，客户端可据此展示进行中状态直至可能的 `tool_bg` 帧。工具侧产出可见文本或生图时，服务端可能在同一 WebSocket 连接上再 `send_json` 一条与正常轮次同形的 assistant 回复，并写入 `chat_history`（`meta_data.source`=`tool_bg`，含 `trace_id`、`reply_to_user_msg_uuid`；解析成功时可选 `meta_data.significance_perception` 与前台同形；生图成功时另含 `meta_data.generated_image`，其中 `image_url` 优先 `gs://...`，否则可为供应商 **`https://`**（如无稳定 gs）；开发期 REPL 另打印 `image-url:` 行并可用 `meta_data.tool_bg_local_image_paths`（`list[str]`，服务端绝对路径）展示便于复制，生产 Android 客户端忽略未知字段）。前台 chat 失败时本轮不启动后台 tool loop（无 `tool_bg` 投递）。前台 HTTP 超时：`INTY_V2_PROTO_ASYNC_CHAT_FRONT_TIMEOUT_SEC`（默认 600 秒）。
>
> **Companion inner-tick（`/api/v1/chat/ws`）**：`user_signed_on` 控制帧用于登记 inner-tick 坐标（原 proactive heartbeat 坐标）；同一帧若带 **`implicit_greeting: true`** 与合法 **`message_id`**（RFC4122 UUID），在 ``user_signed_on_ack`` **成功** 后服务端排队一轮隐式上线 companion 问候（内核与会话记录仍沿用 implicit-sign-on 语义）。动机与触发文案见 [`/app/core/companion_harness/environment/implicit_signal_messages.py`](/app/core/companion_harness/environment/implicit_signal_messages.py)。当 proactive/maintenance inner-tick 功能双关时 ``user_signed_on`` 仍回 ``ok:false``（``proactive_heartbeat_disabled``），此时 **不会** 执行 ``implicit_greeting`` 问候。后台 **`asyncio` task 名 `companion_ws_inner_tick`**（实现入口 `companion_ws_inner_tick_worker`）按 `app.features.companion_ws_proactive_heartbeat_poll_seconds`（默认 **60**，统一轮询间隔，可在 YAML 调大）周期性唤醒；**仅当** `companion_ws_proactive_heartbeat_enabled` 与 `companion_ws_maintenance_inner_tick_enabled` **均为 false** 时整段跳过。**overlap guard 按类型**：上一轮 proactive 若仍有该会话 `tool_background` 未完成则只跳过本轮 proactive，不阻塞 maintenance；上一轮 maintenance 若仍在 `foreground_pending` 则只跳过本轮 maintenance。每周期在坐标齐全时 **先** 尝试 proactive（`companion_ws_proactive_heartbeat_enabled`）：`next_heartbeat_wait_seconds`（`HeartbeatConfig(enabled=True)`）`<= 0` 且订阅允许则跑 `InnerTickMode.PROACTIVE_CHAT`，下行与落库同既有语义（`meta_data` 含 `companion_proactive_heartbeat`、`heartbeat`）。**再** 尝试 maintenance（`companion_ws_maintenance_inner_tick_enabled`）：[`next_inner_tick_wait_seconds`](/app/core/companion_harness/environment/inner_tick_schedule.py) 使用 YAML 的 `companion_ws_maintenance_inner_tick_min_gap_seconds`（默认 120）等覆盖、`InnerTickMode.MAINTENANCE`，用户侧 `chat_history` 短占位见内核 `MAINTENANCE_INNER_TICK_CHAT_HISTORY_USER_MARKER`，`meta_data` 含 `companion_maintenance_inner_tick`；该路径可走工具环：**启用工具时内核不跑前台 dual-LLM envelope**（仅启动 `tool_background`），故可能不发与前台同形的首条 assistant 业务帧，客户端可能仅收到 `tool_bg` 补帧。切换当前会话 agent 时客户端应重发 `user_signed_on`。**对称地**，生产 `/ws` 上 `user_signed_out`（`app.schemas.chat_websocket.ChatWsUserSignedOutFrame`）将英文 Markdown 一行追加到 companion `CHAT_LOGS.md`（`document_kind=chat_logs_md`，运维流水，默认不注入 prompt），不经 outbound queue、不改 inner-tick。`/api/v1/chat/ws/verify` 对 `user_signed_on` 与 `user_signed_out` 均回 `ok:false, reason:not_supported`。
>
> **`/api/v1/chat/ws` `message_id`（production companion）**：每条用户聊天帧的 `request.message_id` **必填**，且须为 RFC4122 UUID（用作 companion transcript `user_msg_uuid`）；缺失或非法时下行 `code=400`（英文 `message`，不经 companion）。`POST /api/v1/chat/completions/{agent_id}` 不要求该字段。
>
> **`request.messageType`（companion WebSocket 聊天帧）**：默认 **`USER_MESSAGE`**；可选 **`IMPLICIT_USER_SIGNED_ON`**（须空用户正文、无多模态图等，见 schema，否则 **422**）。**产品约定**隐式问候用 **`user_signed_on`** + **`implicit_greeting`**；`IMPLICIT` 路径不写 PostgreSQL 用户行，companion transcript 等见 [`implicit_signal_messages.py`](/app/core/companion_harness/environment/implicit_signal_messages.py)。HTTP completions 上传 **`IMPLICIT_USER_SIGNED_ON`** **400**。其它校验失败下行 **`code` 422**。由隐式问候完成的回合 `record_usage` 的 `extra_data` 仍可含 **`implicit_user_signed_on: true`**。**控制帧**校验失败只下行 **`user_signed_on_ack`**（``ok:false``，`reason`）。

> **API companion 无 workspace 磁盘权威**：经 `companion_chat_service` 的 WebSocket companion 路径在配置好数据库 DSN 时，不在磁盘上 `mkdir` 或写入权威状态文件；约定文档、按日 `memory/daily/{date}.md` 与 `memory/{date}.md`、transcript、context、定时队列、image gate、chat settings、生图索引元数据等经 `MemoryStore` 写入 Postgres 表 **`companion_memory_document_versions`**（SQLAlchemy 模型 `CompanionMemoryDocumentVersion`：键为 `user_id` + `companion_id` + `chat_id` + `document_kind` + 可选 `calendar_date`，append-only 版本链），进程内按 **`CompanionScope`**（同一三元组）在 [`memory_registry.get_memory_store`](/app/core/companion_harness/memory/memory_registry.py) 中缓存读取；**不再**使用合成磁盘 `Path` 前缀或 `get_memory_store(Path)`。表结构由 Alembic 管理，运行时不再 `CREATE TABLE`。生图二进制可走 GCS；无本地 generated 文件时 `modify_image` 默认源依赖索引中的 `gcs_http_url`。

> **`/api/v1/chat/completions/{agent_id}` 多模态输入约定**：
>
> - `messages[].content` 兼容两种格式：
>   1. 纯文本字符串（向后兼容）
>   2. OpenAI-style content parts 数组（当前支持 `text` 与 `image_url`）
> - 示例：
>   - 文本：`{"role":"user","content":"hello"}`
>   - 图文：`{"role":"user","content":[{"type":"text","text":"describe this"},{"type":"image_url","image_url":{"url":"https://..."}}]}`
> - **客户端本地消息 ID（乐观 UI 对齐）**：请求体可选 `localId`（camelCase，与 Pydantic `local_id` 对应）；若未传则回退使用已有可选字段 `message_id`。服务端将值写入该条用户消息的 `chat_history.meta_data.localId`。**GET** `/api/v1/chats/agents/{agent_id}/messages` 返回的用户消息中，除 `meta_data.localId` 外，另提供顶层 `local_id`（snake_case）便于解析。**POST** `/api/v1/chat/completions/{agent_id}` 与 **WebSocket** `/api/v1/chat/ws` 成功时，`data` 内回显 `local_id`（与请求一致，便于客户端确认）；订阅/游客限额等业务错误时，`data` 内亦可含 `local_id`（与 `used_count` 等并列）。

> **`/api/v1/chat/ws/verify`**：仅用于验证 WebSocket、业务下行 queue + pump 与最简 LLM；协议与 `/api/v1/chat/ws` 一致，**不写入 chat_history**（不落库）。verify 每帧为单次 `chat.completions`（不经 `_agent_chat_completions_impl` / Agent runtime）；生产 `/ws` 走完整对话编排。
>
> **Evaluation assume user（与 live_chat WS 一致）**：`/api/v1/chat/ws` 与 `/api/v1/chat/ws/verify` 握手 URL 可带 `assume_user_id=<user id>`；仅当 token 对应用户为 **superuser** 时生效，否则忽略。对齐 HTTP `X-Assume-User-Id`（`get_effective_user_for_eval`）。
>
> **`/api/v1/chat/ws` 与 `/api/v1/chat/ws/verify` 上行扩展**：除 `{"type":"ping"}` 与既有 `ChatWebSocketRequest` JSON 外，可发送 `{"type":"client_context","time_context":{...}}`，字段与 HTTP `time_context`（`UserTimeContext`：`local_time`、`timezone`、`utc_offset_minutes`）一致。服务端回 `{"type":"client_context_ack","ok":true|false}`；该连接上若后续 chat 帧未带 `time_context`，则沿用最近一次成功写入的 `client_context`。
>
> **Chat WebSocket idle**：`app.features.chat_ws_idle_timeout_seconds`（默认 60）秒内无上行文本帧则关闭连接；`ping`/`pong` 计入上行。
>
> **Chat header status line**：成功完成一轮 **WS** `/api/v1/chat/ws` 或 `/api/v1/chat/ws/verify` 聊天后，顶层 JSON 含可选 `status_line`（来自 `agents.status_line`，空则省略或 `null`），供客户端聊天顶栏副标题刷新；与 `code`/`data`/`agent_id` 并列。

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

## 仅 Ops：`/api/v1/evaluation` 与节日记忆管理

以下路由由 `backend/ops/api/v1/router.py` 额外挂载，**不在** `backend/inty/main.py` 中。

### 节日记忆（超级用户，`backend/ops/api/v1/festival_memory.py`）

Router 前缀：`/evaluation/admin`（完整路径以 `/api/v1` 开头）。

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/evaluation/admin/festival-memory-configs` | GET | `backend/ops/api/v1/festival_memory.py` |
| `/api/v1/evaluation/admin/festival-memory-configs` | POST | `backend/ops/api/v1/festival_memory.py` |
| `/api/v1/evaluation/admin/festival-memory-configs/{config_id}` | DELETE | `backend/ops/api/v1/festival_memory.py` |
| `/api/v1/evaluation/admin/festival-memory-configs/{config_id}` | PUT | `backend/ops/api/v1/festival_memory.py` |
| `/api/v1/evaluation/admin/festival-memory-extraction/run` | POST | `backend/ops/api/v1/festival_memory.py` |

### 评测（`backend/ops/api/v1/evaluation.py`）

| 路径 | 方法 | 实现文件 |
|------|------|----------|
| `/api/v1/evaluation/sessions` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/start` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/results` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/cancel` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/sessions/{session_id}/monitor` | WS | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/questions/parse` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/models` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/scoring-criteria/validate` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/stats` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}` | PUT | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}` | DELETE | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/check-background-aspect-ratio` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/upload-cropped-background` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/deploy` | POST | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/{agent_id}/generated-images` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/agents/generated-images/counts` | GET | `backend/ops/api/v1/evaluation.py` |
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
| `/api/v1/evaluation/user-analytics/conversations-detail/user-agent-paginated` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/stats` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/reports` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/image-generation-failures` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/image-generation-latency` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-daily-messages` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-today-stats` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-sessions` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/session-messages` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/daily-voice-audios` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/live-chat-stats` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/live-chat-latency` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/llm-latency` | GET | `backend/ops/api/v1/evaluation.py` |
| `/api/v1/evaluation/user-analytics/user-generated-images` | GET | `backend/ops/api/v1/evaluation.py` |

## Chat WebSocket

- **Companion `user_signed_on` control**（`app.schemas.chat_websocket.ChatWsUserSignedOnFrame`）：除登记 inner-tick 坐标外，可选 **`implicit_greeting`**（默认 false）；为 true 时须提供合法 **`message_id`**（RFC4122 UUID）。服务端在 **`user_signed_on_ack` `ok:true`** 之后排队一轮隐式问候。校验失败仅下行 **`user_signed_on_ack`**（`ok:false`, `reason`）。
- **Companion chat frame**（`ChatWebSocketRequest.request` / `ChatCompletionRequest`）：**`messageType`** 为 **`USER_MESSAGE`**（默认）或 **`IMPLICIT_USER_SIGNED_ON`**（须满足 schema）。**产品约定**隐式问候用 **`user_signed_on`** + **`implicit_greeting`**；`IMPLICIT` 聊天帧与内部 synthetic 等价，不落 PostgreSQL 用户行，companion transcript 追加 synthetic **`user`**（[`USER_SIGNED_ON_TRIGGER_USER_TEXT`](/app/core/companion_harness/environment/implicit_signal_messages.py)）。助手落库 `meta_data.messageType` 对该类回合仍可标 **`IMPLICIT_USER_SIGNED_ON`**。HTTP completions 传入 **`IMPLICIT_USER_SIGNED_ON`** **400**。
- **Companion assistant ``meta_data.significance_perception``**（可选）：当内核前台 JSON envelope 解析出重要性三元组时，由 ``chat._companion_ai_meta_from_turn_result`` 写入 PostgreSQL AI 消息 ``meta_data``；异步 tool 收尾推送的 ``meta_data.source``=`tool_bg` 帧在解析成功时亦可含同一键（与前台形状一致：三条 ``importance_*``），供离线任务（如开启 ``memory_extraction.use_significance_perception_in_extraction`` 时的用户画像抽取）按回合重要性排序或加权；契约与数据流见 [`significance_perception.py`](/app/core/companion_harness/system_hierarchy/significance_perception.py) 模块 docstring。
- `/api/v1/chat/ws`：正式对话 WebSocket，走持久化对话流程（写入 chat 历史）。Companion 在模型触发工具时：**维护 inner tick（`InnerTickMode.MAINTENANCE`）且本轮启用工具**走仅 `tool_background`、无前台 dual-LLM envelope，首条 assistant 业务帧可能仅由 `tool_bg` 投递；**其它**回合内核先 **await** 前台 chat（JSON envelope），再将非空的 `user_facing_reply` 作为 **`assistant`** 注入后台 tool 路径的上下文后 **dispatch** 后台线程跑完整 tool loop；下行仍先发 **前台** assistant 业务帧，若工具侧有需要落库展示给用户的内容（含生图），服务端可能在 **同一连接** 再推送一条与正常轮次同形的 assistant 业务帧，且 `meta_data.source`=`tool_bg`。生图成功时该帧可含 **`meta_data.generated_image`**：其中 **`image_url` 优先为 `gs://...`**；若无稳定 `gs://` 而仅有供应商可访问的绝对 **`https://`（如 Fal CDN）**，则可为该 URL；本地 **`use_fake_gcs`** 时可为 **`file://...`**（`gcs_http_url` / `Blob.public_url`，见 `app/core/companion_harness/tools/image_gate.py`）；二者皆无时则不写 `generated_image`。前台助手帧在适用时含 **`meta_data.tool_background_started`: true**（与内核 `CompanionTurnResult` 字段同名），表示本回合已启动仅运行于后台的 tool loop，客户端可等待可能的 `tool_bg` 帧。后台 tool loop 的 OpenRouter（兼容）模型 id 由 **`app.agent.companion_tool_call_model`** 配置（见 `/app/core/AGENTS.md`「Companion tool-call model」）。**产品意图：** `user_signed_on` 控制帧登记 **统一 inner-tick** 坐标（proactive 与 maintenance 共用）；问候优先由 **`implicit_greeting: true`**（同上帧 **UUID `message_id`**）触发，亦可用合法的 **`IMPLICIT_USER_SIGNED_ON`** 聊天帧（文案见 [`/app/core/companion_harness/environment/implicit_signal_messages.py`](/app/core/companion_harness/environment/implicit_signal_messages.py)）。当 **`companion_ws_proactive_heartbeat_enabled` 与 `companion_ws_maintenance_inner_tick_enabled` 均为 false** 时，`user_signed_on` 回 `ok:false`（`proactive_heartbeat_disabled`）；否则 `ok:true`。客户端可先发控制帧 `{"type":"user_signed_on","agent_id":...}`；未发送的旧客户端在任意一轮 **成功** WebSocket companion 聊天后也会写入同等坐标。`Pydantic` 模型见 `app.schemas.chat_websocket.ChatWsUserSignedOnFrame` / `app.schemas.chat_websocket.ChatWsUserSignedOutFrame`。
- **Companion upstream LLM failures**：当 Companion Harness 在框架中调用 OpenRouter/OpenAI 兼容 `chat.completions` 失败（HTTP 4xx/5xx、连接、超时、或上游回 200 但 body `choices: null` + `error.code=...` 的伪成功）时，HTTP 返回 **502**，WebSocket 业务帧为 **`code` 502**、`message` 英文说明，并附带 **`error_kind`: `llm_inference_backend`** 与可选 **`llm_provider_http_status`**（上游状态码，无响应体时可为 `null`）。客户端可据此区分「推理供应商/服务端密钥配额」类错误与普通业务错误。Dual-LLM 路径下前台 chat 失败时本轮不启动后台 tool loop，故无「前台 502 后仍投递 `tool_bg`」语义；`chat.py` 中 `bg_started_on_exc` / `_persist_companion_user_message_for_bg` 异常分支保留为防御代码。
- `/api/v1/chat/ws/verify`：协议与 `/ws` 一致，业务下行同样经 **outbound queue + pump**；回复由 **单次** `chat.completions`（system + user，不经 Agent / companion 主编排）生成，**不写入 chat_history**。用于校验连接、队列与最简 LLM 连通性。见 `app/api/v1/endpoints/chat.py` 与上文「聊天 (Chat)」小节中关于 `/api/v1/chat/ws/verify` 的注记。

### IntelliMate（[`android_app`](../../android_app/)）

- **连接**：用户登录后会维持主 WebSocket，路径即 **`/api/v1/chat/ws`**（[`MainRemoteDataSource.kt`](../../android_app/app/src/main/kotlin/com/ai/intellimate/main/data/MainRemoteDataSource.kt)）；另有 [`ChatWebSocketSessionManager.kt`](../../android_app/core/data/src/main/kotlin/ai/sxwl/android/data/chat/data/ChatWebSocketSessionManager.kt) 使用同路径。Debug 下可选用 **`/api/v1/chat/ws/verify`**（[`DebugBackendEndpointStore.kt`](../../android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/config/DebugBackendEndpointStore.kt)）。
- **发送**：**Release** 默认聊天上行仍走 **HTTP** completions；仅 **Debug** 且在调试设置里打开 chat WebSocket 时，发送才走主 WebSocket（[`ChatViewModel.kt`](../../android_app/app/src/main/kotlin/com/ai/intellimate/chat/viewmodel/ChatViewModel.kt) 与 `DebugBackendEndpointStore.getChatWebSocketEnabled()`）。无论发送走哪条路径，已登录客户端仍会与 `/api/v1/chat/ws` 保持连接（[`MainRepository.kt`](../../android_app/app/src/main/kotlin/com/ai/intellimate/main/data/MainRepository.kt) `connectWebSocket`）。

### 变更联动（客户端）

修改 `/api/v1/chat/ws` 的协议、鉴权、帧形状或 `ChatWebSocketRequest` / `ChatCompletionRequest` 等相关 schema 时，须同步更新已接入的客户端，例如：

- [`imate_android_app`](../../imate_android_app/)（如 [`ChatWebSocketRemoteDataSource.kt`](../../imate_android_app/app/src/main/java/com/inty/imate/chat/data/datasource/ChatWebSocketRemoteDataSource.kt)）
- [`tools/inty_v2_repl/backend_chat_ws.py`](../../tools/inty_v2_repl/backend_chat_ws.py)
- IntelliMate：[`android_app`](../../android_app/)（行为见上「IntelliMate」小节）

[`imate_ios_app`](../../imate_ios_app/) **尚未接入**该 WebSocket；待接入或后端 breaking 变更时，由 **iMate iOS 负责人** 与上述客户端一并核对协议。
