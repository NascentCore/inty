# Generated entirely by Cursor agent for Native 1-LLM / 2-LLM agentic loop sidecar.

## Summary

Sidecar ``app/core/companion_harness/loop/`` wraps Phase 0/0.5 public entries with:

- **Interchangeable** ``run_agentic_loop(..., llm_loop_mode=...)``
- **per-call-streaming** via ``AgenticLoopOutputQueue`` → ``LoopChannelAdapter``
- Thin delegates: ``OneModelInTurnSyncMechanism``, ``TwoModelChatThenToolBgMechanism``

## Rejected: pydantic-ai pilot

Prior ``loop/pydantic_ai_one_llm/`` pilot dropped — poor production parity, duplicate loop logic.

## Phase 0/0.5 (done before sidecar)

- ``run_in_turn_sync_tool_loop`` / ``run_bootstrap_track_sync_tool_loop``
- ``run_dual_llm_foreground_chat``
- ``run_tool_background_loop`` (public rename)
- ``dual_llm_message_stacks``

## Sidecar integration (future)

- ``run_turn`` → ``run_agentic_loop`` single point (#3369 config)
- #3402 ``UserVisibleChunkSink`` replaces interim downlink mapping
- Production 2-LLM may use ``ThreadToolLegAdapter``; sidecar uses in-process ``await``

## Tests

```bash
uv run pytest tests/app/core/companion_harness/loop/ -q
uv run python -m app.core.companion_harness.loop.parity.smoke compare-legacy --scenario tool_feedback
```

## Parity layout

- ``parity/fixtures.py`` — fake LLM clients (smoke + loop tests; no ``tests/`` import in prod CLI)
- ``parity/golden.py`` — four golden scenarios + ``build_golden_scenario``
- ``parity/smoke.py`` — cyclopts CLI ``run`` / ``compare-legacy``
