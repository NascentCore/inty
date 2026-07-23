# Companion harness issue audit 2026-07-23

Cron consolidation run. Scope: companion harness issues + inline TODO refs.

## Summary

- Open repo issues: 316
- `agentic_companion` labeled: 193
- Stale (≥90d, no ready-*): 0
- Inline TODO-linked issue numbers in harness (block-aware): 86
- Orphan `TODO(tag)` blocks missing `#NNNN`: **0** (all anchored)
- World Engine epic subtree (#3700–#3712): 13 open issues

## Actions taken

- Ran `companion_harness_todo_issue_refs.py` — idempotent (0 files, 0 lines changed).
- Ran `companion_harness_todo_audit.py` — passes (170 TODO lines scanned, 0 hygiene rows).
- No new `agentic_companion` issues since 2026-07-21; no timezone user-reports to link (all prior dupes already consolidated → #3391).
- No stale close candidates; no duplicate merges executed this run.
- **No PR** — no companion harness code TODO line changes.

## New since 2026-07-21

None. Issue backlog unchanged since prior cron run.

## Lane notes (unchanged)

- Refactor gate baseline: `.agents/maintenance/COMPANION_HARNESS_REFACTOR_GATE_BASELINE.md`
- CRS / product_blocked / hygiene_defer lanes: no batch closes
- Channel parity pairs (#3441/#3442, #3451/#3452): intentional cross-channel duplicates, not merged
- Timezone user-reports (#3381, #3613, #3735, #3736, #3743, #3782, #3798): already linked to canonical #3391

## Closed-issue TODO refs (informational)

- `#3586` — referenced in `client_time_from_memory_store.py` (launch fallback removal); open, no agentic_companion label
- Known closed redirects (`#3463`→`#3801`, `#3400`→`#3817`) already retargeted in code per `companion_harness_todo_audit.py`
