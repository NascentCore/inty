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
9. **Only if `context_mode` is `intimate`**, and file has content (after caps):
   - `memory/daily/YYYY-MM-DD.md` (today’s raw diary)
   - `memory/YYYY-MM-DD.md` (today’s day summary)
   - **`MEMORY.md`** (long-term)
10. Output / tool contract (REPL adds `user_profile_record`, workspace file tools, optional `google_web_search` (Google Custom Search API; env `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_ID`), optional `generate_image` (text-to-image) with context-inferred `num_images` (default 1), and optional `modify_image` (image-to-image) when editing an existing image).

`generate_image` at runtime uses the **Inty repo-root** `config.yaml` (`fal.api_key`, GCS settings) via `app.core.images.fal`; see [README.md](README.md). Optional env `INTY_V2_PROTO_Z_IMAGE_GCS_BASE` overrides the GCS object prefix; `INTY_V2_PROTO_Z_IMAGE_SKIP_GCS` skips GCS upload for faster local-only images.

Optional docs (2–4) omitted entirely when missing or empty — no placeholder sections.

## Disk read order in `load_prompt_bundle`

Order differs from final prompt section order: implementation reads long-term **`MEMORY.md`** first and clears its body when not intimate; then reads **`IDENTITY` / `SOUL` / `USER`**, then optional **`AGENTS` / `TOOLS` / `HEARTBEAT`**, and under intimate mode the two day-scoped memory paths (`memory/daily/…`, `memory/YYYY-MM-DD.md`). This is an implementation detail; **compatibility and semantics are defined by `build_system_prompt`**, not by read order.

## Day summary LLM cadence

- `memory/YYYY-MM-DD.md` is rewritten by a dedicated summarizer LLM only when `turns_completed % INTY_V2_PROTO_DAY_SUMMARY_EVERY_N_TURNS == 0` (default **100**). **`MEMORY.md`**, **`USER.md`**, and **`SOUL.md`** curator LLMs use the same `turns_completed` counter in **`.inty_v2_memory_pipeline.json`**, with defaults **100** turns each: `INTY_V2_PROTO_MEMORY_UPDATE_EVERY_N_TURNS`, `INTY_V2_PROTO_USER_UPDATE_EVERY_N_TURNS`, `INTY_V2_PROTO_SOUL_UPDATE_EVERY_N_TURNS` (set any to **1** for every turn). **`SOUL`** is also skipped when `INTY_V2_PROTO_SOUL_UPDATE_DISABLED` is set. Raw diary lines still append every turn (`memory/daily/…`). (`user_profile_record` may still append to `USER.md` any turn.)

## Transcript

- **`transcript.jsonl`** is **not** part of `PromptBundle`. It is loaded separately, then **`models.transcript_for_llm_turn`** keeps only the last `TRANSCRIPT_WINDOW_MAX_MESSAGES` entries for **both** normal user turns and **REPL 陪伴心跳** (`heartbeat_turn`), so proactive replies match the same on-screen conversation as normal turns. Appended **after** the system message as alternating user/assistant messages.
- Each line is JSON with `role`, `content`, `ts`, and (for lines written by `orchestrator.run_turn` after this feature) **`uuid`** (stable id for that message; used by `llm_trace` summaries to reference transcript rows without echoing body text). Older lines may omit `uuid`.
- REPL **陪伴心跳**（见 `main.repl` / `heartbeat_schedule.py`）：空闲达到节奏阈值时由程序合成一轮 `user` 行（`content` 为 `HEARTBEAT_SYNTHETIC_USER_TEXT`：要求读本窗口场景与语气**自然续接**，勿改换风格），可带 **`heartbeat`: true**；`build_system_prompt` 的「本轮（陪伴心跳）」段与此一致。该回合不跑记忆管线，且 API 不挂载工具。`heartbeat_schedule.next_heartbeat_wait_seconds(..., heartbeat_enabled=...)` 与 `--repl-heartbeat` / `--no-repl-heartbeat` 对齐；仅传环境变量时参数可省略。

## Required files for a runnable workspace

Initialization checks (`is_workspace_initialized` / `run_turn`) require on disk:

`IDENTITY.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `transcript.jsonl`.

`AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`, `context.json` are optional; missing `context.json` falls back to default `ContextMeta`. **`CAPABILITIES.md` is not read by the prototype** (REPL allowlist may still permit writing it as a normal root file if you use it manually).

## Workspace `AGENTS.md` (human-oriented)

The file may describe operator habits (e.g. which files to read before chatting). That is guidance for humans/agents; it is **not** required to match `build_system_prompt` ordering verbatim.
