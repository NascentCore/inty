---
name: inty-local-backend-repl
description: >-
  Start the local Inty Ops API (port 8001) and the inty_v2 REPL against
  /api/v1/chat/ws. Use when the user wants to run the local backend, connect
  the text REPL for WebSocket chat, or fix "import error" / connection issues
  from wrong REPL invocations. Repository root, venv, config.yaml, and
  INTY_ACCESS_TOKEN are required; see full flow in tools/inty_v2_repl/docs/GET_STARTED.md.
---

# Local backend + inty_v2 REPL (Inty)

## When to use

- 在本机起 **Ops 后端**（默认 `http://127.0.0.1:8001`）并联调 **`tools.inty_v2_repl`**
- 用户用错了启动方式（例如直接 `python tools/inty_v2_repl/main.py`，会报相对导入错误）
- 需要与终端里一致的**可复制命令**（两终端：后端 + REPL）

## Conventions (must follow)

- **工作目录**：始终在 **仓库根** `inty/` 下执行；`app.core.config` 需要根目录存在 `config.yaml`。
- **虚拟环境**：`source .venv/bin/activate`（与后端共用根目录 `.env`、依赖）。

## 1) 启动本地后端（Ops）

与日常终端一致；加快迭代、跳过前端构建时可加 `--no-build-frontend`：

```bash
cd /path/to/inty
source .venv/bin/activate
backend/ops/start.sh --local --no-build-frontend --debug --log-file ./inty-ops-local.log
```

说明：

- **`--local`** / **`--dev`**：见 `backend/ops/start.sh --help` 与 [backend/ops/README.md](backend/ops/README.md)
- **`--no-build-frontend`**：不先跑 `evaluation/build.sh` 构建静态页（与 README「加快迭代」一致）
- **`--debug`**：更细 uvicorn / 应用日志
- **`--log-file ./inty-ops-local.log`**：同时写文件（路径相对**当前 shell cwd**；请在仓库根执行）

**首次/干净环境**（Postgres、`config.yaml`、`.env`）的完整步骤见
[tools/inty_v2_repl/docs/GET_STARTED.md](tools/inty_v2_repl/docs/GET_STARTED.md)。启动脚本会打印 **bearer token**；把其写入根目录 `.env` 的 **`INTY_ACCESS_TOKEN`**（与文档一致），否则 REPL 的 WebSocket 会因 JWT 失败（后端日志中可见 `Signature has expired` 等）。

健康检查：打开 `http://127.0.0.1:8001/health`（或文档中的 Evaluation UI）。

## 2) 启动 REPL（Backend WebSocket）

在**另一终端**（根目录、已 `source .venv`）：

```bash
cd /path/to/inty
source .venv/bin/activate
# 可选: export PYTHONPATH=.
python -m tools.inty_v2_repl.main repl \
  --api-base-url http://127.0.0.1:8001 \
  --agent-id <AGENT_ID>
```

- **`AGENT_ID`**：在 Ops Web UI 创建/查看智能体后复制；也可用环境变量 `INTY_V2_CHAT_AGENT_ID` 代替 `--agent-id`。
- **Token**：`INTY_ACCESS_TOKEN` 放在根 `.env` 或 `tools/inty_v2_repl/.env`（`load_prototype_dotenv` 会加载；见 [tools/inty_v2_repl/AGENTS.md](tools/inty_v2_repl/AGENTS.md) 与 GET_STARTED）。

### 不要这样运行 REPL

```text
python tools/inty_v2_repl/main.py repl ...
```

会触发 `ImportError: attempted relative import with no known parent package`。必须用 **`-m tools.inty_v2_repl.main`**。

## 3) 常见问题

| 现象 | 处理 |
|------|------|
| `error: chat ws send_turn failed after 8 attempts` 且后端报 JWT 过期 | 更新根 `.env` 中 **`INTY_ACCESS_TOKEN`** 为 Ops 启动时新打印的 token，或重新登录/获取有效 bearer |
| 连错 API / WS | REPL 未设置时默认 `http://127.0.0.1:8000`；本地 **Ops** 常见 **8001**（或自定义 `PORT`）。`--api-base-url` / `INTY_API_BASE_URL` 与后端实际根 URL 一致即可 |
| 依赖/配置不全 | 跟完 [GET_STARTED.md](tools/inty_v2_repl/docs/GET_STARTED.md)：`uv pip install -r requirements.txt`、`tools/inty_v2_repl/requirements.txt`，`cp` 本地 `config.yaml` 等 |

## 参考

- 详细联调、环境变量表、WS 重连：`tools/inty_v2_repl/docs/GET_STARTED.md`
- REPL 架构与 WS 行为：`tools/inty_v2_repl/AGENTS.md`
