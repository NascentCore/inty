# AGENTS.md · app/（后端服务）

- `__init__.py` 仅可包含模块 docstring，不得包含任何功能性代码（imports/re-exports/常量/函数等都属于功能性代码，应放入兄弟模块）
- 使用 `app/core/google_genai/wrapped_client.py` 调用 Google 生图模型
- 使用 `app/core/images/fal.py` 来调用 Fal
- 禁止直接使用 httpx 等 http 调用任何第三方 API
- API endpoints 返回给调用方的信息必须用英文，因为用户都是美国用户
- 新增或修改 API endpoints 必须添加端到端测试，假设测试用后端可在 localhost:8000 访问
- Avoid using monkepatch in tests

## AI 生成内容元数据

在设计 AI 内容生成功能时、AI 生成内容的元数据需要保留在数据库中；包括：

- 模型配置：app/api/types/llm_config.py
- 提示词：生成该内容的提示词、与上面的模型配置一起，就可以复现生成内容

## Android App 版本功能门控

- Users 数据表中每个用户会注册自己的 `last_android_app_version_code` 用于进行版本门控
- 版本门控代码示例：
  - 添加配置项到 app/utils/config.py 中的配置对应功能的最小 app version code；后端在 app/api/utils/feature_gating.py 添加与之对应的判断函数
    例子： app/utils/config.py 中的 min_app_version_code_for_festival_memory，
    及 app/api/utils/feature_gating.py 中的 is_festival_memory_enabled
  - app version 不会回退，否则情况过于复杂

## 跨环境数据交换

- 任何跨环境数据交换，如从数据库读出、写入数据类型，从客户端获取、返回数据，等等，都需要定义 Pydantic model 来描述该数据；
- Pydantic model 定义的数据可以经过转换变成 JSON 字符串或者其他结构；
- 在代码中要严格使用 Pydantic model 数据来进行处理；
