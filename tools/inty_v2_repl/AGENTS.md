# REPL: Terminal Text UI through Inty Agentic Companion's WebSocket interface

Used for testing agentic companion locally by human users, agents smoke testing.
WebSocket interface is also used by iMate iOS and Android apps.

## What can be imported from /app/

- **允许**：共享的 **类型与 DTO**（聊天完成体、WebSocket 信封）——用于构造/解析 JSON。
- **禁止**：把 **服务端 companion 实现**、**服务端进程配置（`app.core.config` / 根 `config.yaml`）** 拉进 REPL 进程；REPL 只应像普通 App 一样通过 **URL 与鉴权** 连后端。传输层可调参数留在本工具自己的模块常量 / 环境变量中。
- **原则**：完全呈现后端能力和体验，与 **iMate** [安卓](/imate_android_app/) [iOS](/imate_ios_app/) 完全一致，但是做必要调整
  （比如只显示图片链接而不是直接呈现图片，由于没有 GUI 能力）。

## Setup

```bash
# Launch ops backend elsewhere
# Remember to copy the bearer token in <repo_root>/.inty_ops_bearer_token
# And update the .env file locally before starting repl.
cd tools/inty_v2_repl/
uv venv
source .venv/bin/activate
uv pip install -r tools/inty_v2_repl/requirements.txt
python -m tools.inty_v2_repl.main repl \
  --api-base-url http://127.0.0.1:8001 \
  --agent-id YOUR_AGENT_ID
```

- **Bearer**: `INTY_ACCESS_TOKEN` or `INTY_BEARER_TOKEN` from `tools/inty_v2_repl/.env`; else repo-root `.inty_ops_bearer_token` (`backend/ops/start.sh --local`). LangSmith 可点链接需 `.env` 的 `LANGCHAIN_API_KEY`（见 examine-local-inty-repl-env skill）。
- **Agent**: `--agent-id` or `INTY_V2_CHAT_AGENT_ID`.
- **HTTP base**: `INTY_API_BASE_URL` or `--api-base-url` (default `http://127.0.0.1:8000`); WebSocket URL is derived as `ws(s)://.../api/v1/chat/ws`.
- **Logs**: REPL does not write a local log file; **loguru** is stderr-only (`proto_log.configure_proto_log`).
