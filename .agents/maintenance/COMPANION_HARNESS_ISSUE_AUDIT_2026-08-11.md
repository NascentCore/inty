# Companion harness issue audit 2026-08-11

Cron consolidation run. Scope: companion harness issues + inline TODO refs.

## Summary

- Open repo issues: 267
- `agentic_companion` labeled: 193
- Stale (≥90d, no ready-*): 0
- Inline TODO-linked issue numbers in harness (block-aware): 86
- Orphan `TODO(tag)` blocks missing `#NNNN`: **0** (all anchored)
- World Engine epic subtree (#3700–#3712): 13 open issues

## Actions taken

- Ran `companion_harness_todo_issue_refs.py` — idempotent (0 new annotations).
- Ran `companion_harness_todo_audit.py` — passes (170 TODO lines, 0 hygiene rows, 0 closed-ref violations).
- No new open or updated `agentic_companion` issues since 2026-08-06.
- Timezone user-reports (#3381, #3613, #3736, #3782, #3798) already linked to canonical **#3391**.
- No stale close candidates; no duplicate merges executed this run.
- **No PR** — no companion harness code TODO line changes.

## New since 2026-08-06

None.

## Lane notes (unchanged from 2026-08-06)

- Refactor gate baseline: `.agents/maintenance/COMPANION_HARNESS_REFACTOR_GATE_BASELINE.md`
- CRS / product_blocked / hygiene_defer lanes: no batch closes
- Channel parity pairs (#3441/#3442, #3451/#3452): intentional cross-channel duplicates, not merged
- `TRACKED_WORK.md` removed in #3583 — do not recreate; tracking in GitHub + inline TODO refs
