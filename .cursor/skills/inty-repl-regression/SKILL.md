---
name: inty-repl-regression
description: >-
  Run local Inty REPL regression for companion harness queue-serving changes:
  bootstrap completion, settled USER_CHAT, proactive inner tick, OutputQueue/InputQueue,
  LangSmith prompt inputs, and known legacy greeting issues. Use when validating
  AgenticLoop, OutputQueue, bootstrap, proactive chat, or local REPL smoke behavior.
---

# Inty REPL Regression

## Goal

Verify a local Ops + `inty_v2_repl` session end-to-end enough to catch companion harness regressions across:

- bootstrap queue path
- settled `USER_CHAT`
- proactive inner tick
- durable InputQueue / OutputQueue delivery
- LangSmith prompt inputs

## Prereq

- Repo root cwd.
- Ops `:8001` running with `INTY_CONFIG_YAML=devops/config.yaml.local` — see [`launch-inty-backend`](../launch-inty-backend/SKILL.md).
- REPL environment sane — see [`examine-local-inty-repl-env`](../examine-local-inty-repl-env/SKILL.md).
- Create a fresh bootstrap agent — see [`create-bootstrap-test-agent`](../create-bootstrap-test-agent/SKILL.md).

## Run

### Automated driver (queue / DB / proactive smoke)

Helper: [`.cursor/skills/scripts/run_inty_repl_regression.py`](../scripts/run_inty_repl_regression.py). Repository root cwd; uses the same WebSocket transport as REPL.

```bash
python3 tools/scripts/create_bootstrap_test_agent.py
python3 .cursor/skills/scripts/run_inty_repl_regression.py \
  --agent-id <AGENT_ID> \
  --api-base http://127.0.0.1:8001
```

Or create agent and run in one step:

```bash
python3 .cursor/skills/scripts/run_inty_repl_regression.py \
  --create-agent \
  --api-base http://127.0.0.1:8001
```

- Default exit **0** when settled queue turn passes and InputQueue / OutputQueue rows are all `delivered` (bootstrap completion is LLM-dependent; reported but not required).
- Pass `--strict` to also require `workspace_bootstrap_user_interactive_completed` and inner-tick proactive.
- Proactive idle is ~30s base + 60s poll — use `--proactive-wait-sec 180` when bootstrap + proactive are required (`--strict`).
- JSON report: `tmp/repl-regression-<AGENT_ID>.json` unless `--report` is set.
- Skips `meta_data.source=greeting` downlinks when waiting for proactive (post-restart sign-on is not inner-tick proactive).

### Manual REPL (bootstrap quality judgment)

```bash
python -m tools.inty_v2_repl.main repl \
  --api-base-url http://127.0.0.1:8001 \
  --agent-id <AGENT_ID>
```

Drive the session:

1. Wait for `user_signed_on_ack` and greeting.
2. Complete bootstrap with short realistic turns:
   - ask identity / language preference
   - give user name
   - give assistant name
   - define relationship preference
3. Ask the agent to call `companion_bootstrap_user_interactive_complete` (automated driver sends a bootstrap-finish turn).
4. Continue after bootstrap with at least one settled user turn.
5. Let one proactive tick fire, or inspect the latest existing proactive metadata if already fired.

## DB Checks

Use `agent_id` as `companion_id`; local user is usually `user-testing`.

```sql
SELECT DISTINCT user_id, chat_id
FROM companion_memory_document_versions
WHERE companion_id = '<AGENT_ID>'
ORDER BY user_id, chat_id;
```

Prefer the `agent-scope:user-testing:<AGENT_ID>` scope for REPL queue-serving state.

```sql
SELECT sequence_id,
       created_at,
       trim(content)::json->>'context_mode' AS context_mode,
       trim(content)::json->>'workspace_bootstrap_user_interactive_completed' AS bootstrap_completed
FROM companion_memory_document_versions
WHERE companion_id = '<AGENT_ID>'
  AND user_id = 'user-testing'
  AND chat_id = 'agent-scope:user-testing:<AGENT_ID>'
  AND document_kind = 'context_json'
  AND calendar_date IS NULL
ORDER BY sequence_id DESC
LIMIT 5;
```

```sql
SELECT status, COUNT(*)
FROM agentic_companion_input_queue
WHERE agent_id = '<AGENT_ID>'
GROUP BY status;

SELECT status, COUNT(*)
FROM agentic_companion_output_queue
WHERE agent_id = '<AGENT_ID>'
GROUP BY status;
```

Inspect latest OutputQueue rows:

```sql
SELECT sequence_id, status, batch_id, left(text, 120) AS text_preview,
       langsmith_trace_id, langsmith_run_id, created_at
FROM agentic_companion_output_queue
WHERE agent_id = '<AGENT_ID>'
ORDER BY sequence_id DESC
LIMIT 10;
```

## LangSmith Checks

Download runs with [`langsmith-download-run`](../langsmith-download-run/SKILL.md).

For settled `USER_CHAT` default dual mode:

- parent trace lane should be `explicit_user_message`
- foreground run should be `agentic_companion_chat`
- tool-background initial run may exist
- only foreground-visible OutputQueue text should be delivered unless tool background intentionally emits a follow-up

For proactive:

- lane should be `inner_tick`
- run name usually `agentic_companion_chat`
- inputs should contain:
  - `## Proactive Messaging` system message
  - current tail user message with `[SYSTEM PROACTIVE CHAT] Time since...`
  - historical proactive synthetic user rows when still in transcript window
- `[SILENT]` is a valid output.
- When assistant output is `[SILENT]`, no WS downlink is sent; strict mode still passes if `chat_history` has a synthetic `[SYSTEM PROACTIVE CHAT]` user row for this agent after the run started (driver checks DB after the proactive wait).

## Pass Criteria

- `context.json` latest agent-scope row has `workspace_bootstrap_user_interactive_completed = true`.
- Latest `context_mode` is the expected settled mode, often `emotional_companion`.
- USER / IDENTITY / STYLE / COMPANIONSHIP have non-template bootstrap content.
- InputQueue rows for the run are all `delivered`.
- OutputQueue rows for user-visible replies are all `delivered`.
- Settled user turn produces one coherent delivered reply.
- Proactive LLM input includes the synthetic proactive user marker.
- LangSmith run ids in REPL metadata match delivered OutputQueue rows where applicable.

## Known Non-Blocking Findings

- Proactive currently can fire during bootstrap; record it separately unless the task is to change that behavior.
- Implicit sign-on greeting is legacy non-queue path and may hit LLM timeout after backend restart; do not treat that as AgenticLoop / OutputQueue failure.
- A dual-mode tool-background initial run can produce natural text internally without being delivered; verify OutputQueue before calling it user-visible duplication.
- One queue-served user turn may deliver multiple `source=chat` WS frames (AgenticLoop interim / multi-round tool output); the driver drains trailing downlinks after each turn (up to turn timeout) and records any late `source=chat` frames during proactive wait — they were already delivered on the WebSocket, not withheld by the backend.

## Report

Reply with:

- `agent_id`
- bootstrap: complete / incomplete
- settled queue turn: pass / fail
- proactive prompt marker: present / missing
- InputQueue / OutputQueue status counts
- key LangSmith trace/run ids
- blockers vs known non-blocking findings
