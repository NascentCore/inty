# Generated entirely by Cursor agent — telegram-demo Ops bridge package doc.

Ops **telegram-demo**: Telegram Bot API long-poll ↔ companion harness.

## Integration surface

| Layer | Role |
|-------|------|
| ``app/external_services/telegram_bot_api.py`` | Bot API HTTP (getUpdates, sendMessage, getMe) |
| ``backend/ops/telegram_demo/`` | Provision, Postgres binding, in-process presence, transport |
| ``GET /telegram-demo`` | Team QR: ``https://t.me/{username}?start=onboard`` |
| ``GET /api/v1/telegram-demo/bot-info`` | JSON bot id / username |
| ``GET /api/v1/telegram-demo/bindings`` | Debug: persisted binding rows |
| ``companion_chat_service.run_user_chat`` | Same kernel as WebSocket; ``runtime_channel=TELEGRAM`` |

## Bot ownership

- **Developer** creates the bot in Telegram **BotFather** (``/newbot``).
- Token lives in ``agent.channels.telegram.bot_token``.
- Inty **consumes** the token only.

## User-visible behavior (v2)

1. Teammate opens ``GET /telegram-demo``, scans **team QR** (``start=onboard``).
2. Ops auto-provisions **guest** ``User`` + PRIVATE ``Agent`` per ``telegram_chat_id``.
3. User sends **text**; harness replies (中文 OK).
4. **Inner-tick** proactive / maintenance downlink via ``sendMessage`` (per-binding worker).
5. Ops restart: bindings + presences restore from ``ops_telegram_demo_bindings``.

## Multi-user routing

One shared bot; routing key is Telegram ``chat_id`` → binding → ``(user_id, agent_id, chat_id)``.
See ``TelegramTransport`` class docstring.

## Limits

- Binding + poll offset in Postgres; **single Ops replica** (no multi-pod long-poll) — #3347.
- Text inbound only; no image/voice yet — #3349.
- Production ``/start`` accepts ``onboard`` only; bind-to-existing-agent tests call ``provision_agent_for_existing_agent`` directly.

Manual restore smoke: ``.cursor/skills/telegram-demo-restore-smoke/SKILL.md``.
