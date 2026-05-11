---
name: inty-local-backend-repl
description: >-
  Repo root + venv: Ops :8001 (`backend/ops/start.sh`), then `python -m tools.inty_v2_repl.main repl`.
  Includes how to terminate the launched Ops backend. Full env/JWT: tools/inty_v2_repl/README.md
---

# Launching local backend for terminal REPL

## When to use

- 本机起 Ops（常见 `http://127.0.0.1:8001`）并联调 `tools.inty_v2_repl`
- 细节与排错：[`tools/inty_v2_repl/README.md`](../../../tools/inty_v2_repl/README.md)

## Ops（仓库根 cwd）

```bash
backend/ops/start.sh --local --debug --no-build-frontend --log-file ./tmp/inty-ops-local.log
```

- `--log-file` 相对路径相对 shell cwd；上例在仓库根启动则为 `<repo-root>/tmp/inty-ops-local.log`（`tmp/` 在 `.gitignore`）。
- 不经 `start.sh` 时可在仓库根 `export INTY_LOG_FILE=...`（见 `app/core/logging.py`）。

## Terminate Ops（完成联调后）

若用户要求终止通过本 skill 拉起的 inty 后端，只终止 Ops 后端进程组（`backend/ops/start.sh` 与对应 `uvicorn :8001`）；不要默认杀 REPL，除非用户明确要求。

**首选**：在运行 `backend/ops/start.sh` 的那个前台终端按 **Ctrl+C**（会连带停 uvicorn）。

后台或失联时再查 PID：

```bash
pgrep -af 'backend/ops/start\.sh|uvicorn .*--port 8001'
kill -TERM <uvicorn_pid> <start_sh_pid> <launcher_pid>
lsof -nP -iTCP:8001 -sTCP:LISTEN || true
pgrep -af 'python -m tools\.inty_v2_repl' || true
```

- 若启动时设置了 `PORT`，把上面的 `8001` 替换为实际端口。
- 最后一行只用于确认 REPL 是否仍在运行，不是后端终止目标。
- 终止后向用户说明：Ops 后端已停止、端口是否仍有监听、REPL 是否仍在运行。

## Final reply to user（默认）

Ops 就绪后，对用户 **只** 输出下面两样（不要默认展开 JWT、`ImportError`、`README` 等；用户追问再指路）：

1. 一行：`后端日志：<repo-root>/tmp/inty-ops-local.log`（与上文 `--log-file` 一致时）。
2. **仅** 下列可复制块（必须用 `-m`，勿 `python tools/inty_v2_repl/main.py`）；`YOUR_AGENT_ID` 用户自备或由 superuser 调 `GET /api/v1/ai/agents/admin/list`（Bearer 读 `.inty_ops_bearer_token`）取一条 UUID 替换。

```bash
source .venv/bin/activate && python -m tools.inty_v2_repl.main repl \
  --api-base-url http://127.0.0.1:8001 \
  --agent-id YOUR_AGENT_ID
```

## 其它参考

- [`tools/inty_v2_repl/AGENTS.md`](../../../tools/inty_v2_repl/AGENTS.md)
