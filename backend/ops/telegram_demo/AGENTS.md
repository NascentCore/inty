# Generated entirely by Cursor agent — telegram-demo Ops bridge package doc.

Ops **telegram-demo**: Telegram Bot API long-poll ↔ companion harness.

## Integration surface

| Layer | Role |
|-------|------|
| ``app/external_services/telegram_bot_api.py`` | Bot API HTTP (getUpdates, sendMessage, getMe) |
| ``backend/ops/telegram_demo/`` | Provision, Postgres binding, in-process presence, transport |
| ``GET /telegram`` | Product onboard page (team QR → ``https://t.me/{username}?start=onboard``) |
| ``GET /api/v1/telegram/bot-info`` | Product: JSON bot id / username for QR page |
| ``GET /api/v1/telegram-demo/bindings`` | Debug only when ``app.debug`` (local/dev Ops) |
| ``companion_chat_service.run_user_chat`` | Same kernel as WebSocket; ``runtime_channel=TELEGRAM`` |

## Bot ownership

- **Developer** creates the bot in Telegram **BotFather** (``/newbot``).
- Token lives in ``agent.channels.telegram.bot_token``.
- Inty **consumes** the token only.

## User-visible behavior (v2)

1. Teammate opens ``GET /telegram``, scans **team QR** (``start=onboard``).
2. Ops auto-provisions **guest** ``User`` + PRIVATE ``Agent`` per ``telegram_chat_id``
   (identity: ``user_id`` / ``agent_id`` only; legacy ``readable_id`` unused).
3. **Onboard messages** (``/start`` / ``/start onboard``):
   - **New user**: italic platform notice (*Your agent is waking up…*), then companion LLM sign-on greeting (plain text).
   - **Returning user**: italic platform notice only (*Welcome back…*); no second greeting.
   - Transport notices use Telegram HTML ``parse_mode``; companion output does not.
4. User sends **text**; harness replies (中文 OK).
5. **Inner-tick** proactive / maintenance downlink via ``sendMessage`` (per-binding worker).
6. Ops restart: bindings + presences restore from ``agent_channel_endpoints`` (poll offset in ``ops_telegram_demo_poll_state``).

## Multi-user routing

One shared bot; routing key is Telegram ``chat_id`` → binding → ``(user_id, agent_id, chat_id)``.
See ``TelegramTransport`` class docstring.

## Limits

- Binding + poll offset in Postgres; **single Ops replica** (no multi-pod long-poll) — #3347.
- Text inbound only; no image/voice yet — #3349.
- Production ``/start`` accepts ``onboard`` only; bind-to-existing-agent tests call ``provision_agent_for_existing_agent`` directly.

## Demo vs product routes (#3348)

- **Product** (teammate onboard): ``GET /telegram``, ``GET /api/v1/telegram/bot-info``
- **Public URLs**: ``https://dev.ops.inty.cc/telegram``, ``https://ops.inty.cc/telegram`` (nginx full-path proxy to Ops)
- **Debug** (bindings list): ``GET /api/v1/telegram-demo/bindings`` — mounted only when ``app.debug`` is true (local/dev; not prod)

Manual restore smoke: ``.cursor/skills/telegram-demo-restore-smoke/SKILL.md``.
