# Companion harness issue audit 2026-07-09

Cron consolidation run. Scope: companion harness issues + inline TODO refs.

## Summary

- Open repo issues: 364
- `agentic_companion` labeled: 193
- Stale (≥90d, no ready-*): 0
- Inline TODO-linked issue numbers in harness: 104
- Orphan `TODO(tag)` blocks missing `#NNNN`: **0** (all anchored)
- World Engine epic subtree (#3700–#3712): 13 open issues

## Actions taken

- Ran `companion_harness_todo_issue_refs.py` (idempotent after cleanup); `companion_harness_todo_audit.py` passes (176 TODO lines, 0 hygiene rows).
- Removed stale `TODO(bootstrap-cohort-overlays)` in `system_messages.py` — work shipped via closed #3628; retained docstring note on PromptBuilder wiring.
- Linked timezone user-reports **#3782**, **#3798** to canonical **#3391** (prior runs: #3381, #3735, #3736, #3743).
- No stale close candidates; no duplicate merges executed this run.
- **PR** — companion harness TODO hygiene (`system_messages.py`).

## New since 2026-07-07

| # | title | class | action |
|---|-------|-------|--------|
| 3773 | [CRS] 关系信号 append-only 事件底册与 CQRS 折叠投影 | healthy | open; inline TODO `#3773` in `dreaming_consolidation.py` |
| 3774 | [CRS] MemDoc 信念结构化 provenance | healthy | open; inline TODOs `#3774` in `memdoc_frontmatter.py`, `system_messages.py` |
| 3775 | [Eval] 离线 fork/diff 反事实评测原语 | healthy | open; inline TODO `#3775` in `retrieval.py` |
| 3782 | [user-reported] timezone: US West Coast vs Asia/Shanghai | duplicate | linked → #3391 |
| 3798 | [user-reported] timezone: US West Coast | duplicate | linked → #3391 |
| 3801 | Bootstrap prompt single-source policy | healthy | open; successor to closed #3463; inline `#3801` |
| 3817 | rename-memory-doc follow-ups | healthy | open; inline `#3817` |
| 3819 | [Epic] agentic_companion — productionization | healthy | new epic |
| 3804–3810 | [Ops SMS] channel slice | healthy | SMS epic subtree (out of harness scope) |

## Closed-issue TODO refs (informational)

Open-issue audit cache does not flag closed refs. Known closed targets still cited in harness (prior redirects documented in `companion_harness_todo_audit.py`):

- `#3463` → `#3801` (bootstrap single-source) — already retargeted in code
- `#3400` / `#3413` → `#3817` (rename-memory-doc) — already retargeted in code
- `#3628` (bootstrap-cohort-overlays) — TODO removed this run (shipped)
- `#3632` (tool-bg-inline-agentic-loop) — closed; no orphan tag lines remain

## Lane notes (unchanged from 2026-07-07)

- Refactor gate baseline: `.agents/maintenance/COMPANION_HARNESS_REFACTOR_GATE_BASELINE.md`
- CRS / product_blocked / hygiene_defer lanes: no batch closes
- Channel parity pairs (#3441/#3442, #3451/#3452): intentional cross-channel duplicates, not merged
