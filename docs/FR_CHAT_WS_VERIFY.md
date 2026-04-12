# FR_CHAT_WS_VERIFY - 聊天 WebSocket 对接文档（App 端）

本文档面向 Android App 端开发，说明通过 WebSocket 进行聊天对话的接口约定与协议。当前提供两种端点：**校验端点**（不落库，用于联调/验证）与**现有生产端点**（落库，一发一收）。

---

## 一、端点概览

| 路径 | 用途 | 是否写入 chat_history |
|------|------|------------------------|
| `WebSocket /api/v1/chat/ws` | 生产：一发一收，请求/响应 JSON 与 POST completions 同构；始终走 inty v2 companion kernel（POST 始终 legacy） | 是 |
| `WebSocket /api/v1/chat/ws/verify` | 校验：协议相同，仅用于验证连接与对话效果 | 否 |

- **引擎对齐**：生产 `/ws` 走 `_agent_chat_completions_impl`（落库），始终用 companion kernel；`POST /completions` 始终 legacy `Agent`。`/ws/verify` 仍走 `generate_message_without_user_save`。按 [FR_INTY_V2_CHAT_WS_INTEGRATION_PLAN.md](/docs/FR_INTY_V2_CHAT_WS_INTEGRATION_PLAN.md) 第 7 节统一 verify 或保留 QA 差异说明。
- **Base URL**：与现有 HTTP API 一致，如 `wss://<host>/api/v1/chat/ws` 或 `wss://<host>/api/v1/chat/ws/verify`（HTTPS 环境用 `wss`，HTTP 用 `ws`）。
- **兼容性**：老版本 App 可继续使用 `POST /api/v1/chat/completions/{agent_id}` 或现有 `/api/v1/chat/ws`，无需改动。

---

## 二、鉴权

与现有 HTTP/WebSocket 接口一致，使用用户访问令牌（Bearer Token）：

- **推荐**：建立 WebSocket 时在请求头中携带  
  `Authorization: Bearer <token>`
- **兼容**：若运行环境无法在 WebSocket 握手时设置自定义 Header（如部分客户端库），可在 URL 中携带：  
  `?token=<token>`

未鉴权或 token 无效时，服务端会关闭连接，关闭码 `4001`，reason 为 `Unauthorized`。

### 2.1 评测：Assume user（WebSocket）

与实时语音 WebSocket 一致：握手 URL 可追加 `assume_user_id=<user id>`。仅当当前 token 用户为 **superuser** 时才会切换身份；否则参数被忽略。语义对齐 HTTP 的 `X-Assume-User-Id`（`get_effective_user_for_eval`）。适用于 `/api/v1/chat/ws` 与 `/api/v1/chat/ws/verify`。

---

## 三、协议约定

两端均使用**文本帧**（Text frame），内容为 **JSON 字符串**。

### 3.1 上行（客户端 → 服务端）

每条消息为单个 JSON 对象，与 [ChatWebSocketRequest](app/schemas/chat.py) 对应：

```json
{
  "agent_id": "<角色 ID>",
  "request": {
    "messages": [
      { "role": "user", "content": "文本内容" }
    ],
    "stream": false,
    "model": "chatbot",
    "language": "zh",
    "time_context": null
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `agent_id` | string | 是 | 角色 ID |
| `request` | object | 是 | 与 POST `/chat/completions/{agent_id}` 的 body 同构 |
| `request.messages` | array | 是 | 消息列表，至少一条 `role: "user"` 的消息 |
| `request.messages[].role` | string | 是 | 固定 `"user"` |
| `request.messages[].content` | string \| array | 是 | 文本或多模态 content parts（与现有 Chat 一致） |
| `request.stream` | boolean | 否 | 默认 `false`，当前仅支持非流式 |
| `request.model` | string | 否 | 默认 `"chatbot"` |
| `request.language` | string | 否 | 默认 `"zh"` |
| `request.time_context` | object | 否 | 用户时间上下文，可选 |
| `request.request_id` | string | 否 | 客户端请求 ID，可选 |
| `request.message_id` | string | 否 | 客户端消息 ID，可选 |
| `request.target_imate_id` | string | 否 | 可选 |

多模态示例（图文）：

```json
{
  "agent_id": "xxx",
  "request": {
    "messages": [
      {
        "role": "user",
        "content": [
          { "type": "text", "text": "描述这张图" },
          { "type": "image_url", "image_url": { "url": "https://..." } }
        ]
      }
    ],
    "stream": false,
    "model": "chatbot",
    "language": "zh"
  }
}
```

### 3.2 下行（服务端 → 客户端）

每条消息为单个 JSON 对象，与现有聊天 HTTP 响应外壳一致，并多出 `agent_id`：

**成功时**（`code === 200`）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "chatcmpl-xxx",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "chatbot",
    "user_message_id": null,
    "business_actions": [...],
    "choices": [
      {
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "AI 回复的文本内容",
          "content_parts": null,
          "id": null,
          "meta_data": null,
          "timestamp": null,
          "audio_url": null
        },
        "finish_reason": "stop"
      }
    ],
    "usage": {
      "prompt_tokens": 10,
      "completion_tokens": 20,
      "total_tokens": 30
    }
  },
  "agent_id": "<角色 ID>"
}
```

- **取 AI 文本**：`data.choices[0].message.content`（字符串）。
- **取语音 URL**：若存在，在 `data.choices[0].message.audio_url`（校验端点 `/ws/verify` 当前不生成语音，该字段多为 `null`）。

**失败时**（`code !== 200`）：

```json
{
  "code": 400,
  "message": "No user message found",
  "data": null,
  "agent_id": "<角色 ID>"
}
```

| code | 说明 |
|------|------|
| 400 | 请求非法（如无 user 消息） |
| 404 | 角色不存在 |
| 500 | 服务端处理错误（含 Agent 调用异常） |

**心跳帧**（应用层，与聊天报文并列；**由客户端驱动**，与主流 IM/SDK 一致）：

- 客户端 → 服务端：`{"type":"ping"}`（建议每 20–30 秒发送一次，用于保活与探测）。
- 服务端 → 客户端：`{"type":"pong"}`（对客户端 ping 的回复）。
- 服务端**不主动发 ping**；若在 `app.features.chat_ws_idle_timeout_seconds`（默认 60）秒内未收到任何上行（ping 或聊天），服务端将关闭连接。

---

## 四、行为说明

### 4.1 现有生产端点 `/api/v1/chat/ws`

- **一发一收**：客户端发送一条上行消息后，应等待一条下行消息（成功或失败），再发送下一条；同一连接上可顺序多发，但服务端按「收到一条、处理一条、回一条」的模式工作。
- **落库**：用户消息与 AI 回复会写入 `chat_history`（与 POST completions 一致）；生产 `/ws` 始终走 companion kernel，推理引擎与 POST 不同。
- **多角色**：同一连接可发送不同 `agent_id` 的请求，下行通过 `agent_id` 区分。

### 4.2 校验端点 `/api/v1/chat/ws/verify`

- **协议**：与 `/ws` 完全相同（上行/下行结构一致）。
- **不落库**：用户消息与 AI 回复**不写入** `chat_history`，仅用于联调、验证 WebSocket 连接与对话效果。
- **会话元数据**：为得到 `session_id` 可能调用 `get_or_create_chat`，若该 user+agent 首次使用该校验端点，可能新增一条 `chats` 表记录；不包含聊天内容。

---

## 五、客户端实现要点

1. **建连**：使用与现有 API 相同的 Base URL 和 token，将 path 设为 `/api/v1/chat/ws` 或 `/api/v1/chat/ws/verify`；若无法带 Header，则使用 `?token=<token>`。
2. **心跳**：由**客户端**定期（建议每 20–30 秒，且间隔小于 `app.features.chat_ws_idle_timeout_seconds`）发送 `{"type":"ping"}`，服务端回复 `{"type":"pong"}`。服务端不主动发 ping；超过该配置秒数未收到任何消息（ping 或聊天），将关闭连接。客户端应在连接建立后启动心跳定时器，收到 pong 可视为连接存活；断线后通过 onclose 重连。
3. **重连**：断线后建议指数退避重连，避免频繁重连。
4. **请求与响应对应**：当前为顺序一发一收，可通过本地队列保证「发送顺序与接收顺序一致」；若后续支持异步多请求，下行会带 `request_id` 等字段以便对应。
5. **错误处理**：根据下行 `code` 判断成功/失败，`code !== 200` 时解析 `message` 做提示或重试策略。

---

## 六、与 Kotlin 数据模型的对应关系

- **上行**：与 [ChatWebSocketReq](android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model/ChatBeans.kt)（`agent_id` + `request`）及 [SendMsgReq](android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model/ChatBeans.kt)（`messages`、`model`、`stream` 等）保持一致即可复用。
- **下行**：与现有 [SendMsgResponse](android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model/ChatBeans.kt) 及 HTTP 聊天响应结构一致，仅多出顶层 `agent_id`，便于多角色场景下区分。

---

## 七、相关文件

- 后端端点实现：[app/api/v1/endpoints/chat.py](app/api/v1/endpoints/chat.py)（`/ws`、`/ws/verify`）
- 请求/响应 Schema：[app/schemas/chat.py](app/schemas/chat.py)（`ChatWebSocketRequest`、`ChatCompletionRequest`、`ChatWebSocketResponse`）
- 端点列表与说明：[app/api/ENDPOINTS.md](app/api/ENDPOINTS.md)
