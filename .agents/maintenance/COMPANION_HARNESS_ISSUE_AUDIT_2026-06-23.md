# Companion harness issue audit 2026-06-23

Cron consolidation run (`github-issue-consolidate` skill). Scope: `agentic_companion` label + `app/core/companion_harness/` TODO anchors.

## Snapshot

| Metric | Value |
|--------|-------|
| Open `agentic_companion` issues | 139 (after closes) |
| TODO lines in harness scope | 201 |
| TODO lines with `#NNNN` / `!NNNN` refs | 196 |
| Unique issue numbers referenced in code | 68 |
| New issues since 2026-06-22 | 11 filed → 9 remain open after this run |

## Actions taken (2026-06-23)

| # | title | class | action |
|---|-------|-------|--------|
| 3619 | AI hallucinated feature extraction + lied about tickets | duplicate | **closed** → canonical #3617 |
| 3600 | Proactive inner-tick structured output vs `[SILENT]` | fixed | **closed** → PR #3607 |
| 3617 | Fabricated task + false ticket claims | healthy | comment — honesty/capability lane |
| 3613 | Timezone ignored (US west coast) | healthy | comment → canonical #3391, related #3381 |
| 3596 | Dual-LLM duplicate Telegram bubbles | healthy | comment → parent #3398, sibling #3597 |
| 3593 | Google CSE env missing (weather search) | healthy | comment — ops/config lane |
| 3601 | Split SCHEDULED vs PROACTIVE_CHAT activity | healthy | comment — code anchors |
| 3602 | SDK `completions.parse` spike | healthy | comment — follow-up to #3600 |

## New issues since 2026-06-22 (remaining open)

| # | title | lane | TODO in code |
|---|-------|------|--------------|
| 3593 | Google CSE env not configured | ops/config | no |
| 3596 | Dual-LLM dedupe overlapping downlink | refactor (#3398) | no |
| 3597 | In-session denial ignored (batch re-ask) | user-reported (#3398) | no |
| 3601 | Split INNER_TICK_SCHEDULED activity | refactor | yes (#3601) |
| 3602 | OpenAI SDK completions.parse | enhancement | yes (#3602) |
| 3605 | Telegram English reply launch gate | ops | no |
| 3606 | REPL driver vs LLM eval split | test | no |
| 3613 | Timezone wrong (user-testing) | user-reported → #3391 | yes (#3391, #3586) |
| 3617 | Fabricated task + lying about tickets | user-reported | no |

## TODO hygiene

- `python3 .cursor/skills/scripts/companion_harness_todo_issue_refs.py` — **idempotent, 0 changes** (all tagged TODOs mapped).
- 5 intentional bare TODO mentions remain in docs/meta text (not `TODO(tag)` anchors).
- `TRACKED_WORK.md` intentionally removed (#3583); tracking lives in GitHub + inline `TODO(tag) — #NNNN`.

## Carry-forward from 2026-06-22 audit

All approved close/comment actions from the 2026-06-22 audit are complete (duplicate epics #3162/#3295/#3296/#3511/#3566–#3568 closed; blocked/deferred lanes commented).

## Next cron checks

- Watch #3617 for triage → possible epic for honesty/capability-boundary harness rules
- #3596 + #3597 may merge AC if dual-LLM dedup fix addresses both symptoms
- Re-run audit after #3485 refactor gate milestones
