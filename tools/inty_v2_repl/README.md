# Inty chat WebSocket REPL

Terminal client for Inty **`/api/v1/chat/ws`**. Conversation and companion bootstrap run on the server; this process only holds a WebSocket, prints assistant text, and writes local logs.

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
- **Logs**: `--workspace` (default `tools/inty_v2_repl/workspace/`), optional `--log-file`, or `--no-log-file` for stderr only.

## Layout

| Module | Role |
|--------|------|
| [main.py](main.py) | Cyclopts `repl` command |
| [backend_chat_ws.py](backend_chat_ws.py) | WebSocket bridge |
| [repl_message_io.py](repl_message_io.py) | Sideband downlink formatting |
| [repl_session_messages.py](repl_session_messages.py) | Typed downlink items |
| [proto_log.py](proto_log.py) | loguru file/stderr setup |
| [repl_dotenv.py](repl_dotenv.py) | Dotenv loading |

Companion kernel code lives under **`app/core/agentic_kernel/companion/`**, not in this package.
