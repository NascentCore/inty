# Workspace context loading — design spec

Scope: how `experimental/inty_v2_text_chat_prototype` assembles **one turn** of LLM context from a workspace directory (e.g. `_ws/`). Implementation: `orchestrator.run_turn` → `load_context_meta` + `load_prompt_bundle` + `load_transcript` → `build_system_prompt`.

## Control plane

- **`context.json`** is read first (`load_context_meta`). It drives **`context_mode`** (e.g. `intimate` vs other): when not intimate, long-term and day-scoped private memory files are **not** injected into the bundle (see `models.load_prompt_bundle`).

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
10. Output / tool contract (REPL adds `user_profile_record` + workspace tool rules).

Optional docs (2–4) omitted entirely when missing or empty — no placeholder sections.

## Disk read order in `load_prompt_bundle`

Order differs from final prompt section order: implementation reads **`MEMORY.md`** early, clears long-term body when not intimate, then reads **`IDENTITY` / `SOUL` / `USER`**, then optional **`AGENTS` / `TOOLS` / `HEARTBEAT`**, and under intimate mode the two day-scoped memory paths. This is an implementation detail; **compatibility and semantics are defined by `build_system_prompt`**, not by read order.

## Transcript

- **`transcript.jsonl`** is **not** part of `PromptBundle`. It is loaded separately, truncated to the last `TRANSCRIPT_WINDOW_MAX_MESSAGES` entries, and appended **after** the system message as alternating user/assistant messages.

## Required files for a runnable workspace

Initialization checks (`is_workspace_initialized` / `run_turn`) require on disk:

`IDENTITY.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `transcript.jsonl`.

`AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`, `context.json` are optional; missing `context.json` falls back to default `ContextMeta`.

## Workspace `AGENTS.md` (human-oriented)

The file may describe a **manual** startup habit: read **SOUL → USER → (main session) MEMORY**. That is guidance for agents/operators; it is **not** the same ordering as the programmatic system prompt (where AGENTS/TOOLS/HEARTBEAT precede IDENTITY when present).
