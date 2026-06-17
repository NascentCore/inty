# IntelliMate 本地 Postgres（Docker）

<!-- CREATED_BY_AGENT -->

IntelliMate **dev** 与 **prod** 的数据库均已从 GCP Cloud SQL 迁到 **dev-instance VM 上的同一 Docker Postgres 实例**；Cloud SQL 实例 `inty-prod` 仍作为 **源库 / 历史 / iMate 等其它逻辑库**（见 [GCP.md](GCP.md)）。

## 新旧对比

| 项 | 旧（Cloud SQL） | 新（本地 Docker） |
| --- | --- | --- |
| dev 配置 | [`config.yaml.dev`](config.yaml.dev) | 同上 |
| prod 配置 | [`config.yaml.prod`](config.yaml.prod) | 同上 |
| dev 逻辑库 | `inty-dev` | `inty-dev`（不变） |
| prod 逻辑库 | `inty` | `inty`（不变） |
| `database.host` | `10.41.177.3`（Cloud SQL 私网 IP） | `host.docker.internal`（容器部署；宿主机直连用 `localhost`） |
| `database.port` | 默认 `5432` | `5432` |
| dev `replica_host` | `10.41.177.17`（只读副本） | 已移除 |
| prod `replica_host` | 未配置（读路径回退主库） | 未配置（本地无副本） |
| 运行位置 | Cloud SQL 实例 `inty-prod` 上的逻辑库 | 同一 VM 容器 `inty-dev-postgres` 内两个库 |
| 扩展 | `vector`（dev/prod）；prod 另有 `uuid-ossp` | 同上（镜像 / restore 带入） |
| 备份 / HA | Cloud SQL 托管 | Docker volume，需自行维护 |

## 容器约定

- **容器名**：`inty-dev-postgres`（历史命名；现承载 dev **与** prod 两个逻辑库）
- **镜像**：`pgvector/pgvector:pg16`
- **数据卷**：`inty-dev-postgres-data`（Docker **named volume**；与容器生命周期解耦，见下文「Volume 耐久性」）
- **端口**：宿主机 `5432` → 容器 `5432`
- **逻辑库**：`inty-dev`（dev）、`inty`（prod）
- **账号**：与 [`config.yaml.dev`](config.yaml.dev) / [`config.yaml.prod`](config.yaml.prod) 中 `database` 段一致（`postgres` / 密码相同）

### 启动 / 确保 / 验证（推荐脚本）

在 VM 上、仓库根目录执行：

```bash
# 幂等：创建/启动容器，始终挂载 canonical named volume
devops/scripts/ensure_inty_dev_postgres_container.sh

# 只读检查挂载与 restart policy（不改状态）
devops/scripts/ensure_inty_dev_postgres_container.sh --check-only

# 耐久性验证；加 --restart-test 会在 restart 前后对比库 fingerprint
devops/scripts/verify_local_postgres_durability.sh
devops/scripts/verify_local_postgres_durability.sh --restart-test
```

手动启停（仅当脚本不可用时）：

```bash
docker start inty-dev-postgres   # 日常启动
docker stop inty-dev-postgres    # 停止
```

就绪检查：

```bash
PGPASSWORD='<password>' psql -h localhost -U postgres -d inty-dev -c 'SELECT 1'
PGPASSWORD='<password>' psql -h localhost -U postgres -d inty -c 'SELECT 1'
```

### Volume 耐久性

**Named volume 在以下操作中保留数据**：

- `docker stop` / `docker start` / `docker restart`
- 宿主机 reboot（容器 `--restart unless-stopped` 时自动拉起）
- `docker rm inty-dev-postgres`（含 `-v` 也不会删除 **named** volume）

**会丢数据或导致「空库」的误操作**：

- `docker volume rm inty-dev-postgres-data`
- `docker volume prune`（容器已删、volume 变为 unused 时会被清掉）
- 重建容器时挂载了**不同** volume 名或未挂 `-v`

**防护措施（已脚本化）**：

- [`ensure_inty_dev_postgres_container.sh`](scripts/ensure_inty_dev_postgres_container.sh)：唯一推荐的创建/重建入口；volume label `inty.critical=postgres-data`，容器 label `inty.critical=postgres`
- [`guard_docker_volume_prune.sh`](scripts/guard_docker_volume_prune.sh)：若保护 volume 存在则 **拒绝** 执行 `docker volume prune`（用法：`guard_docker_volume_prune.sh || docker volume prune`）
- [`backup_local_postgres.sh`](scripts/backup_local_postgres.sh)：dump `inty-dev` 与 `inty` 到 `/opt/inty/backups/postgres/`（见 [SOPS.md](SOPS.md) cron 示例）

首次创建（`ensure_*` 脚本会自动执行；**禁止** `docker volume rm`）：

```bash
devops/scripts/ensure_inty_dev_postgres_container.sh
# prod 逻辑库若不存在，需单独 CREATE DATABASE（见下文重同步）
```

## 从 Cloud SQL 重新同步

源库在 Cloud SQL 实例 `inty-prod`（`10.41.177.3`）。客户端须 **PostgreSQL 17**（宿主机 `pg_dump` 14 会版本不匹配）。

### dev（`inty-dev`）

```bash
DUMP=/tmp/inty-dev.dump
rm -f "$DUMP"

docker run --rm \
  -e PGPASSWORD='<cloud-sql password>' \
  -v /tmp:/tmp \
  postgres:17 \
  pg_dump -h 10.41.177.3 -U postgres -d inty-dev --format=custom -f /tmp/inty-dev.dump

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

### prod（`inty`）

```bash
DUMP=/tmp/inty-prod.dump
rm -f "$DUMP"

docker run --rm \
  -e PGPASSWORD='<cloud-sql password>' \
  -v /tmp:/tmp \
  postgres:17 \
  pg_dump -h 10.41.177.3 -U postgres -d inty --format=custom -f /tmp/inty-prod.dump

PGPASSWORD='<local password>' psql -h localhost -U postgres -d postgres \
  -c 'DROP DATABASE IF EXISTS inty;' \
  -c 'CREATE DATABASE inty;'

PGPASSWORD='<local password>' psql -h localhost -U postgres -d inty \
  -c 'CREATE EXTENSION IF NOT EXISTS vector;'

docker run --rm \
  -e PGPASSWORD='<local password>' \
  --network host \
  -v /tmp:/tmp \
  postgres:17 \
  pg_restore -h localhost -U postgres -d inty \
  --clean --if-exists --no-owner --no-privileges /tmp/inty-prod.dump
```

常见无害 warning：`SET transaction_timeout`（PG17 dump → PG16 本地实例参数差异）。

迁移后建议对比表数量、扩展与关键表行数；迁移窗口内远端若有写入，个别表会有少量行数差。

### 增量同步（Cloud SQL → 本地，prod / dev）

Cloud SQL 若仍在接收写入，不必整库重 dump。对含 `created_at` 的表，复制 `remote.created_at > local.max(created_at)` 的行即可（prod 上常见：`chat_history`、`subscription_usage`、`voice_cache`）。

**检查差额**（默认只读；TODO !3497 — 在 VM 上执行并记录结果）：

```bash
devops/scripts/sync_cloudsql_inty_incremental.sh --check-only
devops/scripts/sync_cloudsql_inty_incremental.sh --check-only --db inty-dev
```

**执行增量复制**：

```bash
devops/scripts/sync_cloudsql_inty_incremental.sh --apply
devops/scripts/sync_cloudsql_inty_incremental.sh --apply --db inty-dev
```

脚本行为：

- 逐表对比 Cloud SQL（`10.41.177.3`）与本地 `localhost:5432` 行数
- 对有 `created_at` 且远端更多的表做 `\copy` 增量导入（`created_at > local.max(created_at)`）
- 单列主键表经 staging + `ON CONFLICT DO NOTHING`，可安全重复 `--apply`
- FK 依赖表按固定优先级同步（`users` → `agents` → `chats` → …）；`--apply` 最多重试 5 轮（`APPLY_MAX_PASSES`）
- `chat_history` 同步后更新 `chat_history_id_seq`
- 本地行数多于远端、或无 `created_at` 的表：跳过并提示需整库 resync（见上文 `pg_dump` / `pg_restore`）

VM 宿主机任务（Alembic、日报）用 [`scripts/render_vm_database_config.sh`](scripts/render_vm_database_config.sh) 把 `host.docker.internal` 渲染为 `localhost`。

密码默认从 [`config.yaml.prod`](config.yaml.prod) / [`config.yaml.dev`](config.yaml.dev) 的 `database.password` 读取；可用 `PGPASSWORD` 覆盖。

### Prod 容器部署（手动）

<!-- TODO(!3498): Manual prod backend/push-worker deploy + E2E verify after local Postgres cutover (epic #3495). -->

[`config.yaml.prod`](config.yaml.prod) 已指向本地 Docker（`host.docker.internal`），但 **prod 后端 / Ops / push worker 不会随 push 自动部署**：

- [build_and_deploy_backend.yml](../.github/workflows/build_and_deploy_backend.yml)：`config.yaml.prod` 不在 push paths；prod schedule 已关闭
- [build_and_deploy_ops.yml](../.github/workflows/build_and_deploy_ops.yml)：同上
- [build_and_deploy_push_worker.yml](../.github/workflows/build_and_deploy_push_worker.yml)：同上；prod 定时部署已关闭

推荐顺序：先在 dev 验证本地 Postgres 与 `host.docker.internal` → GitHub Actions **Run workflow** 选手动 environment **prod** 部署 Ops → 再部署 backend（及按需 push worker）。VM 上 Alembic 用 [alembic_upgrade_prod_db.yaml](../.github/workflows/alembic_upgrade_prod_db.yaml)（workflow 内会把 `host.docker.internal` 替换为 `localhost`）。

## 与后端 / Ops 的连接

[`config.yaml.dev`](config.yaml.dev) 与 [`config.yaml.prod`](config.yaml.prod) 均使用 `host: host.docker.internal`、`port: 5432`（构建进 Docker 镜像）：

- **在 VM 宿主机上直接跑** `backend/inty/start.sh`、`backend/ops/start.sh --local`、REPL、Alembic：可直接连 `localhost:5432`。
- **Docker 部署的** `inty-backend-dev` / `inty-backend-prod` / Ops 容器：容器内 `localhost` 指向容器自身，**不能**直接访问宿主机 Postgres。需在部署时增加宿主机网关（例如 `docker run ... --add-host=host.docker.internal:host-gateway` 且 `database.host: host.docker.internal`），或将 Postgres 与后端接入同一 user-defined network 并用容器名 `inty-dev-postgres` 作为 host。见 [RELEASE.md](RELEASE.md) 与各 workflow。

## 相关文档

- 环境总览：[README.md](README.md)
- Cloud SQL（源库 / iMate 逻辑库）：[GCP.md](GCP.md)
- 运维操作：[SOPS.md](SOPS.md)
