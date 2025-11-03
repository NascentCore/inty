# Inty SDK 迁移待办事项

## 未使用生成 SDK 的 API 端点

以下 API 端点目前使用 Retrofit/Moshi 实现，但**在生成的 SDK 中不可用**。这些端点应在可能的情况下迁移到使用生成的
SDK。

### 1. Agent API (IAgentApi.kt)

- `POST /api/v1/ai/agents/text-to-image` - 为角色生成背景图片
- `POST /api/v1/images` - 上传头像图片

### 2. Chat API (IChatApi.kt)

- `POST /api/v1/chat/completions/{agent_id}` - 向角色发送消息
- `GET /api/v1/chats/agents/{agent_id}/messages` - 根据角色 ID 获取聊天消息
- `GET /api/v1/chats/` - 获取用户的聊天对话列表
- `GET /api/v1/ai/agents/{agent_id}` - 获取角色信息（与 IAgentApi 重复）
- `GET /api/v1/chats/agents/{agent_id}/settings` - 根据角色 ID 获取聊天设置
- `PUT /api/v1/chats/agents/{agent_id}/settings` - 根据角色 ID 更新聊天设置
- `POST /api/v1/chats/agents/{agent_id}/messages/{message_id}/voice` - 为消息生成语音

### 3. User API (IUserApi.kt)

- `POST /api/v1/auth/google/login` - Google 身份验证登录
- `POST /api/v1/images` - 上传头像图片（与 IAgentApi 重复）
- `GET /api/v1/users/deletion/check` - 检查用户删除状态
- `POST /api/v1/users/delete-account` - 删除用户账户

### 4. Subscription API (ISubscriptionApi.kt)

- `GET /api/v1/subscription/plans` - 获取订阅计划
- `POST /api/v1/subscription/verify` - 验证订阅

### 5. Common API (ICommonApi.kt)

- `POST /api/v1/version/check` - 检查应用版本更新

## 迁移任务

### 高优先级

1. **图片上传端点** - `POST /api/v1/images` 在 IAgentApi 和 IUserApi 中都出现，应该合并
2. **角色信息** - `GET /api/v1/ai/agents/{agent_id}` 在 IAgentApi 和 IChatApi 中重复
3. **聊天功能** - 核心聊天端点应在可用时迁移到使用生成的 SDK

### 中优先级

1. **身份验证** - Google 登录端点应使用生成的 SDK
2. **订阅管理** - 订阅端点应使用生成的 SDK
3. **版本检查** - 版本检查端点应使用生成的 SDK

### 低优先级

1. **用户管理** - 用户删除端点可能是应用特定的
2. **语音生成** - 语音生成端点可能是应用特定的

## 说明

- 生成的 SDK 似乎更专注于核心角色管理、身份验证和基本订阅功能
- Retrofit 实现包括额外功能，如聊天消息、图片生成、语音合成和更全面的用户管理功能
- 考虑这些额外端点是否应该添加到生成的 SDK 中，还是保持为自定义实现
- 某些端点可能是重复的，无论 SDK 使用情况如何都应该合并

## 总计

目前有**13 个独特的 API 端点**未使用生成的 SDK。
