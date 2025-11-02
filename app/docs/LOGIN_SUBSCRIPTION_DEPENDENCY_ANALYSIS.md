# 登录与订阅依赖统一化分析

## 背景
- 当前 FastAPI 路由广泛依赖 `deps.get_current_active_user` 进行身份校验，但超级管理员验证逻辑在多个端点中重复实现。
- 订阅 / 限额相关判断分别散落在路由层、服务层（`subscription_service`、`chat_service`、`voice_service` 等），缺乏统一的依赖封装。

## 现状问题
- 权限依赖重复：`app/api/v1/endpoints/agents.py`、`app/api/v1/endpoints/admin.py` 等模块各自定义 `get_current_superuser`，逻辑一致却分散。
- 订阅限额校验分散：聊天、语音、图片生成、角色创建等端点直接调用 `subscription_service.check_*`，在失败分支中重复拼装 `BusinessErrorCode` 返回。
- 层间耦合：服务层（如 `chat_service.generate_chat_image`）直接抛出携带业务错误信息的 `HTTPException(499)`，路由层再捕获转换，职责边界模糊。
- 辅助函数冗余：聊天端点专门维护 `_handle_subscription_limit_error` 等工具函数，只为拼装订阅错误响应。

## 改进建议
- 在 `app/api/deps.py` 中新增统一权限依赖（如 `require_superuser`），供各路由通过 `Depends` 复用；必要时预留 `require_staff` 等扩展点。
- 抽象订阅限额依赖：设计通用 `require_subscription_limit`，内部根据 `usage_type` 协调 `subscription_service.check_*`，并在超限时生成统一业务错误。
- 针对常见场景提供语义化封装（`require_chat_quota`、`require_voice_quota`、`require_image_quota`、`require_agent_creation_quota`），替换现有端点内的重复判断逻辑。
- 统一业务错误处理：依赖层抛出结构化异常，由全局异常处理或标准装饰器转换为 `APIResponse`，端点只关注核心业务流程。
- 评估服务层是否需要保留限额校验；若由依赖统一负责，可增加显式参数控制，避免重复查询。

## 后续行动
- 梳理现有端点依赖链，列出需迁移的接口列表和优先级。
- 调整测试用例或新增用例，覆盖依赖超限与正常流程。
- 文档化统一依赖的使用方式，指导后续功能接入。
