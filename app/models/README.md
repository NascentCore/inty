# SqlAlechemy Models

此处定义数据库中数据表结构，与 API 输入、输出数据类型 `app/schemas` 中的类型对应。
所有数据表定义必须定义为 `app.models.Base` 子类，否则无法被 Alembic 识别。

名字有点混淆：`pydantic model` 带了 model，但是这里的 model 是 sqlalchemey schema。
