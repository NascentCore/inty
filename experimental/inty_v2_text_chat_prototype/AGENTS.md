# Workspace context loading — design spec

- _ws/ has:
  1. inty_v2.log (program logs)
  2. llm_trace.jsonl (llm invocations)
  3. transcript.jsonl (messages)

Scope: how `experimental/inty_v2_text_chat_prototype` assembles **one turn** of LLM context from a workspace directory (e.g. `_ws/`). Implementation: `orchestrator.run_turn` → `load_context_meta` + `load_prompt_bundle` + `load_transcript` + `models.transcript_for_llm_turn` → `build_system_prompt`.

## Control plane

- **`INTY_V2_PROTO_ASYNC_TOOL_BG`** — default **on** (unset): chat-first reply in `run_turn`, tool loop in background; set to `0`/`false`/`no`/`off` for synchronous tool loop (then `INTY_V2_PROTO_DUAL_LLM` can apply).
- **`context.json`** is read first (`load_context_meta`). It drives **`context_mode`** (e.g. `intimate` vs other): when not intimate, long-term and day-scoped private memory files are **not** injected into the bundle (see `models.load_prompt_bundle`).
- **REPL stdin** (`main._repl_interactive_loop`): on **POSIX + TTY**, **`run_turn` runs in a worker thread** while the **main thread** uses **`select` + `readline`** to queue further lines (so long tool calls e.g. image gen do not block typing in integrated terminals). On **Windows / non-TTY**, falls back to **`app.core.repl_input.spawn_stdin_line_reader`** (daemon thread).

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
9. **`MODES.md`** — if non-empty.
10. **Only if `context_mode` is `intimate`**, and file has content (after caps):
   - `memory/daily/YYYY-MM-DD.md` (today’s raw diary)
   - `memory/YYYY-MM-DD.md` (today’s day summary)
   - **`MEMORY.md`** (long-term)
11. Output / tool contract (REPL adds `user_profile_record`, `schedule_task`, workspace file tools, optional `google_web_search` (Google Custom Search API; env `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_ID`), optional `generate_image` (text-to-image) with context-inferred `num_images` (default 1), and optional `modify_image` (image-to-image) when editing an existing image).

`generate_image` at runtime uses the **Inty repo-root** `config.yaml` (`fal.api_key`, GCS settings) via `app.core.images.fal`; see [README.md](README.md). Optional env `INTY_V2_PROTO_Z_IMAGE_GCS_BASE` overrides the GCS object prefix; `INTY_V2_PROTO_Z_IMAGE_SKIP_GCS` skips GCS upload for faster local-only images.

Optional docs (2–4) omitted entirely when missing or empty — no placeholder sections.

## Disk read order in `load_prompt_bundle`

Order differs from final prompt section order: implementation reads long-term **`MEMORY.md`** first and clears its body when not intimate; then reads **`IDENTITY` / `SOUL` / `USER`**, then optional **`AGENTS` / `TOOLS` / `HEARTBEAT` / `MODES`**, and under intimate mode the two day-scoped memory paths (`memory/daily/…`, `memory/YYYY-MM-DD.md`). This is an implementation detail; **compatibility and semantics are defined by `build_system_prompt`**, not by read order.

## Day summary LLM cadence

- `memory/YYYY-MM-DD.md` is rewritten by a dedicated summarizer LLM only when `turns_completed % INTY_V2_PROTO_DAY_SUMMARY_EVERY_N_TURNS == 0` (default **100**). **`MEMORY.md`**, **`USER.md`**, and **`SOUL.md`** curator LLMs use the same `turns_completed` counter in **`.inty_v2_memory_pipeline.json`**, with defaults **100** turns each: `INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS`, `INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS`, `INTY_V2_PROTO_SOUL_UPDATE_EVERY_N_TURNS` (set any to **1** for every turn). **`SOUL`** is also skipped when `INTY_V2_PROTO_SOUL_UPDATE_DISABLED` is set. Raw diary lines still append every turn (`memory/daily/…`). (`user_profile_record` may still append to `USER.md` any turn.)

## Transcript

- **`transcript.jsonl`** is **not** part of `PromptBundle`. It is loaded separately, then **`models.transcript_for_llm_turn`** keeps only the last `TRANSCRIPT_WINDOW_MAX_MESSAGES` entries for **both** normal user turns and **REPL 陪伴心跳** (`heartbeat_turn`), so proactive replies match the same on-screen conversation as normal turns. Appended **after** the system message as alternating user/assistant messages.
- Each logical line is one or more concatenated JSON objects; `models.load_transcript` decodes every object on the line and keeps `role` in `user` / `assistant` / `system` (others skipped). **`models.transcript_for_llm_turn`** and **`heartbeat_schedule`** use **`transcript_chat_rows`** so only `user`/`assistant` count toward the sliding window and heartbeat gating. Fields: `content`, `ts` (alias `timestamp`), and (for rows written by `orchestrator.run_turn` after this feature) **`uuid`**. Older rows may omit `uuid`.
- REPL **陪伴心跳**（见 `main.repl` / `heartbeat_schedule.py`）：空闲达到节奏阈值时由程序合成一轮 `user` 行（`content` 为 `HEARTBEAT_SYNTHETIC_USER_TEXT`：要求读本窗口场景与语气**自然续接**，勿改换风格），可带 **`heartbeat`: true**；`build_system_prompt` 的「本轮（陪伴心跳）」段与此一致。该回合不跑记忆管线，且 API 不挂载工具。`heartbeat_schedule.next_heartbeat_wait_seconds(..., heartbeat_enabled=...)` 与 `--repl-heartbeat` / `--no-repl-heartbeat` 对齐；仅传环境变量时参数可省略。**尚无 `BOOSTRAPED` 且 `IDENTITY.md`/`USER.md` 仍像模板桩时**不触发陪伴心跳、也不处理到期 `schedule_task` 队列事件（`orchestrator.repl_heartbeat_suppressed_for_workspace_bootstrap`），避免与模板 bootstrap opening 重叠。
- REPL 同时运行**非 LLM 驱动**的定时队列调度（见 `schedule_queue.py`）：`schedule_task` 写入 `.inty_v2_schedule_tasks.json` 后，后台线程按 `exec_time_utc <= now` 发出到期事件；主循环优先处理到期事件并注入一轮 synthetic user 给 `run_turn`。成功后任务标记 `fired`，失败按 backoff 重试。

## Required files for a runnable workspace

Initialization checks (`is_workspace_initialized` / `run_turn`) require on disk:

`IDENTITY.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `transcript.jsonl`.

REPL 启动时先 `ensure_workspace_skeleton`（从包内 `templates/` 补缺，不覆盖已有文件）。当 `needs_workspace_template_bootstrap` 为真（无 **`BOOSTRAPED`**、五件套已齐、transcript 尚无 user/assistant、IDENTITY/USER 仍像桩）时，首屏与后续每轮用户输入均走 `run_turn`：在 **`is_workspace_bootstrap_complete` 为假** 期间使用 `template_bootstrap_turn_system_prompt`（`BOOSTRAP.md` + canonical 包内四份人格模板 + 安全前缀），不跑记忆管线；模型与用户交互式填模板后写入空文件 **`BOOSTRAPED`** 即结束该阶段。`bootstrap_agent` CLI 仍使用 `run_workspace_bootstrap_loop` 作为非交互批处理入口。

在 **`BOOSTRAPED` 尚未存在** 时，每次启动 opening 或每条用户输入对应的 `run_turn` 结束后，若仍不完整，REPL 会按 `workspace_init_loop.repl_bootstrap_continue_user_message` 自动注入 synthetic user，在 `WORKSPACE_BOOTSTRAP_MAX_LLM_ROUNDS` 上限内继续调用 `run_turn`，语义与 `run_workspace_bootstrap_loop` 的内部续跑对齐，避免模型无正文结束时空白无追问。

`AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`, `context.json` are not required by `is_workspace_initialized`; missing `context.json` falls back to default `ContextMeta`. **`AGENTS.md`** default body is copied from package `templates/` by `ensure_workspace_skeleton` / `init_workspace` and injected when non-empty (same char cap as other optional root docs). **`MODES.md`** is optional: not copied from package templates; if present and non-empty it is loaded like other optional root docs. **`CAPABILITIES.md` is not read by the prototype** (REPL allowlist may still permit writing it as a normal root file if you use it manually).

## Workspace `AGENTS.md` (human-oriented)

The file may describe operator habits (e.g. which files to read before chatting). That is guidance for humans/agents; it is **not** required to match `build_system_prompt` ordering verbatim.
