# models

此处定义数据库中数据表结构，与 API 输入、输出数据类型 `app/schemas` 中的类型对应。
所有数据表定义必须定义为 `app.models.Base` 子类，否则无法被 Alembic 识别。

名字有点混淆：`pydantic model` 带了 model，但是这里的 model 是 sqlalchemey schema。

## Cursor Summary

- 目录用途: 定义 SQLAlchemy ORM 模型（表结构），作为数据库迁移与运行时期的数据结构基准。
- 关键文件: `user.py`、`agent.py`、`chat.py`、`message.py`、`subscription.py`、`settings.py`、`system_settings.py`、`evaluation.py` 等。
- 关联: `app/db` 提供会话与基类，`alembic/` 负责迁移；`app/schemas` 为 Pydantic IO 层，与本目录保持字段语义一致但职责不同。
