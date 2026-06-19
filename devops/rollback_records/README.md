<!-- CREATED_BY_AGENT -->

# Rollback records

运维事件与可恢复部署状态的记录。完整 runbook 在各 dated 文件中；**main 与 `intellimate-client-compat-local-postgres-prod` 均应保留这些引用**，便于在默认分支上发现。

| 日期 | 文件 | 摘要 |
|------|------|------|
| 2026-06-19 | [inty-backend-prod](./2026-06-19-inty-backend-prod.md) | prod 容器回滚镜像、`4a7c0a98` 捕获态、部署时间线 |
| 2026-06-19 | [inty Alembic compat prod](./2026-06-19-inty-pg-alembic-compat-prod.md) | `inty` 逻辑库 Alembic 与 compat 分支不一致、检查命令、回退 SQL |

相关：[LOCAL_POSTGRES.md](../LOCAL_POSTGRES.md)（Prod 容器部署 → Alembic 与 compat prod 后端）。
