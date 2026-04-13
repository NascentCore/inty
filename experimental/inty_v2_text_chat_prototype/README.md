# INTY v2 本地文本聊天原型

## 架构

本 prototype 是 `app/core/agentic_kernel/companion/` (companion kernel) 的 **REPL 外壳**,
用于产品经理持续迭代核心智能体陪伴体验.

- **核心组件** (models / prompts / workspace / file_store / utc / memory_store) 来自 companion kernel
- **本目录保留** REPL 壳 (main.py)、LLM 客户端 (client.py)、双路编排 (orchestrator.py)、
  异步工具后台 (tool_background.py)、生图/改图 (fal_z_image_tool.py)、联网检索 (google_web_search.py)、
  LLM trace (llm_trace.py) 等实验/REPL 特有模块
- 已有 `_ws/` workspace 目录完全兼容

详见 [companion kernel](/app/core/agentic_kernel/companion/) 和本目录 AGENTS.md.

## 安装

首先，在命令行安装 `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

拷贝默认配置文件到代码仓库的顶层目录（在代码库顶层目录运行）：

```bash
cp devops/config.yaml.dev config.yaml
```

依赖与 `.env`（在原型目录执行一次即可）：

```bash
cd experimental/inty_v2_text_chat_prototype
cp .env.example .env

# 编辑 .env 中这一行：LANGSMITH_PROJECT=inty-v2-text-chat-prototype-<USER>
# 将 <USER> 替换为你自己的名字
# 若不需 LangSmith 或 key 无效导致终端刷屏：在 .env 中设 LANGSMITH_TRACING_V2=false

uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

**必须从仓库根目录启动 REPL**：`app.core.config` 在导入时要求**当前工作目录**下存在 `config.yaml`（上文 `cp devops/config.yaml.dev config.yaml` 已在根目录提供该文件）。若在 `experimental/inty_v2_text_chat_prototype` 里直接 `python main.py`，会因找不到 `config.yaml` 而失败。

```bash
# 回到代码库的根目录
cd ../../
python experimental/inty_v2_text_chat_prototype/main.py repl \
  --workspace experimental/inty_v2_text_chat_prototype/_ws
```

bootstrap 阶段会由 AI 自然询问并确认用户期望的 companionship 类型（如朋友/爱人/亲人/自定义），无需命令行强制指定。

`--workspace` 使用相对**仓库根**的路径。`load_prototype_dotenv()` 会读取 cwd 的 `.env` 以及包目录下的 `.env`，因此在根目录启动时仍能加载 `experimental/inty_v2_text_chat_prototype/.env` 里的 API Key。

## 后端 WebSocket 模式（本地 Inty `/api/v1/chat/ws`）

与默认「本地磁盘 `_ws` + `run_turn`」不同，该模式把每一轮用户输入发到**本机已启动**的 Inty 后端 WebSocket，由服务端 companion 写 `chat_history` 与工作区；**不**启用 REPL 内在节拍、排程、本地 bootstrap / `repl_online` 等逻辑。

前置：Postgres + 仓库根 `config.yaml`，在仓库根执行 `./backend/inty/start.sh --test`（或其它方式让 HTTP 根可达，默认 `http://127.0.0.1:8000`）。在仓库根生成 JWT（需已配置 `config.yaml` 中的 JWT 密钥等）：

```bash
cd /path/to/inty/repo
source .venv/bin/activate
export PYTHONPATH=.
python -c "from app.core.security import create_access_token; print(create_access_token('user-testing'))"
```

将输出设为环境变量 `INTY_ACCESS_TOKEN`。再准备数据库里存在的 `agent_id`（可用 Ops 或 API 创建），通过 `--agent-id` 或环境变量 `INTY_V2_CHAT_AGENT_ID` 传入。

```bash
export INTY_ACCESS_TOKEN='<paste-jwt>'
export INTY_V2_CHAT_AGENT_ID='<agent-uuid>'
# 可选：export INTY_API_BASE_URL=http://127.0.0.1:8000

python experimental/inty_v2_text_chat_prototype/main.py repl --backend-ws

# 单轮
python experimental/inty_v2_text_chat_prototype/main.py once --backend-ws "你好"
```

也可不设 `--backend-ws`，改设环境变量 `INTY_V2_REPL_BACKEND_WS=1`（`true` / `yes` / `on` 均可）。

空闲保活：服务端对下一帧有超时（默认约 60s），客户端在后台线程内定期发送 JSON `{"type":"ping"}`。可调 `INTY_V2_BACKEND_WS_PING_INTERVAL_SEC`（默认 25）、单轮等待 `INTY_V2_BACKEND_WS_RECV_TIMEOUT_SEC`（默认 600）。

与本地 `_ws` 并行使用同一 `agent_id` 会在服务端与磁盘各有一套状态，产品联调时请以服务端为准。
