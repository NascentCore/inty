---
name: examine-local-inty-repl-env
description: >-
  Checklist and commands to verify local Inty Ops backend + inty_v2_repl environment
  (venv, INTY_CONFIG_YAML, bearer, API port, LangSmith trace IDs and clickable URLs in REPL
  metadata). For human partners—especially non-engineers—confirming dev setup before
  product evaluation.
  Triggers: 检查本地环境、REPL 没有 langsmith url、环境对不对、
  examine local inty repl env, setup verification, local environment check, etc.
  Also the corresponding Mandarian words（包括对应的中文描述）
---

# Examine local Inty Ops backend + REPL environment

## 读者与目标

- **读者**：人类队友（尤其 **产品经理** 王琢誉）在本地用 **Ops 后端 + terminal REPL** 评 iMate / companion 前，确认「该开的都开了、该配的都配了」。
- **智能体职责**：在仓库根 **实际执行** 下面检查（只读为主），用文末 **报告模板** 回复；密钥只报 **是否已设置**，勿把完整 token/API key 贴进聊天。
- **不替代**：拉后端见 [`launch-inty-backend`](../launch-inty-backend/SKILL.md)；解读单行 metadata 见 [`inspect-repl-message-metadata`](../inspect-repl-message-metadata/SKILL.md)。

## 快速结论（先读）

| 现象 | 常见原因 |
| --- | --- |
| REPL 连不上 / 401 | `tools/inty_v2_repl/.env` 缺 **`INTY_ACCESS_TOKEN`**，或与 `.inty_ops_bearer_token` **不一致**（后端重启后会换新 JWT） |
| metadata **没有** `langsmith_trace_id=` | **服务端** 未 tracing（config / sample rate / key） |
| 有 `langsmith_trace_id=` **没有** `langsmith_trace_url=` | **REPL 进程** 缺 `LANGCHAIN_API_KEY`（与后端 config 无关） |
| 新 agent 首句不像 bootstrap | `context_mode` 非 bootstrap 或 bootstrap 已完成；见 [`inspect-companion-harness/context-mode-in-db`](../inspect-companion-harness/context-mode-in-db/SKILL.md) |

REPL **没有** LangSmith URL 的开关；有 id 就会尝试拼 URL，失败则**静默省略** url 字段（[`tools/inty_v2_repl/main.py`](../../../tools/inty_v2_repl/main.py)）。

---

## 检查流程（智能体按序执行）

### A. 仓库与 Python 环境

```bash
# 仓库根
test -d .venv && echo "venv: yes" || echo "venv: MISSING"
test -f requirements.txt && test -f tools/inty_v2_repl/requirements.txt && echo "requirements: ok"
source .venv/bin/activate 2>/dev/null || true
python -c "import websockets, cyclopts, dotenv; print('repl deps: ok')" 2>&1
python -c "import langsmith; print('langsmith package: ok')" 2>&1 || echo "langsmith package: MISSING (install root requirements.txt)"
```

**期望**：存在 `.venv`；`langsmith` 可 import（来自根目录 `requirements.txt`）。

### B. 后端配置（`INTY_CONFIG_YAML`）

```bash
export INTY_CONFIG_YAML=devops/config.yaml.local
test -f "${INTY_CONFIG_YAML}" && echo "config: ${INTY_CONFIG_YAML}" || echo "config: MISSING"
```

智能体用 **只读** 方式确认（勿输出 secret 全文）：

- `agent.langchain_api_key` 非空（服务端 LangSmith tracing 需要）。
- 本地评 companion 建议：`agent.langsmith_tracing_enabled` 为 true；`langsmith_text_chat_sample_rate: 1.0`（见 `devops/config.yaml.local`）。
- 本地 project 名规则：`{app.name}-{environment}`，environment 为 `local` 时带 `-{username}` slug（与 [`app/core/config.py`](../../../app/core/config.py) `set_langsmith_environment_variables` 一致）。

### C. Ops 后端是否在听

```bash
PORT="${PORT:-8001}"
lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null | head -3 || echo "port ${PORT}: not listening"
curl -s -o /dev/null -w "HTTP %{http_code}\n" "http://127.0.0.1:${PORT}/docs" 2>/dev/null || echo "curl failed"
test -f .inty_ops_bearer_token && echo "bearer file: .inty_ops_bearer_token present" || echo "bearer file: MISSING (run backend/ops/start.sh --local)"
```

**期望**：`8001`（或你的 `PORT`）在 listen；`/docs` 返回 2xx/3xx；存在 `.inty_ops_bearer_token`。

未启动时：按 [`launch-inty-backend`](../launch-inty-backend/SKILL.md) 指引用户，**不要**假定后端已跑。

### D. REPL 专用 `.env`（与后端 **分离**）

REPL **只**加载 [`tools/inty_v2_repl/.env`](../../../tools/inty_v2_repl/.env)，**不**读 **`INTY_CONFIG_YAML`**（[`repl_dotenv.py`](../../../tools/inty_v2_repl/repl_dotenv.py)）。

```bash
REPL_ENV=tools/inty_v2_repl/.env
test -f "$REPL_ENV" && echo "repl .env: present" || echo "repl .env: MISSING (cp .env.example)"
# 仅报告 key 是否存在（不打印值）
for key in INTY_ACCESS_TOKEN INTY_V2_CHAT_AGENT_ID INTY_API_BASE_URL LANGCHAIN_API_KEY LANGSMITH_API_KEY LANGCHAIN_WORKSPACE_ID LANGSMITH_WORKSPACE_ID LANGSMITH_PROJECT_ID LANGCHAIN_PROJECT_ID LANGCHAIN_ENDPOINT LANGSMITH_ENDPOINT; do
  if grep -q "^${key}=" "$REPL_ENV" 2>/dev/null; then
    val=$(grep "^${key}=" "$REPL_ENV" | head -1 | cut -d= -f2-)
    if [ -n "$(echo "$val" | tr -d '[:space:]')" ] && ! echo "$val" | grep -q '^<'; then
      echo "${key}: set"
    else
      echo "${key}: placeholder or empty"
    fi
  else
    echo "${key}: absent"
  fi
done
```

**Bearer：是否要改 REPL `.env`**（不打印 token 全文；`.inty_ops_bearer_token` 仅作对照真源）：

```bash
FILE="$(cat .inty_ops_bearer_token 2>/dev/null | tr -d '[:space:]')"
ENV="$(grep '^INTY_ACCESS_TOKEN=' tools/inty_v2_repl/.env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')"
if [ -z "$FILE" ]; then echo "bearer file: empty or missing"
elif [ -z "$ENV" ] || echo "$ENV" | grep -q '^<'; then echo "INTY_ACCESS_TOKEN: set in .env from bearer file (copy needed)"
elif [ "$FILE" = "$ENV" ]; then echo "INTY_ACCESS_TOKEN: matches bearer file (skip .env update)"
else echo "INTY_ACCESS_TOKEN: DIFFERS — paste bearer file into .env"; fi
```

**期望（REPL 可连 + 可点 LangSmith）**

| 变量 | 用途 |
| --- | --- |
| `INTY_ACCESS_TOKEN` | REPL 鉴权来源（写在 `.env`）；与 `.inty_ops_bearer_token` **已相同则不必再抄** |
| `INTY_API_BASE_URL` | 与 Ops 一致，本地通常 `http://127.0.0.1:8001` |
| `INTY_V2_CHAT_AGENT_ID` | 可选；也可用 `--agent-id` |
| `LANGCHAIN_API_KEY` | **必填** 才能在 metadata 行出现 `langsmith_trace_url=`；值可与 `devops/config.yaml.local` 的 `agent.langchain_api_key` 相同 |

**可选（仅 SDK 失败时的拼接兜底）**：`LANGSMITH_WORKSPACE_ID` + `LANGSMITH_PROJECT_ID`（LangSmith UI 里的 **session UUID**，不是 `LANGSMITH_PROJECT` 字符串名）。后端启动时**不会**自动写入这两项。

修改 REPL `.env` 后 **必须重启 REPL**（`langsmith` import 失败会在进程内永久禁用）。

### E. LangSmith URL 解析自检（REPL 侧）

在 **已 activate 的 venv** 且 **已 export 与 REPL `.env` 相同的 `LANGCHAIN_API_KEY`** 时：

```bash
# 将 RUN_UUID 换成用户 metadata 行里的 langsmith_trace_id
export RUN_UUID="<paste-from-repl-metadata>"
python -c "
import os
from types import SimpleNamespace
from langsmith import Client
ru = os.environ.get('RUN_UUID', '').strip()
key = (os.environ.get('LANGCHAIN_API_KEY') or os.environ.get('LANGSMITH_API_KEY') or '').strip()
print('LANGCHAIN_API_KEY:', 'set' if key else 'MISSING')
if not ru:
    print('RUN_UUID: empty — skip get_run_url')
else:
    try:
        url = Client(auto_batch_tracing=False).get_run_url(run=SimpleNamespace(id=ru))
        print('get_run_url:', url[:80] + '...' if len(url) > 80 else url)
    except Exception as e:
        print('get_run_url FAILED:', type(e).__name__, e)
"
```

**判定**

- `get_run_url` 有 URL → REPL metadata 应能显示 `langsmith_trace_url=`；若仍没有，确认 REPL 是否用同一 `.env` 启动、是否重启过。
- key MISSING → 在 `tools/inty_v2_repl/.env` 增加 `LANGCHAIN_API_KEY`。
- FAILED + 无效 UUID → trace 不在当前 key 可访问的 project/org，或 id 来自别的环境。

### F. 一次 REPL 会话的「冒烟信号」（需用户配合或已有粘贴）

请用户贴 **任意一行** assistant metadata section，或智能体引导用户发一句「你好」后看输出：

```
[墙钟] chat 1234ms user_msg_uuid=... langsmith_trace_id=... langsmith_trace_url=https://...
```

| metadata 内容 | 含义 |
| --- | --- |
| 无 `langsmith_trace_id` | 服务端本回合未 tracing → 查 **B** 节 config / 后端是否重启 |
| 有 id、无 url | 查 **D / E**（REPL key） |
| 有 `langsmith_trace_url` | LangSmith 链路对 PM 调试 **OK** |
| `tool_background_started=true` | 正常：前台先回、后台 tool；不是错误 |
| label `inner-tick proactive-chat` 等 | 见 [`inspect-repl-message-metadata`](../inspect-repl-message-metadata/SKILL.md) |

下载 trace 做深查：[`langsmith-download-run`](../langsmith-download-run/SKILL.md)。

### G. Bootstrap / 关系建立阶段（可选）

产品经理评「第一次见面 / 定人设」时：

- 新 agent **首条 implicit sign-on** 的 `meta_data.context_mode` 应为 `bootstrap`（E2E：`tests/app/features/test_companion_ws_bootstrap_e2e.py`）。
- 用户口头「定下来」后的「初始化完毕」类话术多为 **模型即兴**，不是固定产品文案；规范见 [`BOOTSTRAP.md`](../../../app/core/companion_harness/companion/prompts/BOOTSTRAP.md)（应用关系语境，避免工程术语）。
- DB 真源：`context.json` 的 `workspace_bootstrap_user_interactive_completed`、`context_mode` → [`context-mode-in-db`](../inspect-companion-harness/context-mode-in-db/SKILL.md)。

---

## 给人类队友的修复速查

1. **从未配 REPL**  
   `cp tools/inty_v2_repl/.env.example tools/inty_v2_repl/.env`  
   `INTY_API_BASE_URL=http://127.0.0.1:8001`、`LANGCHAIN_API_KEY`（与 `devops/config.yaml.local` 的 `agent.langchain_api_key` 相同）。  
   **`INTY_ACCESS_TOKEN`**：用 `cat .inty_ops_bearer_token` 填入；**若 `.env` 里已有且与文件相同，不要重复覆盖**。

2. **后端未起**  
   `export INTY_CONFIG_YAML=devops/config.yaml.local` → `backend/ops/start.sh --local`（见 launch skill）。

3. **有 trace id、无 url**  
   几乎总是 REPL 缺 `LANGCHAIN_API_KEY`；改 `.env` 后 **重启 REPL**。

4. **连 id 都没有**  
   查服务端 `devops/config.yaml.local` tracing / sample rate / `langchain_api_key`；重启 Ops。

5. **EU / 自建 LangSmith**  
   REPL `.env` 增加 `LANGCHAIN_ENDPOINT`（与组织一致）。

---

## 报告模板（智能体回复人类时用）

```markdown
## 本地 Inty + REPL 环境检查

**检查时间**：…
**config**：…
**Ops 端口**：… （listen: 是/否）

### 结果摘要
- [ ] Python venv + REPL 依赖
- [ ] Ops 后端在听 + bearer 文件存在
- [ ] `INTY_ACCESS_TOKEN` 已在 REPL `.env` 且与 `.inty_ops_bearer_token` 一致（一致则无需再改）
- [ ] `LANGCHAIN_API_KEY`（REPL）已设置 ← LangSmith 可点击链接的关键
- [ ] （可选）`get_run_url` 对样例 run id 成功
- [ ] （可选）用户粘贴的 metadata 含 `langsmith_trace_url`

### 待办（按优先级）
1. …
2. …

### 参考
- 启动后端：launch-inty-backend
- 解读 metadata 行：inspect-repl-message-metadata
```

---

## 相关文件

| 路径 | 说明 |
| --- | --- |
| [`tools/inty_v2_repl/.env.example`](../../../tools/inty_v2_repl/.env.example) | REPL 环境变量模板 |
| [`tools/inty_v2_repl/AGENTS.md`](../../../tools/inty_v2_repl/AGENTS.md) | REPL 边界与启动 |
| [`devops/config.yaml.local`](../../../devops/config.yaml.local) | 本地 tracing sample rate 参考 |
| [`app/core/config.py`](../../../app/core/config.py) | 服务端 LangSmith 环境变量 |
