# Inty 后端 API 服务端点

- 后台管理用的 API 只能开放给超级用户（superuser）
- 增加新的 API endpoint(s) 需要更新 ENDPOINTS.md
- API endpoint(s) 从一个 py 文件迁移到另一个需要更新 ENDPOINTS.md

## Chat WebSocket

- **Companion chat frame**（`ChatWebSocketRequest.request` / `ChatCompletionRequest`）：可选 **`messageType`**（camelCase JSON），取值 **`USER_MESSAGE`**（默认）或 **`IMPLICIT_USER_SIGNED_ON`**。后者仅 **WebSocket companion** 支持：用户消息正文须为空且不得含图片等多模态 content（否则 **400**）；PostgreSQL `chat_history` **不写**该回合的用户行，但 companion 工作区 transcript JSONL 会落一条 synthetic **`user`**（带 `implicit_user_signed_on: true`）。内核在已加载 transcript 之后 **追加** 这条 tail **`user`**，内容为隐式上线触发文案 [`USER_SIGNED_ON_TRIGGER_USER_TEXT`](/app/core/agentic_kernel/companion/implicit_signal_messages.py)，**不**并入靠前 system 前缀；曾用 tail **`system`** 承载同文案时易出现问候重复，故改为 **`user`**。助手落库 `meta_data.messageType` 可为 `IMPLICIT_USER_SIGNED_ON`。HTTP completions 传入该类型返回 **400**。非法请求体现在上行 JSON 时下行 **`code` 422**，`message` 为 `Invalid chat WebSocket request`。`record_usage` 对该类成功回合附带 **`implicit_user_signed_on: true`**。
- `/api/v1/chat/ws`：正式对话 WebSocket，走持久化对话流程（写入 chat 历史）。Companion 在模型触发工具时：内核先 **await** 前台 chat（JSON envelope），再将非空的 `user_facing_reply` 作为 **`assistant`** 注入后台 tool 路径的上下文后 **dispatch** 后台线程跑完整 tool loop；下行仍先发 **前台** assistant 业务帧，若工具侧有需要落库展示给用户的内容（含生图），服务端可能在 **同一连接** 再推送一条与正常轮次同形的 assistant 业务帧，且 `meta_data.source`=`tool_bg`。生图成功时该帧可含 **`meta_data.generated_image`**：其中 **`image_url` 优先为 `gs://...`**；若无稳定 `gs://` 而仅有供应商可访问的绝对 **`https://`（如 Fal CDN）**，则可为该 URL；本地 **`use_fake_gcs`** 时可为 **`file://...`**（`gcs_http_url` / `Blob.public_url`，见 `app/core/agentic_kernel/companion/image_gate.py`）；二者皆无时则不写 `generated_image`。前台助手帧在适用时含 **`meta_data.tool_background_started`: true**（与内核 `CompanionTurnResult` 字段同名），表示本回合已启动仅运行于后台的 tool loop，客户端可等待可能的 `tool_bg` 帧。后台 tool loop 的 OpenRouter（兼容）模型 id 由 **`app.agent.companion_tool_call_model`** 配置（见 `/app/core/AGENTS.md`「Companion tool-call model」）。**产品意图：** `user_signed_on` 控制帧除登记 proactive heartbeat 坐标外，还应配合客户端可选发出的 `messageType: IMPLICIT_USER_SIGNED_ON` 聊天帧，驱动「用户上线 → 智能体觉察 → 主动问候」（触发文案与动机见 [`/app/core/agentic_kernel/companion/implicit_signal_messages.py`](/app/core/agentic_kernel/companion/implicit_signal_messages.py) 模块说明）。`app.features.companion_ws_proactive_heartbeat_enabled`（默认 True）：连接内存活的 proactive heartbeat 轮询需要 `user_id`/`agent_id`/`chat_id` 坐标；客户端可先发控制帧 `{"type":"user_signed_on","agent_id":...}`（`user_signed_on_ack`），以便首条聊天帧之前即登记；未发送的旧客户端在任意一轮 **成功** WebSocket companion 聊天后也会写入同等坐标。可在 YAML 中设为 false 关闭；关闭时 `user_signed_on` 会 `ok:false`（`proactive_heartbeat_disabled`）。`Pydantic` 模型见 `app.schemas.chat.ChatWsUserSignedOnFrame`。
- **Companion upstream LLM failures**：当 agentic companion 在内核中调用 OpenRouter/OpenAI 兼容 `chat.completions` 失败（HTTP 4xx/5xx、连接、超时、或上游回 200 但 body `choices: null` + `error.code=...` 的伪成功）时，HTTP 返回 **502**，WebSocket 业务帧为 **`code` 502**、`message` 英文说明，并附带 **`error_kind`: `llm_inference_backend`** 与可选 **`llm_provider_http_status`**（上游状态码，无响应体时可为 `null`）。客户端可据此区分「推理供应商/服务端密钥配额」类错误与普通业务错误。Dual-LLM 路径下前台 chat 失败时本轮不启动后台 tool loop，故无「前台 502 后仍投递 `tool_bg`」语义；`chat.py` 中 `bg_started_on_exc` / `_persist_companion_user_message_for_bg` 异常分支保留为防御代码。
- `/api/v1/chat/ws/verify`：协议与 `/ws` 一致，业务下行同样经 **outbound queue + pump**；回复由 **单次** `chat.completions`（system + user，不经 Agent / companion 主编排）生成，**不写入 chat_history**。用于校验连接、队列与最简 LLM 连通性。见 `app/api/v1/endpoints/chat.py` 与本目录 `ENDPOINTS.md`。

### IntelliMate（[`android_app`](../../android_app/)）

- **连接**：用户登录后会维持主 WebSocket，路径即 **`/api/v1/chat/ws`**（[`MainRemoteDataSource.kt`](../../android_app/app/src/main/kotlin/com/ai/intellimate/main/data/MainRemoteDataSource.kt)）；另有 [`ChatWebSocketSessionManager.kt`](../../android_app/core/data/src/main/kotlin/ai/sxwl/android/data/chat/data/ChatWebSocketSessionManager.kt) 使用同路径。Debug 下可选用 **`/api/v1/chat/ws/verify`**（[`DebugBackendEndpointStore.kt`](../../android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/config/DebugBackendEndpointStore.kt)）。
- **发送**：**Release** 默认聊天上行仍走 **HTTP** completions；仅 **Debug** 且在调试设置里打开 chat WebSocket 时，发送才走主 WebSocket（[`ChatViewModel.kt`](../../android_app/app/src/main/kotlin/com/ai/intellimate/chat/viewmodel/ChatViewModel.kt) 与 `DebugBackendEndpointStore.getChatWebSocketEnabled()`）。无论发送走哪条路径，已登录客户端仍会与 `/api/v1/chat/ws` 保持连接（[`MainRepository.kt`](../../android_app/app/src/main/kotlin/com/ai/intellimate/main/data/MainRepository.kt) `connectWebSocket`）。

### 变更联动（客户端）

修改 `/api/v1/chat/ws` 的协议、鉴权、帧形状或 `ChatWebSocketRequest` / `ChatCompletionRequest` 等相关 schema 时，须同步更新已接入的客户端，例如：

- [`imate_android_app`](../../imate_android_app/)（如 [`ChatWebSocketRemoteDataSource.kt`](../../imate_android_app/app/src/main/java/com/inty/imate/chat/data/datasource/ChatWebSocketRemoteDataSource.kt)）
- [`tools/inty_v2_repl/backend_chat_ws.py`](../../tools/inty_v2_repl/backend_chat_ws.py)
- IntelliMate：[`android_app`](../../android_app/)（行为见上「IntelliMate」小节）

[`imate_ios_app`](../../imate_ios_app/) **尚未接入**该 WebSocket；待接入或后端 breaking 变更时，由 **iMate iOS 负责人** 与上述客户端一并核对协议。
