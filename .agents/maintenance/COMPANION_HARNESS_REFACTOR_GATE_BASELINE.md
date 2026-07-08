# Refactor gate baseline — 2026-07-08

Recorded during Companion Harness partial-convergence plan (Stage 1 PR-5 + Stage 2 + inner-tick gate closure).

## Issue tracking policy

Per-issue progress lives on **GitHub issue comments** (not duplicated here).

No verification results recorded here, they'll be tracked in PR descriptions.

Deferred follow-ups (not blocking #3398 epic remainder):

- #3369 — default `llm_loop_mode` / remove `run_dual_llm_turn`
- #3285 — cross-track image delivery
- #3463 — bootstrap proactive overlay
- #3402 — OutputQueue persist `significance_perception` (needs Alembic)

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
| #3398 bootstrap prompt single source | **Met** — `USER_CHAT_BOOTSTRAP` early-return in `turn_pipeline`; `BootstrapUserChatPlugin` + `PromptBuilder` only |
| #3398 in-turn interim chat (#3456–#3458) | **Met** — `resolve_in_turn_assistant_visible_text`; prompt contract; interim `USER_REPLY` via `AgenticLoop` |
| #3398 WS delivery convergence (#3207/#3211) | **Met** — greeting queue-only; `ReadyOutputMessage` wire meta; `WireAssistantSource`; App-WS `foreground_pending` dead code removed |
| #3398 dual-LLM symptoms (#3158/#3123) | **Partial Met** — empty foreground 500 only when queue empty; USER_CHAT/proactive skip `tool_bg_idle` wait; dual silent-fg + tool-bg delivery test |

## Next work (refactor lane)

1. Stage 3/4 replan: retrieval/projection (#3523/#3521)
2. #3369 dual vs single-LLM envelope定案
3. #3463 bootstrap proactive overlay
4. OutputQueue `significance_perception` column (#3402)

CRS (#3341) and product (#3323): inner-tick AgenticLoop gate item **Met** — unblocked for next gate review.
