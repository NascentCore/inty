# Enhance Companion Harness architecture

**Changes needed to align `/app/core/companion_harness/` to `/docs/companion_harness/ARCH.md`**

## TODOs

### Introduce `TurnRuntimeContext` to separate runtime facts from prompt text

**一句话**：`PromptBundle` 承载可注入 prompt text（已是这样）；新增 `TurnRuntimeContext` 承载 turn-level runtime facts（`channel`、`implicit_signal_bundle`、IO sinks、langsmith parent run 等），从 35+ 个签名里抽出来收口。

**当前问题**：`implicit_signal_bundle: ImplicitSignalBundle | None` 在约 35 个函数签名里逐层透传（`turn.py` / `manager.py` / `prompt_stack.py` / `turn_pipeline.py` / `companion_chat_service.py` / `tool_background.py` / `system_messages.py` / `turn_track.py` / `implicit_signal_messages.py`）。`channel`（WS / WEIXIN / REPL）目前根本没有作为一等概念出现——各调用方在最外层默认知道自己是哪个 channel，但 harness 内部分不清。其他 runtime facts（`preset_user_msg_uuid` / `background_output_sink` / `tool_bg_idle_event` / `langsmith_parent_run_enabled` / `bootstrap_interim_output_sink`）也散布在每个 track entrypoint。

**目标字段**（B 档：宽收口）：

- `channel: ChannelKind`（**新概念**）—— StrEnum：`WS` / `WEIXIN` / `REPL`；外层调用方为 truth（`chat_ws.py` 传 `WS`，`weixin_channel/*` 传 `WEIXIN`，`tools/inty_v2_repl` 传 `REPL`）。
- `implicit_signal_bundle: ImplicitSignalBundle | None`
- `preset_user_msg_uuid: str | None`
- `background_output_sink: BackgroundToolEventSink | None`
- `tool_bg_idle_event: threading.Event | None`
- `langsmith_parent_run_enabled: bool | None`
- `bootstrap_interim_output_sink: BootstrapInterimOutputSink | None`

**故意不入** `TurnRuntimeContext`（这些是 turn-shape / per-call payload，不是 channel-scoped runtime fact）：`defer_memory_update`、`memory_config`、`transcript_compaction`、`transcript_llm_window_max_messages`、`repository_only_store_text`、`memory_bootstrap_type`、`scheduled_user_text`、track 本身（`CompanionTurnTrack`）。

**落地切片**（每步独立可合）：

1. 新增 `app/core/companion_harness/companion/turn_runtime_context.py`：`ChannelKind` StrEnum 与 `TurnRuntimeContext`（`@dataclass(frozen=True)`，runtime immutable value object，符合 `/AGENTS.md` 的"Pydantic 用于 I/O；frozen dataclass 用于进程内 immutable value object"）。
2. `turn.py` 内部 `_run_companion_turn_core` 与所有 `run_*_turn` 入口改为接收 `runtime: TurnRuntimeContext`；删除 6 个分散 kwarg。
3. `manager.py` 各 `run_*_turn` 方法签名收敛；`run_turn` 旧 delegator 接收 `runtime`。
4. `companion_chat_service.py` 各 `..._for_api` 入口收敛；上游调用方（`inner_tick_fire.py` 三个 `try_fire_*`、`chat.py` USER_MESSAGE 路径、`weixin_*` adapter、REPL）在最外层构造 `TurnRuntimeContext`。
5. `prompt_stack.py` / `system_messages.py` / `turn_pipeline.py` / `tool_background.py` 内部传递改用 `runtime`；`turn_track.py` 的 `track_from_legacy_flags` 接受 `runtime` 而非 `implicit_signal_bundle` 单参。

**Tests**：每切面跑一遍 `tests/app/core/companion_harness` + `tests/app/services/agentic_companion` 全套（当前 251 通过）；新增 `test_turn_runtime_context.py` 覆盖 `ChannelKind` 与构造校验。

**Risk**：`AGENTS.md` 已明确"DO NOT MAINTAIN BACKWARD COMPATIBILITY"，可直接换签名。但本仓涉及 hermes 等外部 adapter 调用，要确认所有调用点都改到（grep 兜底）。

**Trigger**：可由任一 P1 任务的后续 agent 拾起。AUTONOMY inner-tick（[PR #3224](https://github.com/NascentCore/inty/pull/3224)）已合入新 track 后，本重构的收益更明显——再多一个 track 就再多一份散落 runtime kwargs。
