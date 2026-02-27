# Backend Ops（运营平台）本地运行

Ops 提供 evaluation Web UI 与完整 `/api/v1`，默认端口 **8001**。以下步骤从仓库根目录执行。

## 1. 启动 PostgreSQL

与主后端共用同一数据库：

```bash
docker run --rm --name pg-inty -p 5432:5432 \
  -e POSTGRES_PASSWORD=sxwl666! \
  -e POSTGRES_DB=inty \
  -d postgres:16
```

确认就绪：`docker exec pg-inty pg_isready -U postgres`

## 2. Python 环境与依赖

在**仓库根目录**：

```bash
# 创建并激活虚拟环境（若尚未创建）
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 安装依赖
uv pip install -r requirements.txt
```

## 3. 配置文件

使用测试配置（指向本地 DB）：

```bash
cp devops/config.yaml.test config.yaml
```

若需 GCS/Firebase，与主后端相同：将 `inty-backend-key.json`、`inty-firebase-key.json` 放在 config 中配置的路径，或参考 [backend/README.md](../README.md) 的 GCS 配置。

## 4. 启动 Ops

在**仓库根目录**执行：

**开发模式**（会构建 evaluation 前端、注入测试用户与种子数据、uvicorn --reload）：

```bash
./backend/ops/start.sh --dev
```

**测试模式**（与 --dev 类似，但不构建 evaluation 前端，适合 CI）：

```bash
./backend/ops/start.sh --test
```

**普通模式**（仅跑迁移 + 启动，不构建前端、不注入测试数据）：

```bash
./backend/ops/start.sh
```

启动脚本会依次：执行 Alembic 迁移、`init_subscription_plans_simple.py`，再根据模式选择是否构建 evaluation、注入测试用户并启动 uvicorn。

## 5. 访问

- 健康检查：<http://localhost:8001/>
- Evaluation Web UI：<http://localhost:8001/evaluation>
- API 文档（仅当 `config.yaml` 中 `app.debug` 为 true）：<http://localhost:8001/docs>

默认端口为 **8001**；可通过环境变量 `PORT` 覆盖（例如 Cloud Run 下 `PORT=8080`）。

## 可选：与主后端同时运行

主后端默认端口 8000，Ops 默认 8001，可同时起两个进程：

```bash
# 终端 1：主后端
./backend/inty/start.sh --dev

# 终端 2：Ops
./backend/ops/start.sh --dev
```

两者共用同一 `config.yaml` 与数据库。

## 故障排查

- **迁移失败**：确认 PostgreSQL 已启动且 `config.yaml` 中 `database` 与本地一致。
- **evaluation 页面 404**：开发模式下需执行 `./evaluation/build.sh`（`start.sh --dev` 会自动执行）；若使用 `--test` 或未构建，请先运行一次 `./evaluation/build.sh` 再启动。
- **端口占用**：设置 `PORT=8002 ./backend/ops/start.sh --dev` 使用其他端口。
