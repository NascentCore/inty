---
name: launch-inty-backend
description: >-
  Launch Inty Ops backend locally for terminal REPL, iMate Android, and iMate iOS
  development and evaluation. Includes REPL .env (bearer, API base, LANGCHAIN_API_KEY for clickable LangSmith URLs). After launch, use examine-local-inty-repl-env to verify setup.
---

# Launch Inty backend locally

## When to use

- Launch Inty **Ops** on **`:8001`** (default) for local API / WebSocket against the current workspace
- [`Terminal REPL`](/tools/inty_v2_repl/AGENTS.md)
- **[iMate Android](/imate_android_app/)** / **[iMate iOS](/imate_ios_app/)** pointing at the same Ops instance

环境是否配齐（LangSmith metadata 可点链接、bootstrap 等）：见 [`examine-local-inty-repl-env`](../examine-local-inty-repl-env/SKILL.md)。Ops 已起、需**新建** bootstrap 测试用 agent：见 [`create-bootstrap-test-agent`](../create-bootstrap-test-agent/SKILL.md)。

## Ops

From repository root: `uv venv`, `source .venv/bin/activate`, then
`uv pip install -r requirements.txt -r tools/inty_v2_repl/requirements.txt`
(see [repl AGENTS.md](/tools/inty_v2_repl/AGENTS.md) Setup).

根目录 `requirements.txt` 含 **`langsmith`**；仅装 `tools/inty_v2_repl/requirements.txt` 会导致 REPL metadata **无法** 解析 `langsmith_trace_url=`。

Use `INTY_CONFIG_YAML` env var to specify the config file for launching the ops variant
of Inty backend. Local engineers use **`devops/config.yaml.local`** (Postgres **`localhost:15432`**, db **`inty`**).

### Postgres（smoke 前置）

<!-- TODO(local-dev-database-skills): dedupe this block — link-only in consumer skills; https://github.com/NascentCore/inty/issues/3529 -->

本地 smoke / pytest 共用 **同一 Postgres**（`devops/config.yaml.local` 的 **`database`** 段：`localhost:15432`，user **`postgres`**，db **`inty`**）。**假定**本机库已按该段配好；**不要**在 smoke 步骤里改 Postgres 密码或跑 `ALTER USER`。

- **Ops / REPL**：`INTY_CONFIG_YAML=devops/config.yaml.local`
- **pytest / CI 后端**（`:8000`）：`INTY_CONFIG_YAML=devops/config.yaml.test` — **`database` DSN 与 local 相同**，仅 agent / tracing 等不同（见 [`devops/config.yaml.test`](../../../devops/config.yaml.test) 文件头注释）

本机尚无 Postgres 时（仓库根）：

```bash
./tools/scripts/ensure_postgres_for_tests.sh
# 或：docker run -d --name inty-ci-pg -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD='sxwl666!' -e POSTGRES_DB=inty -p 15432:5432 postgres:16
```

```bash
export INTY_CONFIG_YAML=devops/config.yaml.local
backend/ops/start.sh --local --debug --no-build-frontend
```

### DB migrations（启动时自动执行）

[`backend/ops/start.sh`](../../../backend/ops/start.sh) 与 [`backend/inty/start.sh`](../../../backend/inty/start.sh) 在拉起 uvicorn **之前** 固定执行 **`alembic upgrade head`**（`ALEMBIC_CONFIG=backend/alembic/alembic.ini`，库 URL 来自 **`INTY_CONFIG_YAML`**）。

本地 smoke / pytest / REPL 回归：**不要**再单独跑 `alembic upgrade head`。Postgres（**`localhost:15432`**）已起后，**至少启动一次 Ops**（见上节命令）即可把 schema 升到 head；Ops 可保持运行，或在 migrate 日志出现后再 Ctrl+C，再跑只连 DB 的 pytest。

`INTY_CONFIG_YAML` 使用仓库根目录为相对路径基准；**不传 `--workspace` 时**默认工作目录为仓库根下 **`.inty`**，文件日志 **`.inty/inty.log`**（启动时若已存在会先删除再写）；需要把日志放到其它目录时再传 **`--workspace DIR`**（见 **`backend/ops/start.sh --help`**）。

### 服务端 LangSmith（tracing 出 id）

后端从 **`INTY_CONFIG_YAML`**（本地固定为 **`devops/config.yaml.local`**）写入进程环境（[`app/core/config.py`](../../../app/core/config.py)）：

- `agent.langchain_api_key` → `LANGCHAIN_API_KEY`
- `agent.langsmith_tracing_enabled` → `LANGSMITH_TRACING_V2`
- `langsmith_text_chat_sample_rate`（本地 `devops/config.yaml.local` 常为 **1.0**）

本地评 companion 时 key 非空且 tracing 开启，REPL metadata 才可能出现 **`langsmith_trace_id=`**。这与 REPL 能否显示 **可点击 URL** 是两件独立的事（见下节）。

## REPL `.env`（与后端分离）

REPL **只**读 [`tools/inty_v2_repl/.env`](../../../tools/inty_v2_repl/.env)，**不**加载 `INTY_CONFIG_YAML`。Ops 已起、token 正确，仍可能 **只有 id 没有 url**。

首次或缺文件时：

```bash
cp tools/inty_v2_repl/.env.example tools/inty_v2_repl/.env
```

| 变量 | 来源 / 说明 |
| --- | --- |
| `INTY_ACCESS_TOKEN` | 写入 **`tools/inty_v2_repl/.env`**（与 **`.inty_ops_bearer_token`** 相同）；**已一致则不必再抄** |
| `INTY_API_BASE_URL` | 与 Ops 一致，默认 **`http://127.0.0.1:8001`**（`PORT` 覆盖时同步） |
| `INTY_V2_CHAT_AGENT_ID` | 可选；或 `repl --agent-id` |
| **`LANGCHAIN_API_KEY`** | **推荐**：与 `devops/config.yaml.local` 的 **`agent.langchain_api_key`** 相同；否则 metadata 常有 `langsmith_trace_id=` 但 **无** `langsmith_trace_url=` |

改 REPL `.env` 后 **重启 REPL**。无 feature flag；URL 解析失败会静默省略 url 字段（[`tools/inty_v2_repl/main.py`](../../../tools/inty_v2_repl/main.py)）。

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
# 对照 .inty_ops_bearer_token：已一致则不要重写 .env
FILE="$(cat .inty_ops_bearer_token | tr -d '[:space:]')"
ENV="$(grep '^INTY_ACCESS_TOKEN=' tools/inty_v2_repl/.env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')"
if [ -z "$ENV" ] || echo "$ENV" | grep -q '^<'; then
  echo "REPL: set INTY_ACCESS_TOKEN in .env from bearer file"
elif [ "$FILE" = "$ENV" ]; then
  echo "REPL: INTY_ACCESS_TOKEN matches bearer file (no .env update)"
else
  echo "REPL: INTY_ACCESS_TOKEN differs — update .env from bearer file"
fi
```

勿在聊天里粘贴完整 JWT。

```bash
AGENT_ID=$(python3 .cursor/skills/scripts/list_inty_ops_agents_admin.py | awk -F'\t' 'NR==1 {print $1}')
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
   - REPL：**`INTY_ACCESS_TOKEN` 与 `.inty_ops_bearer_token` 一致则不必再抄**；否则用 `cat .inty_ops_bearer_token` 更新 `.env`
4. **Agent ID**：`python3 .cursor/skills/scripts/list_inty_ops_agents_admin.py` 首列，或上节 `AGENT_ID=…`
5. **Terminal REPL**（另开终端，仓库根）— 见 [repl AGENTS.md](/tools/inty_v2_repl/AGENTS.md)
   - 确认 **`.env`** 含 **`INTY_ACCESS_TOKEN`**、**`INTY_API_BASE_URL`**、**`LANGCHAIN_API_KEY`**（与 config 相同）
   - 发一句试聊后，metadata 行宜含 **`langsmith_trace_url=https://…`**；若只有 `langsmith_trace_id=` → 补 REPL 的 `LANGCHAIN_API_KEY` 并重启 REPL
   - 全量检查：[`examine-local-inty-repl-env`](../examine-local-inty-repl-env/SKILL.md)
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
