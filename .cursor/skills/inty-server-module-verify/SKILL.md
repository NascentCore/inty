---
name: inty-server-module-verify
description: >-
  Runs repo-local smoke scripts under tools/scripts/inty_backend_smoke_tests against a configurable Inty
  API base URL and bearer token (same directory holds config.example.yaml, requirements.txt,
  .gitignore). Use when verifying backend modules against a running server (WebSocket chat /ws,
  etc.), when the user mentions server smoke tests, manual E2E, or INTY_BEARER_TOKEN /
  bearer_token in a local yaml / api_base_url checks.
---

# Inty 服务端模块验证（脚本 + 配置）

## 何时使用

- 需要在**真实运行中的服务端**上验证某个 HTTP/WebSocket 模块是否可用（与 pytest mock 单测互补）。
- 用户或 Agent 要执行「连一下本地」的**快速连通性检查**。

## 本地推荐：backend/ops（运营平台）

**同一仓库里测 chat / agents 等接口时，优先用 Ops**，而不是单独起 `backend/inty`（:8000）：

- Ops 挂载与 App 共用的 **shared** 路由（含 [`backend/ops/api/v1/shared.py`](../../../backend/ops/api/v1/shared.py) 里的 `chat`、`chats` 等），HTTP/WebSocket 路径与 Inty 主后端一致（例如 WebSocket `/api/v1/chat/ws`）。
- `./backend/ops/start.sh --local` 会初始化 `user-testing`、跑迁移，并把 JWT 写入仓库根 **[`.inty_ops_bearer_token`](../../../backend/ops/start.sh)**（可用 `INTY_OPS_BEARER_TOKEN_FILE` 改路径）。smoke 脚本会**自动读取**该文件，通常无需再 `export INTY_BEARER_TOKEN`。
- 默认监听 **`http://127.0.0.1:8001`**（环境变量 `PORT` 可覆盖）。前端构建较慢时可加 **`--no-build-frontend`**。
- 流程示例：`./backend/ops/start.sh --local --no-build-frontend`（另开终端）→ `export INTY_API_BASE_URL=http://127.0.0.1:8001` → `python3 tools/scripts/inty_backend_smoke_tests/test_chat_ws.py --create-agent`。

若你只起了 **Inty 主后端**（`./backend/inty/start.sh ...`），则把 `INTY_API_BASE_URL` / `api_base_url` 设为 `http://127.0.0.1:8000` 并自行提供 token（或仍先用 Ops 写出 `.inty_ops_bearer_token` 仅当 token 来源，基址仍指向 8000 时需一致的有效 JWT；实践中**同源测 Ops 最省事**）。

## 约定

1. **工作目录**：始终在**仓库根目录**执行下面的 `python` 命令；脚本会向上查找 `pyproject.toml` / `requirements.txt` 以加入 `sys.path`，从而复用 `app` 与 `tools/inty_v2_repl/backend_chat_ws.py`。
2. **输出结论（必须）**：验证脚本在**结束前**须打印一行固定前缀的结论，便于 Agent 与用户不看全文也能判断是否通过：
   - 成功：`[inty-server-module-verify] RESULT: PASS (exit=0, elapsed=…s)`（stdout，接在助手正文之后）。
   - 失败：`[inty-server-module-verify] RESULT: FAIL (exit=…)`（stderr，附带简短原因）。
   **Agent 汇报「端到端 smoke 结果」时，应优先复述该行**，并与退出码交叉核对。
3. **凭据（Cursor 里无法在「聊天窗」里设置环境变量；命令是在终端里跑的）**  
   Token 优先级：`--token` 参数 > 环境变量 `INTY_BEARER_TOKEN` > 配置文件里可选字段 `bearer_token` > 仓库根 `.inty_ops_bearer_token`（见 `backend/ops/start.sh --local`）。  
   常用方式：在 **Cursor 底部集成终端** 中先 `export INTY_BEARER_TOKEN=...` 再运行 `python3 tools/scripts/inty_backend_smoke_tests/test_chat_ws.py`；或将 [config.example.yaml](../../../tools/scripts/inty_backend_smoke_tests/config.example.yaml) 复制为同目录下 `config.local.yaml`，填写 `bearer_token` 与 `agent_id` 等，并用 `-c` 指定（`config.local.yaml` 已列入 [tools/scripts/inty_backend_smoke_tests/.gitignore](../../../tools/scripts/inty_backend_smoke_tests/.gitignore)）。**切勿**将含真 token 的文件提交到 git。  
   `INTY_API_BASE_URL` 可选，与 `--api-base` 或 `api_base_url` 二选一；**本地配合 Ops** 时常用 `http://127.0.0.1:8001`，**仅 Inty 主后端**时用 `http://127.0.0.1:8000`。
4. **配置文件**：使用 `--config` 指向 yaml 时若未安装 PyYAML，可执行  
   `pip install -r tools/scripts/inty_backend_smoke_tests/requirements.txt`。

## 脚本清单

| 脚本 | 验证目标 |
|------|----------|
| [tools/scripts/inty_backend_smoke_tests/test_chat_ws.py](../../../tools/scripts/inty_backend_smoke_tests/test_chat_ws.py) | 伴侣聊天 WebSocket `/api/v1/chat/ws`（`chat_completions_websocket`），单轮用户消息 + 解析助手回复 |

后续新模块请在 `tools/scripts/inty_backend_smoke_tests/` 增加 `test_<module>.py`，并复用同一套约定（`INTY_API_BASE_URL`、`INTY_BEARER_TOKEN`、以及可选的 `bearer_token` / `api_base_url` 等配置键名），避免每个脚本一套命名。

## Chat WebSocket（首支脚本）

### 行为说明

- WebSocket URL 可为 `.../api/v1/chat/ws?agent_id=...`（与交互 REPL 一致）。服务端不在连接建立后主动推送开场；若需首轮问候，先发 `user_signed_on` 控制帧并设 `implicit_greeting: true` 与 RFC4122 `message_id`（见 `/app/core/companion_harness/environment/implicit_signal_messages.py`）。脚本若仍「先收再发」，仅适用于排空 ping 或异步 tool 补帧等场景。

### 运行示例

```bash
# 终端 A：仓库根，已激活 venv（推荐 Ops，token 自动写入 .inty_ops_bearer_token）
./backend/ops/start.sh --local --no-build-frontend

# 终端 B：仓库根，已激活 venv
export INTY_API_BASE_URL='http://127.0.0.1:8001'
# 可选：export INTY_BEARER_TOKEN='...'（不传则读仓库根 .inty_ops_bearer_token）

python3 tools/scripts/inty_backend_smoke_tests/test_chat_ws.py \
  --agent-id YOUR_AGENT_ID \
  -m "你好"
```

**无需预先持有 agent id**：加 `--create-agent`（或配置文件里 `create_agent: true`）会先 `POST /api/v1/ai/agents` 创建一个 PRIVATE 测试角色，stdout 会打印一行 `[inty-server-module-verify] created_agent_id=...`，再用该 id 跑同一套 WebSocket 单轮测试。若同时配置了 `--agent-id` / `agent_id`，以新建为准并忽略已有 id（stderr 会提示）。创建失败常见原因：账号已达角色创建上限（业务码非 200，`error_code` / `used_count` / `limit` 见 stderr）、或未登录 token 无效。

使用配置文件：

```bash
cp tools/scripts/inty_backend_smoke_tests/config.example.yaml /tmp/inty-verify.yaml
# 编辑 /tmp/inty-verify.yaml 中的 api_base_url、agent_id 等
python3 tools/scripts/inty_backend_smoke_tests/test_chat_ws.py -c /tmp/inty-verify.yaml
```

### 退出码

- `0`：收到 `code=200` 的回复并打印助手文本；stdout 末尾应有 `RESULT: PASS`。
- `1`：业务错误、连接失败、未授权等；stderr 末尾应有 `RESULT: FAIL`。
- `2`：参数/配置不合法（缺少 `api_base`、`agent_id`、token 等）；stderr 末尾应有 `RESULT: FAIL`。

### 成功输出示例（节选）

```text
[inty-server-module-verify] created_agent_id=<uuid>
OK (6.97s)

<助手回复正文>

[inty-server-module-verify] RESULT: PASS (exit=0, elapsed=6.97s)
```

（仅 `--create-agent` 时会出现第一行 `created_agent_id`。）

## 常见故障

| 现象 | 可能原因 |
|------|----------|
| WebSocket `4001` / 脚本提示 Unauthorized | `INTY_BEARER_TOKEN` 无效或未设置 |
| 连接超时 | `api_base_url` 不是当前环境地址，或服务未监听 |
| `BackendChatWsError` / 非 200 | 订阅限制、禁用接口、或 agent 不存在等，查看 stderr 中的 `code` 与 `message` |
| `Missing token` | 未设置 `INTY_BEARER_TOKEN` 且未传 `--token` / 配置中无 `bearer_token` |
| `create agent failed` / `AGENT_CREATION_LIMIT_REACHED` | 用户自建角色数已达上限；删旧角色或换账号 / superuser，再试 `--create-agent` |
| `python-socks is required to use a SOCKS proxy` | 本机环境变量里配置了 `socks5://` 等代理，而 websockets 默认会走代理。验证脚本已固定 **`proxy=None` 直连**，若你仍用旧版脚本，可 `pip install python-socks[asyncio]` 或取消相关代理环境变量 |
| 使用 `--config` 时提示需要 PyYAML | `pip install -r tools/scripts/inty_backend_smoke_tests/requirements.txt` |

## 与代码库的关系

- 协议与客户端复用 [tools/inty_v2_repl/backend_chat_ws.py](../../../tools/inty_v2_repl/backend_chat_ws.py)；服务端实现见 [app/api/v1/endpoints/chat.py](../../../app/api/v1/endpoints/chat.py) 中 `chat_completions_websocket`（`@router.websocket("/ws")`）。
