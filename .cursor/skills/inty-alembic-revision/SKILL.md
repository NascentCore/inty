---
name: inty-alembic-revision
description: >-
  Create new Alembic revision files at repo root with `backend/alembic/alembic.ini`:
  `revision --autogenerate` (schema diff) or empty `revision` (manual SQL).
  Covers PYTHONPATH, config.yaml, Postgres baseline, and repo rules in
  `/backend/alembic/AGENTS.md`. Use when adding DB migrations, autogenerate from models,
  or empty revision stubs.
---

# Inty: create Alembic revision files (CLI)

## When to use

- 需要新增 `backend/alembic/versions/` 下的迁移脚本
- 用户提到 `alembic revision`、`--autogenerate`、数据库 schema 变更

## 约定（本仓库）

- 配置文件：`/backend/alembic/alembic.ini`；迁移目录：`/backend/alembic/versions/`
- 从**仓库根目录**执行；必须让 Alembic 读到该 ini（见下文环境变量）
- 完整规则见 `/backend/alembic/AGENTS.md`（禁止改历史迁移、禁止纯数据迁移 version、变更须走迁移）

## 环境（每次开终端都要）

```bash
cd /path/to/repo-root
source .venv/bin/activate
export PYTHONPATH=.
export ALEMBIC_CONFIG=backend/alembic/alembic.ini
```

可选等价写法（不显式 export ini）：

```bash
python -m alembic -c backend/alembic/alembic.ini <subcommand> ...
```

默认：`config.yaml` 在仓库根，`backend/alembic/env.py` 通过 `app.core.config` 读库 URL。生成迁移前通常：

```bash
# TODO(INTY_CONFIG_YAML): prefer export INTY_CONFIG_YAML=devops/config.yaml.test
cp devops/config.yaml.test config.yaml
```

按需改 `database.host` 等为可连的 Postgres（本地多为 `localhost`）。

不换文件名时可用自定义路径（见 `backend/alembic/env.py`）：

```bash
python -m alembic -c backend/alembic/alembic.ini -x config=/abs/path/to.yaml revision --autogenerate -m "<msg>"
```

## 方式 A：根据模型生成（常用）

前提：Postgres 已起，库结构处于「当前 head 对应状态」，且你已改好 SQLAlchemy models。

推荐流程与 `/backend/alembic/AGENTS.md` 一致：干净库 `upgrade head` 后再 autogenerate，避免 diff 噪声。

```bash
alembic upgrade head
alembic revision --autogenerate -m "<short description>"
```

生成后**人工检查**新生成的 `backend/alembic/versions/*.py`：删多余 op、补索引/约束说明，勿盲提交。

CLI 生成的 revision 会带 **`INTY_REVISION_SOURCE = "alembic-cli"`** 与 docstring 行 `Revision source: alembic-cli`；**Agent 手写 migration 时不要复制该标记**——优先用本 skill 的 `alembic revision` 命令。

## 方式 B：空 revision（手写 upgrade/downgrade）

不改模型、只写手工 SQL 或少量 op 时用：

```bash
alembic revision -m "<short description>"
```

## 方式 C：指定父 revision（分支合并后）

多 head 时先 `alembic heads` 理清；需要挂在特定 revision 上时：

```bash
alembic revision --autogenerate -m "<msg>" --head <revision_id>
# 或
alembic revision -m "<msg>" --head <revision_id>
```

日常应保持**单一 head**（与 CI 检查一致）；若出现多个 head，用 `alembic merge` 生成 merge revision（见 Alembic 文档），不在此展开。

## 生成后自检

```bash
alembic history -v | head
python -m alembic heads
```

CI 要求恰好一个 head；合并前可跑 Cursor command **`/run_ci_tests`**（[`.cursor/commands/run_ci_tests.md`](/.cursor/commands/run_ci_tests.md)）。

## 常用命令速查

| 目的 | 命令 |
|------|------|
| 当前 DB 升到最新 | `alembic upgrade head` |
| 新建自动迁移 | `alembic revision --autogenerate -m "..."` |
| 新建空迁移 | `alembic revision -m "..."` |
| 当前 heads | `alembic heads` |
