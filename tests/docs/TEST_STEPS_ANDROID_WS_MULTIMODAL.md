# TEST_STEPS_ANDROID_WS_MULTIMODAL

## 目标

验证 `docs/FR_ANDROID_WEBSOCKET_AGENT_MULTIMODAL_DESIGN.md` 中定义的协议与流程在实现后可被端到端满足。

## 前置条件

1. Backend WebSocket endpoint 已部署并可访问。
2. Android 客户端已实现 `session.start/text.input/audio.chunk/image.input/video.frame` 等协议消息。
3. 已准备可用测试账号与 JWT。

## 用例 1：文本单模态

1. Android 连接 WebSocket，发送 `session.start`（仅 text 能力）。
2. 发送 `text.input`。
3. 观察服务端返回 `text.delta` 与 `text.final`。
4. 客户端回 `ack`，检查服务端侧无重复重发。

期望结果：

- 文本响应连续、顺序正确，`seq` 单调递增。
- `trace_id` 在客户端日志与服务端日志可关联。

## 用例 2：语音上行 + 文本/语音下行

1. 开启 audio 能力发起会话。
2. 连续发送多个 `audio.chunk`，并发送 `audio.end`。
3. 观察服务端 `text.delta/final` 与 `audio.delta/final`。

期望结果：

- 后端可正确聚合 chunk 并生成响应。
- 首包延迟与总耗时在可接受范围。

## 用例 3：图片输入理解

1. 开启 image 能力发起会话。
2. 发送单张 `image.input`（来源可为相册或相机）。
3. 观察服务端 `image.result` 与后续 Agent 文本解释。

期望结果：

- 返回对象/场景/OCR 摘要。
- 图片大小、格式在服务端约束内可被正确处理。

## 用例 4：视频帧输入理解

1. 开启 video 能力发起会话。
2. 连续发送 1-3 秒采样帧（`video.frame`）后发送 `video.end`。
3. 观察服务端 `vision.result` 与后续 Agent 文本解释。

期望结果：

- 返回对象/场景识别摘要。
- 不出现协议字段缺失或 codec 不兼容错误。

## 用例 5：断线恢复

1. 会话中途主动断网或关闭 socket。
2. 客户端使用 `session.resume(session_id, last_acked_seq, resume_token)` 重连。
3. 继续发送输入并接收输出。

期望结果：

- 服务端仅重放未确认下行事件。
- 已确认事件不重复消费。

## 用例 6：流控与降级

1. 模拟高频发送音视频与大图片。
2. 观察服务端下发 `flow.control`。
3. 客户端执行降级（降帧/降码率/降图片质量）后继续会话。

期望结果：

- 连接不被异常断开。
- 服务端缓冲队列稳定，无持续膨胀。

## 记录要求

每个用例保留以下证据：

1. 客户端关键日志（发送/接收消息类型、`seq`、`trace_id`）。
2. 服务端关键日志（会话路由、处理结果、错误码）。
3. 异常场景的错误事件原文（`error.code`, `retryable`）。
