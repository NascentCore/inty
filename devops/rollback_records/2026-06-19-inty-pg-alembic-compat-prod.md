<!-- CREATED_BY_AGENT -->

# inty 逻辑库 Alembic 与 compat prod 后端不一致（2026-06-19）

## Scope

记录 `inty-pg` 上 **prod 逻辑库 `inty`** 与 **`intellimate-client-compat-local-postgres-prod` 分支部署的 `inty-backend-prod`** 之间的 Alembic 版本冲突、已执行修复，以及后续运维约束。

适用：IntelliMate release 客户端兼容后端（基于 `4a7c0a98`）+ VM 本地 Postgres；不适用于 iMate 或 main 线 companion harness 全量部署。

## 背景

- **prod 容器**：`inty-backend-prod`，镜像来自分支 `intellimate-client-compat-local-postgres-prod`（`4a7c0a98` + local Postgres devops 变更，**不含** main 上 companion / WS 队列等 runtime 变更）。
- **prod 逻辑库**：`inty-pg` 容器内 `inty`（与 dev 逻辑库 `inty-dev` 共用同一 Postgres 实例）。
- **compat 分支 Alembic head**：`20260512_phone_call_bindings`。
- **main 线 Alembic head**（2026-06-19）：`28ea966f0c57`（`companion_bonds` 等）。

本地 `inty` 在 cutover / sync 过程中曾用 **main 线** 跑过 migration，`alembic_version` 停在 `28ea966f0c57`，而 compat 分支代码中 **不存在** 该 revision 文件。

## 症状

容器启动时执行 `alembic upgrade`，日志：

```text
FAILED: Can't locate revision identified by '28ea966f0c57'
```

进程无法完成 migration，容器 crash loop。

## 根因

启动 migration 会读取 DB 中 `alembic_version`，再在本分支 `backend/alembic/versions/` 中解析 revision 链。DB 版本高于分支已知 head 时，Alembic 找不到对应 revision 文件即失败。

main 相对 compat head 多出的 revision 链（仅 schema，2026-06-19 当时）：

| Revision | 主要对象 |
|----------|----------|
| `f73e1b518bfe` | `ops_wechat_demo_bridges` |
| `20260612_120000` | `ops_telegram_demo_bindings`, `ops_telegram_demo_poll_state` |
| `1a83f89c9a41` | `agent_channel_endpoints`（并 drop `ops_telegram_demo_bindings`） |
| `efcea1e32a72` | `agentic_companion_input_queue`, `agentic_companion_output_queue` |
| `28ea966f0c57` | `companion_bonds` |

## 已执行修复（2026-06-19）

在 `inty-pg` 的 `inty` 库上手动回退 schema 标记，使与 compat 分支 head 对齐：

1. 删除上表所列超出 compat head 的表及 `companionbondstate` enum（当时均为空表或仅 demo 行）。
2. `UPDATE alembic_version SET version_num = '20260512_phone_call_bindings'`。
3. `docker restart inty-backend-prod` — migration 通过，服务正常启动。

**备选方案（未采用）**：在 compat 分支 cherry-pick 上述 5 个 Alembic revision 文件（纯 schema），使代码能识别 main 已迁过的 DB 版本。

## 运维约束

### 与 `inty-backend-prod`（compat 分支）同时存在时

| 对 `inty` 的操作 | 容器不重启 | 容器重启 |
|------------------|------------|----------|
| 仅新增 main 后续表/列（compat 代码不读写） | 可能继续服务 | migration 失败若 `alembic_version` 已抬高 |
| `alembic upgrade head`（main） | 运行中可能仍正常 | **会** 触发 `Can't locate revision` |
| Cloud SQL sync / restore 覆盖 `inty` | 数据/连接可能即时异常 | 同上 + 数据突变 |
| `inty-pg` restart / PG major upgrade | 连接池断连，请求可能 500 | 需等 DB 就绪后重启后端 |

**不重启只能推迟 Alembic 校验问题**，不能当作「改库无影响」的保证。

### 安全边界

- 动 **`inty-dev`** 不影响 compat prod 后端（不同逻辑库）。
- 动 **`inty`** 前：确认 `alembic_version` 仍为 `20260512_phone_call_bindings`，或已部署 **matching** 的后端镜像（含相同 migration 链）。
- 计划升级 main 全量后端前：先换镜像再对 `inty` 跑 migration，勿在 compat 容器仍负责 prod 时单独升 DB。

## 相关

- [2026-06-19 inty-backend-prod rollback record](./2026-06-19-inty-backend-prod.md)
- [LOCAL_POSTGRES.md](../LOCAL_POSTGRES.md)
- Git 分支：`intellimate-client-compat-local-postgres-prod`
