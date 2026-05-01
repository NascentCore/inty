# Inty 后端 API 服务端点

- 后台管理用的 API 只能开放给超级用户（superuser）
- 增加新的 API endpoint(s) 需要更新 ENDPOINTS.md
- API endpoint(s) 从一个 py 文件迁移到另一个需要更新 ENDPOINTS.md

## Chat WebSocket

- `/api/v1/chat/ws`：正式对话 WebSocket，走持久化对话流程（写入 chat 历史）。
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
