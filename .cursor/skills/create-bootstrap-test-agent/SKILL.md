---
name: create-bootstrap-test-agent
description: >-
  Creates a fresh PRIVATE agent on local Ops (:8001) for interactive bootstrap
  testing via POST /api/v1/ai/agents. Assumes Ops is already running and bearer
  is in .inty_ops_bearer_token. Use when the user asks for a new bootstrap test
  agent, bootstrap REPL agent, create agent on 8001, or to re-test
  companion_bootstrap_user_interactive_complete without reusing an old agent_id.
---

# Create bootstrap test agent (Ops :8001)

## 前提（默认，勿重复启动后端）

- **Ops 已在监听** **`http://127.0.0.1:8001`**（`PORT` 覆盖时同步 `--api-base` / `INTY_API_BASE_URL`）。
- **Bearer** 在仓库根 **[`.inty_ops_bearer_token`](../../../.inty_ops_bearer_token)**（`backend/ops/start.sh --local` 写入）。
- **工作目录**：仓库根。

未起 Ops 时见 [`launch-inty-backend`](../launch-inty-backend/SKILL.md)，**不要**在本 skill 里再跑 `start.sh`，除非用户明确要求启动。

## 执行

```bash
python3 tools/scripts/create_bootstrap_test_agent.py
```

可选：`--api-base`、`--token-file`、`--timeout`（与 [`list_inty_ops_agents_admin.py`](../../../tools/scripts/list_inty_ops_agents_admin.py) 同源约定）。

成功时 stdout 含固定前缀 **`[create-bootstrap-test-agent]`** 行：

- `agent_id=…`
- `name=…`
- `api_base=…`
- `repl_command=…`（整行可复制）

**Agent 汇报时优先复述 `agent_id` 与 `repl_command` 行**；勿在聊天粘贴完整 JWT。

## Terminal REPL

另开终端，仓库根：

```bash
python -m tools.inty_v2_repl.main repl \
  --api-base-url http://127.0.0.1:8001 \
  --agent-id <AGENT_ID>
```

或把 `repl_command=` 后的命令原样交给用户。

- 首次连 WS 走 **interactive bootstrap**；模型应调用 **`companion_bootstrap_user_interactive_complete`** 结束阶段。
- LangSmith / `.env`：[`examine-local-inty-repl-env`](../examine-local-inty-repl-env/SKILL.md)
- 库里 `context_mode`：[`inspect-companion-harness/context-mode-in-db`](../inspect-companion-harness/context-mode-in-db/SKILL.md)

## 与 smoke 的区别

| 方式 | 行为 |
|------|------|
| **本 skill / 脚本** | 只 **创建** agent，输出 id + REPL 命令 |
| [`test_chat_ws.py --create-agent`](../../../tools/scripts/inty_backend_smoke_tests/test_chat_ws.py) | 创建后 **再跑** WebSocket 单轮 smoke |

bootstrap 手测用本 skill；要自动验证 `/ws` 用 smoke。

## 给用户的最简回复

1. **Agent ID**（来自 `agent_id=` 行）
2. **REPL 命令**（来自 `repl_command=` 或上节模板）
3. 一句说明：新 agent、未走完 bootstrap 前勿复用旧 `agent_id`
