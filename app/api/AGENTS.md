# Inty 后端 API 服务端点

- 后台管理用的 API 只能开放给超级用户（superuser）
- 增加新的 API endpoint(s) 需要更新 ENDPOINTS.md
- API endpoint(s) 从一个 py 文件迁移到另一个需要更新 ENDPOINTS.md

## Chat WebSocket

- **Companion chat frame**（`ChatWebSocketRequest.request` / `ChatCompletionRequest`）：可选 **`messageType`**（camelCase JSON），取值 **`USER_MESSAGE`**（默认）或 **`IMPLICIT_USER_SIGNED_ON`**。后者仅 **WebSocket companion** 支持：用户消息正文须为空且不得含图片等多模态 content（否则 **400**），服务端不写用户 history 行；companion 内核在 transcript 之后 **追加** 一条 tail `system` 触发问候（不混在靠前 system 前缀里），不发送空 `user` 行；助手落库 `meta_data.messageType` 可为 `IMPLICIT_USER_SIGNED_ON`。HTTP completions 传入该类型返回 **400**。非法请求体现在上行 JSON 时下行 **`code` 422**，`message` 为 `Invalid chat WebSocket request`。`record_usage` 对该类成功回合附带 **`implicit_user_signed_on: true`**。详见 [`/docs/FR_USER_SIGN_ON_GREETINGS.md`](/docs/FR_USER_SIGN_ON_GREETINGS.md)。
- **Companion upstream LLM failures**：当 agentic companion 在内核中调用 OpenRouter/OpenAI 兼容 `chat.completions` 失败（HTTP 4xx/5xx、连接、超时等）时，HTTP 返回 **502**，WebSocket 业务帧为 **`code` 502**、`message` 英文说明，并附带 **`error_kind`: `llm_inference_backend`** 与可选 **`llm_provider_http_status`**（上游状态码，无响应体时可为 `null`）。客户端可据此区分「推理供应商/服务端密钥配额」类错误与普通业务错误。
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
