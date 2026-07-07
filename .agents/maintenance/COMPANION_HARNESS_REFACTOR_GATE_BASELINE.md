# Refactor gate baseline — 2026-07-07

Recorded during Companion Harness partial-convergence plan (Stage 1 PR-5 + Stage 2).

## Checklist status

| Item | Status |
|------|--------|
| Transport all channels enqueue+wake+OutputQueue | Partial — App-WS done (pull/3512); Weixin #3493 open |
| User chat only AgenticLoop (dual + single) | **Met** — all turn tracks require ``agentic_output_queue``; legacy turn.py orchestration removed |
| Inner-tick tracks on single-LLM AgenticLoop | Open — #3580, #3459 |
| Dreaming unchanged (non-turn batch) | OK |
| Soft gate: no live turn.py orchestration | **Met** — ``_run_companion_turn_core`` routes only via ``AgenticLoop`` + ``OutputQueue``; parallel ``background_events`` / ``WebSocketDownlink`` removed |
| WS typed outbound emit (Stage 2) | **Met** — ``WsOutboundPayload`` union; pump ``model_dump``; materializers + REPL ``model_validate`` |
| Memory phase CI | **Pass** |
| User-reported blockers | Open — see user_bug lane |

## Verification run (2026-07-07)

```
check_companion_turn_invariants.py — PASSED
pytest tests/app/core/companion_harness/companion/ — 258 passed
pytest tests/app/services tests/app/api tests/app/schemas/test_chat_websocket_completion_models.py — (see CI)
rg legacy turn orchestration / WebSocketDownlink / background_events pump — no live production callers
REPL regression — not run (requires Ops :8001)
```

## Next work (refactor lane)

1. #3493 Weixin enqueue+wake
2. #3542–#3543 inner-tick/output pump (App-WS greeting + inner-tick converge on pump-owned delivery)
3. #3580 maintenance/autonomy on AgenticLoop
4. Stage 3/4 replan: prompt single source (#3463), retrieval/projection (#3523/#3521)

CRS (#3341) and product (#3323) remain **blocked** on inner-tick AgenticLoop (#3580) and Weixin transport (#3493).
