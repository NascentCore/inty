# Sqlalchemy 表模型定义及 Alembic 集成

- 表定义中包含 JSON 格式的 `metadata` 列，用来保存可供代码自定义扩展的数据类型
  - `metadata` 列要有对应的 Pydantic Model 数据类型，用于 Python 代码内部使用，读取、写入数据库表列，从而提供更严谨的代码逻辑
