# `app/models/`：ORM 与数据库表的 Python 投影

**一句话**：SQLAlchemy 模型定义 **表结构与关系**；Alembic 迁移应与之 **同步演进**。

## JSON 元数据列

- 表中若使用 **`metadata` 等 JSON 列** 承载可扩展载荷，应在 Python 侧有 **对应的 Pydantic 类型** 做读写转换，避免无模式字典在业务里扩散。
