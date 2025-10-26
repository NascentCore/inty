# schemas

此处定义了 API 输入、输出数据类型、与数据库表结构定义的 `app/models` 中的类型对应。
此处的数据结构均为类型化，精确定义，如 `ModelConfig` 字段，其对应的是数据库中的 JSON 字段。
这样的设计是为了平衡接口定义与数据库存储的灵活性和复杂度。

这样的好处是，系统对接的边界通过严整的数据结构定义来提供明确的语义和行为定义。
后端则提供足够的灵活性，减少开发试错过程中复杂度。

## Cursor Summary

- 目录用途: 定义 Pydantic 模型，作为 API 入参/出参的严格校验与结构化载体。
- 关键文件: `user.py`、`agent.py`、`chat.py`、`message.py`、`subscription.py`、`settings.py`、`system_settings.py`、`evaluation.py`、`response.py` 等。
- 关联: 与 `app/models` 中的 ORM 模型字段语义对应；服务层在路由处理时进行转换与落库/读取。
