# Chat WebSocket dev E2E (real LLM)

Tests: `tests/app/features/test_chat_websocket_dev_e2e.py` (marked `noci`, gated by env).

## Preconditions

1. Use `devops/config.yaml.dev` or `devops/config.yaml.local` as the server config (copy to repo root `config.yaml`, or your usual flow). `config.yaml.local` needs `app.gcp_service_account_key` pointing at a readable service account JSON and `firebase.service_account_path` pointing at a Firebase admin JSON (see `devops/config.yaml.local`).
2. For Docker Postgres: `docker run ... postgres:16` on `localhost:5432` with password matching `database.password` in that YAML.
3. Backend reachable at `http://localhost:8000` (override with `INTY_API_BASE_URL`).
4. LLM and external API keys in the chosen YAML must work (local config uses `inception/mercury-2` via OpenRouter).

## Run

```bash
export INTY_CHAT_WS_REAL_TEST=1
# optional: export INTY_DEV_CONFIG_PATH=/absolute/path/to/devops/config.yaml.local
# optional: export INTY_CHAT_WS_RECV_TIMEOUT=180
pytest tests/app/features/test_chat_websocket_dev_e2e.py -v -s -m noci
```

Default CI command `pytest -m "not noci"` skips these tests.

## What is asserted

- Ping/pong over `/api/v1/chat/ws` with Bearer token.
- One full chat round-trip (creates a disposable agent, expects `code==200` and non-empty assistant text).
- Unauthenticated connect closes with WebSocket code `4001`.
