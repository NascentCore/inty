# Companion WebSocket 运行与排障手册

## 范围

本文面向维护 `/api/v1/chat/ws` 生产文本通道的后端、移动端与排障工程师，解释一条 Companion WebSocket 连接内的运行归属、排队语义、可观测线索和常见故障判断；本文不定义新的 wire schema，不替代 Companion Harness 架构说明，也不覆盖 Gemini Live audio 或 HTTP chat completion。

## 读前判断

- 需要判断“为什么用户消息、主动搭话、后台工具补帧谁挡住了谁”时，读本文。
- 需要对齐字段形状、必填字段或客户端序列化时，读 WebSocket schema。
- 需要理解 Companion 的长期记忆、prompt 或工具策略时，读 Companion Harness 架构与 MemoryStore 文档。

## 运行归属

| 对象 | 归属 | 作用 | 排障含义 |
| --- | --- | --- | --- |
| WebSocket 连接 | 单个客户端长连接 | 承载控制帧、用户聊天帧和业务下行 | 断线、重连、`ws_conn_id` 都先按传输问题判断。 |
| `turn_lock` | 单条 WebSocket 连接 | 序列化该连接上的用户轮、签入问候、inner-tick 与 tool background 补帧组装 | 同一连接内不会并行跑两个 Companion turn；慢轮次会让后续业务轮排队。 |
| 业务 outbound 队列 | 单条 WebSocket 连接 | FIFO 发送 assistant、业务错误、tool background 等对话下行 | 控制 ack 不在这条 FIFO 里；排查“消息顺序”时先区分业务下行与信令下行。 |
| tool background 事件队列 | 单条 WebSocket 连接 | 接收工具线程完成事件，再组装成可见补帧 | 事件只说明工具完成；真正下发还要等连接读循环取到事件并拿到 `turn_lock`。 |
| foreground pending | 单条 WebSocket 连接 | 用 `user_msg_uuid` 保存当轮 chat、voice、history 等补帧上下文 | “missing foreground ctx”通常指事件与当轮上下文脱钩，不是模型无回复。 |
| `voice_message` TTS | 单条业务下行 | 当 Companion 选择语音消息时，为对应 assistant 行生成并回填 `audio_url` | 语音缺失先按该业务下行排查，不要按 Live Chat audio 或 REST TTS 排查。 |
| `tool_bg_idle` | Companion session | 标记该 session 的后台工具是否空闲 | inner-tick 会用它避免主动心跳与上一次 proactive tool background 重叠。 |
| inflight turn tracker | 单条 WebSocket 连接，另有进程级索引 | 跟踪连接上已派生但未完成的 turn | 当前连接结束和进程关闭会取消未完成 turn；目标方向是完成后持久化为未投递。 |

## 当前事实

- `ping`、`client_context`、`user_signed_on`、`user_signed_out`、`ws_conn_dropped` 等控制帧直接回 ack；assistant 主回复、业务错误和 tool background 补帧进入业务 outbound 队列。
- `user_signed_on` 会刷新当前连接的 inner-tick 坐标，并可排入一条隐式问候 turn；`message_id` 必须是 UUID，失败会在 ack 中表现为 `missing_message_id` 或 `invalid_message_id`。
- 普通用户聊天帧必须带 `agent_id` 与 completion-shaped request；Companion WebSocket 文本通道当前拒绝图片类多模态用户轮。
- 用户轮的 `message_id` 被规范化为 `user_msg_uuid`，用于 transcript、LangSmith、tool background 事件和下行 `meta_data` 关联。
- 维护性 inner-tick 可产生无前台正文但有后台工具的轮次；主动心跳和 scheduled reminder 走可见主动聊天语义。
- 同一连接上的用户轮、inner-tick 和 tool background 补帧组装都要经过 `turn_lock`；当前没有“新用户消息打断正在运行用户轮”的 WebSocket supersede 语义。
- 当 assistant 或 tool background 的 `reply_modality = "voice_message"` 时，WebSocket 路径会在 assistant 行落库后合成 TTS；成功后把 `audio_url` 写回同一条 `chat_history` assistant 行，并在 completion message 里返回。
- `voice_message` 朗读文本优先取 `voice_message_script`；为空时才使用可见 assistant 文本。
- 连接结束时，当前实现会取消仍在运行的连接内 turn；这是当前事实，不是目标生命周期。

## Inner-tick 调度

完整机制（proactive **rhythm**、worker **poll**、maintenance **min_gap**、REPL 原型 env）见 [INNER_TICK_SCHEDULING.md](./INNER_TICK_SCHEDULING.md)。当前事实摘要：

- 签入后 inner-tick worker 约每 **60s** 醒一次（`companion_ws_proactive_chat_poll_seconds`，下限 5s），顺序尝试 scheduled → proactive → maintenance。
- Proactive 是否到期由 `next_proactive_chat_wait_seconds` 决定：锚在 **最后一条 assistant** 的 `ts`，quiet 时长 **rhythm** 默认约 **30–60s**（随真实用户消息间隔自适应，上限 `2×base_idle`）。
- 两条 proactive 在 REPL 上的时间差常为 **rhythm + 至多一轮 poll + LLM/占锁**，故可能远大于 60s。
- `[SILENT]` 可能已写 `transcript.jsonl` 但不推业务下行；`prev_inner_tick_tool_bg` 会跳过本轮 proactive / scheduled。

## 正常工作流

### 客户端签入

```json
{"type":"client_context","time_context":{"local_time":"2026-05-17T14:01:16-07:00","timezone":"America/Los_Angeles","utc_offset_minutes":-420}}
{"type":"user_signed_on","agent_id":"aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee","message_id":"11111111-2222-4aaa-8bbb-333333333333"}
```

期望结果：

- 服务端先校验并 ack 控制帧。
- 签入成功后，连接拥有 user、agent、chat 三元坐标。
- 若排入隐式问候，问候作为业务下行进入 FIFO，而不是控制 ack。

### 用户聊天轮

```json
{
  "agent_id": "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee",
  "request": {
    "message_id": "22222222-3333-4aaa-8bbb-444444444444",
    "messages": [{"role": "user", "content": "Are you there?"}]
  }
}
```

期望结果：

- 主 assistant 回复写入 chat history 并进入业务 outbound 队列。
- 若本轮启动 tool background，主回复的 `meta_data.tool_background_started` 为真。
- 后台工具若需要可见投递，会追加一条 `meta_data.source = "tool_bg"` 的业务下行，并用 `reply_to_user_msg_uuid` 指回原用户轮。

### 语音消息下行

触发条件：

- Companion turn 或 tool background 输出 `reply_modality = "voice_message"`。
- 对应 assistant 文本已经写入 chat history；语音 URL 归属这条 assistant 行，而不是用户行。
- 语音文本来自 `voice_message_script`，没有脚本时才朗读可见气泡文本。

期望结果：

- completion message 的 `meta_data.reply_modality` 为 `voice_message`，`meta_data.is_voice` 为真。
- TTS 成功时，completion message 的 `audio_url` 指向生成的音频；同一 assistant 行的 `chat_history.audio_url` 也被更新。
- 有音频时，时长写入 `meta_data.audioDuration`，供客户端播放进度和分析使用。

约束：

- 这是 `/api/v1/chat/ws` 专用路径，不是 HTTP chat completion 的 legacy auto-play TTS，也不是用户按需点击的 REST TTS。
- 语音选择顺序是 chat settings voice、agent voice、agent gender mapping、backend TTS default。
- 该路径调用 TTS 时不传订阅用户上下文；不要用它推断订阅计费或 REST 语音额度。

### 非主动断线后重连

```json
{"type":"ws_conn_dropped","agent_id":"aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee","dropped_at_utc":"2026-05-17T02:22:25Z","message_id":"33333333-4444-4aaa-8bbb-555555555555"}
{"type":"user_signed_on","agent_id":"aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee","message_id":"44444444-5555-4aaa-8bbb-666666666666"}
```

期望结果：

- `ws_conn_dropped` 只记录前一次传输断线事实，不表示用户登出。
- 重连后仍需重新签入，才能恢复 inner-tick 与 scheduled reminder 的投递坐标。

## 排障顺序

1. **先定位连接**：用 `ws_conn_id` 找 `chat_ws session_open` / `session_end`，确认是否是同一条连接、是否发生断线或 idle timeout。
2. **再定位业务轮**：用客户端 `message_id` / 服务端 `user_msg_uuid` 关联主 assistant 回复、tool background、LangSmith trace 和 runtime event。
3. **区分信令与业务下行**：ack 直接发送，assistant / tool background / queued error 走业务 FIFO；不要用 ack 顺序推断 assistant 顺序。
4. **检查锁与队列症状**：如果后续用户轮没有进入处理，先看前一个用户轮或 inner-tick 是否仍持有连接级 `turn_lock`。
5. **检查后台工具补帧**：若主回复已发但补帧缺失，找 `tool_background_started`、`reply_to_user_msg_uuid`、`tool_bg_output_to_user` 和 “missing foreground ctx” 日志。
6. **检查 inner-tick 坐标**：如果没有主动心跳或维护轮，确认是否已成功 `user_signed_on`，以及当前 chat 是否仍匹配连接保存的坐标。

## `meta_data` 速查

`meta_data` 挂在 chat history 的 user / assistant 行，以及 WebSocket 业务下行里的 completion message 上；字段真源是 `ChatWsCompanionWireMetaData`，下表只解释 Companion WebSocket 排障时最常用的组合。

| 字段/组合 | 出现位置 | 含义 | 排障用途 |
| --- | --- | --- | --- |
| `localId` | 用户 chat 行 | 客户端乐观消息 id；只服务端侧镜像，不是 Companion 轮次 id。 | 排查端上去重或临时气泡时用；不要用它找 LangSmith。 |
| `source = "chat"` | assistant 主回复 | 普通用户轮或可见主动轮的前台 assistant 回复。 | 结合 `user_msg_uuid`、`assistant_msg_uuid` 定位一次业务轮。 |
| `source = "inner_tick"` | assistant 主回复 | 服务端 synthetic inner-tick 的前台 assistant 回复。 | 看到它先看 `inner_tick_activity`，再判断是否应展示给用户。 |
| `source = "greeting"` | assistant 主回复 | `user_signed_on` 触发的隐式问候。 | 没有对应用户 chat_history 行是正常现象；上行控制帧不是用户正文。 |
| `source = "tool_bg"` | tool background 补帧 | 后台工具线程完成后追加的业务下行。 | 用 `reply_to_user_msg_uuid` 指回前台轮；它不是新的用户输入。 |
| `reply_modality = "voice_message"`、`is_voice = true` | assistant 主回复 / tool_bg 补帧 | Companion 要求客户端把该气泡按语音消息呈现。 | 若无 `audio_url`，继续查 TTS 触发、音色解析、持久化回填。 |
| `voice_message_script` | assistant 主回复 / tool_bg 补帧 | 实际朗读脚本；可与可见气泡文本不同。 | 排查“听到的内容和气泡不同”时优先看它。 |
| `audioDuration` | assistant 主回复 / tool_bg 补帧 | 生成音频时长，写在 `meta_data`。 | 客户端播放 UI 或分析口径异常时用。 |
| `inner_tick_activity = "proactive_chat"` | inner-tick assistant / tool_bg | 主动心跳或 scheduled reminder 所属轮次。 | 与 `companion_proactive_heartbeat`、`companion_scheduled_reminder` 区分来源。 |
| `inner_tick_activity = "maintenance"` | maintenance assistant / tool_bg | 维护型 inner-tick；可无前台正文，仅启动后台工具。 | 用户发消息无回复时，若前序 maintenance 仍有 tool_bg，优先查 `turn_lock` + `tool_bg_idle`。 |
| `tool_background_started = true` | assistant 主回复 | 当前前台轮已启动后台工具线程，之后可能有 `source = "tool_bg"` 补帧。 | 主回复已到但后续缺失时，继续查 foreground pending 与工具事件队列。 |
| `tool_bg_output_to_user` | tool_bg 补帧 | 该工具输出是否面向用户可见。 | 为假或缺失时，不要期待客户端展示新的气泡。 |
| `tool_bg_generation_deliver`、`generated_image`、`tool_bg_local_image_paths` | tool_bg 补帧 | 后台生成类投递及生成图片元数据。 | 排查图片/生成物补投递，不用于普通文本轮判定。 |
| `context_mode` | assistant 主回复 | 该轮开始时的体验档位。 | 只说明本轮 prompt 起点；若工具后续改 `context.json`，下一轮才体现。 |
| `transcript_compaction` | assistant 主回复 | 本轮 transcript 截窗压实时的摘要信息。 | 排查长上下文行为；inner-tick 通常不跑用户轮式 memory pipeline。 |

约束：

- `message_id` / `user_msg_uuid` / `assistant_msg_uuid` / `langsmith_trace_id` 分别归属客户端请求、Companion 轮次、assistant 行、LangSmith trace；不要相互替代。
- `inner_tick_activity` 的取值是 `proactive_chat` 或 `maintenance`；旧名 `InnerTickMode` 只应出现在历史讨论里。
- `source = "tool_bg"` 的补帧进入同一业务 outbound FIFO，但组装补帧仍要拿到连接级 `turn_lock`。

## 常见症状

### 用户连发后第二条迟迟无回复

判断：

- 当前 WebSocket 通道按连接串行执行 Companion turn。
- 若第一条用户轮仍在模型、工具前台、持久化或补帧组装阶段，第二条不会抢占它。
- 这不是客户端重试语义，也不是 supersede；当前没有“后发用户消息取消前一用户轮”的生产 WebSocket 行为。

证据：

- 同一 `ws_conn_id` 下第一条 `user_msg_uuid` 已进入处理但未出现主回复或错误业务下行。
- 第二条客户端帧之后没有对应的新 `chat_turn route=websocket` 日志，或出现时间晚于第一轮完成。

### 主回复已出现，tool background 补帧没出现

判断：

- 主回复和 tool background 是两条业务下行。
- 工具事件必须能用 `user_msg_uuid` 找回 foreground pending，之后还要拿到 `turn_lock` 才能组装补帧。
- 某些 tool background 只写记忆，不一定对用户可见。

证据：

- 主回复 `meta_data.tool_background_started` 为真。
- 查后续是否有 `meta_data.source = "tool_bg"`，以及 `reply_to_user_msg_uuid` 是否等于原用户轮。
- 若有 “missing foreground ctx”，优先怀疑连接生命周期、重复 UUID 或 pending 被过早清理。

### `voice_message` 气泡没有音频

判断：

- **tool 先合成**：`generate_voice_message` 成功时 `ToolOutputEvent.precomputed_audio_url` 已带 URL，WS tool_bg 路径只落库、不再打 `chat_ws voice_message TTS`；日志里该短语出现两次即重复合成 bug。
- **信封 fallback**：未调 voice tool 但 `reply_modality = voice_message` 时，仍由 `_chat_ws_voice_message_audio_url` 合成。
- `reply_modality = "voice_message"` 只表示 Companion 选择语音消息；`audio_url` 只有 TTS 成功并回填后才出现。
- 若 `voice_message_script` 和可见 assistant 文本都为空，不会合成音频。
- 若音色无法解析或 TTS provider 返回空数据，业务下行仍可返回文本气泡。

证据：

- completion message 或 chat_history assistant 行有 `meta_data.reply_modality = "voice_message"` 与 `meta_data.is_voice = true`。
- 同一 assistant 行缺少 `audio_url` 或 `meta_data.audioDuration`。
- 后端日志可见 `chat_ws voice_message TTS`、`TTS 生成完成`、`tts_provider_returned_empty` 或 `chat_ws voice_message persist audio_url failed`。

### inner-tick 没有主动说话

判断：

- inner-tick 依赖成功签入后的 user、agent、chat 坐标。
- scheduled reminder、proactive heartbeat 和 maintenance inner-tick 共用连接级轮次串行化。
- 上一次 proactive tool background 未空闲时，后续 proactive / scheduled reminder 会跳过，避免同一 session 的自主消息重叠。
- rhythm 未到（`remain > 0`）时 worker 每轮 poll 不会跑 proactive，属正常而非故障。
- transcript 末条不是 `assistant` 时 proactive 长期禁用，直到 assistant 回复落库。
- 模型返回 `[SILENT]` 时不推下行；若「很久没说话」但 LangSmith 有 proactive trace，先查是否 silent。

证据：

- 查 `user_signed_on_ack.ok` 是否为真。
- 查 `companion_ws_inner_tick_poll no_heartbeat_coords` 或 chat_id mismatch 日志。
- 查 `prev_inner_tick_tool_bg`、`prev_maintenance_pending`、`companion_ws_proactive_chat silent` 等跳过日志。
- 对照 [INNER_TICK_SCHEDULING.md](./INNER_TICK_SCHEDULING.md) 核对 rhythm / poll 是否解释观测间隔。

### 断线后用户没有收到原本可能完成的回复

判断：

- 当前实现会在连接结束时取消连接内未完成 turn。
- `ws_conn_dropped` 只写断线事实；它不会恢复已被取消的业务下行。
- “完成后持久化为 undelivered 并在下次签入投递”是目标方向，不是当前事实。

证据：

- 同一 `ws_conn_id` 出现 `session_end` 后，没有对应主回复或 queued error。
- 当前连接结束路径会取消 inflight turn；排查时不要假设后台仍会自然完成并补发。

## 约束与坑

- 不要把 `ws_conn_id` 当业务轮标识；它只表示传输连接。
- 不要把 `message_id`、`user_msg_uuid`、LangSmith trace id 混用；它们分别服务客户端去重、业务轮关联和模型调用追踪。
- 不要把控制 ack 展示成 Companion 说话；它们是信令下行。
- 不要用普通断线代替 `user_signed_out`；登出有 scope teardown 语义，普通断线没有。
- 不要预期 HTTP chat completion 与 WebSocket chat completion 的 async tool background 投递完全一致；本文只覆盖 WebSocket 文本通道。
- 不要把 `audio_url` 缺失解释成 WebSocket 帧丢失；先确认该 assistant 行是否真的完成 TTS 并成功回填。

