---
name: inty-local-backend-repl
description: >-
  Launch inty backend for running terminal REPL.
  This is used for local development and evaluation of the agentic companion experience.
---

# Launching local backend for terminal REPL

## When to use

- Launch Inty ops on `:8001` for `tools.inty_v2_repl` to connect with
- [`Local REPL README.md`](/tools/inty_v2_repl/README.md)

## Ops

Use `INTY_CONFIG_YAML` env var to specify the config file for launching the ops variant
of Inty backend.

```bash
export INTY_CONFIG_YAML=devops/config.yaml.local
backend/ops/start.sh --local --debug --no-build-frontend
```

`INTY_CONFIG_YAML` 使用仓库根目录为相对路径基准；**不要传 `--workspace`**，沿用 `start.sh` 默认工作目录 **`.inty`**，文件日志 **`.inty/inty.log`**（启动时若已存在会先删除再写）；完整参数与环境说明见 **`backend/ops/start.sh --help`**。

## Terminate Ops

若用户要求终止通过本 skill 拉起的 inty 后端，只终止 Ops 后端进程组（`backend/ops/start.sh` 与对应 `uvicorn :8001`）；不要默认杀 REPL，除非用户明确要求。

**首选**：在运行 `backend/ops/start.sh` 的那个前台终端按 **Ctrl+C**（会连带停 uvicorn）。

后台或失联时再查 PID：

```bash
pgrep -af 'backend/ops/start\.sh|uvicorn .*--port 8001'
kill -TERM <uvicorn_pid> <start_sh_pid> <launcher_pid>
lsof -nP -iTCP:8001 -sTCP:LISTEN || true
pgrep -af 'python -m tools\.inty_v2_repl' || true
```

- 最后一行只用于确认 REPL 是否仍在运行，不是后端终止目标。
- 终止后向用户说明：Ops 后端已停止、端口是否仍有监听、REPL 是否仍在运行。

## 获取 agent-id（仓库根 cwd，`user-testing` superuser）

Bearer 默认读 **`${INTY_OPS_BEARER_TOKEN_FILE:-.inty_ops_bearer_token}`**（`--local` 启动已写入）。API 基址默认 **`http://127.0.0.1:8001`**；若使用环境变量 **`PORT`** 覆盖监听端口，请同步改 **`INTY_API_BASE_URL`**（例如 `export INTY_API_BASE_URL=http://127.0.0.1:9001`）。

Run the command below to get the agent ID for launching the repl:

```bash
AGENT_ID=$(python3 tools/scripts/list_inty_ops_agents_admin.py | awk -F'\t' 'NR==1 {print $1}')
```

## Final reply to user（默认）

After ops instance is ready, respond to user with：

1. Log file path：**`.inty/inty.log`**（仓库根相对路径）
2. Repl launch command, use the AGENT_ID obtained before:

   ```bash
   source .venv/bin/activate
   python -m tools.inty_v2_repl.main repl \
     --api-base-url http://127.0.0.1:8001 \
     --agent-id AGENT_ID
   ```

## Reference

- [`tools/inty_v2_repl/AGENTS.md`](../../../tools/inty_v2_repl/AGENTS.md)
