# `inty_v2_repl`：终端里的 WebSocket 客户端

**一句话**：这是一个 **只负责传输与交互** 的 REPL——把你在终端输入的每一行变成 **合法的聊天 WebSocket 上行**，并把下行业务帧打印出来；**伴侣如何想、如何做** 完全在服务端 companion 内核中发生。

## 读者

- 本地调试聊天、inner-tick、断线重连、implicit greeting 等 **链路与时间线** 的工程师与编码智能体。

## 边界（为什么禁止 import 某些库）

- **允许**：共享的 **类型与 DTO**（聊天完成体、WebSocket 信封）——用于构造/解析 JSON。
- **禁止**：把 **服务端 companion 实现**、**服务端进程配置（`app.core.config` / 根 `config.yaml`）** 拉进 REPL 进程；REPL 只应像普通 App 一样通过 **URL 与鉴权** 连后端。传输层可调参数留在本工具自己的模块常量 / 环境变量中。

## 行为直觉（不谈具体函数名）

- **连接身份**：每次会话有稳定的传输层 id 便于和服务器日志对齐；**单轮业务关联** 请优先用 **用户消息 UUID、trace id、LangSmith** 等，而不是只看传输 id。
- **登录与隐式问候**：首次连上带 `agent_id` 的 URL 时，会按产品规则发送 **签到与隐式问候**；断线重连会 **刷新坐标但不重复「第一次见面」式问候**。
- **时间与上下文**：周期性上报 **本地时间 / 时区** 等业务上下文，让服务端做「像人一样知道现在是几点」的决策。
- **断线**：检测到非用户主动退出的断线后，重连路径会按契约发送 **掉线声明** 再恢复签到，让服务器在记忆里记一笔。
- **多帧下行**：一次用户输入可能对应 **多条 JSON**（主回复、后台工具、心跳等），REPL 把它们视作 **队列** 顺序展示。
- **元数据行**：首行展示墙钟耗时、可选追踪链接、inner-tick 是 **主动搭话** 还是 **维护** 等——用于人类扫一眼判断这一轮「是什么性质的工作」。

## Setup

- Shell cwd: **repository root** (so `app` and `config.yaml` resolve like other Inty tools).
- Venv: use a **repository-root** `.venv` (same convention as [backend/ops/README.md](../../backend/ops/README.md)). Create with **uv**, then install root [requirements.txt](../../requirements.txt) plus this package’s [requirements.txt](requirements.txt):

  ```bash
  uv venv
  source .venv/bin/activate
  uv pip install -r requirements.txt -r tools/inty_v2_repl/requirements.txt
  ```

  If `.venv` already exists, skip `uv venv`, activate it, and re-run `uv pip install ...` when dependencies change.
- Copy [.env.example](.env.example) to **`tools/inty_v2_repl/.env`** (or use repo-root `.env`). Variables exported in the shell override `.env`.

## Run

After **Setup** (venv + `uv pip install`), from the repository root:

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
