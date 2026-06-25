# Companion harness config move

Canonical example: `app.features.companion_*` moved to `agent.companion_harness.*`.

## Field mapping

- `app.features.companion_default_context_mode` -> `agent.companion_harness.default_context_mode`
- `app.features.companion_memory_bootstrap_type` -> `agent.companion_harness.memory_bootstrap_type`
- `app.features.companion_transcript_compaction` -> `agent.companion_harness.transcript.compaction`
- `app.features.companion_transcript_llm_window_max_messages` -> `agent.companion_harness.transcript.llm_window_max_messages`
- `app.features.companion_ws_session_system_text` -> `agent.companion_harness.ws.session_system_text`
- `app.features.companion_ws_proactive_chat_base_idle_seconds` -> `agent.companion_harness.inner_tick.proactive_chat.base_idle_seconds`
- `app.features.companion_ws_proactive_chat_stop_after_silence_minutes` -> `agent.companion_harness.inner_tick.proactive_chat.stop_after_silence_minutes`
- `app.features.companion_ws_proactive_chat_poll_seconds` -> `agent.companion_harness.inner_tick.proactive_chat.poll_seconds`
- `app.features.companion_ws_monolog_inner_tick_min_gap_seconds` -> `agent.companion_harness.inner_tick.monolog.min_gap_seconds`
- `app.features.companion_tool_bg_idle_wait_timeout_sec` -> `agent.companion_harness.tool_bg_idle_wait_timeout_sec`
- `app.features.companion_implicit_sign_on_greeting_llm_timeout_sec` -> `agent.companion_harness.implicit_sign_on_greeting.llm_timeout_sec`
- `app.features.companion_implicit_sign_on_greeting_llm_max_attempts` -> `agent.companion_harness.implicit_sign_on_greeting.llm_max_attempts`

## Shape

- `transcript.*`: compaction and transcript-window settings.
- `ws.*`: WebSocket session text.
- `inner_tick.proactive_chat.*`: proactive timing.
- `inner_tick.monolog.*`: monolog inner-tick timing.
- `implicit_sign_on_greeting.*`: implicit greeting LLM limits.

## What changed

- Added `AgentConfig.CompanionHarnessConfig` with nested `TranscriptConfig`, `WsConfig`, `InnerTickConfig`, and `ImplicitSignOnGreetingConfig`.
- Kept module-level `_normalize_*` / `_validate_*` helpers; moved validator calls to the harness model.
- Removed legacy fields from `FeaturesConfig`.
- Removed reconcile helpers after all YAML and callers used the new path.
- Updated runtime readers in companion chat service, channel turn handling, inner tick workers, presence, websocket bootstrap, and living sphere curator.

## YAML before / after

```yaml
# before
app:
  features:
    companion_memory_bootstrap_type: USER_INTERACTIVE

# after
agent:
  companion_harness:
    memory_bootstrap_type: USER_INTERACTIVE
```

Proactive chat local overrides moved under:

```yaml
agent:
  companion_harness:
    inner_tick:
      proactive_chat:
        base_idle_seconds: 10
        poll_seconds: 5
```

## Test notes

- Use `features: {}` in minimal config fixtures; bare `features:` parses as `null`.
- Harness load tests should put fixture content under `agent.companion_harness`.
- Delete sync/reconcile assertions once legacy fields are gone.

## Verification

```bash
uv run pytest tests/app/utils/test_config.py tests/backend/ops/telegram_channel/test_telegram_channel_config.py -q
rg 'app\.features\.companion_|features\.companion_' app backend devops config.yaml
```
