# IntelliMate 本地 Postgres（Docker）

<!-- CREATED_BY_AGENT -->

IntelliMate **dev** 与 **prod** 共用 **dev-instance VM** 上同一 Docker Postgres 实例（容器 `inty-pg`），通过不同逻辑库隔离：

- **dev**：`inty-dev`（[`config.yaml.dev`](config.yaml.dev)）
- **prod**：`inty`（[`config.yaml.prod`](config.yaml.prod)）

两份配置的 `database.host` / `port` / `user` / `password` **必须一致**；仅 `database.db` 不同。Cloud SQL `inty-prod`（`10.41.177.3`）仍作源库 / 灾备 / iMate 等其它逻辑库（见 [GCP.md](GCP.md)）。

## 容器约定

- **容器名**：`inty-pg`（承载 dev + prod 两个逻辑库；旧名 `inty-dev-postgres` 由 ensure 脚本自动 rename）
- **镜像**：`pgvector/pgvector:pg17`
- **数据卷**：`inty-dev-postgres-data`（named volume；与容器生命周期解耦）
- **端口**：宿主机 `5432` → 容器 `5432`
- **超级用户**：`postgres`；密码由 `ensure_*` 从 config 对齐（见下文）

## 日常运维（VM，仓库根目录）

```bash
# 幂等：启动/创建容器、pg_hba、将 postgres 密码与 config 对齐
devops/scripts/ensure_inty_dev_postgres_container.sh

# 只读检查挂载与 restart policy
devops/scripts/ensure_inty_dev_postgres_container.sh --check-only

# 换镜像或容器漂移时：删容器重建，保留 volume
devops/scripts/ensure_inty_dev_postgres_container.sh --recreate

# 耐久性验证；--restart-test 对比 restart 前后库 fingerprint
devops/scripts/verify_local_postgres_durability.sh
devops/scripts/verify_local_postgres_durability.sh --restart-test

# 逻辑备份（inty-dev + inty）→ /opt/inty/backups/postgres/
devops/scripts/backup_local_postgres.sh
```

定时任务见 [`.github/workflows/local_postgres_maintenance.yaml`](../.github/workflows/local_postgres_maintenance.yaml)。

### 密码与宿主机访问

- `POSTGRES_PASSWORD` 环境变量**仅在空库 initdb 时**生效；已有 volume 上的密码以库内 catalog 为准。
- [`ensure_inty_dev_postgres_container.sh`](scripts/ensure_inty_dev_postgres_container.sh) 每次 ensure 会：
  1. 校验 `config.yaml.dev` 与 `config.yaml.prod` 的 host/port/user/password 一致
  2. 补全 `pg_hba.conf` 宿主机规则（`host all all all scram-sha-256`）
  3. `ALTER USER postgres` 使实例密码与 config 一致
- 宿主机脚本（sync、Alembic、REPL）用 `localhost:5432`；密码从对应 config 的 `database.password` 读取（可用 `PGPASSWORD` 覆盖）。

就绪检查：

```bash
devops/scripts/ensure_inty_dev_postgres_container.sh
PGPASSWORD="$(grep -A12 '^database:' devops/config.yaml.dev | grep password: | head -1 | sed -E 's/.*password:[[:space:]]*"?([^"#]*)"?.*/\1/')"
psql -h localhost -U postgres -d inty-dev -c 'SELECT 1'
psql -h localhost -U postgres -d inty -c 'SELECT 1'
```

### Volume 耐久性

**保留数据**：`docker stop/start/restart`、宿主机 reboot（`unless-stopped`）、`docker rm inty-pg`（named volume 不随 `-v` 删除）。

**会丢数据**：`docker volume rm inty-dev-postgres-data`、`docker volume prune`（unused volume）、重建时挂载错误 volume。

防护：[`guard_docker_volume_prune.sh`](scripts/guard_docker_volume_prune.sh)（`guard_docker_volume_prune.sh || docker volume prune`）。

## 从 Cloud SQL 同步

源库：`10.41.177.3`（Cloud SQL `inty-prod`）。dump/restore 客户端须 **PostgreSQL 17**。

### 增量同步（推荐，prod / dev 逻辑库）

```bash
devops/scripts/sync_cloudsql_inty_incremental.sh --check-only --db inty
devops/scripts/sync_cloudsql_inty_incremental.sh --apply --db inty
devops/scripts/sync_cloudsql_inty_incremental.sh --check-only --db inty-dev
```

对有 `created_at` 且远端行数更多的表，复制 `remote.created_at > local.max(created_at)` 的行；可重复 `--apply`。本地行数多于远端、或无 `created_at` 的表会跳过（需整库 resync）。

### 整库 resync（`pg_dump` / `pg_restore`）

**dev（`inty-dev`）**

```bash
DUMP=/tmp/inty-dev.dump
docker run --rm -e PGPASSWORD='<cloud-sql password>' -v /tmp:/tmp postgres:17 \
  pg_dump -h 10.41.177.3 -U postgres -d inty-dev --format=custom -f /tmp/inty-dev.dump
PGPASSWORD='<password>' psql -h localhost -U postgres -d inty-dev -c 'CREATE EXTENSION IF NOT EXISTS vector;'
docker run --rm -e PGPASSWORD='<password>' --network host -v /tmp:/tmp postgres:17 \
  pg_restore -h localhost -U postgres -d inty-dev --clean --if-exists --no-owner --no-privileges /tmp/inty-dev.dump
```

**prod（`inty`）**

```bash
DUMP=/tmp/inty-prod.dump
docker run --rm -e PGPASSWORD='<cloud-sql password>' -v /tmp:/tmp postgres:17 \
  pg_dump -h 10.41.177.3 -U postgres -d inty --format=custom -f /tmp/inty-prod.dump
PGPASSWORD='<password>' psql -h localhost -U postgres -d postgres \
  -c 'DROP DATABASE IF EXISTS inty WITH (FORCE);' -c 'CREATE DATABASE inty;'
PGPASSWORD='<password>' psql -h localhost -U postgres -d inty -c 'CREATE EXTENSION IF NOT EXISTS vector;'
docker run --rm -e PGPASSWORD='<password>' --network host -v /tmp:/tmp postgres:17 \
  pg_restore -h localhost -U postgres -d inty --clean --if-exists --no-owner --no-privileges /tmp/inty-prod.dump
```

VM 宿主机任务用 [`scripts/render_vm_database_config.sh`](scripts/render_vm_database_config.sh) 将 `host.docker.internal` 渲染为 `localhost`。

## Prod 容器部署

<!-- TODO(!3498): Manual prod backend/push-worker deploy + E2E verify after local Postgres cutover (epic #3495). -->

[`config.yaml.prod`](config.yaml.prod) 已指向本地 Docker（`host.docker.internal`）。prod 后端 / Ops / push worker **不会随 push 自动部署**——在 GitHub Actions 选手动 environment **prod** 部署 Ops → backend → push worker。见 [RELEASE.md](RELEASE.md) 与各 workflow。

### Alembic 与 compat prod 后端

若 prod 跑 **`intellimate-client-compat-local-postgres-prod`**（Alembic head 以该分支 `alembic heads` 为准），对逻辑库 **`inty`** 执行 main 线 migration 或整库 restore 抬高 `alembic_version` 后，**`inty-backend-prod` / `inty-ops-prod` / prod push worker 重启会失败**（`Can't locate revision`）。不重启可能暂时无感，但 `inty-pg` 重启、sync、删改现有表仍可能影响运行中容器。

改库或重启前检查、手动回退 SQL 见 [rollback_records/2026-06-19-inty-pg-alembic-compat-prod.md](rollback_records/2026-06-19-inty-pg-alembic-compat-prod.md)。

## Post-cutover：Cloud SQL 降本

<!-- TODO: Track Cloud SQL right-size on epic #3495 after !3498 soak. -->

IntelliMate dev/prod 稳定运行于本地 Docker 后，对 `inty-prod` 降配（**勿删整个实例**——iMate 逻辑库仍在）。见 [GCP.md](GCP.md)。

## 与后端 / Ops 的连接

- **VM 宿主机**（REPL、Alembic、`start.sh --local`）：`localhost:5432`
- **Docker 部署的后端**：`host.docker.internal`（需 `--add-host=host.docker.internal:host-gateway`）

## 相关文档

- [README.md](README.md)、[GCP.md](GCP.md)、[SOPS.md](SOPS.md)
