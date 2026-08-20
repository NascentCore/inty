# Companion harness issue audit 2026-08-20

Cron consolidation run. Scope: companion harness issues + inline TODO refs.

## Summary

- Open repo issues: 271
- `agentic_companion` labeled: 193
- Stale (≥90d, no ready-*): 1 (#3025)
- Inline TODO-linked issue numbers in harness: 86 (block-aware)
- Orphan `TODO(tag)` blocks missing `#NNNN`: **0** (all anchored)
- World Engine epic subtree (#3700–#3712): 13 open issues

## Actions taken

- Ran `gh_issue_audit_json.sh` → `.inty/issue_audit_all.json`
- Ran `companion_harness_todo_issue_refs.py` — **idempotent** (0 new annotations)
- Ran `companion_harness_todo_audit.py` — passes (170 TODO lines, 0 hygiene rows, 0 closed-ref violations)
- All timezone user-reports (#3381, #3736) already linked to canonical **#3391** (prior runs)
- No duplicate merges or stale closes executed this run
- **No PR** — no companion harness code TODO line changes

## New since 2026-08-18

| # | title | class | action |
|---|-------|-------|--------|
| 3887 | 【后端系统 Bug】Prod VM ENOSPC 复发防护 | healthy | out of harness scope (backend/ops) |
| 3888 | 【后端系统 Bug】OpenRouter 余额耗尽导致 Android 聊天 500 | healthy | out of harness scope (backend/ops) |
| 3889 | 【后端系统 Bug】Ops deploy CI checkout 前 grep config.yaml.dev | healthy | out of harness scope (backend/ops) |
| 3890 | 【后端系统 Bug】Certbot 死域名 lineage 导致 renew 失败 | healthy | out of harness scope (backend/ops) |

No new `agentic_companion` issues since 2026-08-18.

## Updated `agentic_companion` since 2026-08-13

| # | title | class | action |
|---|-------|-------|--------|
| 3453 | PromptTemplate dataclass for named-slot system slices | healthy | open; 15+ inline `#3453` refs in harness |
| 3460 | Consolidate AgenticLoop direct user-turn modes and OutputQueue | healthy | open; inline `#3460` in `prompt_builder.py`, `turn.py`, `loop/` |
| 3488 | AppWsChannelAdapter + one Coordinator per scope on presence | healthy | open; child of epic #3485; no inline TODO yet (WS infra) |

## Stale candidate (informational)

| # | title | class | reason | action |
|---|-------|-------|--------|--------|
| 3025 | LLM returns no outputs (LangSmith) | stale | ≥90d (updated 2026-05-20), no ready-* label | no close — needs spot-check / repro before batch close |

## Lane notes (unchanged)

- Refactor gate baseline: `.agents/maintenance/COMPANION_HARNESS_REFACTOR_GATE_BASELINE.md`
- CRS / product_blocked / hygiene_defer lanes: no batch closes
- Channel parity pairs (#3441/#3442, #3451/#3452): intentional cross-channel duplicates, not merged
- `TRACKED_WORK.md` removed in #3583 — tracking in GitHub + inline TODO refs only
