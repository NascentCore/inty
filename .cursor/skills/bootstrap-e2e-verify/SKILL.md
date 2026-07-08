---
name: bootstrap-e2e-verify
description: >-
  Verify interactive bootstrap end-to-end on local Ops: unit tests, new agent,
  WS bootstrap conversation, Postgres MemoryDoc acceptance. Use when validating
  bootstrap harness changes, memory_store_write_document allowlist, or
  companion_bootstrap_user_interactive_complete behavior.
---

# Bootstrap E2E verify

Orchestration only — details live in linked skills / AGENTS.

## When

- Bootstrap tool/policy change (e.g. `USER_CHAT_BOOTSTRAP`, `BOOTSTRAP_WRITABLE_REL_PATHS`).
- Need proof: USER/IDENTITY/STYLE written, SOUL/MEMORY stay template seeds, `context.json` complete.

## Prereq

- Repo root cwd.
- Postgres **`localhost:15432`** / db **`inty`** — 与 `devops/config.yaml.local` **`database`** 一致（**假定已配好，勿改密码**）。
- Ops `:8001` up — [`launch-inty-backend`](../launch-inty-backend/SKILL.md)（`INTY_CONFIG_YAML=devops/config.yaml.local`；`start.sh` 自动 migrate；勿单独 `alembic upgrade head`；勿在此重复 `start.sh` 全文）。
- Bearer: [`.inty_ops_bearer_token`](../../../.inty_ops_bearer_token).

Domain: [`companion/AGENTS.md`](../../../app/core/companion_harness/companion/AGENTS.md) (bootstrap carve-outs).

## Steps

### 1. Unit tests

```bash
uv run pytest \
  tests/app/core/companion_harness/companion/test_bootstrap.py \
  tests/app/core/companion_harness/companion/test_bootstrap_transcript_order.py \
  tests/app/core/companion_harness/prompting/test_system_messages.py \
  tests/app/core/companion_harness/companion/test_system_messages.py \
  tests/app/core/companion_harness/tools/test_official_assistant_tool_loop.py \
  -q
```

Rules: [`tests/AGENTS.md`](../../../tests/AGENTS.md).

### 2. New agent

[`create-bootstrap-test-agent`](../create-bootstrap-test-agent/SKILL.md):

```bash
python3 tools/scripts/create_bootstrap_test_agent.py
```

Keep `agent_id`. Do not reuse old agent mid-bootstrap.

### 3. Run bootstrap (real LLM)

**Preferred — REPL** (multi-turn, human or partner):

```bash
python -m tools.inty_v2_repl.main repl \
  --api-base-url http://127.0.0.1:8001 \
  --agent-id <AGENT_ID>
```

- First WS: implicit sign-on greeting (no tools).
- Then user chat: model should `memory_store_write_document` → IDENTITY/STYLE/USER only; `companion_set_experience_profile` if mode chosen; `companion_bootstrap_user_interactive_complete` to finish.

Env/LangSmith: [`examine-local-inty-repl-env`](../examine-local-inty-repl-env/SKILL.md).

**Not full bootstrap** — WS one-turn smoke only: [`inty-server-module-verify`](../inty-server-module-verify/SKILL.md) (`test_chat_ws.py --create-agent`).

**Not full bootstrap** — pytest implicit sign-on only: `tests/app/features/test_companion_ws_bootstrap_e2e.py` (gated `INTY_COMPANION_WS_BOOTSTRAP_E2E=1`).

### 4. Accept in Postgres

Use `agent_id` as `companion_id`.

| Check | Where |
|-------|--------|
| `workspace_bootstrap_user_interactive_completed: true` | [`context-mode-in-db`](../inspect-companion-harness/context-mode-in-db/SKILL.md) |
| All MemDocs at a glance (`--meta-only`) | [`list-agent-documents`](../inspect-companion-harness/list-agent-documents/SKILL.md) |
| USER / identity / style customized | [`inspect-companion-harness`](../inspect-companion-harness/SKILL.md) — `document_kind` `user`, `identity`, `style` |
| SOUL / memory = package template, **one** `sequence_id` each | same skill; compare to `load_template_seed_text` in code |
| Optional transcript | `document_kind = transcript` (latest row) |

Optional LangSmith: [`langsmith-download-run`](../langsmith-download-run/SKILL.md) — search `memory_store_write_document`.

### 5. Terminate services launched during tests

- backend service instances
- cleanup temporary data created during tests

## Pass criteria (short)

- `context.json`: `workspace_bootstrap_user_interactive_completed` **true**.
- `identity` / `style` / `user`: body reflects conversation (not empty template stubs only).
- `soul` / `memory`: unchanged template seed; bootstrap allowlist must **not** add extra versions for SOUL.
- If profile set: `context_mode` matches chosen mode (e.g. `emotional_companion`).

## Report

1. pytest pass/fail
2. `agent_id`
3. bootstrap complete yes/no + which docs verified
4. LangSmith trace id if captured from REPL metadata — [`inspect-repl-message-metadata`](../inspect-repl-message-metadata/SKILL.md)
