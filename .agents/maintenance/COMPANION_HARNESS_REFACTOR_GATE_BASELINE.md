# Refactor gate baseline — 2026-07-08

Recorded during Companion Harness partial-convergence plan (Stage 1 PR-5 + Stage 2 + inner-tick gate closure).

## Issue tracking policy

Per-issue progress lives on **GitHub issue comments** (not duplicated here).

No verification results recorded here, they'll be tracked in PR descriptions.

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

## Next work (refactor lane)

1. Stage 3/4 replan: prompt single source (#3463), retrieval/projection (#3523/#3521)
2. #3398 dual vs single-LLM envelope (remaining epic scope)

CRS (#3341) and product (#3323): inner-tick AgenticLoop gate item **Met** — unblocked for next gate review (full #3485/#3398 epics still partial).
