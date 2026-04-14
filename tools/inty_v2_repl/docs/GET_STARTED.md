# INTY v2 文本原型：启动后端与本地 REPL

本文说明如何在本机拉起 **Inty 主后端**，以及如何用本目录的 **REPL** 做联调测试。

## 0. 固定约定

- **工作目录**：凡运行 `python experimental/...` 或 `./backend/inty/start.sh`，均在 **仓库根目录** 的 shell 中执行。`app.core.config` 要求根目录存在 `config.yaml`。
- **虚拟环境与依赖**：与后端共用根目录 `.venv` 即可；需安装根 `requirements.txt` 与 `experimental/inty_v2_text_chat_prototype/requirements.txt`（首次安装步骤见 [README.md](../README.md)「安装」）。
- **环境变量**：`cp experimental/inty_v2_text_chat_prototype/.env.example .env` 并填入真实 Key；从根目录启动时 `load_prototype_dotenv()` 会加载该 `.env`。

**以下各节默认已执行**（路径请换成你的本机仓库）：

```bash
cd /path/to/inty/repo
uv venv
source .venv/bin/activate
# 安装 Inty 后端依赖文件
uv pip install -r requirements.txt
# 安装本地 repl 依赖文件
uv pip install -r experimental/inty_v2_text_chat_prototype/requirements.txt
export PYTHONPATH=.
```

## 启动 Inty 后端

```bash
# 启动后端数据库
docker run --rm --name pg-inty -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD='sxwl666!' \
  -e POSTGRES_DB=inty \
  -d postgres:16

# 拷贝配置文件
cp devops/config.yaml.local config.yaml

# 启动本地 Inty Ops 后端服务，包含了 Inty API server 及运营平台 Web UI
# 启动过程中会创建管理员账户及打印对应的 bearer token，复制并拷贝进 .env
# INTY_ACCESS_TOKEN
backend/ops/start.sh --local

# 启动 repl 之前，需要在运营平台上创建新的角色用于接入 Inty 后端。
# 记录该角色的 AGENT_ID，并将前面启动 Inty Ops 后端服务时拷贝的 bearer token
# 写入 .env 
# 在另一个 terminal 窗口启动 repl 实例

python experimental/inty_v2_text_chat_prototype/main.py repl \
    --backend-ws \
    --agent-id <AGENT_ID> \
    --api-base-url http://127.0.0.1:8001
```
