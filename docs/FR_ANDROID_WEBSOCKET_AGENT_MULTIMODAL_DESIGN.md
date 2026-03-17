# FR_ANDROID_WEBSOCKET_AGENT_MULTIMODAL_DESIGN - Android 与 Backend Agent 的 WebSocket 多模态通信设计

CREATED_BY_AGENT

## 1. 目标与范围

本设计用于支持 Android App 与后端 AI Agent 之间的实时双向通信，统一承载三类输入：

1. 文本（text）
2. 语音（voice）
3. 视频信号（video）

并支持后端实时返回：

1. 文本增量输出（text delta/final）
2. 语音输出（audio delta/final）
3. 多模态理解事件（vision/audio understanding event）

本设计聚焦在线实时会话，不覆盖离线批处理。

## 2. 成功标准（用于后续实现验收）

满足以下条件可判定设计被正确实现：

1. Android 通过单个 WebSocket 会话即可在同一 `session_id` 下发送文本、语音 chunk、视频帧。
2. 后端能对三类输入进行有序处理，并返回可增量渲染的 AI 响应事件。
3. 断线重连后，客户端可基于 `last_acked_seq` 恢复会话，避免重复处理已确认消息。
4. 服务端能够通过流控事件限制客户端发送速率，避免内存和队列失控。
5. 全链路具备鉴权、审计追踪（`trace_id`）和错误可观测性。

## 3. 架构概览

### 3.1 Android 侧

- `WsSessionManager`：会话生命周期管理（connect/start/stop/reconnect）。
- `OutboundMuxer`：统一封装文本、音频、视频三类上行消息为协议包。
- `InboundDemuxer`：按消息类型分发到 UI、播放器、状态机。
- `AudioCapturePipeline`：录音、编码（PCM16/Opus）、分片发送。
- `VideoCapturePipeline`：相机帧采样、压缩（JPEG/WebP）、分片发送。
- `SessionStateStore`：保存 `session_id`、`next_seq`、`last_acked_seq` 用于重连恢复。

### 3.2 Backend 侧

- `WebSocket Gateway`：连接接入、JWT 校验、协议解包与基础限流。
- `Session Router`：将同一 `session_id` 路由到同一 Agent Runtime 实例。
- `Agent Runtime`：融合文本/语音/视频上下文，驱动 LLM/VLM/ASR/TTS。
- `Media Preprocessor`：音频 VAD/ASR、视频关键帧抽取与特征化。
- `Response Streamer`：将 AI 结果切分为增量事件下发。
- `Observability`：记录 `trace_id`、时延、丢包、重试、错误码指标。

### 3.3 连接拓扑

Android `OkHttp WebSocket` -> Backend `FastAPI WebSocket endpoint` -> `Session Router` -> `Agent Runtime Worker`

## 4. 连接与会话流程

## 4.1 握手

- Endpoint（示例）：`wss://<host>/api/v1/agent/ws`
- Header：
  - `Authorization: Bearer <access_token>`
  - `X-Client-Trace-Id: <uuid>`
- Query（可选）：
  - `agent_id=<agent_id>`
  - `session_id=<optional_existing_session_id>`

服务端通过后返回 `session.started`，包含服务端生成或确认的 `session_id`。

### 4.2 会话阶段

1. `session.start`：声明本会话能力（text/audio/video）和编解码参数。
2. 上行多模态数据：
   - 文本：`text.input`
   - 语音：`audio.chunk` ... `audio.end`
   - 视频：`video.frame` ... `video.end`
3. 下行 AI 结果：
   - `text.delta` / `text.final`
   - `audio.delta` / `audio.final`
   - `agent.event`（如情绪、场景、工具调用建议）
4. `session.stop`：会话关闭与资源回收。

### 4.3 断线恢复

客户端重连时发送 `session.resume`：

- `session_id`
- `last_acked_seq`
- `resume_token`（服务端签发）

服务端仅重放 `last_acked_seq` 之后的未确认下行事件。

## 5. 协议设计（统一 Envelope）

所有消息使用同一外层结构，便于扩展：

- `version`: 协议版本，当前 `1`
- `type`: 消息类型
- `session_id`: 会话 ID
- `seq`: 发送序号（单调递增）
- `trace_id`: 链路追踪 ID
- `ts_ms`: 客户端或服务端毫秒时间戳
- `payload`: 类型相关负载

示例（文本输入）：

```json
{
  "version": 1,
  "type": "text.input",
  "session_id": "sess_123",
  "seq": 18,
  "trace_id": "tr_abc",
  "ts_ms": 1760000000123,
  "payload": {
    "text": "帮我总结一下这段视频",
    "lang": "zh-CN"
  }
}
```

## 5.1 上行消息类型（Android -> Backend）

1. `session.start`
   - 能力声明：`supports_text`, `supports_audio`, `supports_video`
   - 编解码声明：音频 codec / sample rate，视频 codec / fps / max resolution
2. `text.input`
   - 文本内容，支持 `is_final`
3. `audio.chunk`
   - `codec`（`pcm_s16le` / `opus`）
   - `sample_rate_hz`, `channels`, `chunk_ms`
   - `data_b64`
4. `audio.end`
   - 表示一段语音输入结束
5. `video.frame`
   - `codec`（建议 `jpeg` 或 `webp`）
   - `width`, `height`, `rotation`
   - `frame_ts_ms`
   - `data_b64`
6. `video.end`
   - 表示一次视频片段输入结束
7. `session.stop`
8. `ack`
   - 回执服务端下行 `seq`
9. `ping`

## 5.2 下行消息类型（Backend -> Android）

1. `session.started`
2. `text.delta`
3. `text.final`
4. `audio.delta`
5. `audio.final`
6. `vision.result`
   - 视频理解结果（标签、场景、OCR/对象摘要）
7. `agent.event`
   - Agent 中间状态（思考阶段、工具调用阶段、完成阶段）
8. `flow.control`
   - 流控参数（`max_inflight_bytes`, `send_interval_ms`）
9. `error`
   - 结构化错误：`code`, `message`, `retryable`
10. `pong`
11. `session.stopped`

## 6. 顺序、可靠性与流控

### 6.1 顺序保证

- 每个方向独立 `seq`。
- 会话内按 `seq` 排序处理，检测乱序与重复包。
- 对高频媒体包（`audio.chunk`, `video.frame`）允许在可配置窗口内轻微乱序重排。

### 6.2 ACK 与重传

- 接收方周期性发送 `ack`（累计确认最大连续 `seq`）。
- 发送方维护待确认窗口，超时未确认则重发（带重试上限）。
- 重连时基于 `last_acked_seq` 执行差量重放。

### 6.3 流控与背压

- 服务端通过 `flow.control` 动态下发发送预算。
- 客户端超过预算时降采样：
  - 音频：增大 `chunk_ms` 或切换 Opus 低码率。
  - 视频：降低帧率或分辨率，仅保留关键帧。

## 7. 安全与合规

1. 仅允许 `wss`（TLS）。
2. 使用短期 JWT，服务端在握手和续期时校验。
3. 会话级 `resume_token` 必须绑定 `user_id + session_id + expiry`。
4. Android 端需在录音/摄像前获取显式权限与用户同意。
5. 生产日志不记录原始音视频内容，仅记录哈希、大小、时长、错误码。

## 8. 可观测性指标

核心指标：

- 连接成功率、平均会话时长
- 上行/下行吞吐（bytes/s）
- 文本首 token 延迟（TTFT）
- 语音端到端延迟（capture -> first audio.delta）
- 视频帧处理延迟（frame ingest -> vision.result）
- 重连成功率、重传率、丢包率

链路追踪字段：

- `trace_id`
- `session_id`
- `user_id`
- `agent_id`
- `seq`

## 9. Android 实现分层建议（与现有网络栈兼容）

1. 鉴权 token 获取继续复用现有 HTTP 栈（避免新增第三套鉴权逻辑）。
2. WebSocket 连接使用统一 `OkHttpClient` 配置来源，避免重复连接池与拦截器配置漂移。
3. 业务层通过 `ChatRepository` 暴露统一接口：
   - `sendText(...)`
   - `sendAudioChunk(...)`
   - `sendVideoFrame(...)`
   - `observeAgentEvents(...)`

## 10. Backend 实现分层建议

1. `app/api/ws/agent_ws_endpoint.py`：仅负责连接、鉴权、协议收发。
2. `app/services/agent_session_service.py`：会话状态机、路由、ACK/重传窗口。
3. `app/services/multimodal_ingest_service.py`：音视频预处理与标准化输入。
4. `app/services/agent_runtime_service.py`：编排 LLM/VLM/ASR/TTS。
5. `app/schemas/ws_agent.py`：协议 DTO（实现时与 Android DTO 同步）。

## 11. 数据结构同步约束

在落地实现协议 DTO 时，必须双端同步维护：

- Android Kotlin DTO：`android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model`
- Python Schema DTO：`app/schemas`

避免协议字段漂移导致线上兼容问题。

## 12. 失败场景与处理策略

1. `AUTH_FAILED`
   - 直接关闭连接，客户端刷新 token 后重连。
2. `UNSUPPORTED_CODEC`
   - 服务端返回可接受 codec 列表，客户端降级重试。
3. `RATE_LIMITED`
   - 客户端根据 `retry_after_ms` 退避。
4. `SESSION_EXPIRED`
   - 客户端触发 `session.start` 新会话，并提示用户上下文可能中断。
5. `INTERNAL_ERROR`
   - 服务端返回 `retryable=true/false`，客户端按策略重连或终止。

## 13. 实现里程碑建议

1. M1（文本先行）
   - `session.start`, `text.input`, `text.delta/final`, `ack`, `error`
2. M2（语音上/下行）
   - `audio.chunk/end`, `audio.delta/final`, 基础流控
3. M3（视频输入）
   - `video.frame/end`, `vision.result`, 关键帧策略
4. M4（可靠性增强）
   - `session.resume`, 重放窗口, 观测指标完善

## 14. 对应测试文档建议

落地开发时应补充 `tests/docs/TEST_STEPS_ANDROID_WS_MULTIMODAL.md`，至少覆盖：

1. 文本单模态回归
2. 语音端到端回归
3. 视频理解回归
4. 弱网断线重连回归
5. 流控与降级策略验证
