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
6. **`CAPABILITIES.md`** — if non-empty. System-level **intrinsic limits** (human physiology/reality on the user side; model/channel/product constraints on the assistant side), placed before soul so persona (`SOUL`) is read in light of hard constraints; negotiated social boundaries still live primarily in `SOUL.md` / `USER.md`.
7. **`SOUL.md`**
8. Context-mode clause (derived from `context.json`, not a file).
9. **`USER.md`**
10. **Only if `context_mode` is `intimate`**, and file has content (after caps):
   - `memory/daily/YYYY-MM-DD.md` (today’s raw diary)
   - `memory/YYYY-MM-DD.md` (today’s day summary)
   - **`MEMORY.md`** (long-term)
11. Output / tool contract (REPL adds `user_profile_record` + workspace tool rules).

Optional docs (2–4, 6) omitted entirely when missing or empty — no placeholder sections.

## Disk read order in `load_prompt_bundle`

Order differs from final prompt section order: implementation reads long-term **`MEMORY.md`** first and clears its body when not intimate; then reads **`IDENTITY` / `SOUL` / `USER`**, then optional **`CAPABILITIES` / `AGENTS` / `TOOLS` / `HEARTBEAT`**, and under intimate mode the two day-scoped memory paths (`memory/daily/…`, `memory/YYYY-MM-DD.md`). This is an implementation detail; **compatibility and semantics are defined by `build_system_prompt`**, not by read order.

## Transcript

- **`transcript.jsonl`** is **not** part of `PromptBundle`. It is loaded separately, truncated to the last `TRANSCRIPT_WINDOW_MAX_MESSAGES` entries, and appended **after** the system message as alternating user/assistant messages.

## Required files for a runnable workspace

Initialization checks (`is_workspace_initialized` / `run_turn`) require on disk:

`IDENTITY.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `transcript.jsonl`.

`AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`, `CAPABILITIES.md`, `context.json` are optional; missing `context.json` falls back to default `ContextMeta`.

## Workspace `AGENTS.md` (human-oriented)

The file may describe a **manual** startup habit: read **CAPABILITIES → SOUL → USER → (main session) MEMORY** so hard limits precede persona, matching the spirit of programmatic order (optional workspace `AGENTS` / `TOOLS` / `HEARTBEAT` still come earlier in the actual system prompt when present). That is guidance for agents/operators; it is **not** identical to `build_system_prompt` ordering (e.g. optional docs 2–4 precede `IDENTITY` in the assembled prompt).
