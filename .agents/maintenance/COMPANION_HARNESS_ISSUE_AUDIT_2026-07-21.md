# Companion harness issue audit 2026-07-21

Cron consolidation run. Scope: companion harness issues + inline TODO refs.

## Summary

- Open repo issues: 316
- `agentic_companion` labeled: 193
- Stale (≥90d, no ready-*): 0
- Inline TODO-linked issue numbers in harness: 105
- Orphan `TODO(tag)` blocks missing `#NNNN`: **0** (all anchored)
- World Engine epic subtree (#3700–#3712): 13 open issues

## Actions taken

- Ran `companion_harness_todo_issue_refs.py` — idempotent (0 files, 0 lines).
- Ran `companion_harness_todo_audit.py` — 170 TODO lines scanned; 0 planned hygiene rows; no closed-issue ref violations.
- All timezone user-reports already linked to canonical **#3391** (#3381, #3613, #3647, #3735, #3736, #3743, #3782, #3798); #3649 disclosure tracked on **#3652**.
- No new `agentic_companion` issues since 2026-07-16.
- No stale close candidates; no duplicate merges executed this run.
- **No PR** — no companion harness code TODO line changes.

## New since 2026-07-16

None.

## Lane notes (unchanged from 2026-07-14)

- Refactor gate baseline: `.agents/maintenance/COMPANION_HARNESS_REFACTOR_GATE_BASELINE.md`
- CRS / product_blocked / hygiene_defer lanes: no batch closes
- Channel parity pairs (#3441/#3442, #3451/#3452): intentional cross-channel duplicates, not merged
- `TRACKED_WORK.md` removed in #3583 — tracking in GitHub + inline TODO refs only
