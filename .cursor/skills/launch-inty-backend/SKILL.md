---
name: launch-inty-backend
description: >-
  Launch Inty Ops backend locally for terminal REPL, iMate Android, and iMate iOS
  development and evaluation.
---

# Launch Inty backend locally

## When to use

- Launch Inty **Ops** on **`:8001`** (default) for local API / WebSocket against the current workspace
- [`Terminal REPL`](/tools/inty_v2_repl/AGENTS.md)
- **[iMate Android](/imate_android_app/)** / **[iMate iOS](/imate_ios_app/)** pointing at the same Ops instance

## Ops

From repository root: `uv venv`, `source .venv/bin/activate`, then
`uv pip install -r requirements.txt -r tools/inty_v2_repl/requirements.txt`
(see [repl AGENTS.md](/tools/inty_v2_repl/AGENTS.md) Setup).

Use `INTY_CONFIG_YAML` env var to specify the config file for launching the ops variant
of Inty backend.

```bash
export INTY_CONFIG_YAML=devops/config.yaml.local
backend/ops/start.sh --local --debug --no-build-frontend
```

`INTY_CONFIG_YAML` 使用仓库根目录为相对路径基准；**不传 `--workspace` 时**默认工作目录为仓库根下 **`.inty`**，文件日志 **`.inty/inty.log`**（启动时若已存在会先删除再写）；需要把日志放到其它目录时再传 **`--workspace DIR`**（见 **`backend/ops/start.sh --help`**）。

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

Bearer 默认读 **`${INTY_OPS_BEARER_TOKEN_FILE:-.inty_ops_bearer_token}`**（`--local` 启动已写入）。API 基址默认 **`http://127.0.0.1:8001`**；若使用环境变量 **`PORT`** 覆盖监听端口，请同步改客户端与 **`INTY_API_BASE_URL`**（例如 `export INTY_API_BASE_URL=http://127.0.0.1:9001`）。

```bash
cat .inty_ops_bearer_token
```

Read `.inty_ops_bearer_token` to fill in the value of `INTY_ACCESS_TOKEN` env var in `tools/inty_v2_repl/.env`

Run the command below to get the agent ID for launching the repl:

```bash
AGENT_ID=$(python3 tools/scripts/list_inty_ops_agents_admin.py | awk -F'\t' 'NR==1 {print $1}')
```

## Final reply to user（默认）

First, read [repl AGENTS.md](/tools/inty_v2_repl/AGENTS.md) to understand how to launch repl.

After ops instance is ready, respond to user with the following (always include **local URL** and **bearer** paths):

1. **Log file**：**`.inty/inty.log`**（仓库根相对路径）
2. **Local API base URL**（宿主机 / REPL / iOS 模拟器）：
   - **`http://127.0.0.1:8001`**（默认；`PORT` 覆盖时改为 `http://127.0.0.1:<PORT>`）
   - WebSocket 由客户端从 HTTP 基址推导（例如 **`ws://127.0.0.1:8001/api/v1/chat/ws`**）
3. **Bearer token**（`user-testing` JWT，`Authorization: Bearer …`）：
   - 文件：**仓库根 [`.inty_ops_bearer_token`](../../../.inty_ops_bearer_token)**（`backend/ops/start.sh --local` 写入；可用 **`INTY_OPS_BEARER_TOKEN_FILE`** 改路径）
   - 读取：`cat .inty_ops_bearer_token`（勿提交 git）
4. **Agent ID**：`python3 tools/scripts/list_inty_ops_agents_admin.py` 首列，或上节 `AGENT_ID=…`
5. **Terminal REPL**（另开终端，仓库根）— 见 [repl AGENTS.md](/tools/inty_v2_repl/AGENTS.md)
6. **iMate Android**（[`imate_android_app/core/build.gradle.kts`](../../../imate_android_app/core/build.gradle.kts) debug **`API_BASE_URL`**）：
   - **模拟器**连宿主机 Ops：**`http://10.0.2.2:8001/`**（`10.0.2.2` = 宿主机 loopback）
   - **真机**：**`http://<电脑局域网 IP>:8001/`**（与 Mac/PC 同一 Wi‑Fi）
   - Debug 默认是远程 dev URL；改 `API_BASE_URL` 后需 **重新编译** debug 包
   - 本地 Ops 为 **HTTP**；连不上时检查 debug 是否允许明文流量（`networkSecurityConfig` / `usesCleartextTraffic`）
   - Bearer：走 App 登录后 `MainViewModel` 注入；本地 Ops 联调时若需固定 JWT，内容与 **`.inty_ops_bearer_token`** 相同（`user-testing`）
7. **iMate iOS**（[`imate_ios_app/imate/home/HomeView.swift`](../../../imate_ios_app/imate/home/HomeView.swift) 启动页字段）：
   - **Backend base URL**：**`http://127.0.0.1:8001`**（模拟器；真机用 **`http://<电脑局域网 IP>:8001`**）
   - **Bearer token**：粘贴 **`cat .inty_ops_bearer_token`** 输出
   - **Agent ID**：与第 4 步相同
