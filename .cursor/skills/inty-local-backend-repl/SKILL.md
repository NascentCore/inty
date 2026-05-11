---
name: inty-local-backend-repl
description: >-
  Repo root + venv: Ops :8001 (`backend/ops/start.sh`); list agent UUIDs via admin/list script below;
  then `python -m tools.inty_v2_repl.main repl`. Terminate Ops notes included. Full env: tools/inty_v2_repl/README.md
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

## 获取 agent-id（仓库根 cwd，`user-testing` superuser）

Bearer 默认读 **`${INTY_OPS_BEARER_TOKEN_FILE:-.inty_ops_bearer_token}`**（`--local` 启动已写入）。API 基址默认 **`http://127.0.0.1:8001`**；若使用环境变量 **`PORT`** 覆盖监听端口，请同步改 **`INTY_API_BASE_URL`**（例如 `export INTY_API_BASE_URL=http://127.0.0.1:9001`）。

下列脚本仅依赖 **stdlib**（无需 `jq`），打印 **`id<TAB>name`**：

```bash
INTY_API_BASE_URL="${INTY_API_BASE_URL:-http://127.0.0.1:8001}" python3 <<'PY'
import json, os, urllib.error, urllib.request

base = os.environ["INTY_API_BASE_URL"].rstrip("/")
path = os.environ.get("INTY_OPS_BEARER_TOKEN_FILE", ".inty_ops_bearer_token")
with open(path, encoding="utf-8") as f:
    tok = f.read().strip()
req = urllib.request.Request(
    f"{base}/api/v1/ai/agents/admin/list?limit=50",
    headers={"Authorization": f"Bearer {tok}"},
)
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.load(resp)
except urllib.error.HTTPError as e:
    raise SystemExit(f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:800]}") from e
rows = body.get("data") or []
if not rows:
    print(
        "admin/list returned no agents. Create one, then re-run:",
        "python3 scripts/inty_backend_smoke_tests/test_chat_ws.py \\",
        f"  --api-base {base} --create-agent",
        sep="\n",
    )
else:
    for a in rows:
        print(str(a.get("id", "")), str(a.get("name", "")), sep="\t")
PY
```

仅需 **第一条** UUID 时可：`… | awk -F'\t' 'NR==1 {print $1}'`。

## Final reply to user（默认）

Ops 就绪后，对用户依次给出下面 **三样**（不要默认展开 JWT、`ImportError`、`README` 等；用户追问再指路）：

1. 一行：`后端日志：<repo-root>/tmp/inty-ops-local.log`（与上文 `--log-file` 一致时）。
2. **本节「获取 agent-id」中的 `python3 <<'PY'` 整块**（让用户粘贴一行 `id` 给下一步）。
3. **仅** 下列 REPL 块；把 `YOUR_AGENT_ID` 换成上一步输出的 UUID。

```bash
source .venv/bin/activate && python -m tools.inty_v2_repl.main repl \
  --api-base-url http://127.0.0.1:8001 \
  --agent-id YOUR_AGENT_ID
```

（若实际 **`PORT`≠8001**，将两处 URL 中的端口改成一致。）

## 其它参考

- [`tools/inty_v2_repl/AGENTS.md`](../../../tools/inty_v2_repl/AGENTS.md)
