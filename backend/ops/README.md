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

**开发模式**（默认先跑 `evaluation/build.sh` 同步静态资源、注入测试用户与种子数据、uvicorn `--reload`；加快迭代可加 `--no-build-frontend`）：

```bash
# 启动 Ops；另开终端按需运行: cd evaluation && npm run dev
./backend/ops/start.sh --dev
```

**普通模式**（仅跑迁移 + 启动，不构建前端、不注入测试数据）：

```bash
evaluation/build.sh  # build static html for ops platform
backend/ops/start.sh  # 启动后端
```

## 5. 访问

- 健康检查：<http://localhost:8001/health>
- Evaluation Web UI（后端静态托管）：<http://localhost:8001/>
- Evaluation Web UI（Vite 本地开发服务器）：<http://localhost:3000/>
- API 文档（仅当 `config.yaml` 中 `app.debug` 为 true）：<http://localhost:8001/docs>

默认端口为 **8001**；可通过环境变量 `PORT` 覆盖（例如 Cloud Run 下 `PORT=8080`）。
