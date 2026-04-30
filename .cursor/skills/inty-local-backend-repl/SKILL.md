---
name: inty-local-backend-repl
description: >-
  Start the local Inty Ops API and tools/inty_v2_repl against /api/v1/chat/ws.
  Use backend/ops/start.sh with --debug --log-file for file logging; after startup tell user log path (cwd-relative).
  Wrong REPL invocation (ImportError), JWT / URL mismatches: see GET_STARTED.md
  (venv, repo-root config.yaml, tools/inty_v2_repl/.env).
---

# Local backend + inty_v2 REPL

## When to use

- 本机起 **Ops**（常见 `http://127.0.0.1:8001`）并联调 **`tools.inty_v2_repl`**
- `ImportError: attempted relative import with no known parent package`（错误地用 `python tools/inty_v2_repl/main.py ...`）
- JWT / 端口 / 依赖不全：按下文文档排查

## Single source of truth（步骤、命令、环境变量表）

正文一律见 **[tools/inty_v2_repl/docs/GET_STARTED.md](../../../tools/inty_v2_repl/docs/GET_STARTED.md)**：Postgres、`config.yaml`、`tools/inty_v2_repl/.env`（由 `.env.example` 复制）、`backend/ops/start.sh`、`python -m tools.inty_v2_repl.main repl ...`。

## Ops 后端写文件日志（勿漏）

联调时推荐 **always** 带上 **`--debug`** 与 **`--log-file`**（与 `GET_STARTED.md` 示例一致）：

```bash
# 仓库根 cwd；与 GET_STARTED 默认示例一致（跳过 evaluation 构建以加快冷启动）
backend/ops/start.sh --local --debug --log-file ./inty-ops-local.log --no-build-frontend
```

- **`--log-file PATH`**：由 `start.sh` 设置 `INTY_LOG_FILE`；Loguru 追加 UTF-8 文件 sink（与控制台并行）。详见 GET_STARTED 小节「`--debug` 与 `--log-file`」及环境变量表。
- **路径规则**：`PATH` 为相对路径时相对于 **启动进程的 shell 当前目录**。上例在仓库根启动则日志文件为 **`<repo-root>/inty-ops-local.log`**（可用绝对路径避免歧义）。
- **Agent 契约**：完成拉起 Ops 后，向用户 **一句话说明日志文件完整路径**（若用 `./inty-ops-local.log` 且在仓库根启动，即仓库根下的 `inty-ops-local.log`）。

不经 `start.sh` 封装时（例如仅 `uvicorn`）：在仓库根 `.env` 或 `export` 设置 `INTY_LOG_FILE`（及可选 `INTY_LOGGING_LEVEL` / `INTY_CONSOLE_LOGGING_LEVEL`），规则同上表。

## Agent 易错点（不经 `-m` 必挂）

必须用模块方式启动 REPL：

```bash
python -m tools.inty_v2_repl.main repl ...
```

不要用 `python tools/inty_v2_repl/main.py repl ...`。

## 其它参考

- REPL 行为与架构：[tools/inty_v2_repl/AGENTS.md](../../../tools/inty_v2_repl/AGENTS.md)
