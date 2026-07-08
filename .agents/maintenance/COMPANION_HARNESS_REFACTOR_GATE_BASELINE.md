# Refactor gate baseline — 2026-07-08

Recorded during Companion Harness partial-convergence plan (Stage 1 PR-5 + Stage 2 + inner-tick gate closure).

## Issue tracking policy

Per-issue progress lives on **GitHub issue comments** (not duplicated here). Each PR must link issues in its description: `Closes #NNNN` when the PR completes an issue or slice; `Refs #NNNN` for partial progress or epics.

This file retains only the **gate checklist**, verification runs, and next-work pointers.

## Checklist status

| Item | Status |
|------|--------|
| Transport all channels enqueue+wake+OutputQueue | **Met** — App-WS + Weixin + Telegram + SMS via `ScopeQueueServing` (#3780, #3398 P3) |
| User chat only AgenticLoop (dual + single) | **Met** — all turn tracks require ``agentic_output_queue``; legacy turn.py orchestration removed |
| Inner-tick tracks on single-LLM AgenticLoop | **Met** — all inner-tick tracks via `InnerTickChatOnlyPlugin` / `InnerTickToolLoopPlugin`; dead tool-bg + WS fire removed (#3580, #3459) |
| Dreaming unchanged (non-turn batch) | OK |
| Soft gate: no live turn.py orchestration | **Met** — ``_run_companion_turn_core`` routes only via ``AgenticLoop`` + ``OutputQueue``; parallel ``background_events`` / ``WebSocketDownlink`` removed |
| WS typed outbound emit (Stage 2) | **Met** — ``WsOutboundPayload`` union; pump ``model_dump``; materializers + REPL ``model_validate`` |
| Track-derived transcript user JSONL flags (#3401) | **Met (slice 3b)** — user rows use `inner_tick_kind` (`InnerTickKind`); legacy `inner_tick`/`proactive_chat`/`scheduled` bool removed from `ChatMessage` and write path |
| Memory phase CI | **Pass** |
| User-reported blockers | Open — see user_bug lane |

## Verification run (2026-07-08, inner-tick gate closure)

```
check_companion_turn_invariants.py — PASSED
pytest tests/app/core/companion_harness/companion/test_harness_orchestration_scripted_llm.py — includes INNER_TICK_AUTONOMY scripted test
pytest tests/app/core/companion_harness tests/app/services/agentic_companion tests/app/services/agentic_channel — PASSED
pytest tests/app/api/v1/endpoints/test_chat.py -k inner_tick — PASSED
rg try_fire_monolog_inner_tick|try_fire_autonomy_inner_tick|bind_inner_tick_|tool_bg_still_running app/ — no production callers
REPL regression — not run (requires Ops :8001)
```

## Verification run (2026-07-07, slice 3b)

```
check_companion_turn_invariants.py — PASSED
pytest tests/app/core/companion_harness — 576 passed (~8s)
rg turn_flags_for_track — no live callers (deleted; LangSmith track-native in llm_chat_runtime)
rg "\.proactive_chat|\.scheduled|\.inner_tick\b" app/core/companion_harness/companion — no transcript read residuals
resolve_agentic_loop(track) -> AgenticLoopTurnPlugin; turn.py loop delegates to plugin
```

## Next work (refactor lane)

1. Stage 3/4 replan: prompt single source (#3463), retrieval/projection (#3523/#3521)
2. #3398 dual vs single-LLM envelope (remaining epic scope)

CRS (#3341) and product (#3323): inner-tick AgenticLoop gate item **Met** — unblocked for next gate review (full #3485/#3398 epics still partial).
