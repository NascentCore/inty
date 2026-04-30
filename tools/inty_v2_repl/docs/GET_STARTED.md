# INTY v2 文本原型：启动后端与本地 REPL

本文说明如何在本机拉起 **Inty 主后端**（或与 Ops 同栈的本地 API），以及如何用 **`tools/inty_v2_repl`** 的 REPL 做联调测试。

## 0. 固定约定

- **工作目录**：凡运行 `python -m tools.inty_v2_repl...` 或 `./backend/inty/start.sh` / `backend/ops/start.sh`，均在 **仓库根目录** 的 shell 中执行。`app.core.config` 要求根目录存在 `config.yaml`。
- **虚拟环境与依赖**：与后端共用根目录 `.venv` 即可；需安装根 `requirements.txt` 与 `tools/inty_v2_repl/requirements.txt`（更多说明见 [README.md](../README.md)「安装」）。
- **环境变量（REPL）**：`load_prototype_dotenv()` 会依次加载 **当前工作目录** 下的 `.env`，以及 **`tools/inty_v2_repl/.env`**（后者可用 [`tools/inty_v2_repl/.env.example`](../.env.example) 复制得到）。**已在 shell 中 `export` 的变量优先于 `.env` 中的同名键**（`python-dotenv` 默认 `override=False`）。
- **环境变量（Inty / Ops / push_worker 进程）**：`backend/inty/main.py`、`backend/ops/main.py`、`backend/push_worker/main.py` 在导入 `app` 之前调用 `load_dotenv()`（无参），从 **进程当前工作目录** 读取 `.env`（与上文「始终在仓库根执行」一致）。可选：在仓库根保留 `.env` 仅用于 `INTY_LOGGING_LEVEL` / `INTY_LOG_FILE` 等日志相关变量（见下表）；与 REPL 的 `tools/inty_v2_repl/.env` 相互独立。

**以下各节默认已执行**（路径请换成你的本机仓库）：

```bash
cd /path/to/inty/repo
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -r tools/inty_v2_repl/requirements.txt
export PYTHONPATH=.
```

## 启动 Inty 后端（Ops 本地栈）

```bash
# 启动后端数据库
docker run --rm --name pg-inty -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD='sxwl666!' \
  -e POSTGRES_DB=inty \
  -d postgres:16

# REPL 用的环境文件（与后端无关，可提前建好）
cp tools/inty_v2_repl/.env.example tools/inty_v2_repl/.env

# 拷贝配置文件
cp devops/config.yaml.local config.yaml

# 启动本地 Inty Ops 后端（含 Inty API 与运营 Web UI）
# --no-build-frontend：跳过 evaluation 前端构建（依赖已有 app/static/evaluation；首次或改版评测 UI 时请去掉）
# 启动过程中会打印 bearer token：写入 tools/inty_v2_repl/.env 的 INTY_ACCESS_TOKEN
backend/ops/start.sh --local --debug --log-file ./inty-ops-local.log --no-build-frontend
```

### `backend/ops/start.sh`：`--debug` 与 `--log-file`

与 `--local`（或 `--dev`）组合使用，便于联调 WebSocket、`/api/v1/chat/ws`、companion 等：

- **`--debug`**：导出 `INTY_LOGGING_LEVEL=DEBUG`，并为 uvicorn 增加 `--log-level debug`，应用内 Loguru 与访问日志更细。
- **`--log-file PATH`**：导出 `INTY_LOG_FILE=PATH`，由 `app/core/logging.py` 为 Loguru **追加**一个 UTF-8 文件 sink（与控制台并行）。与 **`--debug` 同用时**，脚本会设 `INTY_CONSOLE_LOGGING_LEVEL=INFO`，终端 INFO、文件仍 DEBUG。`PATH` 相对**当前 shell 工作目录**。
- **`--no-build-frontend`**：`--local` 下不执行 `evaluation/build.sh`，沿用现有 `app/static/evaluation`。默认会先构建评测静态资源；需要刷新前端产物时去掉该参数或传 `--build-frontend`。

查看全部选项：`backend/ops/start.sh --help`。

若只跑 `./backend/inty/start.sh --test` 等未封装上述 flag 的入口，可在仓库根 `.env` 中写入下表变量，或启动前手动 `export`（由 `app/core/logging.py` 的 `init_logger()` 读取）。

### 后端日志相关环境变量（可选）

| 变量 | 作用 |
|------|------|
| `INTY_LOGGING_LEVEL` | Loguru **文件** sink 与「控制台默认级别」的基准（如 `DEBUG`、`INFO`）。未设置时回落到 `config.yaml` 的 `logging.level`。 |
| `INTY_CONSOLE_LOGGING_LEVEL` | 仅控制 **stderr** 上的 Loguru 级别；未设置时与 `INTY_LOGGING_LEVEL`（或 YAML）相同。可与 `INTY_LOGGING_LEVEL=DEBUG` 组合实现「终端 INFO、文件 DEBUG」。 |
| `INTY_LOG_FILE` | 若为非空路径，Loguru 额外 **追加** UTF-8 文件 sink（`enqueue=True`）。路径为**相对路径时相对于进程 cwd**，请在仓库根启动或写绝对路径。 |

LangSmith tracing 默认开启：未在 YAML 中写出时等价 **`agent.langsmith_tracing_enabled: true`**。若要关闭，在 `config.yaml` 的 `agent` 段显式设 **`langsmith_tracing_enabled: false`**。`app.core.config` 在导入时写入进程内的 `LANGSMITH_TRACING_V2`，并设置 `LANGSMITH_PROJECT` 与 `LANGCHAIN_API_KEY`。

Ops 平台启动后，参考下面的截图来创建智能体，并使用该智能体进行测试。

<img width="600" height="1140" alt="image" src="https://github.com/user-attachments/assets/ef6e2ec7-bcdb-46d1-8dee-085d0c66670f" />
<img width="600" height="1512" alt="image" src="https://github.com/user-attachments/assets/9c337f9b-174f-469d-bf97-a772063ff9cf" />

## 启动 REPL（后端 WebSocket）

1. 打开运营平台：<http://localhost:8001/>，在平台上创建角色并记下 **AGENT_ID**。
2. 将 Ops 启动时打印的 **bearer token** 与 `AGENT_ID` 写入 **`tools/inty_v2_repl/.env`**（推荐），或在另一个终端里 `export`。

```bash
# 仓库根目录，已 export PYTHONPATH=.
python -m tools.inty_v2_repl.main repl \
  --agent-id <AGENT_ID> \
  --api-base-url http://127.0.0.1:8001
```

Bearer：`INTY_ACCESS_TOKEN` 或 `INTY_BEARER_TOKEN`，缺省时读取仓库根 `.inty_ops_bearer_token`（`backend/ops/start.sh --local` 会写入）。`--agent-id` 可由 `INTY_V2_CHAT_AGENT_ID` 代替（也可写在 `tools/inty_v2_repl/.env`）。

### REPL 后端 WebSocket：自动重连

REPL 在**单独的后台线程**里维持到 `INTY_API_BASE_URL` 对应主机的 `/api/v1/chat/ws` 连接：

- **读循环结束**（对端关闭、网络闪断等）时，同一线程会按 **指数退避** 自动再次 `connect`，一般**不必**为短暂断网重启 REPL 进程。
- **正在发送的一轮**若遇到已关闭的 socket（`ConnectionClosed`），会**整轮重试**（含重新发同一条用户消息），次数有上限。

可调环境变量（默认值见下）：

| 变量 | 含义 |
|------|------|
| `INTY_V2_BACKEND_WS_RECONNECT_INITIAL_SEC` | 重连退避初始间隔秒（0.5） |
| `INTY_V2_BACKEND_WS_RECONNECT_MAX_SEC` | 退避上限秒（20） |
| `INTY_V2_BACKEND_WS_SEND_RETRIES` | 单轮发送遇断连时的最大重试次数（8） |
| `INTY_V2_BACKEND_WS_PING_INTERVAL_SEC` | 客户端 JSON `ping` 间隔秒（25） |
| `INTY_V2_BACKEND_WS_RECV_TIMEOUT_SEC` | 单轮等待服务端带 `code` 的回包上限秒（600） |

### 输入与并发（全双工）

- **行为**：`send_turn` 在**后台线程**执行时，在 **POSIX 终端**下主循环仍可用 `select` 读入**下一整行**并先排进 FIFO，上一轮返回后再按顺序发出；在 `>` 无进行中的轮次时，仍像以往一样可 `try_pop_queued_chat` 打印**空闲**时服务端已入队的侧带消息；**有未完成的 `send_turn` 时**不再 `try_pop`（与共享 `_response_q` 的 FIFO 一致，避免抢帧）。
- **非 TTY / Windows**：等回复时仅退化为周期等待，**不能**在等一条回复时先敲下一行（可改终端或 `export` 到类 Unix 环境）。

CLI 仅保留 `repl`；对话与 bootstrap 由服务端处理。`--workspace` 仅影响本地日志等输出路径（如 `inty_v2.log`）。
