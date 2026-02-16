# Pydantic models for API endpoints

- 不要使用 model_config 在 Pydantic Model 对象中：否则会与内置变量冲突：https://docs.pydantic.dev/2.0/usage/model_config/
- 更改 HTTP API request response 数据类型之后，要更新 [kotlin 数据类型定义](../../android_app/library/inty)
