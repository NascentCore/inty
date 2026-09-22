# Companion harness issue audit 2026-09-22

Cron consolidation run. Scope: companion harness issues + inline TODO refs.

## Summary

- Open repo issues: 273
- `agentic_companion` labeled: 193
- Stale close candidates (≥90d, no ready-*): 0 actionable this run (87 aged tickets remain informational; no spot-check fixes)
- Inline TODO-linked issue numbers in harness: 76 (block-aware)
- Orphan `TODO(tag)` blocks missing `#NNNN`: **0** (all anchored)
- World Engine epic subtree (#3700–#3712): 13 open issues (unchanged)

## Actions taken

- Ran `gh_issue_audit_json.sh` (273 open issues).
- Ran `companion_harness_todo_issue_refs.py` — idempotent (0 files, 0 lines).
- Ran `companion_harness_todo_audit.py` — passes (170 TODO lines, 0 hygiene rows, 0 closed-ref violations).
- All timezone user-reports (#3381, #3736, and prior linked dupes) already reference canonical **#3391**; no new user-reported timezone issues since 2026-09-10.
- No duplicate merges or stale closes executed this run.
- **No PR** — no companion harness TODO line changes in code.

## New since 2026-09-17

| # | title | class | action |
|---|-------|-------|--------|
| — | *(none)* | — | No new open issues since 2026-09-10 |

## Companion ticket activity (updated since 2026-09-17)

| # | updated | note |
|---|---------|------|
| 3375 | 2026-09-21 | Narrow monolog inner-tick — healthy |
| 3409 | 2026-09-20 | companion/ module reorg — healthy |
| 3453 | 2026-09-20 | PromptTemplate dataclass — healthy |
| 3521 | 2026-09-18 | MemDoc-projected prompt composition — healthy |

## Lane notes (unchanged)

- Refactor gate baseline: `.agents/maintenance/COMPANION_HARNESS_REFACTOR_GATE_BASELINE.md`
- `TRACKED_WORK.md` removed in #3583 — do not recreate
- Channel parity pairs (#3441/#3442, #3451/#3452): intentional cross-channel duplicates, not merged
- CRS / product_blocked / hygiene_defer lanes: no batch closes
