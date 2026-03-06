# FR: Chat Voice Selection MVP

## Goal

Allow users to choose a per-chat voice for TTS playback.

## Scope

- Add `chat_settings.voice_id` to backend persistence and API schema.
- Restrict chat settings voice updates to Gemini voices for MVP (`google/*`).
- Apply selected voice in both:
  - auto-play voice generation in `POST /api/v1/chat/completions/{agent_id}`
  - manual voice generation in `POST /api/v1/chats/agents/{agent_id}/messages/{message_id}/voice`
- Add Android chat settings voice picker (Gemini voices only) and persist via chat settings API.

## Voice Resolution Order

For chat message TTS generation:

1. `chat_settings.voice_id`
2. `agent.voice_id`
3. backend TTS default fallback

## Non-goals (MVP)

- ElevenLabs voice selection in chat settings
- New monetization rules for voice selection
- Voice list pagination/filter controls in Android UI
