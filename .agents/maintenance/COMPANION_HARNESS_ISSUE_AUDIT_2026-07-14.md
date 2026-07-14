# Companion harness issue audit 2026-07-14

Cron consolidation run. Scope: companion harness issues + inline TODO refs.

## Summary

- Open repo issues: 317
- `agentic_companion` labeled: 193
- Stale (≥90d, no ready-*): 0
- Inline TODO-linked issue numbers in harness: 105
- Orphan `TODO(tag)` blocks missing `#NNNN`: **0** (all anchored)
- World Engine epic subtree (#3700–#3712): 13 open issues

## Actions taken

- Ran `companion_harness_todo_issue_refs.py` — idempotent (0 new annotations).
- Ran `companion_harness_todo_audit.py` — 170 TODO lines scanned; 0 planned hygiene rows; no closed-ref violations.
- Exported issue caches: `/tmp/gh_issues_open.json` (317 open), `.inty/issue_audit_all.json` (500 recent all-state).
- No new open `agentic_companion` issues since #3819 (last run).
- Timezone user-reports #3381, #3613, #3647, #3649, #3735, #3736, #3743, #3782, #3798 already linked to canonical **#3391** (prior runs).
- Closed timezone dupes **#3821**, **#3823** (2026-07-08) — closed by inty-repl-regression cleanup; no harness TODO impact.
- No stale close candidates; no duplicate merges executed this run.
- **No PR** — no companion harness code TODO line changes.

## New since 2026-07-09

| # | title | class | action |
|---|-------|-------|--------|
| 3821 | [user-reported] timezone: US West Coast vs Shanghai inference | duplicate | closed (repl-regression cleanup) |
| 3823 | [user-reported] timezone: assistant ignored user timezone | duplicate | closed (repl-regression cleanup) |
| 3835 | [Cleanup] Large functions to be broken down | out-of-scope | open; `cleanup` label only, not harness |

## Closed-issue TODO refs (informational)

Open-issue audit cache does not flag closed refs. Known closed targets still cited in harness (redirects in `companion_harness_todo_audit.py`):

- `#3463` → `#3801` (bootstrap single-source) — already retargeted in code
- `#3400` / `#3413` → `#3817` (rename-memory-doc) — already retargeted in code
- `#3628` (bootstrap-cohort-overlays) — TODO removed 2026-07-09 (shipped)
- `#3632` (tool-bg-inline-agentic-loop) — closed; no orphan tag lines remain

## Lane notes (unchanged from 2026-07-09)

- Refactor gate baseline: `.agents/maintenance/COMPANION_HARNESS_REFACTOR_GATE_BASELINE.md`
- CRS / product_blocked / hygiene_defer lanes: no batch closes
- Channel parity pairs (#3441/#3442, #3451/#3452): intentional cross-channel duplicates, not merged
- Productionization epic **#3819** and CRS follow-ups **#3773–#3775** remain healthy open tickets with inline TODO anchors
