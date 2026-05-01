---
name: inty-local-backend-repl
description: >-
  Start the local Inty Ops API and tools/inty_v2_repl against /api/v1/chat/ws.
  Use backend/ops/start.sh with --debug --log-file for file logging; after startup tell user log path (cwd-relative).
  Wrong REPL invocation (ImportError), JWT / URL mismatches: see tools/inty_v2_repl/README.md
  (venv, repo-root config.yaml, tools/inty_v2_repl/.env).
---

# Local backend + inty_v2 REPL

## When to use

- 本机起 **Ops**（常见 `http://127.0.0.1:8001`）并联调 **`tools.inty_v2_repl`**
- `ImportError: attempted relative import with no known parent package`（错误地用 `python tools/inty_v2_repl/main.py ...`）
- JWT / 端口 / 依赖不全：按 [`tools/inty_v2_repl/README.md`](../../../tools/inty_v2_repl/README.md) 排查

## Single source of truth（步骤、命令、环境变量）

见 **[tools/inty_v2_repl/README.md](../../../tools/inty_v2_repl/README.md)**：`config.yaml`、`tools/inty_v2_repl/.env`（由 `.env.example` 复制）、`backend/ops/start.sh`、`python -m tools.inty_v2_repl.main repl ...`。

## Ops 后端写文件日志（勿漏）

联调时推荐 **always** 带上 **`--debug`** 与 **`--log-file`**：

```bash
# 仓库根 cwd
backend/ops/start.sh --local --debug --log-file ./inty-ops-local.log --no-build-frontend
```

- **`--log-file PATH`**：由 `start.sh` 设置 `INTY_LOG_FILE`；Loguru 追加 UTF-8 文件 sink（与控制台并行）。
- **路径规则**：`PATH` 为相对路径时相对于 **启动进程的 shell 当前目录**。上例在仓库根启动则日志文件为 **`<repo-root>/inty-ops-local.log`**（可用绝对路径避免歧义）。
- **Agent 契约**：完成拉起 Ops 后，向用户 **一句话说明日志文件完整路径**（若用 `./inty-ops-local.log` 且在仓库根启动，即仓库根下的 `inty-ops-local.log`）。

不经 `start.sh` 封装时（例如仅 `uvicorn`）：在仓库根 `.env` 或 `export` 设置 `INTY_LOG_FILE`（及可选 `INTY_LOGGING_LEVEL` / `INTY_CONSOLE_LOGGING_LEVEL`）。

## Agent 易错点（不经 `-m` 必挂）

必须用模块方式启动 REPL：

```bash
python -m tools.inty_v2_repl.main repl ...
```

不要用 `python tools/inty_v2_repl/main.py repl ...`。

## 其它参考

- 包内索引：[tools/inty_v2_repl/AGENTS.md](../../../tools/inty_v2_repl/AGENTS.md)
