# Inty chat WebSocket REPL

Terminal client for Inty **`/api/v1/chat/ws`**. Conversation and companion bootstrap run on the server; this process only holds a WebSocket, prints assistant text, and emits structured **loguru** lines on **stderr** (TTY banners use wall clock via `repl_wall_ts_str`, not loguru).

**Dependencies**: This package may import **types/models** from **`app/schemas/chat`** (WebSocket payload contract). Do **not** import `app/core/companion_harness` or other companion implementation modules here. **`app/schemas`** holds types only; parsing of downlink JSON frames lives in [`backend_chat_ws.py`](backend_chat_ws.py).

## Setup

- Shell cwd: **repository root** (so `app` and `config.yaml` resolve like other Inty tools).
- Venv: same root `.venv` as the backend; install root `requirements.txt` plus [requirements.txt](requirements.txt).
- Copy [.env.example](.env.example) to **`tools/inty_v2_repl/.env`** (or use repo-root `.env`). Variables exported in the shell override `.env`.

## Run

```bash
source .venv/bin/activate
python -m tools.inty_v2_repl.main repl \
  --api-base-url http://127.0.0.1:8001 \
  --agent-id YOUR_AGENT_ID
```

- **Bearer**: `INTY_ACCESS_TOKEN` or `INTY_BEARER_TOKEN`, or repo-root `.inty_ops_bearer_token` (e.g. from `./backend/ops/start.sh --local`).
- **Agent**: `--agent-id` or `INTY_V2_CHAT_AGENT_ID`.
- **HTTP base**: `INTY_API_BASE_URL` or `--api-base-url` (default `http://127.0.0.1:8000`); WebSocket URL is derived as `ws(s)://.../api/v1/chat/ws`.
- **Logs**: REPL does not write a local log file; **loguru** is stderr-only (`proto_log.configure_proto_log`).

Interactive **`repl`** sends each line with **`post_turn`** (upload immediately). Downlink prints as frames arrive; the server still handles chat **in request order** per WebSocket. Override send-thread wait budget with **`INTY_V2_BACKEND_WS_POST_TURN_TIMEOUT_SEC`** (default `180`) if reconnect-heavy environments need more headroom.

## Layout

| Module | Role |
|--------|------|
| [main.py](main.py) | Cyclopts `repl` command |
| [backend_chat_ws.py](backend_chat_ws.py) | WebSocket bridge |
| [repl_message_io.py](repl_message_io.py) | Sideband downlink formatting |
| [repl_session_messages.py](repl_session_messages.py) | Typed downlink items |
| [proto_log.py](proto_log.py) | loguru stderr setup |
| [repl_dotenv.py](repl_dotenv.py) | Dotenv loading |

Companion harness code lives under **`app/core/companion_harness/companion/`**, not in this package.
