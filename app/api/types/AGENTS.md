# API types

- 在 API 面向客户端的接口和内部同时使用的稳固类型，要避免改动
- 使用 Pydantic Model 定义
- `llm_config.py` 提供 API 与内部共用的 `LLMConfig` 类型，字段与约束与 agent 的 ModelConfig 及各处实际使用的 LLM 参数一致；使用处通过 `from app.api.types.llm_config import LLMConfig` 引用
