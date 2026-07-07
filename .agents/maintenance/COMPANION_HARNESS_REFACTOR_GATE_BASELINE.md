# Refactor gate baseline — 2026-07-07

Recorded during Companion Harness partial-convergence plan (Stage 1 PR-5 + Stage 2).

## GitHub issue progress (merged to `main`)

| Issue | Status after PR-5 + Stage 2 |
|-------|-----------------------------|
| #3632 | **Closed** — pull/3764 (Stage 2); threaded `start_tool_background_job` removed |
| #3401 | **Partial (slice 1–3b on branch)** — pull/3765 slice 1; pull/3766 slice 2; slice 3 (`resolve_agentic_loop_mechanism`, delete `TurnRouteMode`) merged; slice 3b typed JSONL `inner_tick_kind` + `resolve_agentic_loop` Protocol + track-native LangSmith on branch |
| #3490 | **Partial** — App-WS `background_events` recv-loop + `WebSocketDownlink` deleted; `foreground_pending` kept for inner-tick (#3580) |
| #3211 | **Partial** — `bootstrap_interim_queued_events` consumer removed; greeting/tool-bg via scope `OutputQueue` + pump (#3576 greeting direct materialize remains) |
| #3209 | **Superseded direction** — user-turn chunks via `OutputQueue` + `AppWsChannelAdapter` (not `WebSocketDownlink` module); #3402 sink still open |
| #3207 / #3208 | **Partial (Stage 2)** — typed `WsOutboundPayload`, materializers, pump, REPL `model_validate`; HTTP meta + `chat_history_service` typed row still open |
| #3543 | **Partial** — WS `TOOL_BACKGROUND` / `USER_REPLY` via presence pump; inner-tick App-WS still direct `outbound_queue.put` |
| #3398 | **Open** — epic; dual vs single-LLM debate unchanged |

Merged to `main`: pull/3765 (#3401 slice 1), pull/3766 (#3401 slice 2). Gate doc updated 2026-07-07 post-merge.

## Checklist status

| Item | Status |
|------|--------|
| Transport all channels enqueue+wake+OutputQueue | Partial — App-WS done (pull/3512); Weixin #3493 open |
| User chat only AgenticLoop (dual + single) | **Met** — all turn tracks require ``agentic_output_queue``; legacy turn.py orchestration removed |
| Inner-tick tracks on single-LLM AgenticLoop | Open — #3580, #3459 |
| Dreaming unchanged (non-turn batch) | OK |
| Soft gate: no live turn.py orchestration | **Met** — ``_run_companion_turn_core`` routes only via ``AgenticLoop`` + ``OutputQueue``; parallel ``background_events`` / ``WebSocketDownlink`` removed |
| WS typed outbound emit (Stage 2) | **Met** — ``WsOutboundPayload`` union; pump ``model_dump``; materializers + REPL ``model_validate`` |
| Track-derived transcript user JSONL flags (#3401) | **Met (slice 3b)** — user rows use `inner_tick_kind` (`InnerTickKind`); legacy `inner_tick`/`proactive_chat`/`scheduled` bool removed from `ChatMessage` and write path |
| Memory phase CI | **Pass** |
| User-reported blockers | Open — see user_bug lane |

## Verification run (2026-07-07, slice 3b)

```
check_companion_turn_invariants.py — PASSED
pytest tests/app/core/companion_harness — 576 passed (~8s)
rg turn_flags_for_track — no live callers (deleted; LangSmith track-native in llm_chat_runtime)
rg "\.proactive_chat|\.scheduled|\.inner_tick\b" app/core/companion_harness/companion — no transcript read residuals
resolve_agentic_loop(track) -> AgenticLoopTurnPlugin; turn.py loop delegates to plugin
```

## Verification run (2026-07-07, slice 3 branch)

```
check_companion_turn_invariants.py — PASSED
pytest tests/app/core/companion_harness — 572 passed (~9s)
rg TurnRouteMode|resolve_turn_route_mode — no live production/test callers
rg turn_flags_for_track — live call only llm_chat_runtime.py (LangSmith bridge)
```

## Verification run (2026-07-07, main post slice 1–2)

```
check_companion_turn_invariants.py — PASSED
pytest tests/app/core/companion_harness — 546 passed (~8s)
pytest tests/app/services — 345 passed (~16s)
pytest tests/app/api — 90 passed, 48 skipped (~5s; test_chat.py 45 passed ~3s)
pytest tests/app/schemas/test_chat_websocket_completion_models.py — 14 passed
rg legacy turn orchestration / WebSocketDownlink / background_events pump — no live production callers
rg rewrite_generic_inner_tick_batch / GENERIC_INNER_TICK_BATCH_TRACK_LABEL — no references (shim removed in review)
REPL regression — not run (requires Ops :8001)
```

## Next work (refactor lane)

1. #3493 Weixin enqueue+wake
2. #3542–#3543 inner-tick/output pump (App-WS greeting + inner-tick converge on pump-owned delivery)
3. #3580 maintenance/autonomy on AgenticLoop
4. Stage 3/4 replan: prompt single source (#3463), retrieval/projection (#3523/#3521)

CRS (#3341) and product (#3323) remain **blocked** on inner-tick AgenticLoop (#3580) and Weixin transport (#3493).
