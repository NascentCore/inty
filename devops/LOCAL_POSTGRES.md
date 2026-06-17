# IntelliMate dev 本地 Postgres（Docker）

<!-- CREATED_BY_AGENT -->

IntelliMate **dev** 环境的数据库已从 GCP Cloud SQL 迁到 **dev-instance VM 上的 Docker Postgres**；**prod** 仍使用 Cloud SQL（见 [GCP.md](GCP.md)）。

## 新旧对比

| 项 | 旧（Cloud SQL） | 新（本地 Docker） |
| --- | --- | --- |
| 适用配置 | `devops/config.yaml.dev` | 同上 |
| 逻辑库名 | `inty-dev` | `inty-dev`（不变） |
| `database.host` | `10.41.177.3`（Cloud SQL 私网 IP） | `localhost` |
| `database.port` | 默认 `5432` | `5432` |
| `database.replica_host` | `10.41.177.17`（只读副本） | 已移除（读写均走本地主库） |
| 运行位置 | GCP 托管实例 `inty-prod` 上的逻辑库 | VM 容器 `inty-dev-postgres` |
| 扩展 | `vector`（pgvector） | 同上（镜像自带） |
| 备份 / HA | Cloud SQL 托管 | Docker volume，需自行维护 |

**prod**（`devops/config.yaml.prod`）未变：`database.host` 仍为 Cloud SQL 私网 IP，逻辑库 `inty`。

## 容器约定

- **容器名**：`inty-dev-postgres`
- **镜像**：`pgvector/pgvector:pg16`（需 `vector` 扩展，与线上一致）
- **数据卷**：`inty-dev-postgres-data`（named volume，best-effort 持久化；迁移前源库约 637MB，远低于 16GB 上限）
- **端口**：宿主机 `5432` → 容器 `5432`
- **账号**：与 [`config.yaml.dev`](config.yaml.dev) 中 `database` 段一致（`postgres` / 库名 `inty-dev`）

### 启动 / 停止

```bash
# 首次或重建（会清空 volume 内数据，慎用）
docker volume create inty-dev-postgres-data
docker run -d \
  --name inty-dev-postgres \
  --restart unless-stopped \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD='<见 config.yaml.dev database.password>' \
  -e POSTGRES_DB=inty-dev \
  -p 5432:5432 \
  -v inty-dev-postgres-data:/var/lib/postgresql/data \
  pgvector/pgvector:pg16

docker start inty-dev-postgres   # 日常启动
docker stop inty-dev-postgres    # 停止
```

就绪检查：

```bash
PGPASSWORD='<password>' psql -h localhost -U postgres -d inty-dev -c 'SELECT 1'
```

## 从 Cloud SQL 重新同步（一次性迁移或刷新）

源库在 Cloud SQL 实例 `inty-prod` 上，逻辑库 `inty-dev`。客户端须 **PostgreSQL 17**（源端 PG 17；宿主机 `pg_dump` 14 会版本不匹配）。

```bash
DUMP=/tmp/inty-dev.dump
rm -f "$DUMP"

# dump（PG 17 客户端）
docker run --rm \
  -e PGPASSWORD='<cloud-sql password>' \
  -v /tmp:/tmp \
  postgres:17 \
  pg_dump -h 10.41.177.3 -U postgres -d inty-dev --format=custom -f /tmp/inty-dev.dump

# 本地启用 vector 后 restore
PGPASSWORD='<local password>' psql -h localhost -U postgres -d inty-dev \
  -c 'CREATE EXTENSION IF NOT EXISTS vector;'

docker run --rm \
  -e PGPASSWORD='<local password>' \
  --network host \
  -v /tmp:/tmp \
  postgres:17 \
  pg_restore -h localhost -U postgres -d inty-dev \
  --clean --if-exists --no-owner --no-privileges /tmp/inty-dev.dump
```

常见无害 warning：`SET transaction_timeout`（PG17 dump → PG16 本地实例参数差异）。

迁移后建议对比表数量与关键表行数（`users`、`agents`、`chats` 等）；迁移窗口内远端若有写入，个别表会有少量行数差。

## 与 dev 后端 / Ops 的连接

[`config.yaml.dev`](config.yaml.dev) 使用 `host: localhost`、`port: 5432`：

- **在 VM 宿主机上直接跑** `backend/inty/start.sh`、`backend/ops/start.sh --local`、REPL、Alembic：可直接连 `localhost:5432`。
- **Docker 部署的** `inty-backend-dev` / `inty-ops-dev`：容器内 `localhost` 指向容器自身，**不能**直接访问宿主机上的 Postgres。若镜像内配置仍为 `localhost`，需在部署时增加宿主机网关（例如 `docker run ... --add-host=host.docker.internal:host-gateway`，并把 `database.host` 改为 `host.docker.internal`），或将 Postgres 与后端接入同一 user-defined network 并用容器名 `inty-dev-postgres` 作为 host。部署细节见 [RELEASE.md](RELEASE.md) 与各 workflow。

## 相关文档

- 环境总览：[README.md](README.md)
- prod / Cloud SQL / iMate 逻辑库：[GCP.md](GCP.md)
- 运维操作（用户、Alembic、历史 dump 示例）：[SOPS.md](SOPS.md)
