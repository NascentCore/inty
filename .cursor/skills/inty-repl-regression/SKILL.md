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

- implicit sign-on greeting (`IMPLICIT_SIGN_ON_GREETING`, `meta_data.source=greeting`)
- bootstrap queue path + MemoryDoc writes (`USER.md` / `IDENTITY.md` / `STYLE.md`; SOUL/MEMORY stay seed)
- `companion_set_experience_profile` → settled `context_mode` (default `emotional_companion`, casual_chat intent)
- settled `USER_CHAT`
- user complaint → `companion_record_user_feedback` → real GitHub issue (then auto-closed)
- proactive inner tick
- scope-worker dreaming consolidation → `MEMORY.md` update (fast `dreaming_idle_seconds: 10` in local config); default **one-shot curator** (`agent.companion_harness.dreaming_curator_mode: one_shot`) — single LLM request with parallel `update_dreaming_document` tool calls and explicit `content_changed=false` no-op for unchanged docs; rollback with `sequential`
- durable InputQueue / OutputQueue delivery
- LangSmith prompt inputs

## Prereq

- Repo root cwd.
- **Reset config before this phase:** in any reused shell, run `export INTY_CONFIG_YAML=devops/config.yaml.regression_tests` immediately before starting Ops and before invoking the driver. Do not rely on a previous `INTY_CONFIG_YAML` from pytest/CI or local REPL work.
- Postgres **`localhost:15432`** / db **`inty`** — 与 `devops/config.yaml.regression_tests` **`database`** 一致（**假定已配好，勿改密码**）。
- Ops `:8001` running — see [`launch-inty-backend`](../launch-inty-backend/SKILL.md)（**回归专用** `INTY_CONFIG_YAML=devops/config.yaml.regression_tests`；`start.sh --local` **默认** `config.yaml.local`，回归前须 **export**；`start.sh` **自动 migrate**；勿单独 `alembic upgrade head`）。
  - Start: `export INTY_CONFIG_YAML=devops/config.yaml.regression_tests && ./backend/ops/start.sh --local --no-build-frontend`（仓库根、已激活 venv）。
  - **勿**给 uvicorn 加 `--reload`：文件变更触发的进程重启会断开 WS、打断 queue/proactive 等待，导致回归 flaky；`start.sh --local` 已不带 reload。
- REPL environment sane — see [`examine-local-inty-repl-env`](../examine-local-inty-repl-env/SKILL.md).
- Create a fresh bootstrap agent — see [`create-bootstrap-test-agent`](../create-bootstrap-test-agent/SKILL.md).
- **GitHub issue phase (mandatory for pass):** `gh` CLI authenticated for `nascentcore/inty`; token in `devops/config.yaml.regression_tests` → `agent.companion_harness.user_feedback_github.token`, or `GH_TOKEN`.

## Run

### Automated driver (queue / DB / proactive / github issue smoke)

Helper: [`.cursor/skills/scripts/run_inty_repl_regression.py`](../scripts/run_inty_repl_regression.py). Repository root cwd; uses the same WebSocket transport as REPL.

Run `python3 .cursor/skills/scripts/run_inty_repl_regression.py --help` for the full flag reference and the live `--target` preset table (epilog generated from `_target_presets()`, the same function the driver runs — cannot drift from runtime behavior).

**`--target` is required.** It resolves `api_base`, config YAML, DB verification mode, and turn scope together.

Local (export config before Ops **and** regression driver sets the same preset):

```bash
export INTY_CONFIG_YAML=devops/config.yaml.regression_tests
backend/ops/start.sh --local --no-build-frontend

python3 .cursor/skills/scripts/run_inty_repl_regression.py \
  --target local \
  --create-agent
```

- After this phase, reset `INTY_CONFIG_YAML` before running other tests. Backend CI / pytest must run with `INTY_CONFIG_YAML=devops/config.yaml.test`; leaving `devops/config.yaml.regression_tests` in the shell can make unrelated tests fail on regression-only limits, Telegram bot config, or fake-GCS paths.

Dev (full turn sequence; DB-dependent checks reported as `skipped`; GitHub issue verified via WS text + `gh` CLI):

```bash
python3 .cursor/skills/scripts/run_inty_repl_regression.py \
  --target dev \
  --create-agent \
  --login-email test1@sxwl.ai \
  --login-password '<password>'
```

Prod (health check only — no bootstrap MemDoc writes, no complaint/GitHub issue turn):

```bash
python3 .cursor/skills/scripts/run_inty_repl_regression.py \
  --target prod \
  --create-agent \
  --login-email <your-prod-account> \
  --login-password '<password>'
```

- `--login-email` / `--login-password` (optional pair): obtain bearer token via `POST /api/v1/auth/google/login` and write to `--token-file`. Required for remote targets unless a valid token file already exists.
- `--api-base`, `--config`, `--proactive-*`, `--dreaming-wait-sec` still override preset defaults when explicitly set.
- Remote runs (`dev`, `prod`) skip direct Postgres per `devops/README.md`; skipped DB bits do not fail the pass gate.
- Remote `--create-agent`: before POST create, driver **purges** owned agents whose `name` starts with `bootstrap-test-` via `GET /api/v1/ai/agents/me` + `DELETE /api/v1/ai/agents/{id}`. Delete cascades ACTIVE companion bond to `INACTIVE` on the server (requires deployed backend with bond deactivate on `delete_agent`). If a user's ACTIVE bond is on a **non**-`bootstrap-test-*` agent, purge will not clear it — delete that agent manually or resolve the bond before re-running.
- **Deploy dependency:** dev/prod smoke for `--create-agent` needs the Ops image that includes `delete_agent` bond cascade; updating only the regression script against an older backend still leaves bonds ACTIVE after purge.
- Exit **0** when **infra gate** passes with no warnings; **1** when the gate passes but ``summary.warnings`` is non-empty (human partner review); **2** when the gate fails or CLI args are invalid. Implemented in #3793; WARNINGS stdout aligned with actual exit in #3807.
- **`github_issue_disclosed_in_chat`**, **`proactive_target_rounds`**, **`dreaming_one_shot`**, and **`github_tool_native`** live under `summary.eval` (telemetry). They are no longer exit-code gates.
- GitHub issues created by the regression run are **closed automatically** in driver cleanup (`gh issue close`).
- Local full run target wall-clock: **~3–4 minutes** (9+ live LLM turns dominate; proactive DB early-exit and settle quiet 8s reduce fixed waits).
- Proactive idle uses `agent.companion_harness.inner_tick.proactive_chat.base_idle_seconds` (**10s**, config minimum) and `poll_seconds` (**3s**) in `devops/config.yaml.regression_tests`. Dreaming uses `agent.companion_harness.dreaming_idle_seconds` (**10s** locally; default prod **7200s**). Scope-worker dreaming batches can take several minutes; avoid parallel regression runs that backlog the worker.
- A **silent first proactive** (`output_to_user=false`) leaves the transcript without an assistant reply, so the scheduler will **not** fire a second round until a visible proactive happens — waiting longer cannot fix that.
- JSON report: `tmp/repl-regression-<AGENT_ID>.json` unless `--report` is set (`report.github_issue` has issue number/URL and `closed: true`).
- Skips `meta_data.source=greeting` downlinks when waiting for proactive (post-restart sign-on is not inner-tick proactive).
- Unit tests for DB/JSONL parsers and one-shot dreaming verification helpers (`_required_paths_from_dreaming_llm_inputs`, `_evaluate_dreaming_one_shot_tool_calls`): `tests/cursor/skills/scripts/test_run_inty_repl_regression.py` (skill script is not an `app/` module).

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
5. Send a complaint and ask the agent to file it with `companion_record_user_feedback` (same wording as driver `_DEFAULT_GITHUB_ISSUE_TURN`); with `app.debug: true`, the WS reply should include the GitHub issue URL prepended by the harness. With `app.debug: false`, users only see empathetic acknowledgment (issue still created server-side).
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

### Infra gate（决定 exit 0 / 1 / 2）

- exit **0**：infra gate 全 pass 且 ``summary.warnings`` 为空
- exit **1**：infra gate pass 但存在 warning（如 dreaming checkpoint 已写入、MEMORY.md LLM no-op）— 需 human partner 查阅
- exit **2**：infra gate fail 或参数错误

- `meta_data.source=greeting` on at least one implicit sign-on WS downlink after connect.
- `context.json` latest agent-scope row has `workspace_bootstrap_user_interactive_completed = true`.
- Latest `context_mode` is the expected settled mode after experience-profile phase (default **`emotional_companion`**).
- Experience-profile phase uses a **natural casual-chat user message** (no harness meta-instruction or explicit tool names). It validates the `companion_set_experience_profile` pipeline, not the roleplay-specific system clause (roleplay path covered by harness unit tests).
- USER / IDENTITY / STYLE have non-template bootstrap content (`大雄` / `多啦` markers); SOUL / MEMORY remain template seed (`sequence_id=1`).
- InputQueue rows for the run are all `delivered`.
- OutputQueue **user-visible** rows are all `delivered` (`agent-initiated:inner_tick` **skipped** rows allowed; `summary.output_user_visible_delivered: pass`).
- Settled user turn produces one coherent delivered reply.
- **GitHub issue pipeline:** complaint turn produces feedback JSONL + issue created; `gh issue view` validates; issue closed in cleanup (`summary.github_issue_e2e: pass`). In-process tool fallback allowed.
- Proactive **infra:** **≥1** synthetic `[SYSTEM PROACTIVE CHAT]` row in DB (`proactive_inner_tick: present`); no `[SILENT]` token leak (`proactive_no_silent_token: pass`).
- **Dreaming consolidation:** `.companion_dreaming_state.json` checkpoint required; `MEMORY.md` update is **warn** (LLM `content_changed=false` no-op) not fail when checkpoint saved (`summary.dreaming_consolidation: warn`).

### Eval telemetry（`summary.eval`，report-only，不 block exit 0）

- **`github_tool_native`:** model called `companion_record_user_feedback` vs in-process fallback.
- **`github_issue_disclosed_in_chat`:** when `app.debug: true`, WS-visible chat includes issue URL (`pass` / `fail` / `skipped`).
- **`proactive_target_rounds`:** stretch `met` / `miss` (silent-first round blocks a 2nd until visible reply).
- **`dreaming_one_shot`:** LangSmith one-shot tool-call shape (`pass` / `fail` / `skipped`).
- **`proactive_visible_rounds` / `proactive_silent_rounds`:** round counts.

LangSmith run ids in REPL metadata match delivered OutputQueue rows where applicable (informational).

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
- **infra gate** (exit 0/1/2): bootstrap, greeting, memdocs, experience_profile, settled turn, queue delivery (`output_user_visible_delivered`), github pipeline, proactive infra, dreaming checkpoint (MEMORY no-op → warning)
- **`summary.warnings`**: human-review items (dreaming MEMORY no-op, bootstrap memdoc drift, etc.)
- **`summary.eval`**: github_tool_native, github_issue_disclosed_in_chat, proactive_target_rounds, dreaming_one_shot, proactive round counts
- InputQueue / OutputQueue status counts
- key LangSmith trace/run ids
- blockers vs known non-blocking findings
