---
name: inty-local-backend-repl
description: >-
  Start the local Inty Ops API and tools/inty_v2_repl against /api/v1/chat/ws.
  Use for local backend + WebSocket REPL, wrong REPL invocation (ImportError),
  or JWT / URL mismatches. Prerequisites and commands: tools/inty_v2_repl/docs/GET_STARTED.md
  (venv, repo-root config.yaml, tools/inty_v2_repl/.env with INTY_ACCESS_TOKEN from backend startup).
---

# Local backend + inty_v2 REPL

## When to use

- 本机起 **Ops**（常见 `http://127.0.0.1:8001`）并联调 **`tools.inty_v2_repl`**
- `ImportError: attempted relative import with no known parent package`（错误地用 `python tools/inty_v2_repl/main.py ...`）
- JWT / 端口 / 依赖不全：按下文文档排查

## Single source of truth（步骤、命令、环境变量表）

正文一律见 **[tools/inty_v2_repl/docs/GET_STARTED.md](../../../tools/inty_v2_repl/docs/GET_STARTED.md)**：Postgres、`config.yaml`、`tools/inty_v2_repl/.env`（由 `.env.example` 复制）、`backend/ops/start.sh`、`python -m tools.inty_v2_repl.main repl ...`。

## Agent 易错点（不经 `-m` 必挂）

必须用模块方式启动 REPL：

```bash
python -m tools.inty_v2_repl.main repl ...
```

不要用 `python tools/inty_v2_repl/main.py repl ...`。

## 其它参考

- REPL 行为与架构：[tools/inty_v2_repl/AGENTS.md](../../../tools/inty_v2_repl/AGENTS.md)
