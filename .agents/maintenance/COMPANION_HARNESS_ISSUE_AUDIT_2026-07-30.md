# Companion harness issue audit 2026-07-30

Cron consolidation run. Scope: companion harness issues + inline TODO refs.

## Summary

- Open repo issues: 270
- `agentic_companion` labeled: 193
- Stale (≥90d, no ready-*): 0
- Inline TODO-linked issue numbers in harness (block-aware): 76
- Orphan `TODO(tag)` blocks missing `#NNNN`: **0** (all anchored)
- World Engine epic subtree (#3700–#3712): 13 open issues

## Actions taken

- Ran `companion_harness_todo_issue_refs.py` — idempotent (0 new annotations).
- Ran `companion_harness_todo_audit.py` — 170 TODO lines scanned; 0 hygiene rows.
- No new `agentic_companion` issues since 2026-07-28; timezone user-reports already linked to canonical **#3391**.
- No stale close candidates; no duplicate merges executed this run.
- **No PR** — no companion harness code TODO line changes.

## New since 2026-07-28

| # | title | class | action |
|---|-------|-------|--------|
| — | — | — | No new companion issues |

## Lane notes (unchanged from 2026-07-28)

- Refactor gate baseline: `.agents/maintenance/COMPANION_HARNESS_REFACTOR_GATE_BASELINE.md`
- CRS / product_blocked / hygiene_defer lanes: no batch closes
- Channel parity pairs (#3441/#3442, #3451/#3452): intentional cross-channel duplicates, not merged
- Timezone user-reports (#3381, #3613, #3735, #3736, #3743, #3782, #3798): linked → **#3391**

## Closed-issue TODO refs (informational)

Open-issue audit cache shows 0 inline refs pointing at closed issues. Known redirects remain documented in `companion_harness_todo_audit.py` (`CLOSED_REDIRECTS`, `TAG_REDIRECTS`).
