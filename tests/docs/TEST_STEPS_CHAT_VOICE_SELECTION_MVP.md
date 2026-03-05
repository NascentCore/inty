# TEST_STEPS_CHAT_VOICE_SELECTION_MVP

## Backend API checks

1. Update chat settings with `voice_id=google/Zephyr`:
   - `PUT /api/v1/chats/agents/{agent_id}/settings`
   - Expect `200` and returned `data.voice_id == "google/Zephyr"`.
2. Reject non-Gemini voice in chat settings:
   - `PUT /api/v1/chats/agents/{agent_id}/settings` with `voice_id=11labs/...`
   - Expect `400` and detail: `Only Gemini voices are supported in chat settings for now.`
3. Manual voice generation path:
   - `POST /api/v1/chats/agents/{agent_id}/messages/{message_id}/voice`
   - Ensure TTS uses chat settings voice when present.
4. Auto voice generation path:
   - `POST /api/v1/chat/completions/{agent_id}` with `chat_settings.voice_enabled=true`
   - Ensure TTS uses chat settings voice when present.

## Android app checks

1. Open chat settings drawer.
2. Confirm a new `Voice` row exists and shows current value.
3. Pick a Gemini voice and verify `updateChatSettings` is called with `voice_id`.
4. Re-open drawer and verify selected voice persists from chat settings response.
5. Select `Default (Agent voice)` and verify `voice_id` is cleared (`null`).
