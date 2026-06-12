---
name: telegram-demo-restore-smoke
description: >-
  Manual release smoke for Ops Telegram demo Postgres persistence and Ops-restart
  restore. Use when verifying telegram binding resume, ops_telegram_demo_bindings,
  restore_persisted_bindings, or release smoke before merge.
---

# Telegram demo restore smoke

## Prerequisites

1. Postgres running; migration includes `ops_telegram_demo_bindings` and `ops_telegram_demo_poll_state`.
2. `agent.channels.telegram.bot_token` configured in `INTY_CONFIG_YAML`.
3. Ops on `:8001` (`backend/ops/start.sh --local --no-build-frontend`).

## Smoke steps

1. Open `http://127.0.0.1:8001/telegram-demo` → scan team QR with Telegram.
2. Send a user message; confirm bot replies.
3. Check bindings:
   ```bash
   curl -s http://127.0.0.1:8001/api/v1/telegram-demo/bindings | jq
   ```
   Expect `count >= 1` with your `telegram_chat_id`.
4. **Restart Ops** (Ctrl+C on start.sh, relaunch).
5. Send another message **without** re-scanning QR.
6. Expect reply; logs should show `telegram-demo: restored N persisted binding(s)`.

## Optional: proactive after restore

- Wait for `companion_ws_proactive_chat_poll_seconds` after bootstrap complete.
- Or check logs for `inner_tick_turn=True` on Telegram path.

## DB verify

```sql
SELECT telegram_chat_id, user_id, agent_id, chat_id
FROM ops_telegram_demo_bindings;
SELECT id, last_update_id FROM ops_telegram_demo_poll_state;
```
