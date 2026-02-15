# AGENTS.md · alembic/（数据库迁移）

- 配置文件为 `alembic/alembic.ini`；从仓库根目录执行时需 `export ALEMBIC_CONFIG=alembic/alembic.ini` 或 `alembic -c alembic/alembic.ini ...`。
- 禁止生成更新数据表的 version 文件
- `alembic revision --autogenerate -m "<revision description>"`
  使用该命令生成新的 version 文件
- 一切数据库模式变更必须通过迁移完成；禁止绕过迁移直接改表。
- 禁止重写或删除历史迁移；如需修复，追加新迁移说明原因与影响。
