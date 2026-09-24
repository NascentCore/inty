# Companion harness issue audit 2026-09-24

Cron consolidation run. Scope: companion harness issues + inline TODO refs.

## Summary

- Open repo issues: 273
- `agentic_companion` labeled: 193
- Stale close candidates (companion): 0
- Inline TODO-linked issue numbers in harness: 94 (grep); block-aware audit via `companion_harness_todo_audit.py`
- Orphan `TODO(tag)` blocks missing `#NNNN`: **0** (all anchored; multiline refs OK)
- World Engine epic subtree (#3700–#3712): 13 open issues (unchanged)

## Actions taken

- Ran `gh_issue_audit_json.sh` → `.inty/issue_audit_all.json`
- Ran `companion_harness_todo_issue_refs.py` — idempotent (`0 files, 0 lines`)
- `companion_harness_todo_audit.py` passes (170 TODO lines, 0 hygiene rows, 0 closed-ref violations)
- No new open issues since 2026-09-10; no timezone user-reports needing link to **#3391**
- No duplicate merges or closes executed this run
- **No PR** — no companion harness TODO line changes in code files

## Updated since 2026-09-22 (existing tickets)

| # | title | class | action |
|---|-------|-------|--------|
| 3375 | Narrow monolog inner-tick to ai_private.jsonl appearance | healthy | open; tracked |
| 3409 | Reorganize companion/ flat modules into companion_* packages | healthy | open; tracked |
| 3453 | Define PromptTemplate dataclass for named-slot prompts | healthy | open; tracked |
| 3460 | Consolidate AgenticLoop direct user-turn modes and OutputQueue | healthy | open; tracked |
| 3835 | [Cleanup] Large functions to be broken down | healthy | out of inline-TODO scope |

## Lane notes (unchanged)

- Refactor gate baseline: `.agents/maintenance/COMPANION_HARNESS_REFACTOR_GATE_BASELINE.md`
- CRS / product_blocked / hygiene_defer lanes: no batch closes
- Channel parity pairs (#3441/#3442, #3451/#3452): intentional cross-channel duplicates, not merged
- Timezone user-reports (#3381, #3613, #3647, #3649, #3735, #3736, #3743, #3782, #3798): already linked **#3391**
