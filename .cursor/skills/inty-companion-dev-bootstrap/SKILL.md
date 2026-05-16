---
name: inty-companion-dev-bootstrap
description: >-
  Bootstrap a machine for Inty agentic companion development: Docker PostgreSQL 16 on
  localhost:5432 aligned with app DatabaseSettings defaults (user postgres, password
  sxwl666!, database inty), Python venv or uv, install requirements, choose
  devops/config.yaml.local vs devops/config.yaml.test via INTY_CONFIG_YAML or root
  config.yaml, then Ops and terminal REPL. Use when onboarding a new engineer or agent,
  "first time dev setup", "local Postgres for companion", companion harness work under
  app/core/companion_harness before inty-local-backend-repl, or when CI-local docs assume
  a DB that is not running yet. Not for LiteLLM proxy (tools/lite_llm_proxy) or
  experimental locust compose stacks.
---

# Inty agentic companion：本地开发环境初始化

## 意图

把 **数据库 + Python 依赖 + 配置入口** 一次对齐到仓库默认假设，使 **Ops（:8001）** 能跑迁移并承载 **companion harness**；具体起服与 REPL 见 **inty-local-backend-repl**，CI 镜像流程见 **inty-backend-ci-local**。

## 前置

- **Docker**（用于本机 PostgreSQL；与 CI / `devops/config.yaml.test` 一致为 **postgres:16**）。
- **Python 3.12**（与 `.github/workflows/ci_backend.yaml` 一致）。
- Shell **cwd** 为 **仓库根目录**（下文路径均相对根目录）。

## 1) PostgreSQL 容器

默认连接参数见 [`app/utils/config.py`](../../../app/utils/config.py) 中 `DatabaseSettings`：`host=localhost`、`port=5432`、`user=postgres`、`password=sxwl666!`、`db=inty`。容器需与之匹配。

若 **5432 已被占用**，先停止占用该端口的进程或其它容器，再执行；**不要**在未与用户约定的情况下改端口改配置。

启动（与 `backend/ops/README.md` 一致；密码用单引号避免 `!` 被 shell 误解析；显式 `POSTGRES_USER` 与 `inty-backend-ci-local` 的 CI 用例对齐）：

```bash
docker run --rm --name pg-inty \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD='sxwl666!' \
  -e POSTGRES_DB=inty \
  -p 5432:5432 -d postgres:16
```

就绪检查：

```bash
docker exec pg-inty pg_isready -U postgres
```

`inty-backend-ci-local` 示例容器名为 **`inty-ci-pg`**，与本节 **`pg-inty`** 二选一即可，**不要**同时占 **5432**。

## 2) Python 环境与依赖

任选其一，与团队习惯一致即可：

**A. uv（`backend/ops/README.md` 路径）**

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
# 若跑 pytest（含 companion 测试）：uv pip install -r tests/requirements.txt
```

**B. venv + pip（与 CI 本地复现一致）**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r tests/requirements.txt
```

## 3) 配置文件

[`app/core/config.py`](../../../app/core/config.py)：`INTY_CONFIG_YAML` 优先；未设置时读仓库根 **`config.yaml`**。

- **日常连真实/半真实依赖、调 companion**：`export INTY_CONFIG_YAML=devops/config.yaml.local`（见其中 `database` 与 `gcs.use_fake_gcs` 等；部分路径指向 **`.secrets/`**，按需放置密钥文件或按文档关闭/替换）。
- **偏测试叠层、接近 CI**：`export INTY_CONFIG_YAML=devops/config.yaml.test`，或按 `backend/ops/README.md` 将测试配置拷为根目录 `config.yaml`。

不要猜测未在仓库中出现的密钥文件内容；只使用 **`devops/`** 下已有模板与用户本机已有 secret。

## 4) 验证数据库与迁移

**Ops 启动脚本会在 uvicorn 前执行 `alembic upgrade head`**（见 `backend/ops/start.sh` 注释）。首次成功起服即表示 DB 可达且迁移链可用。

快速健康检查（Ops 默认 **8001**）：

```bash
curl -sf http://127.0.0.1:8001/health
```

## 5) 起 Ops 与终端 REPL（companion 调试主路径）

与 **inty-local-backend-repl** 对齐的本地模式示例：

```bash
export INTY_CONFIG_YAML=devops/config.yaml.local
backend/ops/start.sh --local --debug --no-build-frontend
```

Bearer 与 **agent-id**、REPL 命令见 **inty-local-backend-repl** 与 [`tools/inty_v2_repl/README.md`](../../../tools/inty_v2_repl/README.md)。

Companion 实现目录：**[`app/core/companion_harness/`](../../../app/core/companion_harness/)**。

## 6) 相关技能与文档

- **inty-local-backend-repl**：起 Ops、日志路径、终止进程、拿 agent-id。
- **inty-backend-ci-local**：与 GitHub CI 同序的本地检查（含 pytest 叠层）。
- **inty-server-module-verify**：对运行中服务做 smoke（含 WebSocket）。
- **inspect-companion-harness**：需要读 Postgres 里 MemoryStore 文档版本时的 SQL 指引。
- 人类可读 Ops 步骤：**[`backend/ops/README.md`](../../../backend/ops/README.md)**。

## 非本 skill 范围

- **tools/lite_llm_proxy**：独立 `docker-compose.yml` 与自有数据库名，与 Inty 主库 **`inty`** 无关。
- **experimental/locust_test**：负载测试 compose，非日常 companion 开发默认路径。
