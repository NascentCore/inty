# AGENTS.md · alembic/（数据库迁移）

- `alembic revision --autogenerate -m "<revision description>"`
  使用该命令生成新的 version 文件
- 一切数据库模式变更必须通过迁移完成；禁止绕过迁移直接改表。
- 禁止重写或删除历史迁移；如需修复，追加新迁移说明原因与影响。
