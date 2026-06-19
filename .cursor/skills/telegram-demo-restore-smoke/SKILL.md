---
name: telegram-demo-restore-smoke
description: >-
  Manual release smoke for Ops Telegram demo Postgres persistence and Ops-restart
  restore. Use when verifying telegram binding resume, ops_telegram_demo_bindings,
  restore_persisted_bindings, or release smoke before merge.
---

# Telegram demo restore smoke

## Prerequisites

1. Postgres on **`localhost:15432`**，db **`inty`** — matches [`devops/config.yaml.local`](../../../devops/config.yaml.local) **`database`**；**assume already configured; do not change password** during smoke.
2. `export INTY_CONFIG_YAML=devops/config.yaml.local`；`agent.channels.telegram.bot_token` 已配置。
3. Ops on **`:8001`**：`backend/ops/start.sh --local --no-build-frontend`（启动时 **自动 migrate**；含 `ops_telegram_demo_bindings` / `ops_telegram_demo_poll_state`）。**勿**单独 `alembic upgrade head` — 见 [`launch-inty-backend`](../launch-inty-backend/SKILL.md)。

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
