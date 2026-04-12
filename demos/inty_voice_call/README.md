# Inty Voice Call Android Demo

Minimal standalone app for Inty live chat WebSocket voice (see `docs/FR_EXTERNAL_INTY_VOICE_CALL_INTEGRATION.md`).

## Open in Android Studio

File - Open - select folder `demos/inty_voice_call` (this directory, not the repo root).

Android Studio creates `local.properties` with `sdk.dir=...` automatically. For command-line Gradle, set `ANDROID_HOME` to your SDK or add the same `sdk.dir` line in `local.properties` (file is gitignored if you add it locally).

Run configuration: module `app`, `assembleDebug` then install on device or emulator.

## Fields

- API endpoint: Inty HTTPS base URL, no trailing slash (example `https://your-dev-host`).
- API key: JWT used as `Authorization: Bearer` for HTTP and WebSocket (long-term token or login token).
- Agent id: live-chat path segment `.../live-chat/{agent_id}`.
- Speech language code / response language name: optional query parameters on the WebSocket URL.

## Flow

1. Tap "Request microphone permission".
2. Optional: "GET /api/v1/live-chat/status" to verify `enabled` and sample rates.
3. "Start voice call" opens WebSocket with Bearer header (no token in URL), then streams microphone PCM at `send_sample_rate` and plays `audio_response` PCM.
