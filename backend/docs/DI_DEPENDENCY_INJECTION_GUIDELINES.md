# 后端依赖注入规范（第一批）

## 目标

- service/repository 通过 FastAPI `Depends` 暴露和注入。
- 减少 endpoint 对全局单例与隐式依赖的直接耦合。

## 适用范围

- `app/api/` 下的 FastAPI endpoint。
- 本批次优先覆盖聊天主链路：`chat.py`、`chats.py`。

## 规则

- 在 `app/api/deps.py` 统一定义依赖提供器函数。
- endpoint 函数参数通过 `Depends(get_xxx_service)` 声明依赖。
- endpoint 内不再直接 `from app.services.global_services import ...` 读取单例。
- 需要在 WebSocket 路径复用依赖时，显式透传同一依赖对象。

## 当前已落地依赖提供器

- `get_subscription_service() -> SubscriptionService`
- `get_voice_service() -> VoiceService`

## 示例

- endpoint 依赖声明：
  - `subscription_svc: SubscriptionService = Depends(deps.get_subscription_service)`
  - `voice_svc: VoiceService = Depends(deps.get_voice_service)`
- 调用方式：
  - `await subscription_svc.check_chat_limit(...)`
  - `await voice_svc.generate_voice(...)`

## 测试约定

- 通过 `app.dependency_overrides[deps.get_xxx_service]` 覆盖依赖。
- 单测/集成测试对服务方法打桩时，优先打在注入对象实例上。

