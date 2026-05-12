---
name: inty-local-backend-repl
description: >-
  Repo root + venv: `export INTY_CONFIG_YAML=devops/config.yaml.local`; Ops :8001
  (`backend/ops/start.sh`); list agent UUIDs via `scripts/list_inty_ops_agents_admin.py`;
  then `python -m tools.inty_v2_repl.main repl`. Terminate Ops notes included.
  Full env: tools/inty_v2_repl/README.md
---

# Launching local backend for terminal REPL

## When to use

- 本机起 Ops（常见 `http://127.0.0.1:8001`）并联调 `tools.inty_v2_repl`
- 细节与排错：[`tools/inty_v2_repl/README.md`](../../../tools/inty_v2_repl/README.md)

## Ops（仓库根 cwd）

后端读配置见 [`app/core/config.py`](../../../app/core/config.py)：`INTY_CONFIG_YAML` 优先，否则 cwd 下 `config.yaml`。本地联调在**同一 shell** 里先导出再启 Ops：

```bash
export INTY_CONFIG_YAML=devops/config.yaml.local
backend/ops/start.sh --local --debug --no-build-frontend --log-file ./tmp/inty-ops-local.log
```

- `INTY_CONFIG_YAML` 可为相对路径（相对**启动进程时的 cwd**，上例为仓库根）。
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

## 获取 agent-id（仓库根 cwd，`user-testing` superuser）

Bearer 默认读 **`${INTY_OPS_BEARER_TOKEN_FILE:-.inty_ops_bearer_token}`**（`--local` 启动已写入）。API 基址默认 **`http://127.0.0.1:8001`**；若使用环境变量 **`PORT`** 覆盖监听端口，请同步改 **`INTY_API_BASE_URL`**（例如 `export INTY_API_BASE_URL=http://127.0.0.1:9001`）。

Run the command below to get the agent ID for launching the repl:

```bash
AGENT_ID=$(python3 scripts/list_inty_ops_agents_admin.py | awk -F'\t' 'NR==1 {print $1}')
```

## Final reply to user（默认）

Ops 就绪后，对用户依次给出下面 **三样**（不要默认展开 JWT、`ImportError`、`README` 等；用户追问再指路）：

1. 一行：`后端日志：<repo-root>/tmp/inty-ops-local.log`（与上文 `--log-file` 一致时）。
2. repl launch command, use the AGENT_ID obtained before:

```bash
source .venv/bin/activate
python -m tools.inty_v2_repl.main repl \
  --api-base-url http://127.0.0.1:8001 \
  --agent-id ${AGENT_ID}
```

（若实际 **`PORT`≠8001**，将两处 URL 中的端口改成一致。）

## 其它参考

- [`tools/inty_v2_repl/AGENTS.md`](../../../tools/inty_v2_repl/AGENTS.md)
