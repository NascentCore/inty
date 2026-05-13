# db - 数据库

These are for accessing database, it's different from models, which defines tables.
Tables are critical for alembic to work correctly.

`models` are used for updating database schema.

## Cursor Summary

- 目录用途: 提供数据库基础设施，包括会话工厂、引擎与 ORM 基类。
- 关键文件:
  - `session.py`: 创建数据库会话与依赖注入入口。
  - `base.py`: ORM 基类导入聚合，供 Alembic 发现与迁移使用。
- 关联: `app/models` 定义表结构；`backend/alembic/` 管理迁移；业务服务通过依赖获得 `Session` 进行 CRUD。
