# TEST_STEPS_TTS_PROVIDER_MODEL_ROUTING

## Goal

Verify the TTS stop-gap routing fix in `docs/TTS_SYSTEM_2026_04.md` task 5.1:

1. `google/...` voice never uses ElevenLabs model IDs.
2. Explicit provider/model mismatch fails immediately.
3. Gemini -> ElevenLabs fallback rebinds ElevenLabs model + voice.

## Commands

```bash
source .venv/bin/activate
pytest -q tests/app/services/test_voice_service_provider_model_routing.py
pytest -q tests/app/services/test_voice_service_gemini_gcs_urls.py
```

## Expected results

- All tests pass.
- No regression on existing GCS URL behavior tests.
