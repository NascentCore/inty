# Live Chat：评测平台与 Android 端技术对比与运维说明

本文记录评测平台语音通话与 Android 端实时语音通话的技术差异、体验差异原因，以及评测平台展示保存录音的说明。

## 1. 完整记录能力

**评测平台与 Android 端均能完整记录用户消息和 AI 语音。**

- **后端**：同一套 `app/services/live_chat_service.py`。当 `config.save_history` 为 true 时，在发送/接收路径按顺序累积 `("user", bytes)` / `("ai", bytes)` 到 `conversation_audio_chunks`，会话结束时拼接为 24k 单路 WAV 上传 GCS，并将 `audio_url` 与总时长写回 `chat_history` 对应用户消息与 AI 消息。
- **协议**：两端均使用同一 WebSocket 端点 `/api/v1/live-chat/{agent_id}`，协议一致。只要连接时开启「保存到聊天历史」，服务端即按上述流程落库与落 GCS。

## 2. 技术差异概览

后端完全一致，差异在**客户端**：运行环境、采集/播放管线、缓冲与调度策略不同。

| 维度       | 评测平台（Web）                          | Android App                                      |
|------------|------------------------------------------|--------------------------------------------------|
| 连接       | `evaluation/services/liveChat.ts`，浏览器 WebSocket | `AICallRepository`，Ktor WebSocket，同一 URL     |
| 上行采集   | `getUserMedia` + `ScriptProcessorNode`，浏览器端从原生采样率重采样到 16kHz 再发 | `AudioRecord` 直接 16kHz 单声道 PCM（`VOICE_COMMUNICATION`） |
| 下行播放   | `AudioContext(sampleRate: 24000)` + 预调度播放（等 2 个片段再播，50ms 提前量无缝调度） | `AudioTrack` 24kHz 单声道 16bit，队列驱动（250 包队列，满则丢旧包） |
| 回声/噪声  | `getUserMedia` 中开启 `echoCancellation`、`noiseSuppression`、`autoGainControl` | `VOICE_COMMUNICATION` 走系统语音通路，依赖设备实现 |
| 缓冲策略   | 发送 4096 采样/块；播放 PREFILL_COUNT=2、SCHEDULE_AHEAD_MS=50 | 播放 8×minBufferSize + 250 包队列；发送 30 包队列 |

相关代码位置：

- 评测端：`evaluation/services/liveChat.ts`（SEND_SAMPLE_RATE 16k、RECEIVE_SAMPLE_RATE 24k、PREFILL_COUNT、scheduleNextChunk）。
- Android：`android_app/app/src/main/kotlin/com/ai/intellimate/audio/AudioRecordManager.kt`（16k）、`AudioStreamPlayer.kt`（24k、队列）、`VoiceCallScreen.kt`（播放/录制生命周期）、`UiConfigs.VoiceCall`（队列容量）。

## 3. 为何评测平台主观体验更好

1. **环境更可控**：评测多在办公室 Wi‑Fi 或稳定网络下用电脑进行；Android 面临移动网络、弱网、切换 Wi‑Fi/4G、机型差异，延迟与抖动更大。
2. **播放管线更顺**：评测端用 Web Audio 的精确时间调度（`scheduleNextChunk` + `nextPlayTime` + 50ms 提前量），多段 PCM 按时间轴无缝衔接；Android 端有数据就写 `AudioTrack`，依赖队列吸收抖动，队列满会丢包，网络抖动时易出现轻微断句或爆音。
3. **首包延迟**：评测端仅等 2 个片段即开播，且 PC 音频栈延迟较稳定；Android 需等 AudioTrack 初始化与首包入队，部分机型/系统延迟更大，「静默后首响应」在端侧体现会更长。
4. **采集与回声**：两端上行均为 16k，格式一致。浏览器显式开启回声消除与降噪；Android 依赖厂商对 `VOICE_COMMUNICATION` 的实现，部分机型在扬声器较大或环境嘈杂时回声/底噪更明显。
5. **无电量/后台限制**：评测在桌面浏览器前台运行；Android 在后台或息屏时可能被限速或限制网络，导致延迟升高或断续。

## 4. 评测平台展示保存的语音通话录音

**可以**通过修改评测前端来展示并播放保存的录音。

- **数据链路**：后端 `get_session_messages`（`/evaluation/user-analytics/session-messages`）已返回每条消息的 `audio_url`；live chat 保存的录音会写入对应用户/AI 消息的 `audio_url`，评测前端拿到的消息结构已包含该字段。
- **当前前端**：`evaluation/pages/UserDailyMessagesPage.tsx` 在存在 `msg.audio_url` 时仅展示「语音消息」Tag，**没有**播放按钮或可点击链接。
- **建议改动**：在会话消息展示处（如 UserDailyMessagesPage）对 `msg.audio_url` 增加可播放/可打开入口，例如：
  - 使用 `<audio src={msg.audio_url} controls />` 内嵌播放，或
  - 提供「播放」「打开录音」按钮/链接（新开标签或弹窗播放）。
- 若需区分「语音通话整段录音」与单条 TTS，可利用 `meta_data.is_voice`、`meta_data.voice_session_id` 等（若后端有写）做标签或筛选。

详见 `app/services/user_analytics_service.py` 中 `get_session_messages` 的返回结构及 `evaluation/types.ts` 中 `ChatMessageResponse`。

## 5. Android 端可选优化方向

若希望缩小与评测端的体验差距，可考虑：

- **播放**：参考评测端的「预缓冲 + 时间轴调度」，在 Android 对 24k PCM 做一定预缓冲（如攒够 N ms 再开播），并按时间戳或固定块长连续写入 `AudioTrack`，减少网络抖动导致的断句。
- **发送**：在保证实时性的前提下适当增大发送队列或做轻度平滑，避免弱网下频繁丢包。
- **设备与网络**：在弱网与低端机上做针对性测试；必要时做网络质量检测，在极差时提示用户或降级。

## 6. 相关文档

- 功能与存储形式：`docs/FR_LIVE_CHAT_AUDIO_GCS.md`
- 实时语音通话整体设计：`docs/FR_LIVE_VOICE_CHAT.md`
- 测试步骤：`tests/docs/TEST_STEPS_LIVE_CHAT_AUDIO_GCS.md`
