# `app/models/`：ORM 与数据库表的 Python 投影

SQLAlchemy 模型定义 **表结构与关系**；Alembic 迁移应与之 **同步演进**。

- 表中若使用 **`metadata` 等 JSON 列** 承载可扩展载荷，应在 Python 侧有 **对应的 Pydantic 类型** 做读写转换，避免无模式字典在业务里扩散。
- 此处定义数据库中数据表结构，与 API 输入、输出数据类型 `app/schemas` 中的类型对应，或其他地方定义的 pydantic model。
- 所有数据表定义必须定义为 `app.models.Base` 子类，否则无法被 Alembic 识别。
- 勿与 `pydantic model` 混淆，这里的 model 是 sqlalchemey schema。
- 使用 `Pydantic model_validate / model_dump`，不要手写 mapper
