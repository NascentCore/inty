# Companion harness issue audit 2026-09-15

Cron consolidation run. Scope: companion harness issues + inline TODO refs.

## Summary

- Open repo issues: 273
- `agentic_companion` labeled: 193
- Stale close candidates: 0
- Inline TODO-linked issue numbers in harness: 76 (block-aware)
- Orphan `TODO(tag)` blocks missing `#NNNN`: **0** (all anchored)
- World Engine epic subtree (#3700–#3712): 13 open issues

## Actions taken

- Ran `companion_harness_todo_issue_refs.py` — idempotent (0 files, 0 lines changed).
- Ran `companion_harness_todo_audit.py` — passes (170 TODO lines, 0 hygiene rows, 0 closed-ref violations).
- All timezone user-reports (#3381, #3613, #3647, #3649, #3735, #3736, #3743, #3782, #3798) already linked to canonical **#3391**.
- No stale close candidates; no duplicate merges executed this run.
- **No PR** — no companion harness code TODO line changes.

## New since 2026-09-10

No new open issues created since 2026-09-10. Five existing `agentic_companion` tickets received updates (healthy, in-flight work):

| # | title | class | action |
|---|-------|-------|--------|
| 3629 | [Agentic companion] PromptPlan 端到端 typed prompt | healthy | updated 2026-09-14 |
| 3516 | [Agentic companion] Simplify scope turn serialization | healthy | updated 2026-09-14 |
| 3460 | Consolidate AgenticLoop direct user-turn modes | healthy | updated 2026-09-14 |
| 3453 | [Agentic companion] Define PromptTemplate dataclass | healthy | updated 2026-09-12 |
| 3409 | [Agentic companion] Reorganize companion/ flat modules | healthy | updated 2026-09-12 |

## Lane notes (unchanged)

- Refactor gate baseline: `.agents/maintenance/COMPANION_HARNESS_REFACTOR_GATE_BASELINE.md`
- CRS / product_blocked / hygiene_defer lanes: no batch closes
- Channel parity pairs (#3441/#3442, #3451/#3452): intentional cross-channel duplicates, not merged
- `TRACKED_WORK.md` removed in #3583 — do not recreate; tracking in GitHub + inline TODO refs
