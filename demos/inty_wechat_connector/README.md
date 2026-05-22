# Inty WeChat Connector (demo)

Minimal bridge: **Hermes** `WeixinAdapter` (WeChat iLink long-poll) forwards each inbound DM text to **Inty** `/api/v1/chat/ws`, then returns the assistant reply to WeChat.

No error handling, retries, media, or group chat — demo only.

## Prerequisites

- Personal WeChat linked via Hermes (`hermes gateway setup` → Weixin)
- Inty backend running locally (or reachable URL)
- JWT for a user that can chat with the target `agent_id`

## Install

```bash
cd inty/demos/inty_wechat_connector

# Hermes Weixin also needs `aiohttp` and `cryptography`
# (included via `hermes-agent[messaging]`).
pip install -r requirements.txt
```

## WeChat QR login

```bash
python weixin_login.py
```

The script calls Hermes iLink QR login and prints the QR code / QR URL in the terminal. Scan it with the WeChat account that should receive DMs, then export the printed `WEIXIN_ACCOUNT_ID`, `WEIXIN_TOKEN`, and optional `WEIXIN_BASE_URL` values before running the bridge.

## Environment

```bash
export WEIXIN_ACCOUNT_ID=...          # from python weixin_login.py
export WEIXIN_TOKEN=...               # from python weixin_login.py
export INTY_API_BASE_URL=http://127.0.0.1:8000
export INTY_JWT=...                   # Bearer token for Inty API
export INTY_AGENT_ID=...              # companion agent id

# optional
export WEIXIN_BASE_URL=https://ilinkai.weixin.qq.com
```

## Run

```bash
python bridge.py
```

Send a DM to the logged-in WeChat account; the bridge should reply with Inty companion output.

## Smoke test (Inty WebSocket only)

With Inty running and `INTY_*` vars set:

```bash
export INTY_API_BASE_URL=http://127.0.0.1:8001   # or :8000
export INTY_JWT="$(cat ../../.inty_ops_bearer_token)"  # from inty repo root

python smoke_connect.py   # transport: client_context_ack
python smoke_ws.py        # full companion turn (needs INTY_AGENT_ID)
```

`smoke_connect.py` only checks WebSocket auth + `client_context_ack`. `smoke_ws.py` sends one chat turn (requires a valid companion `INTY_AGENT_ID`).

WeChat end-to-end: set `WEIXIN_*`, run `python bridge.py`, DM the linked account.

## Architecture

```
WeChat user → iLink API → Hermes WeixinAdapter → bridge handler
  → Inty WS /api/v1/chat/ws → assistant text → WeixinAdapter.send → WeChat
```

## Limitations

- Text DMs only (`dm_policy=open`, `group_policy=disabled`)
- New WebSocket per WeChat message (no connection pooling)
- Skips `user_signed_on` / `user_signed_out` lifecycle frames
- Does not correlate multiple queued WS frames; uses first `code` response
