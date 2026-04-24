---
name: inty-server-module-verify
description: >-
  Runs repo-local smoke scripts under .cursor/skills/inty-server-module-verify/scripts against a
  configurable Inty API base URL and bearer token. Use when verifying backend modules against a
  running server (WebSocket chat /ws, etc.), when the user mentions server smoke tests, manual E2E,
  or INTY_BEARER_TOKEN / bearer_token in a local yaml / api_base_url checks.
---

# Inty 服务端模块验证（脚本 + 配置）

## 何时使用

- 需要在**真实运行中的服务端**上验证某个 HTTP/WebSocket 模块是否可用（与 pytest mock 单测互补）。
- 用户或 Agent 要执行「连一下测试环境 / 本地 8000」的**快速连通性检查**。

## 约定

1. **工作目录**：始终在**仓库根目录**执行下面的 `python` 命令；脚本会向上查找 `pyproject.toml` / `requirements.txt` 以加入 `sys.path`，从而复用 `app` 与 `tools/inty_v2_repl/backend_chat_ws.py`。
2. **凭据（Cursor 里无法在「聊天窗」里设置环境变量；命令是在终端里跑的）**  
   Token 优先级：`--token` 参数 > 环境变量 `INTY_BEARER_TOKEN` > 配置文件里可选字段 `bearer_token`。  
   常用方式：在 **Cursor 底部集成终端** 中先 `export INTY_BEARER_TOKEN=...` 再运行 `python3 .../test_chat_ws.py`；或将 [config.example.yaml](config.example.yaml) 复制为 `config.local.yaml`，填写 `bearer_token` 与 `agent_id` 等，并用 `-c` 指定（`config.local.yaml` 已列入本 skill 的 `.gitignore`）。**切勿**将含真 token 的文件提交到 git。  
   `INTY_API_BASE_URL` 可选，与 `--api-base` 或 `api_base_url` 二选一，例如 `http://127.0.0.1:8000`。
3. **配置文件**：使用 `--config` 指向 yaml 时若未安装 PyYAML，可执行  
   `pip install -r .cursor/skills/inty-server-module-verify/requirements.txt`。

## 脚本清单

| 脚本 | 验证目标 |
|------|----------|
| [scripts/test_chat_ws.py](scripts/test_chat_ws.py) | 伴侣聊天 WebSocket `/api/v1/chat/ws`（`chat_completions_websocket`），单轮用户消息 + 解析助手回复 |

后续新模块请新增 `scripts/test_<module>.py`，并复用同一套约定（`INTY_API_BASE_URL`、`INTY_BEARER_TOKEN`、以及可选的 `bearer_token` / `api_base_url` 等配置键名），避免每个脚本一套命名。

## Chat WebSocket（首支脚本）

### 行为说明

- **默认**（不带 `--connect-kickoff`）：WebSocket URL **不**带 query `agent_id`，与 [`chat_turn_single_http_base`](../../../tools/inty_v2_repl/backend_chat_ws.py) 一致，单轮发 `ChatWebSocketRequest`。
- **`--connect-kickoff`**：URL 为 `.../api/v1/chat/ws?agent_id=...`，连接后**最多**先收一帧再发用户轮次，用于覆盖服务端可能下发的 interactive bootstrap kickoff；若该帧为 `code != 200` 会报错退出。

### 运行示例

```bash
# 在仓库根目录，已激活 venv
export INTY_BEARER_TOKEN='...'
export INTY_API_BASE_URL='http://127.0.0.1:8000'

python3 .cursor/skills/inty-server-module-verify/scripts/test_chat_ws.py \
  --agent-id YOUR_AGENT_ID \
  -m "你好"
```

使用配置文件：

```bash
cp .cursor/skills/inty-server-module-verify/config.example.yaml /tmp/inty-verify.yaml
# 编辑 /tmp/inty-verify.yaml 中的 api_base_url、agent_id 等
python3 .cursor/skills/inty-server-module-verify/scripts/test_chat_ws.py -c /tmp/inty-verify.yaml
```

### 退出码

- `0`：收到 `code=200` 的回复并打印助手文本。
- `1`：业务错误、连接失败、未授权等。
- `2`：参数/配置不合法（缺少 `api_base`、`agent_id`、token 等）。

## 常见故障

| 现象 | 可能原因 |
|------|----------|
| WebSocket `4001` / 脚本提示 Unauthorized | `INTY_BEARER_TOKEN` 无效或未设置 |
| 连接超时 | `api_base_url` 不是当前环境地址，或服务未监听 |
| `BackendChatWsError` / 非 200 | 订阅限制、禁用接口、或 agent 不存在等，查看 stderr 中的 `code` 与 `message` |
| `Missing token` | 未设置 `INTY_BEARER_TOKEN` 且未传 `--token` / 配置中无 `bearer_token` |
| `python-socks is required to use a SOCKS proxy` | 本机环境变量里配置了 `socks5://` 等代理，而 websockets 默认会走代理。验证脚本已固定 **`proxy=None` 直连**，若你仍用旧版脚本，可 `pip install python-socks[asyncio]` 或取消相关代理环境变量 |
| 使用 `--config` 时提示需要 PyYAML | 安装 `requirements.txt` 中的依赖 |

## 与代码库的关系

- 协议与客户端复用 [tools/inty_v2_repl/backend_chat_ws.py](tools/inty_v2_repl/backend_chat_ws.py)；服务端实现见 [app/api/v1/endpoints/chat.py](app/api/v1/endpoints/chat.py) 中 `chat_completions_websocket`（`@router.websocket("/ws")`）。
