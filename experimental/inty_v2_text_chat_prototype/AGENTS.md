# Workspace context loading — design spec

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
| `heartbeat_schedule.py` | re-export `companion.heartbeat.HEARTBEAT_SYNTHETIC_USER_TEXT` + prototype 心跳调度逻辑 |
| `orchestrator.py` | `is_workspace_initialized` / `needs_startup_profile_inquiry` 委托 kernel |

REPL 特有模块(orchestrator / client / tool_background / fal_z_image_tool / google_web_search / llm_trace / image_gate / schedule_queue / workspace_init_tools 等)保留在本目录.

`workspace_init_tools.py` 中的 `openai_assistant_message_dict` 与 kernel `companion.turn.openai_assistant_message_dict` 逻辑相同; 如有变更需双改.

改动核心逻辑时应修改 kernel(`app/core/agentic_kernel/companion/`), 本目录 shim 自动生效.

- _ws/ has:
  1. inty_v2.log (program logs)
  2. llm_trace.jsonl (llm invocations)
  3. transcript.jsonl (messages)

Scope: how `experimental/inty_v2_text_chat_prototype` assembles **one turn** of LLM context from a workspace directory (e.g. `_ws/`). Implementation: `orchestrator.run_turn` → `load_context_meta` + `load_prompt_bundle` + `load_transcript` + `models.transcript_for_llm_turn` → `build_system_prompt`.

## Control plane

- **`INTY_V2_PROTO_ASYNC_TOOL_BG`** — default **on** (unset): chat-first reply in `run_turn`, tool loop in background; set to `0`/`false`/`no`/`off` for synchronous tool loop (then `INTY_V2_PROTO_DUAL_LLM` can apply).
- **`context.json`** is read first (`load_context_meta`). It drives **`context_mode`** (e.g. `intimate` vs other): when not intimate, long-term and day-scoped private memory files are **not** injected into the bundle (see `models.load_prompt_bundle`).
- **REPL stdin** (`main._repl_interactive_loop`): on **POSIX + TTY**, **`run_turn` runs in a worker thread** while the **main thread** uses **`select` + `readline`** to queue further lines (so long tool calls e.g. image gen do not block typing in integrated terminals). On **Windows / non-TTY**, falls back to **`app.core.repl_input.spawn_stdin_line_reader`** (daemon thread). When **idle** (no heartbeat / no schedule due), the loop **polls stdin on a short timeout** instead of blocking `readline` forever so **`source=tool_bg` async replies** can print as they arrive.

## System prompt order (what the model sees)

Authoritative assembly: `prompts.build_system_prompt`. Sections are joined with `\n\n---\n\n`.

1. Fixed security baseline (untrusted user input; respect SOUL/USER boundaries).
2. **`AGENTS.md`** — if non-empty.
3. **`TOOLS.md`** — if non-empty.
4. **`HEARTBEAT.md`** — if non-empty.
5. **`IDENTITY.md`**
6. **`SOUL.md`**
7. Context-mode clause (derived from `context.json`, not a file).
8. **`USER.md`**
9. **Only if `context_mode` is `intimate`**, and file has content (after caps):
   - `memory/daily/YYYY-MM-DD.md` (today’s raw diary)
   - `memory/YYYY-MM-DD.md` (today’s day summary)
   - **`MEMORY.md`** (long-term)
10. Output / tool contract (REPL adds `user_profile_record`, `schedule_task`, workspace file tools, optional `google_web_search` (Google Custom Search API; env `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_ID`), optional `generate_image` (text-to-image) with context-inferred `num_images` (default 1), and optional `modify_image` (image-to-image) when editing an existing image).

`generate_image` at runtime uses the **Inty repo-root** `config.yaml` (`fal.api_key`, GCS settings) via `app.core.images.fal`; see [README.md](README.md). Optional env `INTY_V2_PROTO_Z_IMAGE_GCS_BASE` overrides the GCS object prefix; `INTY_V2_PROTO_Z_IMAGE_SKIP_GCS` skips GCS upload for faster local-only images.

Optional docs (2–4) omitted entirely when missing or empty — no placeholder sections.

## Disk read order in `load_prompt_bundle`

Order differs from final prompt section order: implementation reads long-term **`MEMORY.md`** first and clears its body when not intimate; then reads **`IDENTITY` / `SOUL` / `USER`**, then optional **`AGENTS` / `TOOLS` / `HEARTBEAT`**, and under intimate mode the two day-scoped memory paths (`memory/daily/…`, `memory/YYYY-MM-DD.md`). This is an implementation detail; **compatibility and semantics are defined by `build_system_prompt`**, not by read order.

## Day summary LLM cadence

- `memory/YYYY-MM-DD.md` is rewritten by a dedicated summarizer LLM only when `turns_completed % INTY_V2_PROTO_DAY_SUMMARY_EVERY_N_TURNS == 0` (default **100**). **`MEMORY.md`**, **`USER.md`**, and **`SOUL.md`** curator LLMs use the same `turns_completed` counter in **`.inty_v2_memory_pipeline.json`**, with defaults **100** turns each: `INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS`, `INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS`, `INTY_V2_PROTO_SOUL_UPDATE_EVERY_N_TURNS` (set any to **1** for every turn). **`SOUL`** is also skipped when `INTY_V2_PROTO_SOUL_UPDATE_DISABLED` is set. Raw diary lines still append every turn (`memory/daily/…`). (`user_profile_record` may still append to `USER.md` any turn.)

## Transcript

- **`transcript.jsonl`** is **not** part of `PromptBundle`. It is loaded separately, then **`models.transcript_for_llm_turn`** keeps only the last `TRANSCRIPT_WINDOW_MAX_MESSAGES` entries for **both** normal user turns and **REPL 陪伴心跳** (`heartbeat_turn`), so proactive replies match the same on-screen conversation as normal turns. Loaded rows are appended **after** the assembled system prompt; `role` is usually `user` / `assistant`, with optional persisted **`system`** rows (e.g. markers) passed through to the API as additional `system` messages in history order.
- Each line is JSON with `role`, `content`, `ts`, and (for lines written by `orchestrator.run_turn` after this feature) **`uuid`** (stable id for that message; used by `llm_trace` summaries to reference transcript rows without echoing body text). Older lines may omit `uuid`. `role` may be `user`, `assistant`, or `system`.
- **REPL 上下线**：`main.repl` 在进入交互循环前追加一行 `role=user` 且 **`presence`: `repl_online`**，随后立刻跑一轮 `run_turn(..., repl_online_ack_turn=True)`（合成 user 行 `REPL_ONLINE_ACK_USER_TEXT`，持久化时带 **`repl_online_ack`: true**），让助手**立即接话**；退出（含 quit / EOF / 正常离开循环）后追加 **`presence`: `repl_offline`**。`presence` / `repl_online_ack` 行**不算**真实用户输入；陪伴心跳调度会忽略末尾仅含 `presence` 的 user 行（见 `models.transcript_without_trailing_presence_signals`）。`repl_online_ack` 轮**不跑**记忆管线（与陪伴心跳一致，避免把合成提示写入日记管线）。
- REPL **陪伴心跳**（见 `main.repl` / `heartbeat_schedule.py`）：空闲达到节奏阈值时由程序合成一轮 `user` 行（`content` 为 `HEARTBEAT_SYNTHETIC_USER_TEXT`：要求读本窗口场景与语气**自然续接**，勿改换风格），可带 **`heartbeat`: true**；`build_system_prompt` 的「本轮（陪伴心跳）」段与此一致。该回合不跑记忆管线，且 API 不挂载工具。`heartbeat_schedule.next_heartbeat_wait_seconds(..., heartbeat_enabled=...)` 与 `--repl-heartbeat` / `--no-repl-heartbeat` 对齐；仅传环境变量时参数可省略。
- REPL 同时运行**非 LLM 驱动**的定时队列调度（见 `schedule_queue.py`）：`schedule_task` 写入 `.inty_v2_schedule_tasks.json` 后，后台线程按 `exec_time_utc <= now` 发出到期事件；主循环优先处理到期事件并注入一轮 synthetic user 给 `run_turn`。成功后任务标记 `fired`，失败按 backoff 重试。

## Required files for a runnable workspace

Initialization checks (`is_workspace_initialized` / `run_turn`) require on disk:

`IDENTITY.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `transcript.jsonl`.

`AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`, `context.json` are optional; missing `context.json` falls back to default `ContextMeta`. **`CAPABILITIES.md` is not read by the prototype** (REPL allowlist may still permit writing it as a normal root file if you use it manually).

## Workspace `AGENTS.md` (human-oriented)

The file may describe operator habits (e.g. which files to read before chatting). That is guidance for humans/agents; it is **not** required to match `build_system_prompt` ordering verbatim.
