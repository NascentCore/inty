# `backend/alembic/`：数据库模式演进

**一句话**：全仓库 **唯一权威的 schema migration 链**——Inty 主服务、Ops、push worker **共用** 同一 `versions/` 目录；**禁止**为 Ops 单独分叉一套迁移历史。

## 读者

- 改 SQLAlchemy 模型、需要演进表结构的任何人。

## 原则（比命令更重要）

- **一切表结构变更走迁移**：不要手工在生产改表后忘了补 revision。
- **禁止改写历史**：已合并的 revision 文件视为 **只读**；修正用 **新 revision** 说明补救原因。
- **数据回填**：避免生成「仅批量改数据」的 migration 文件——数据修复用脚本或运维任务，schema 迁移专注 DDL。
- **Ops 与主站共头**：任何 Ops 会读写的共享表，必须在 **同一 Alembic head** 上演进。

## 实操入口

- 具体 `alembic.ini` 路径、`PYTHONPATH`、与 Postgres 基线等 **可复制命令** 见仓库技能 **inty-alembic-revision** 与 `backend/alembic` 旁维护说明；此处不重复长脚本块以免与真环境漂移。

## Revision 来源标记

- `alembic revision`（含 `--autogenerate`）经 `script.py.mako` 生成的文件会带 **`Revision source: alembic-cli`**（docstring）与 **`INTY_REVISION_SOURCE = "alembic-cli"`**（模块常量）。
- **Agent 手写** migration 时 **禁止** 复制上述标记；优先走 CLI 生成后再人工审阅。
- 审阅时可 `rg 'INTY_REVISION_SOURCE = "alembic-cli"' backend/alembic/versions/` 区分 CLI 与手写。
