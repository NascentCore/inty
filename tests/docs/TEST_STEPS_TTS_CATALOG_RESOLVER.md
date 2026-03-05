# TEST_STEPS_TTS_CATALOG_RESOLVER

## Goal

Verify `docs/TTS_SYSTEM_2026_04.md` task 5.2 (TTS catalog + resolver):

1. TTS models are resolved by provider model ID and nickname.
2. Unknown model IDs/nicknames fail loudly via `must_resolve_*`.
3. Provider ownership check rejects unknown or cross-provider model IDs.

## Commands

```bash
source .venv/bin/activate
pytest -q tests/app/core/voice/test_tts_catalog.py
pytest -q tests/app/services/test_voice_service_provider_model_routing.py
```

## Expected results

- All tests pass.
- `VoiceService.generate_voice()` rejects invalid model IDs before TTS API calls.
