---
name: inty-repl-regression
description: >-
  Run local Inty REPL regression over app-ws (/api/v1/chat/ws): bootstrap, settled USER_CHAT,
  GitHub issue from user complaint, proactive inner tick, InputQueue/OutputQueue, LangSmith.
  Canonical E2E for user-facing harness features (Telegram/Weixin excluded).
---

# Inty REPL Regression

## Scope

- **E2E channel:** app-ws only — `inty_v2_repl` and the automated driver use `/api/v1/chat/ws` (same as iMate app WebSocket path).
- **Not in this harness:** Telegram, Weixin, and other IM gateways (no practical client simulation today).
- **Feature rule:** new user-facing non-trivial features should add a phase to [`.cursor/skills/scripts/run_inty_repl_regression.py`](../scripts/run_inty_repl_regression.py) (GitHub user-feedback issue is the template).

## Goal

Verify a local Ops + `inty_v2_repl` session end-to-end enough to catch companion harness regressions across:

- bootstrap queue path
- settled `USER_CHAT`
- user complaint → `companion_record_user_feedback` → real GitHub issue (then auto-closed)
- proactive inner tick
- durable InputQueue / OutputQueue delivery
- LangSmith prompt inputs

## Prereq

- Repo root cwd.
- Postgres **`localhost:15432`** / db **`inty`** — 与 `devops/config.yaml.local` **`database`** 一致（**假定已配好，勿改密码**）。
- Ops `:8001` running — see [`launch-inty-backend`](../launch-inty-backend/SKILL.md)（`INTY_CONFIG_YAML=devops/config.yaml.local`；`start.sh` **自动 migrate**；勿单独 `alembic upgrade head`）。
  - Start: `./backend/ops/start.sh --local --no-build-frontend`（仓库根、已激活 venv）。
  - **勿**给 uvicorn 加 `--reload`：文件变更触发的进程重启会断开 WS、打断 queue/proactive 等待，导致回归 flaky；`start.sh --local` 已不带 reload。
- REPL environment sane — see [`examine-local-inty-repl-env`](../examine-local-inty-repl-env/SKILL.md).
- Create a fresh bootstrap agent — see [`create-bootstrap-test-agent`](../create-bootstrap-test-agent/SKILL.md).
- **GitHub issue phase (mandatory for pass):** `gh` CLI authenticated for `nascentcore/inty`; token in `devops/config.yaml.local` → `agent.companion_harness.user_feedback_github.token`, or `GH_TOKEN`.

## Run

### Automated driver (queue / DB / proactive / github issue smoke)

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

- Exit **0** only when settled queue turn passes, bootstrap is complete (`workspace_bootstrap_user_interactive_completed`), **github_issue_e2e** passes, inner-tick proactive is present, and InputQueue / OutputQueue rows are all `delivered`.
- GitHub issues created by the regression run are **closed automatically** in driver cleanup (`gh issue close`).
- Proactive idle uses `agent.companion_harness.inner_tick.proactive_chat.base_idle_seconds` (**10s**, config minimum) and `poll_seconds` (**3s**) in `devops/config.yaml.local`. Driver flags:
  - `--proactive-wait-sec` (**120** default): wall-clock listen duration after github_issue phase
  - `--proactive-min-rounds` (**1** default): **pass gate** — at least this many proactive rounds (WS and/or DB)
  - `--proactive-target-rounds` (**2** default): stretch goal in summary only; **does not fail** the run
- A **silent first proactive** (`output_to_user=false`) leaves the transcript without an assistant reply, so the scheduler will **not** fire a second round until a visible proactive happens — waiting longer cannot fix that.
- JSON report: `tmp/repl-regression-<AGENT_ID>.json` unless `--report` is set (`report.github_issue` has issue number/URL and `closed: true`).
- Skips `meta_data.source=greeting` downlinks when waiting for proactive (post-restart sign-on is not inner-tick proactive).
- Unit tests for DB/JSONL parsers: `tests/cursor/skills/scripts/test_run_inty_repl_regression.py` (skill script is not an `app/` module).

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
5. Send a complaint and ask the agent to file it with `companion_record_user_feedback` (same wording as driver `_DEFAULT_GITHUB_ISSUE_TURN`); confirm acknowledgment.
6. Let one proactive tick fire, or inspect the latest existing proactive metadata if already fired.

Automated driver remains the pass/fail gate; manual REPL is optional sanity check.

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
- silent proactive = structured `output_to_user=false` → no WS downlink; regression still passes if `chat_history` has a synthetic `[SYSTEM PROACTIVE CHAT]` user row without an assistant reply (driver checks DB; `silent: true`). Legacy `[SILENT]` in any preview fails the run.
- Two-round stretch (`proactive_target_rounds: met`) only happens when round 1 is **visible** (assistant reply) and idle elapses before wait ends.

## Pass Criteria

- `context.json` latest agent-scope row has `workspace_bootstrap_user_interactive_completed = true`.
- Latest `context_mode` is the expected settled mode, often `emotional_companion`.
- USER / IDENTITY / STYLE / COMPANIONSHIP have non-template bootstrap content.
- InputQueue rows for the run are all `delivered`.
- OutputQueue rows for user-visible replies are all `delivered`.
- Settled user turn produces one coherent delivered reply.
- **GitHub issue E2E:** complaint turn produces feedback JSONL `snapshot` + `github_issue_created`; `gh issue view` validates title/labels/body; issue closed in cleanup (`summary.github_issue_e2e: pass`).
- Proactive LLM input includes the synthetic proactive user marker; **≥1 proactive round** (`proactive_inner_tick: present`); no `[SILENT]` token (`proactive_no_silent_token: pass`). Optional stretch: `proactive_target_rounds: met` when the model speaks on round 1.
- LangSmith run ids in REPL metadata match delivered OutputQueue rows where applicable.

## Known Non-Blocking Findings

- Proactive currently can fire during bootstrap; record it separately unless the task is to change that behavior.
- Implicit sign-on greeting is legacy non-queue path and may hit LLM timeout after backend restart; do not treat that as AgenticLoop / OutputQueue failure.
- A dual-mode tool-background initial run can produce natural text internally without being delivered; verify OutputQueue before calling it user-visible duplication.
- One queue-served user turn may deliver multiple `source=chat` WS frames (AgenticLoop interim / multi-round tool output); the driver drains trailing downlinks after each turn (up to turn timeout) and records any late `source=chat` frames during proactive wait — they were already delivered on the WebSocket, not withheld by the backend.

## Cleanup（Agent 必做）

若你为本轮回归**自行拉起** Ops，测完按 [`launch-inty-backend`](../launch-inty-backend/SKILL.md) **Terminate Ops** 停掉；汇报中说明 **`:8001` 是否空闲**。勿终止用户会话开始时已在运行的 Ops。

## Report

Reply with:

- `agent_id`
- bootstrap: complete / incomplete
- settled queue turn: pass / fail
- github_issue_e2e: pass / fail (issue # if created)
- proactive prompt marker: present / missing
- InputQueue / OutputQueue status counts
- key LangSmith trace/run ids
- blockers vs known non-blocking findings
