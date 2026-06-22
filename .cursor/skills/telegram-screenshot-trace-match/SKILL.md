---
name: telegram-screenshot-trace-match
description: >-
  Match a Telegram chat screenshot to LangSmith companion traces and Ops server
  logs: extract clock time and distinctive message snippets, scan
  agentic_companion_user_turn runs in a UTC window, rank by keyword hits and
  telegram channel metadata, then grep local/dev logs. Use when a Telegram
  conversation looks broken, wacky, or duplicated and you need backend traces
  or log correlation from a screenshot.
---

# Telegram screenshot → LangSmith trace + server logs

## Test / review status

**TESTED** (initial validation). **Effectiveness review pending** — use on real incidents; cleanup or extend the skill if gaps show up.

### Evidence (2026-06-22)

- Unit tests: `pytest tests/cursor/skills/scripts/test_telegram_screenshot_trace_match.py` — 7 passed (clock/window, snippet parse, scoring, child channel metadata).
- Live smoke: 2026-06-21 Joy ↔ 沈听言 Telegram wacky-chat on **`inty-backend-dev`** — screenshot clock `21:24` + keywords matched trace `019eea5a-5f48…` with correct `user_snippet` / `reply_snippet`.

### Agent report line

After running the helper, append one line:

- Match found: `[telegram-screenshot-trace-match] RESULT: TESTED (matches=N, top_trace=<trace_id>)`
- No match: `[telegram-screenshot-trace-match] RESULT: TESTED (matches=0)` — widen window/keywords per Troubleshooting before giving up.

### Effectiveness review (open — revisit after 2–3 real uses)

- **LangSmith rate limits** — broad windows + many keywords trigger 429; may need higher `--read-delay-seconds` or server-side name filter.
- **Log correlation** — local `.inty/inty.log` grep hints only; dev/prod VM (`gcplogs`) not automated.
- **Screenshot without clock** — workflow assumes bubble timestamp; fallback is manual date + transcript keyword only.
- **Generic keywords** — short/common snippets (e.g. `可以`) rank poorly; skill depends on distinctive snippets.
- **Prod project** — `inty-backend-prod` may be absent; confirm project name per deployment before searching.

When review concludes the skill is ineffective or redundant, shrink to manual workflow only or merge into [`langsmith-download-run`](../langsmith-download-run/SKILL.md).

## When to use

- User shares a **Telegram chat screenshot** and asks why replies are wrong, duplicated, or looping.
- You need **LangSmith trace IDs** and **Ops log grep hints** for a specific visible exchange.
- Channel is Ops **telegram-demo** (`runtime_channel=telegram` on dev/local/prod Ops).

## Inputs to extract from the screenshot

1. **Clock time** on bubbles (e.g. `21:24`) — use the **most distinctive turn** (not the whole session).
2. **Calendar date** if not today (ask or infer from context).
3. **2–4 distinctive snippets** — short unique substrings from user or bot lines (e.g. `batch`, `为什么来找我`, `黄金4帧`). Avoid generic words.
4. **Deployment hint** — usually `dev` (`dev.ops.inty.cc` → LangSmith project `inty-backend-dev`); local REPL smoke → `inty-backend-local-<username>`.

Timezone default: **`Asia/Shanghai`** unless user states otherwise.

## Preferred: helper script

Run from **repo root** with venv active:

```bash
source .venv/bin/activate

python .cursor/skills/scripts/telegram_screenshot_trace_match.py 21:24 \
  --date 2026-06-21 \
  --keyword batch \
  --keyword 为什么来找我 \
  --keyword 找你闲聊 \
  --environment-hint dev
```

Options (see `--help`):

- `--padding-minutes 15` — search window around screenshot clock (default 15).
- `--project-name inty-backend-dev` — override auto project pick (repeatable).
- `--require-telegram` / `--no-require-telegram` — filter by `inty_runtime_channel`.
- `--json` — machine-readable output for follow-up automation.
- `--read-delay-seconds 0.35` — reduce LangSmith 429 rate limits.

Script output includes **`trace_id`**, **`agent_id`**, **`user_id`**, **`user_snippet`**, **`reply_snippet`**, **`langsmith_url`**, and ready-made **`rg`** + **`download_run.py`** commands.

Helper script path: [`.cursor/skills/scripts/telegram_screenshot_trace_match.py`](../scripts/telegram_screenshot_trace_match.py)

## Manual workflow (if script unavailable)

1. **Resolve LangSmith project** — list projects; pick `inty-backend-dev` for dev Ops, or `inty-backend-local-<slug>` for local Ops. API key: `devops/config.yaml.local` → `agent.langchain_api_key`.
2. **Convert screenshot time → UTC window** — e.g. `21:24 Asia/Shanghai` on `2026-06-21` → `13:09–13:39 UTC` with ±15 min padding.
3. **List root runs** named `agentic_companion_user_turn` in the window (`is_root=True`, `limit=100`).
4. **Keyword-filter** — `read_run(id, load_child_runs=True)`; scan `inputs.messages` tail and child spans `agentic_companion_chat` / `tool_background_initial` for snippets.
5. **Confirm channel** — `extra.metadata.inty_runtime_channel == telegram`.
6. **Download full trace** — see [`langsmith-download-run`](../langsmith-download-run/SKILL.md):

   ```bash
   python .cursor/skills/scripts/download_run.py \
     --trace-id "<TRACE_UUID>" --project-name inty-backend-dev
   ```

## Server logs correlation

- **Local Ops** — `.inty/inty.log` (`INTY_LOG_FILE` from `backend/ops/start.sh`; default workspace `.inty` under repo root)
- **Dev/prod VM** — Docker `gcplogs` on GCP VM; SSH to Ops host; filter by `application=inty-backend` label

**Grep patterns** (after you have `trace_id` / `agent_id` from LangSmith):

```bash
rg -n '<trace_id>|<agent_id>|run_turn|telegram-demo|langsmith_trace_id' .inty/inty.log
```

Turn lifecycle log lines to expect: `run_turn loop_done`, `repl.turn.bg policy_summary`, `telegram-demo:` transport events.

Postgres transcript fallback (same agent): [`inspect-companion-harness`](../inspect-companion-harness/SKILL.md) — only when LangSmith retention expired or key mismatch.

## Analyze matched traces

Each user turn typically has **two LLM child spans**:

- `agentic_companion_chat` — foreground `user_facing_reply` → always delivered as first bubble when non-empty.
- `tool_background_initial` — may deliver a **second** bubble when `output_to_user: true`.

Duplicate Telegram bubbles often mean **both legs sent overlapping text** — compare both child `outputs` in the downloaded trace JSON under `.inty/langsmith_traces/`.

Track fixes:

- **issues/3596** — dual-LLM dedupe (foreground + tool_background overlapping downlink)
- **issues/3597** — in-session denial ignored (batch re-ask loop)
- Parent epic: **issues/3398**

## Troubleshooting

- **0 matches** — widen `--padding-minutes`; try `--environment-hint any`; verify date/timezone; drop `--keyword` to list all roots in window first.
- **429 LangSmith** — increase `--read-delay-seconds`; pass explicit `--project-name`; reduce keyword count.
- **Wrong project** — dev Telegram traffic is **`inty-backend-dev`**, not your local `-local-<user>` project unless Ops runs with `app.environment: local` on that machine.
- **Many inner-tick runs in window** — script paginates LangSmith root runs (100/page) until `--max-roots` user_turn spans are collected.

## Related skills

- [`langsmith-download-run`](../langsmith-download-run/SKILL.md) — archive trace JSON.
- [`inspect-companion-harness`](../inspect-companion-harness/SKILL.md) — MemoryStore / transcript in Postgres.
- [`telegram-demo-restore-smoke`](../telegram-demo-restore-smoke/SKILL.md) — binding + transport smoke.
