# Chat WebSocket dev E2E (real LLM)

Tests: `tests/app/features/test_chat_websocket_dev_e2e.py` (marked `noci`, gated by env).

## Preconditions

1. Use `devops/config.yaml.dev` as the server config (copy or symlink to repo root `config.yaml`, or start with `CONFIG_FILE` / your usual dev flow so `app.environment` is `dev`).
2. Backend reachable at `http://localhost:8000` (override with `INTY_API_BASE_URL`).
3. Dev DB and LLM keys in `devops/config.yaml.dev` are valid (same as normal dev server).

## Run

```bash
export INTY_CHAT_WS_REAL_TEST=1
# optional: export INTY_DEV_CONFIG_PATH=/absolute/path/to/devops/config.yaml.dev
# optional: export INTY_CHAT_WS_RECV_TIMEOUT=180
pytest tests/app/features/test_chat_websocket_dev_e2e.py -v -s -m noci
```

Default CI command `pytest -m "not noci"` skips these tests.

## What is asserted

- Ping/pong over `/api/v1/chat/ws` with Bearer token.
- One full chat round-trip (creates a disposable agent, expects `code==200` and non-empty assistant text).
- Unauthenticated connect closes with WebSocket code `4001`.
