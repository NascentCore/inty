---
name: telegram-demo-restore-smoke
description: >-
  Manual release smoke for Ops Telegram demo Postgres persistence and Ops-restart
  restore. Use when verifying telegram binding resume, agent_channel_endpoints,
  restore_persisted_bindings, or release smoke before merge.
---

# Telegram demo restore smoke

## Prerequisites

1. Postgres on **`localhost:15432`**，db **`inty`** — matches [`devops/config.yaml.local`](../../../devops/config.yaml.local) **`database`**；**assume already configured; do not change password** during smoke.
2. `export INTY_CONFIG_YAML=devops/config.yaml.local`；`agent.channels.telegram.bot_token` 已配置。
3. Ops on **`:8001`**：`backend/ops/start.sh --local --no-build-frontend`（启动时 **自动 migrate**；含 `agent_channel_endpoints` / `ops_telegram_demo_poll_state`）。**勿**单独 `alembic upgrade head` — 见 [`launch-inty-backend`](../launch-inty-backend/SKILL.md)。

## Smoke steps

1. Open product onboard page — local `http://127.0.0.1:8001/telegram` or public `https://dev.ops.inty.cc/telegram` → scan team QR with Telegram.
2. Send a user message; confirm bot replies.
3. Check bindings (**requires `app.debug: true` on Ops**, e.g. local/dev):
   ```bash
   curl -s http://127.0.0.1:8001/api/v1/telegram-demo/bindings | jq
   ```
   Product bot metadata: `curl -s http://127.0.0.1:8001/api/v1/telegram/bot-info | jq`
   Expect bindings `count >= 1` with your `telegram_chat_id`.
4. **Restart Ops** (Ctrl+C on start.sh, relaunch).
5. Send another message **without** re-scanning QR.
6. Expect reply; logs should show `telegram-demo: restored N agent_channel endpoint(s)`.

## Optional: proactive after restore

- Wait for `agent.companion_harness.inner_tick.proactive_chat.poll_seconds` after bootstrap complete.
- Or check logs for `inner_tick_turn=True` on Telegram path.

## DB verify

```sql
SELECT channel_address, user_id, agent_id
FROM agent_channel_endpoints
WHERE channel = 'telegram';
SELECT id, last_update_id FROM ops_telegram_demo_poll_state;
```

## Cleanup（Agent 必做）

若你为本轮 smoke**自行拉起** Ops（见 Prerequisites），测完按 [`launch-inty-backend`](../launch-inty-backend/SKILL.md) **Terminate Ops** 停掉；汇报中说明 **`:8001` 是否空闲**。勿终止用户会话开始时已在运行的 Ops。

## 汇报

- 全过：`[telegram-demo-restore-smoke] RESULT: PASS`
- 任一步失败：`[telegram-demo-restore-smoke] RESULT: FAIL (<一步>)`

## Pre-ad paid flight (TODO)

Expand this skill with pause playbook + pre-flight checklist before first Telegram paid ad dollar — #3536 (epic #3531). Blockers: #3532, #3533, #3534.
