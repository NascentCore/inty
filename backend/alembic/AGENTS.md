# AGENTS.md · backend/alembic/（数据库迁移）

- Alembic is the database schema management tool
- 配置文件为 `backend/alembic/alembic.ini`；从仓库根目录执行时需 `export ALEMBIC_CONFIG=backend/alembic/alembic.ini` 或 `alembic -c backend/alembic/alembic.ini ...`。
- `backend/alembic/versions/` 是 Inty 主后端、Ops 与 push worker 共用的数据库 schema revision 链。
- Ops 读写的共享业务表必须跟随同一 Alembic head；禁止为 Ops 拆出独立 migration 目录。
- 禁止生成更新数据表的 version 文件
- `alembic revision --autogenerate -m "<revision description>"`
  使用该命令生成新的 version 文件
- 一切数据库模式变更必须通过迁移完成；禁止绕过迁移直接改表。
- 禁止重写或删除历史迁移；如需修复，追加新迁移说明原因与影响。

配置文件位于 `backend/alembic/alembic.ini`。从仓库根目录执行 alembic 时需指定配置：先 `export ALEMBIC_CONFIG=backend/alembic/alembic.ini`，或使用 `alembic -c backend/alembic/alembic.ini ...`。

## 增加新的 Alembic version 文件的步骤

```bash
# 删除现有的 postgres 实例及其存储卷，从而彻底清空；然后启动并确保数据库为空
docker rm -f -v pg-inty
docker run --rm --name pg-inty -p 5432:5432 \
    -e POSTGRES_PASSWORD=sxwl666! -e POSTGRES_DB='inty' -d \
    postgres:16
# 运行 alembic 将数据库升级到最新状态，此时必须确保没有新增的 alembic version 文件！！！
cp devops/config.yaml.test config.yaml
export PYTHONPATH=.
export ALEMBIC_CONFIG=backend/alembic/alembic.ini
alembic upgrade head
alembic revision --autogenerate -m "<revision description>"
```
