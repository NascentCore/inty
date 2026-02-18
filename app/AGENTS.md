# AGENTS.md · app/（后端服务）

- `__init__.py` 必须为空
- 使用 OpenAI SDK 进行 text LLM API 调用
- 使用 Google GenAI SDK 调用 multimodal 生成 API 调用
- 禁止直接使用 httpx 等 http 调用任何第三方 API
- API endpoints 返回给调用方的信息必须用英文，因为用户都是美国用户
- 新增或修改 API endpoints 必须添加端到端测试，假设测试用后端可在 localhost:8000 访问

## AI 生成内容元数据

在设计 AI 内容生成功能时、AI 生成内容的元数据需要保留在数据库中；包括：

- 模型配置：app/api/types/llm_config.py
- 提示词：生成该内容的提示词、与上面的模型配置一起，就可以复现生成内容

## Feature gating

1. 添加配置项到 app/utils/config.py 中的配置对应功能的最小 app version code；后端在 app/api/utils/feature_gating.py 添加与之对应的判断函数

例子： app/utils/config.py 中的 min_app_version_code_for_festival_memory，及 app/api/utils/feature_gating.py 中的 is_festival_memory_enabled

假设 app version 不会回退，否则情况非常难以处理、并且会要求后端代码做很复杂处理。

节日记忆若考虑版本回退：高版本已投递的 festival_memory_prompt 会写入 chat_history，用户若回退到低版本再拉消息，需在 GET messages、GET agent、chat completions 等多处按 appVersionCode 过滤返回内容（不返回节日记忆相关字段）。过滤逻辑分散、易漏、难维护，且需与「未传版本时照常返回」等策略一致。因此当前选择不做「为低版本过滤」的代码，依赖产品假设（版本不回退）。

## 跨环境数据交换

- 任何跨环境数据交换，如从数据库读出、写入数据类型，从客户端获取、返回数据，等等，都需要定义 Pydantic model 来描述该数据；
- Pydantic model 定义的数据可以经过转换变成 JSON 字符串或者其他结构；
- 在代码中要严格使用 Pydantic model 数据来进行处理；
