# `inty_v2_repl`：终端里的 `/api/v1/chat/ws` WebSocket 客户端

**DO NOT MAINTAIN BACKWARD COMPATIBILITY**

这是一个 **只负责传输与交互** 的 REPL——把你在终端输入的每一行变成 **合法的聊天 WebSocket 上行**，并把下行业务帧打印出来。
用来测试 Inty 后端的真实表现。

## 边界（为什么禁止 import 某些库）

- **允许**：共享的 **类型与 DTO**（聊天完成体、WebSocket 信封）——用于构造/解析 JSON。
- **禁止**：把 **服务端 companion 实现**、**服务端进程配置（`app.core.config` / 根 `config.yaml`）** 拉进 REPL 进程；REPL 只应像普通 App 一样通过 **URL 与鉴权** 连后端。传输层可调参数留在本工具自己的模块常量 / 环境变量中。
- **原则**：完全呈现后端能力和体验，与 **iMate** [安卓](/imate_android_app/) [iOS](/imate_ios_app/) 完全一致，但是做必要调整
  （比如只显示图片链接而不是直接呈现图片，由于没有 GUI 能力）。

## Setup

- Shell cwd: **repository root** (so `app` and `config.yaml` resolve like other Inty tools).
- Venv: use a **repository-root** `.venv` (same convention as [backend/ops/README.md](../../backend/ops/README.md)). Create with **uv**, then install root [requirements.txt](../../requirements.txt) plus this package’s [requirements.txt](requirements.txt):

  ```bash
  uv venv
  source .venv/bin/activate
  uv pip install -r requirements.txt -r tools/inty_v2_repl/requirements.txt
  ```

  If `.venv` already exists, skip `uv venv`, activate it, and re-run `uv pip install ...` when dependencies change.
- Copy [.env.example](.env.example) to **`tools/inty_v2_repl/.env`** (REPL reads this).

## Run

After **Setup** (venv + `uv pip install`), from the repository root:

```bash
source .venv/bin/activate
python -m tools.inty_v2_repl.main repl \
  --api-base-url http://127.0.0.1:8001 \
  --agent-id YOUR_AGENT_ID
```

- **Bearer**: `INTY_ACCESS_TOKEN` or `INTY_BEARER_TOKEN` from `tools/inty_v2_repl/.env`; else repo-root `.inty_ops_bearer_token` (`backend/ops/start.sh --local`). LangSmith 可点链接需 `.env` 的 `LANGCHAIN_API_KEY`（见 examine-local-inty-repl-env skill）。
- **Agent**: `--agent-id` or `INTY_V2_CHAT_AGENT_ID`.
- **HTTP base**: `INTY_API_BASE_URL` or `--api-base-url` (default `http://127.0.0.1:8000`); WebSocket URL is derived as `ws(s)://.../api/v1/chat/ws`.
- **Logs**: REPL does not write a local log file; **loguru** is stderr-only (`proto_log.configure_proto_log`).

Interactive **`repl`** sends each line with **`post_turn`** (upload immediately). Downlink prints as frames arrive; the server still handles chat **in request order** per WebSocket. Override send-thread wait budget with **`INTY_V2_BACKEND_WS_POST_TURN_TIMEOUT_SEC`** (default `180`) if reconnect-heavy environments need more headroom.

- REPL / 本地：`python-dotenv`、`.env`。
