# Refactor gate baseline — 2026-06-22

Recorded during issue/TODO cleanup plan execution. Gate is **NOT green**.

## Checklist status

| Item | Status |
|------|--------|
| Transport all channels enqueue+wake+OutputQueue | Partial — App-WS done (pull/3512); Weixin #3493 open |
| User chat only AgenticLoop (dual + single) | Partial — queue path on AgenticLoop; legacy turn.py still has live callers |
| Inner-tick tracks on single-LLM AgenticLoop | Open — #3580, #3459 |
| Dreaming unchanged (non-turn batch) | OK |
| Soft gate: no live turn.py orchestration | **Not met** — `_run_companion_turn_core` still active in turn.py |
| Memory phase CI | **Pass** |
| User-reported blockers | Open — see user_bug lane |

## Verification run

```
check_companion_turn_invariants.py — PASSED
test_harness_orchestration_scripted_llm.py — 7 passed
rg legacy turn orchestration — live callers in turn.py (expected until #3398 closes)
REPL regression — not run (requires Ops :8001)
```

## Next work (refactor lane)

1. #3493 Weixin enqueue+wake
2. #3542–#3543 inner-tick/output pump
3. #3580 maintenance/autonomy on AgenticLoop
4. Retire legacy turn.py branches per #3398

CRS (#3341) and product (#3323) remain **blocked** until this gate is green.
