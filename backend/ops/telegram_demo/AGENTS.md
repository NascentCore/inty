# Generated entirely by Cursor agent — telegram-demo Ops bridge package doc.

"""Ops **telegram-demo**: Telegram Bot API long-poll ↔ companion harness.

## Integration surface

| Layer | Role |
|-------|------|
| ``app/external_services/telegram_bot_api.py`` | Bot API HTTP (getUpdates, sendMessage, getMe) |
| ``backend/ops/telegram_demo/`` | Provision, in-memory binding, in-process presence, transport |
| ``GET /telegram-demo`` | Onboard page: bot info + QR deep link ``https://t.me/{username}?start=agent_{id}`` |
| ``GET /api/v1/telegram-demo/bot-info`` | JSON bot id / username for the page |
| ``companion_chat_service.run_user_chat`` | Same kernel as WebSocket; ``runtime_channel=TELEGRAM`` |

## Bot ownership

- **Developer** creates the bot in Telegram **BotFather** (``/newbot``).
- Token lives in ``agent.channels.telegram.bot_token`` (fallback: legacy ``agent.telegram_bot_token``).
- Inty **consumes** the token only; it does not create or register bots.

## User-visible behavior (MVP)

1. Tester opens ``http://localhost:8001/telegram-demo``, enters an existing **agent_id**, scans QR.
2. Telegram opens the bot DM with embedded ``/start agent_{id}``.
3. Ops provisions a **guest** ``User`` (``nickname=Telegram_*``, ``meta_data.telegram_chat_id``).
4. User sends **text**; harness replies (中文 OK — language follows harness, not forced English).
5. **No proactive** inner-tick on Telegram; **no** image/voice inbound yet.

## Prototype limits (code TODOs, not product promises)

- Binding **in-memory only** — Ops restart requires ``/start`` again.
- Still requires **agent_id** on the web page (follow-up: auto onboard like ``/weixin``).
- One active runtime channel per Inty user within this Ops process (Telegram vs App WS).

TODO(telegram-demo-no-app-required): Telegram users need only the Telegram app; no iMate install.
Follow-up: public ``/telegram`` onboard, webhook mode, ORM bridge restore — see plan issue backlog.
