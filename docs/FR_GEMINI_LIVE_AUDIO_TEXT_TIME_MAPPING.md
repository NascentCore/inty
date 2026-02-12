# FR: Gemini Live API 文本与语音时间信息关联能力调研

## 调研结论（2026-02-12）

当前 Gemini Live API **不直接提供**“转写文本片段 ↔ 音频文件时间戳（起止 ms）”的一一对应结构，无法直接拿到可回放定位用的词级/句级 timecode。

依据官方文档（`https://ai.google.dev/api/live`）可确认：

- `BidiGenerateContentTranscription` 仅包含 `text` 字段；
- `inputTranscription` / `outputTranscription` 与其他服务端消息“独立发送，且无顺序保证”；
- `BidiGenerateContentSetup.generationConfig` 明确列出 `audioTimestamp` 为 **not supported**。

## 对当前需求的影响

- 可以稳定完成：会话级关联（`voiceSessionId`）与整段录音回放；
- 不能直接完成：点击某条文本后精准跳转到录音内对应时间位置（依赖官方 timecode 能力）。

## 建议落地策略

在服务端未提供官方 timecode 期间，采用“客户端近似时间轴”：

1. 发送/接收每段音频帧时记录单调时钟（`elapsedRealtime`）；
2. 文本增量到达时记录同一时钟并绑定 `voiceSessionId`；
3. 使用分段插值近似映射文本到录音偏移量（仅用于体验增强，标注为近似定位）。

该策略可后续无缝替换为官方时间戳字段（若 Gemini Live API 增补相关能力）。
