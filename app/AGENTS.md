# AGENTS.md · app/（后端服务）

- __init__.py 必须为空
- 使用 openai sdk 进行 text LLM API 调用
- 使用 Google GenAI SDK 调用 multimodal 生成 API 调用
- 禁止直接使用 httpx 等 http 调用任何第三方 API
- API endpoints 返回给调用方的信息必须用英文，因为用户都是美国用户

## Feature gating

1. 添加配置项到 app/utils/config.py 中的配置对应功能的最小 app version code；后端在 app/api/utils/feature_gating.py 添加与之对应的判断函数

例子： app/utils/config.py 中的 min_app_version_code_for_festival_memory，及 app/api/utils/feature_gating.py 中的 is_festival_memory_enabled

## 超级用户权限

- 超级用户跳过所有订阅检查，使用 is_superuser（位于 app/core/user_privilege/superuser_check.py）

## 测试与文档

- 测试时假设本地已有测试用后端服务器运行在 http://localhost:8000/
