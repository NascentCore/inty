# INTY v2 文本原型：启动后端与本地 REPL

本文说明如何在本机拉起 **Inty 主后端**（FastAPI，默认 `http://127.0.0.1:8000`），以及如何用本目录的 **REPL** 做联调或纯本地 `run_turn` 测试。更完整的依赖与架构见 [README.md](../README.md)。

## 0. 固定约定

- **工作目录**：凡运行 `python experimental/...` 或 `./backend/inty/start.sh`，均在 **仓库根目录** 的 shell 中执行。`app.core.config` 要求根目录存在 `config.yaml`。
- **虚拟环境与依赖**：与后端共用根目录 `.venv` 即可；需安装根 `requirements.txt` 与 `experimental/inty_v2_text_chat_prototype/requirements.txt`（首次安装步骤见 [README.md](../README.md)「安装」）。
- **环境变量**：在 `experimental/inty_v2_text_chat_prototype` 下 `cp .env.example .env` 并填入真实 Key；从根目录启动时 `load_prototype_dotenv()` 仍会加载该 `.env`。

**以下各节默认已执行**（路径请换成你的本机仓库）：

```bash
cd /path/to/inty/repo
source .venv/bin/activate
export PYTHONPATH=.
```

## 1. 启动 Inty 后端

1. **PostgreSQL 16**（端口占用时请改 `-p` 映射并在 `config.yaml` 里改连接串；容器名冲突时改掉 `--name`）：

```bash
docker run --rm --name pg-inty -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD='sxwl666!' \
  -e POSTGRES_DB=inty \
  -d postgres:16
```

可用 `docker exec pg-inty pg_isready -U postgres` 确认就绪。

2. **根目录配置**（任选其一）：

```bash
cp devops/config.yaml.test config.yaml
# 或: cp devops/config.yaml.dev config.yaml
```

3. **启动服务**（`start.sh` 内已 `export PYTHONPATH=.`；`--test` 为带 `--reload` 的开发模式，并会跑迁移与种子脚本，见仓库根 [AGENTS.md](../../../AGENTS.md)）：

```bash
./backend/inty/start.sh --test
```

就绪后可用浏览器或 `curl -sS http://127.0.0.1:8000/` 访问根路径健康检查（返回 JSON 即表示进程已监听）。再按第 2.2 节接 REPL 的 WebSocket 模式。

## 2. 本地 REPL 的两种用途

| 模式 | 作用 | 是否需要后端已启动 |
|------|------|---------------------|
| **本地 workspace**（默认） | 磁盘 `_ws` + `run_turn`，走 OpenRouter 等与 [README.md](../README.md) 一致的工具链；含 bootstrap / 内在节拍 / 排程等 | 否 |
| **`--backend-ws`** | 每轮用户输入走 Inty **`/api/v1/chat/ws`**，服务端写 `chat_history`；REPL 不跑本地 bootstrap / `repl_online` 等 | 是 |

### 2.1 本地 workspace REPL（不测后端 HTTP）

在第 0 节同一 shell 中：

```bash
python experimental/inty_v2_text_chat_prototype/main.py repl \
  --workspace experimental/inty_v2_text_chat_prototype/_ws
```

未初始化工作区时 `repl` 会自动跑一轮 bootstrap；也可先落盘空壳：

```bash
python experimental/inty_v2_text_chat_prototype/main.py init-workspace \
  --path experimental/inty_v2_text_chat_prototype/_ws
```

`--workspace` 为相对仓库根的路径。输入 `quit` 或 EOF 结束。

### 2.2 对接本机后端的 WebSocket REPL

1. 按 **第 1 节** 启动 Postgres 与 `./backend/inty/start.sh --test`。
2. **JWT 的 `sub` 必须是数据库里存在的用户 `id`**。`start.sh --test` 会执行 `scripts/create_email_password_user.py` 创建 `test@sxwl.ai`；脚本日志里会有 `User ID: ...`，将该 id 传入 `create_access_token`：

```bash
python -c "from app.core.security import create_access_token; print(create_access_token('<User ID from log>'))"
```

若你本地另有固定测试用户（例如自行跑通过 `init_admin_user` 写入的 `user-testing`），也可把对应 id 作为参数。仓库根 [AGENTS.md](../../../AGENTS.md) 中的 `user-testing` 示例仅在**该用户确实存在于当前库**时成立。

3. 在数据库中准备一个真实 **`agent_id`**（Ops 或 API 创建），然后：

```bash
export INTY_ACCESS_TOKEN='<上一步输出的 token>'
export INTY_V2_CHAT_AGENT_ID='<agent-uuid>'
# 可选: export INTY_API_BASE_URL=http://127.0.0.1:8000

python experimental/inty_v2_text_chat_prototype/main.py repl --backend-ws
```

单轮冒烟：

```bash
python experimental/inty_v2_text_chat_prototype/main.py once --backend-ws "你好"
```

也可用环境变量 `INTY_V2_REPL_BACKEND_WS=1`（`true` / `yes` / `on`）代替命令行 `--backend-ws`。空闲保活与超时相关变量见 [README.md](../README.md) 中「后端 WebSocket 模式」一节。

## 3. 常见问题

- **Import 或找不到 `config.yaml`**：确认 cwd 为仓库根，且根目录已有 `config.yaml`。
- **WebSocket 401**：核对 `INTY_ACCESS_TOKEN` 是否用**当前库中存在的用户 id** 签发、是否与当前 `config.yaml` 的 JWT 密钥一致；不要用未创建用户的占位 id。
- **连不上 HTTP**：核对 `INTY_API_BASE_URL`、防火墙与端口；确认第 1 节服务已起来。
- **与 `_ws` 并行同一 `agent_id`**：服务端状态与本地磁盘各一套，联调以服务端为准。
