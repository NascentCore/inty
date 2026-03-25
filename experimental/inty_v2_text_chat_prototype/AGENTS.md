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
5. **`CAPABILITIES.md`** — if non-empty. **Intrinsic limits** (human physiology/reality on the user side; model/channel/product constraints on the assistant side), not negotiated social boundaries (those live in `SOUL.md` / `USER.md`). Placed before persona files so hard constraints are seen first.
6. **`IDENTITY.md`**
7. **`SOUL.md`**
8. Context-mode clause (derived from `context.json`, not a file).
9. **`USER.md`**
10. **Only if `context_mode` is `intimate`**, and file has content (after caps):
   - `memory/daily/YYYY-MM-DD.md` (today’s raw diary)
   - `memory/YYYY-MM-DD.md` (today’s day summary)
   - **`MEMORY.md`** (long-term)
11. Output / tool contract (REPL adds `user_profile_record`, workspace file tools, and optional `generate_image` with context-inferred `num_images`, default 1).

Optional docs (2–4, 5) omitted entirely when missing or empty — no placeholder sections.

## Disk read order in `load_prompt_bundle`

Order differs from final prompt section order: implementation reads long-term **`MEMORY.md`** first and clears its body when not intimate; then reads **`IDENTITY` / `SOUL` / `USER`**, then optional **`CAPABILITIES` / `AGENTS` / `TOOLS` / `HEARTBEAT`**, and under intimate mode the two day-scoped memory paths (`memory/daily/…`, `memory/YYYY-MM-DD.md`). This is an implementation detail; **compatibility and semantics are defined by `build_system_prompt`**, not by read order.

## Transcript

- **`transcript.jsonl`** is **not** part of `PromptBundle`. It is loaded separately, truncated to the last `TRANSCRIPT_WINDOW_MAX_MESSAGES` entries, and appended **after** the system message as alternating user/assistant messages.
- Each line is JSON with `role`, `content`, `ts`, and (for lines written by `orchestrator.run_turn` after this feature) **`uuid`** (stable id for that message; used by `llm_trace` summaries to reference transcript rows without echoing body text). Older lines may omit `uuid`.

## Required files for a runnable workspace

Initialization checks (`is_workspace_initialized` / `run_turn`) require on disk:

`IDENTITY.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `transcript.jsonl`.

`AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`, `CAPABILITIES.md`, `context.json` are optional; missing `context.json` falls back to default `ContextMeta`.

## Workspace `AGENTS.md` (human-oriented)

The file may describe a **manual** startup habit: read **CAPABILITIES → SOUL → USER → (main session) MEMORY** when you want hard limits before persona (programmatic order injects optional `CAPABILITIES.md` **before** `IDENTITY.md`, after optional `AGENTS` / `TOOLS` / `HEARTBEAT`). That is guidance for agents/operators; it is **not** identical to `build_system_prompt` ordering (e.g. optional docs 2–4 still precede `CAPABILITIES` in the assembled prompt).
