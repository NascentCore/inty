# Workspace context loading — design spec

## CLI（`main.py`）

- `python -m tools.inty_v2_repl.main repl` **仅**连接 Inty `/api/v1/chat/ws`（`backend_chat_ws.BackendChatWsBridge`）；对话与 bootstrap 由服务端处理。
- 连接后首轮 **burst drain** 等服务端主动 kickoff：`INTY_V2_BACKEND_WS_KICKOFF_DRAIN_SEC`（默认 10，单位秒，上限 600；0 表示仅 `get_nowait` 一次）。POSIX 且 TTY 时在 `>` 等输入会 **侧带** 轮询 `try_pop_queued_chat`，晚到的聊天 JSON 也会打印；Windows / 非 TTY 仍为阻塞 `input()`。
- 默认 **全双工**（`INTY_V2_REPL_DUPLEX` 非 `0`/`false` 等）：`send_turn` 在单线程池里跑，主循环在等一轮时可 `select` 把下一**整行**排入队列；**有 in-flight 轮次时**不 `try_pop_queued_chat`（与 `BackendChatWsBridge` 共享 FIFO，避免抢帧）。`INTY_V2_REPL_DUPLEX=0` 回退为与旧版相同的主线程同步 `send_turn`。
- `--workspace` 只影响本进程的 **日志**（`inty_v2.log`）与 **`llm_trace.jsonl`** 路径，不是对话权威存储。

## Kernel re-export 架构

本 prototype 的核心数据类型和逻辑从 `app/core/agentic_kernel/companion/` (companion kernel) 导入:

| prototype 文件 | 来源 |
|---|---|
| `utc.py` | re-export `companion.utc` |
| `file_store.py` | re-export `companion.file_store` |
| `paths.py` | 继承 `companion.workspace.WorkspacePaths`(默认 `.inty_v2` 前缀) |
| `memory_store.py` | re-export `companion.memory_store` |
| `memory_store_registry.py` | adapter: 读 env vars, 委托 `companion.memory_registry` |
| `memory_update.py` | adapter: 读 `INTY_V2_PROTO_*` env vars 构建 `MemoryPipelineConfig`, 委托 `companion.memory_pipeline` |
| `models.py` | re-export `companion.models` + prototype 兼容 `load_prompt_bundle` |
| `prompts.py` | re-export `companion.prompts` |
| `inner_tick_schedule.py` | shim: 实现见 `companion.inner_tick_schedule` |
| `orchestrator.py` | REPL `run_turn`；transcript 组装/落盘用 `companion.turn_engine`；`is_workspace_initialized` 等仍委托 kernel |
| `tool_background.py` | shim: 实现见 `companion.tool_background`（输出队列与后台工具环） |

REPL 特有模块: `orchestrator.py`, `client.py`, `llm_trace`, `workspace_init_tools`（薄封装/历史路径）, `main` 等。媒体与检索工具实现已在 `companion`（`fal_z_image_tool`, `google_web_search`, `image_gate`, `schedule_queue`）；prototype 文件可能仍为 re-export 或 shim。

`openai_assistant_message_dict` 与 `TRANSCRIPT_MSG_UUID_KEY` 单一真源: `companion.message_format`（`turn_engine` / `turn` / `companion_tool_runtime` / REPL `llm_trace` 引用）。prototype `workspace_init_tools` 若仍导出同名字段，应与 kernel 保持一致。

改动核心逻辑时应修改 kernel(`app/core/agentic_kernel/companion/`), 本目录 shim 自动生效.

- _ws/ has:
  1. inty_v2.log (program logs)
  2. llm_trace.jsonl (llm invocations)
  3. transcript.jsonl (messages)

Scope: how `experimental/inty_v2_text_chat_prototype` assembles **one turn** of LLM context from a workspace directory (e.g. `_ws/`). Implementation: `orchestrator.run_turn` → `load_context_meta` + `load_prompt_bundle` + `load_transcript` + `models.transcript_for_llm_turn` → `build_system_prompt`.

## Control plane

- **`INTY_V2_PROTO_ASYNC_TOOL_BG`** — default **on** (unset): chat-first reply in `run_turn`, tool loop in background; set to `0`/`false`/`no`/`off` for synchronous tool loop (then `INTY_V2_PROTO_DUAL_LLM` can apply).
- **`context.json`** is read first (`load_context_meta`). Field **`context_mode`** holds the **experience profile id** (normalized lowercase). Private long-term and day-scoped memory files inject only when `experience_profile_injects_private_memory(context_mode)` is true (see `app/core/agentic_kernel/experience_profile.py` and `models.load_prompt_bundle`).
- **交互式 `run_turn` 驱动方**（单测或自写脚本在本地 workspace 上调用 `orchestrator.run_turn`，**不是**当前 Cyclopts `repl`）：在 **POSIX + TTY** 上常见模式为 **`run_turn` 跑在工作线程**、主线程 **`select` + `readline`** 排队输入（长工具调用时不阻塞输入）。TTY 上可用 **`readline` + `input()`** 缓解部分集成终端里 CJK 退格错位；**Windows / 非 TTY** 可退回 **`app.core.repl_input.spawn_stdin_line_reader`**。空闲时对 stdin **短超时 poll**，以便 **`source=tool_bg`** 等异步输出有机会刷出；泵路径需避免在用户编辑行中途打印破坏 TTY。`INTY_V2_PROTO_ASYNC_CHAT_FRONT_TIMEOUT_SEC`（默认 **600**）约束 `async_chat_tool_background` 前景 HTTP；超时 `run_turn` 抛 **`RuntimeError`**。
- **连续输入与取代（POSIX + TTY 泵路径）**：`run_turn` 执行中用户再输入非空行可触发协作式取消与 **`ReplTurnSuperseded`**（不落盘该轮）；**`tool_bg`** 经 `mark_tool_background_aborted(user_msg_uuid)` 作废等语义仍见 `orchestrator` / `tool_background`。Windows / 非 TTY 不保证与 POSIX 泵完全一致。

## System prompt order (what the model sees)

Authoritative assembly: `prompts.build_system_prompt`. Sections are joined with `\n\n---\n\n`.

1. **`AXIOM.md`** (package template via `workspace.get_imate_axiom_system_text`) — product axiom; omitted if file empty after strip.
2. Fixed security baseline (untrusted user input; respect SOUL/USER boundaries).
3. **`AGENTS.md`** — if non-empty.
4. **`TOOLS.md`** — if non-empty.
5. **`HEARTBEAT.md`** — if non-empty.
6. **`IDENTITY.md`**
7. **`SOUL.md`**
8. Context-mode clause (derived from `context.json`, not a file).
9. **`USER.md`**
10. **Only if the experience profile injects private memory** (`intimate`, `emotional_companion`, ...), and file has content (after caps):
   - `memory/daily/YYYY-MM-DD.md` (today’s raw diary)
   - `memory/YYYY-MM-DD.md` (today’s day summary)
   - **`MEMORY.md`** (long-term)
11. Output / tool contract (REPL adds `user_profile_record`, `schedule_task`, workspace file tools, `companion_set_experience_profile` (persist `context_mode` after explicit user confirmation), optional `google_web_search` (Google Custom Search API; env `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_ID`), optional `generate_image` (text-to-image) with context-inferred `num_images` (default 1), and optional `modify_image` (image-to-image) when editing an existing image).

`generate_image` at runtime uses the **Inty repo-root** `config.yaml` (`fal.api_key`, GCS settings) via `app.core.images.fal`; see [README.md](README.md). Optional env `INTY_V2_PROTO_Z_IMAGE_GCS_BASE` overrides the GCS object prefix; `INTY_V2_PROTO_Z_IMAGE_SKIP_GCS` skips GCS upload for faster local-only images.

Optional docs (3–5) omitted entirely when missing or empty — no placeholder sections.

## Disk read order in `load_prompt_bundle`

Order differs from final prompt section order: implementation reads long-term **`MEMORY.md`** first and clears its body when private memory is not injected for the profile; then reads **`IDENTITY` / `SOUL` / `USER`**, then optional **`AGENTS` / `TOOLS` / `HEARTBEAT`**, and when private memory injects the two day-scoped memory paths (`memory/daily/…`, `memory/YYYY-MM-DD.md`). This is an implementation detail; **compatibility and semantics are defined by `build_system_prompt`**, not by read order.

## Day summary LLM cadence

- `memory/YYYY-MM-DD.md` is rewritten by a dedicated summarizer LLM only when `turns_completed % INTY_V2_PROTO_DAY_SUMMARY_EVERY_N_TURNS == 0` (default **100**). **`MEMORY.md`**, **`USER.md`**, and **`SOUL.md`** curator LLMs use the same `turns_completed` counter in **`.inty_v2_memory_pipeline.json`**, with defaults **100** turns each: `INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS`, `INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS`, `INTY_V2_PROTO_SOUL_UPDATE_EVERY_N_TURNS` (set any to **1** for every turn). **`SOUL`** is also skipped when `INTY_V2_PROTO_SOUL_UPDATE_DISABLED` is set. Raw diary lines still append every turn (`memory/daily/…`). (`user_profile_record` may still append to `USER.md` any turn.)

## Transcript

- **`transcript.jsonl`** is **not** part of `PromptBundle`. It is loaded separately, then **`models.transcript_for_llm_turn`** keeps only the last `TRANSCRIPT_WINDOW_MAX_MESSAGES` entries for **both** normal user turns and **REPL 内在节拍** (`inner_tick_turn`), so proactive replies match the same on-screen conversation as normal turns. Loaded rows are appended **after** the assembled system prompt; `role` is usually `user` / `assistant`, with optional persisted **`system`** rows (e.g. markers) passed through to the API as additional `system` messages in history order.
- Each line is JSON with `role`, `content`, `ts`, and (for lines written by `orchestrator.run_turn` after this feature) **`uuid`** (stable id for that message; used by `llm_trace` summaries to reference transcript rows without echoing body text). Older lines may omit `uuid`. `role` may be `user`, `assistant`, or `system`. **`inner_tick`: true** on a user row marks the intrinsic-beat synthetic prompt; assistant rows may use **`source`: `inner_tick`**.
- **REPL 上下线**：`main.repl` 在进入交互循环前追加一行 `role=user` 且 **`presence`: `repl_online`**，随后立刻跑一轮 `run_turn(..., repl_online_ack_turn=True)`（合成 user 行 `REPL_ONLINE_ACK_USER_TEXT`，持久化时带 **`repl_online_ack`: true**），让助手**立即接话**；退出（含 quit / EOF / 正常离开循环）后追加 **`presence`: `repl_offline`**。`presence` / `repl_online_ack` 行**不算**真实用户输入；`inner_tick_schedule` 与 `models.transcript_without_trailing_presence_signals` 会忽略末尾仅含 `presence` 的 user 行以便判断末条是否为 assistant。`repl_online_ack` 轮**不跑**记忆管线。
- **`ai_private.md`**（可选，新 workspace 由 `bootstrap.init_workspace` 创建空文件）：内在活动自然语言载体；`ai_private_store` 提供进程内缓存、原子写盘，并通过 **`append_jsonl_with_db`** 写入 **`ai_private.jsonl`**（与 transcript 同 PG 流机制）。注入上限见 **`INTY_V2_PROTO_AI_PRIVATE_MAX_CHARS`**（默认与 `models.AI_PRIVATE_INJECT_MAX_CHARS` 一致）。`run_turn(inner_tick_turn=True)` 时在 system 中注入「内在活动」区块（见 `prompts.build_system_prompt`）。
- REPL **内在节拍**（`main._repl_interactive_loop` / `inner_tick_schedule.py`）：**`INTY_V2_PROTO_INNER_TICK_SEC`**（默认 90s）是主循环里单次 `select`/睡眠的**上限块**，也是「多久醒来再看一眼」的粒度，**不等于**两次内在节拍之间的真实间隔。**`INTY_V2_PROTO_INNER_TICK_MIN_GAP_SEC`**（默认 120s）才是**两次成功内在节拍**之间的最小间隔（由进程内 `last_inner_fire_mono` 与 `next_inner_tick_wait_seconds` 共同约束）。前置：末条为 assistant、transcript（经 `transcript_without_trailing_presence_signals`）不少于 **`INTY_V2_PROTO_INNER_TICK_MIN_TRANSCRIPT_MSGS`**（默认 2）。用户输入与到期 `schedule_task` **优先**。开关：**`INTY_V2_PROTO_INNER_TICK_ENABLED`**：未设置或空则默认开启；`0`/`false`/`no`/`off` 关闭（**不再**读取 `INTY_V2_PROTO_HEARTBEAT`）。**工具**：`run_turn(inner_tick_turn=True)` 使用 **`build_openai_repl_tools_inner_tick()`**（仅 `user_profile_record` 与 `workspace_*`），不含定时、联网、生图/改图、chat 输出格式工具；语义见 `prompts.build_system_prompt` 的「本轮（内在节拍）」与「内在节拍输出与工具契约」。内在节拍除内向整理外，还承担**轻推当下场景下一拍**与**适时软转场**（见该节「场景演化」），外显仍以一句为主。**`INTY_V2_PROTO_ASYNC_TOOL_BG` 开启时**，内在节拍仍走同步工具环（不启用 `async_chat_tool_background`），避免与「内向整理」语义冲突。
- **手工冒烟（可选）**：REPL 等到内在节拍触发后查看 `<workspace>/llm_trace.jsonl` 是否出现工具相关轮次（取决于模型是否发起 `user_profile_record` / `workspace_*`）。
- REPL 同时运行**非 LLM 驱动**的定时队列调度（见 `schedule_queue.py`）：`schedule_task` 写入 `.inty_v2_schedule_tasks.json` 后，后台线程按 `exec_time_utc <= now` 发出到期事件；主循环优先处理到期事件并注入一轮 synthetic user 给 `run_turn`。成功后任务标记 `fired`，失败按 backoff 重试。

## Required files for a runnable workspace

Initialization checks (`is_workspace_initialized` / `run_turn`) require on disk:

`IDENTITY.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `transcript.jsonl`.

`AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`, `context.json` are optional; missing `context.json` falls back to default `ContextMeta`. **`CAPABILITIES.md` is not read by the prototype** (REPL allowlist may still permit writing it as a normal root file if you use it manually).

## Workspace `AGENTS.md` (human-oriented)

The file may describe operator habits (e.g. which files to read before chatting). That is guidance for humans/agents; it is **not** required to match `build_system_prompt` ordering verbatim.
