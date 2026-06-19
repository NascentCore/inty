<!-- CREATED_BY_AGENT -->

# inty 逻辑库 Alembic 与 compat prod 后端不一致（2026-06-19）

## Scope

记录 `inty-pg` 上 **prod 逻辑库 `inty`** 与 **`intellimate-client-compat-local-postgres-prod` 分支部署的 prod 容器** 之间的 Alembic 版本冲突、已执行修复、检查命令与后续运维约束。

适用：IntelliMate release 客户端兼容后端（基于 `4a7c0a98`）+ VM 本地 Postgres；不适用于 iMate 或 main 线 companion harness 全量部署。

## 为何需要 compat 分支

- **Release 客户端**：IntelliMate Android 发行版 commit `64615013`（`android_app/`），生产默认走 HTTP `/api/v1/chat/completions`，非 debug WebSocket。
- **main 部署失败**：2026-06-19 曾部署 main（`6c46b2f8c`），出现发消息后需退出重进才看到最新回复等问题；已回滚至 `4a7c0a98`。
- **分支目的**：在 `4a7c0a98` runtime 上 **仅** cherry-pick local Postgres devops/workflow，得到 `intellimate-client-compat-local-postgres-prod`。
- **分支命名**：不用 `deploy/` 前缀——GitHub Actions 构建的 Docker 镜像 tag 不能含该前缀（曾用 `intellimate-client-compat-local-postgres-prod`）。

时间线见 [2026-06-19 inty-backend-prod rollback record](./2026-06-19-inty-backend-prod.md)（含 `4a7c0a98` 回滚镜像与失败版 `6c46b2f8c` 本地 tag `inty-backend-prod-broken:20260619T0757Z-6c46b2f8c`）。

## 背景

- **prod 容器**：`inty-backend-prod`（及共用 `config.yaml.prod` 的 `inty-ops-prod`、prod push worker），镜像来自 `intellimate-client-compat-local-postgres-prod`（`4a7c0a98` + local Postgres devops，**不含** main companion / WS 队列 runtime）。
- **prod 逻辑库**：`inty-pg` 内 `inty`（与 `inty-dev` 共用 Postgres 实例，逻辑隔离）。
- **compat 分支 Alembic head**：`20260512_phone_call_bindings`（截至 2026-06-19；以分支上 `alembic heads` 为准）。
- **main 线 Alembic head**（2026-06-19 快照）：`28ea966f0c57`。**main 会继续新增 revision**——冲突时勿死记 ID，应对比两分支 `alembic heads` 与 DB `alembic_version`。

本地 `inty` 在 cutover / sync 过程中曾用 **main 线** 跑过 migration，`alembic_version` 停在 `28ea966f0c57`，compat 分支代码中 **不存在** 该 revision 文件。

## 症状

任一 prod 服务容器启动时执行 `alembic upgrade head`（见 `backend/inty/start.sh`、`backend/ops/start.sh`、`backend/push_worker/start.sh`），日志：

```text
FAILED: Can't locate revision identified by '28ea966f0c57'
```

进程无法完成 migration，容器 crash loop。

## 根因

启动 migration 读取 DB `alembic_version`，再在本分支 `backend/alembic/versions/` 解析 revision 链。DB 版本高于分支已知 head 时，Alembic 找不到对应 revision 文件即失败。

main 相对 compat head 多出的 revision 链（2026-06-19 当时；main 继续演进后需重新 diff）：

| Revision | 主要对象 |
|----------|----------|
| `f73e1b518bfe` | `ops_wechat_demo_bridges` |
| `20260612_120000` | `ops_telegram_demo_bindings`, `ops_telegram_demo_poll_state` |
| `1a83f89c9a41` | `agent_channel_endpoints`（并 drop `ops_telegram_demo_bindings`） |
| `efcea1e32a72` | `agentic_companion_input_queue`, `agentic_companion_output_queue` |
| `28ea966f0c57` | `companion_bonds` |

## 重启 / 改库前检查

在 VM 仓库根目录、已 checkout compat 分支时：

```bash
# 1. DB 当前 Alembic 版本
docker exec inty-pg psql -U postgres -d inty -At -c \
  "SELECT version_num FROM alembic_version;"

# 2. compat 分支代码期望 head（须与上一步一致）
git checkout intellimate-client-compat-local-postgres-prod
PYTHONPATH=. ALEMBIC_CONFIG=backend/alembic/alembic.ini alembic heads

# 3. 若已对齐，下列 post-head 表应不存在（或为空且即将删除）
docker exec inty-pg psql -U postgres -d inty -At -c "
SELECT tablename FROM pg_tables WHERE schemaname='public'
AND tablename IN (
  'companion_bonds','agentic_companion_input_queue','agentic_companion_output_queue',
  'agent_channel_endpoints','ops_telegram_demo_poll_state','ops_wechat_demo_bridges',
  'ops_telegram_demo_bindings'
) ORDER BY 1;"
```

对比 main 与 compat 的 head 差距（main 会漂移）：

```bash
git checkout main && PYTHONPATH=. ALEMBIC_CONFIG=backend/alembic/alembic.ini alembic heads
git checkout intellimate-client-compat-local-postgres-prod && PYTHONPATH=. ALEMBIC_CONFIG=backend/alembic/alembic.ini alembic heads
```

## 已执行修复（2026-06-19）

在 `inty-pg` 的 `inty` 库上手动回退 schema，使与 compat head 对齐（当时 post-head 表均为空或仅 1 条 demo 行）。

**注意**：下列 SQL **仅** 在确认 `alembic_version` 高于 compat head、且 post-head 表无生产数据时使用。执行前备份：`devops/scripts/backup_local_postgres.sh`。

```bash
docker exec inty-pg psql -U postgres -d inty -v ON_ERROR_STOP=1 -c "
BEGIN;

DROP TABLE IF EXISTS companion_bonds CASCADE;
DROP TYPE IF EXISTS companionbondstate;

DROP INDEX IF EXISTS ix_agentic_companion_output_queue_scope_status_seq;
DROP INDEX IF EXISTS ix_agentic_companion_output_queue_batch_seq;
DROP TABLE IF EXISTS agentic_companion_output_queue CASCADE;

DROP INDEX IF EXISTS ix_agentic_companion_input_queue_scope_status_seq;
DROP TABLE IF EXISTS agentic_companion_input_queue CASCADE;

DROP TABLE IF EXISTS agent_channel_endpoints CASCADE;
DROP TABLE IF EXISTS ops_telegram_demo_poll_state CASCADE;
DROP TABLE IF EXISTS ops_telegram_demo_bindings CASCADE;
DROP TABLE IF EXISTS ops_wechat_demo_bridges CASCADE;

UPDATE alembic_version SET version_num = '20260512_phone_call_bindings';

COMMIT;

SELECT version_num FROM alembic_version;
"
```

然后重启受影响的 prod 容器（至少 `inty-backend-prod`；若 ops / push worker 也连 `inty` 且曾 crash，一并 restart）。

**未回滚项**：`efcea1e32a72` 对部分列 **comment** 的 `ALTER COLUMN` 未手动还原；compat runtime 不依赖这些 comment，可忽略。

**备选方案（未采用）**：在 compat 分支 cherry-pick 上述 5 个 Alembic revision 文件（纯 schema），使代码能识别 main 已迁过的 DB 版本。

## Cloud SQL 与 `inty` 的关系

| 操作 | 对 `alembic_version` | 对运行中 compat 容器 |
|------|----------------------|----------------------|
| 增量 sync（`sync_cloudsql_inty_incremental.sh --apply --db inty`） | 通常 **不变** | 数据变更可能导致读写异常 |
| 整库 `pg_restore` 覆盖 `inty` | **被 dump 内版本覆盖** | 数据突变；若 Cloud 版本高于 compat head，重启后同样 `Can't locate revision` |
| 在 VM 上对 `inty` 跑 main 的 `alembic upgrade head` | **抬高** | 不重启可能暂时无感；重启 prod 容器即失败 |
| GitHub `alembic_upgrade_prod_db.yaml` | 针对 **Cloud SQL**，非本地 `inty-pg` | 不直接改本地 `inty`，但勿与本地 prod cutover 步骤混淆 |

## 运维约束

### 与 compat prod 容器同时存在时

| 对 `inty` 的操作 | 容器不重启 | 容器重启 |
|------------------|------------|----------|
| 仅新增 main 后续表/列（compat 代码不读写） | 可能继续服务 | migration 失败若 `alembic_version` 已抬高 |
| `alembic upgrade head`（main） | 运行中可能仍正常 | **会** 触发 `Can't locate revision` |
| Cloud SQL sync / restore 覆盖 `inty` | 数据/连接可能即时异常 | 同上 + 数据突变 |
| `inty-pg` restart / PG major upgrade | 连接池断连，请求可能 500 | 需等 DB 就绪后重启后端 |

**不重启只能推迟 Alembic 校验问题**，不能当作「改库无影响」的保证。

### 共用 `inty` 且启动时跑 Alembic 的服务

- `inty-backend-prod`
- `inty-ops-prod`（`backend/ops/start.sh`）
- prod push worker（`backend/push_worker/start.sh`）

上述容器 **共用同一 `alembic_version` 行**；版本不一致时任一重启都可能失败。

### 安全边界

- 动 **`inty-dev`** 不影响 compat prod（不同逻辑库）。
- 动 **`inty`** 前：运行上文「重启 / 改库前检查」。
- 计划升级 main 全量后端：先换 **matching** 镜像，再对 `inty` 跑 migration；勿在 compat 容器仍负责 prod 时单独升 DB。

## 相关

- [2026-06-19 inty-backend-prod rollback record](./2026-06-19-inty-backend-prod.md)
- [LOCAL_POSTGRES.md](../LOCAL_POSTGRES.md)
- Git 分支：`intellimate-client-compat-local-postgres-prod`
