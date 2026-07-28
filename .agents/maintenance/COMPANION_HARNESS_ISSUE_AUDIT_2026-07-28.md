# Companion harness issue audit 2026-07-28

Cron consolidation run. Scope: companion harness issues + inline TODO refs.

## Summary

- Open repo issues: 279
- `agentic_companion` labeled: 193
- Stale (≥90d, no ready-*): 22 (0 companion — all out-of-scope lanes: Android, security backlog, ops)
- Inline TODO-linked issue numbers in harness: 76
- Orphan `TODO(tag)` blocks missing `#NNNN`: **0** (all anchored)
- World Engine epic subtree (#3700–#3712): 13 open issues (unchanged)
- New `agentic_companion` issues since 2026-07-23: **0**

## Actions taken

- Ran `companion_harness_todo_issue_refs.py` — idempotent (0 new annotations).
- Ran `companion_harness_todo_audit.py` — 170 TODO lines scanned; 0 hygiene rows; no closed-issue refs.
- Timezone user-reports (#3381, #3736) already linked to canonical **#3391** (prior runs).
- No stale close candidates in companion lane; no duplicate merges executed this run.
- **No PR** — no companion harness code TODO line changes.

## New since 2026-07-23

None.

## Timezone lane (unchanged)

| # | title | class | action |
|---|-------|-------|--------|
| 3391 | User time context: inference hardening | healthy | canonical engineering ticket |
| 3381 | [user-reported] timezone wrong | duplicate | linked → #3391 |
| 3736 | [user-reported] assumed timezone/location | duplicate | linked → #3391 |
| 3411 | Telegram user timezone E2E smoke | healthy | open; channel acceptance slice |
| 3586 | Remove default_user_time_zone launch fallback | healthy | open; cleanup after #3391 lands |

## Stale issues (informational, out of scope)

22 repo-wide stale issues (≥90d, no ready-*); none carry `agentic_companion`. Domains: legacy Android bugs (#1694–#2372), security backlog (#171, #563–#565), ops (#2316), tooling (#283–#284), early backlog (#13–#30). No batch closes this run.

## Lane notes (unchanged from 2026-07-23)

- Refactor gate baseline: `.agents/maintenance/COMPANION_HARNESS_REFACTOR_GATE_BASELINE.md`
- CRS / product_blocked / hygiene_defer lanes: no batch closes
- Channel parity pairs (#3441/#3442, #3451/#3452): intentional cross-channel duplicates, not merged
- `TRACKED_WORK.md` removed in #3583 — tracking in GitHub + inline TODO refs only
