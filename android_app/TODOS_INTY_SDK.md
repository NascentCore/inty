# Inty SDK 迁移待办事项

## 概述

本文档列出了 Android 应用中所有仍在直接调用后端 API endpoints 但**未使用 Stainless 生成的 Inty Kotlin SDK** 的地方。

**注意**: 本文档只包含 Android app 实际使用的 API，不包括 evaluation 或其他工具使用的 API。

## 分析依据

- **stainless.yml**: Stainless SDK 配置，定义了所有应该在 SDK 中可用的 endpoints
- **Retrofit 接口**: `IAgentApi`, `IChatApi`, `IUserApi`, `ISubscriptionApi`, `ICommonApi`
- **实际代码使用**: 通过搜索 `NetServiceMgr.get*Api()` 的使用情况，确认哪些端点在 Android app 中实际被调用

## 未使用 SDK 的 API 端点

### 1. Agent API (IAgentApi.kt)

以下端点目前使用 Retrofit/Moshi 实现，但**在 Stainless SDK 中已定义但未迁移**：

| Endpoint | Method | Stainless 定义 | 当前使用位置 | 状态 |
|----------|--------|----------------|--------------|------|
| `/api/v1/ai/agents/recommend` | GET | ✅ `recommend` | `ExplorePagingSource`, `AgentPagingSource`, `MainViewModel` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/ai/agents/me` | GET | ✅ `list` | `MainViewModel` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/ai/agents/{agent_id}` | GET | ✅ `retrieve` | `AgentInfoViewModel`, `ChatViewModel` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/ai/agents/{agent_id}` | DELETE | ✅ `delete` | `MainViewModel` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/ai/agents` | POST | ✅ `create` | `CreateRoleActivity` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/ai/agents/{agent_id}` | PUT | ✅ `update` | `CreateRoleActivity` | ⚠️ SDK 已定义但未使用 |

以下端点**在 Stainless SDK 中未定义**（需要添加到 stainless.yml）：

| Endpoint | Method | Stainless 定义 | 当前使用位置 | 状态 |
|----------|--------|----------------|--------------|------|
| `/api/v1/ai/agents/text-to-image` | POST | ❌ 未定义 | `AvatarGenerateViewModel` | ❌ SDK 中缺失 |
| `/api/v1/images` | POST | ❌ 未定义 | `CreateRoleActivity`, `IAgentApi`, `IUserApi` | ❌ SDK 中缺失 |

### 2. Chat API (IChatApi.kt)

以下端点目前使用 Retrofit/Moshi 实现，但**在 Stainless SDK 中已定义但未迁移**：

| Endpoint | Method | Stainless 定义 | 当前使用位置 | 状态 |
|----------|--------|----------------|--------------|------|
| `/api/v1/chats/` | GET | ✅ `list` | `ChatViewModel` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/chats/` | POST | ✅ `create` | `ChatViewModel` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/chats/{chat_id}` | DELETE | ✅ `delete` | 未找到直接使用 | ⚠️ SDK 已定义但未使用 |
| `/api/v1/chats/agents/{agent_id}/messages` | GET | ✅ `getMessages` | `ChatRemoteDataSource`, `ChatViewModel` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/chats/agents/{agent_id}/settings` | GET | ✅ `getSettings` | `ChatViewModel` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/chats/agents/{agent_id}/settings` | PUT | ✅ `updateSettings` | `ChatViewModel` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/chats/agents/{agent_id}/messages/{message_id}/voice` | POST | ✅ `generateMessageVoice` | `TtsManager` | ⚠️ SDK 已定义但未使用 |

以下端点**在 Stainless SDK 中未定义**（需要添加到 stainless.yml）：

| Endpoint | Method | Stainless 定义 | 当前使用位置 | 状态 |
|----------|--------|----------------|--------------|------|
| `/api/v1/chat/completions/{agent_id}` | POST | ❌ 未定义 | `ChatRemoteDataSource` | ❌ SDK 中缺失（但在 v2 中有 `send_message`） |

### 3. User API (IUserApi.kt)

以下端点目前使用 Retrofit/Moshi 实现，但**在 Stainless SDK 中已定义但未迁移**：

| Endpoint | Method | Stainless 定义 | 当前使用位置 | 状态 |
|----------|--------|----------------|--------------|------|
| `/api/v1/auth/google/login` | POST | ✅ `google.login` | `LoginViewModel`, `MainActivity` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/users/me` | GET | ✅ `users.profile.me` | `SettingViewModel`, `MySettingViewModel` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/users/deletion/check` | GET | ✅ `deletion.check_eligibility` | `SettingViewModel` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/users/delete-account` | POST | ✅ `delete_account` | `SettingViewModel` | ⚠️ SDK 已定义但未使用 |

以下端点**在 Stainless SDK 中未定义**（需要添加到 stainless.yml）：

| Endpoint | Method | Stainless 定义 | 当前使用位置 | 状态 |
|----------|--------|----------------|--------------|------|
| `/api/v1/images` | POST | ❌ 未定义 | `IUserApi`, `CreateRoleActivity` | ❌ SDK 中缺失 |

### 4. Subscription API (ISubscriptionApi.kt)

以下端点目前使用 Retrofit/Moshi 实现，但**在 Stainless SDK 中已定义但未迁移**：

| Endpoint | Method | Stainless 定义 | 当前使用位置 | 状态 |
|----------|--------|----------------|--------------|------|
| `/api/v1/subscription/plans` | GET | ✅ `list_plans` | `BillingRemoteManager` | ⚠️ SDK 已定义但未使用 |
| `/api/v1/subscription/verify` | POST | ✅ `verify` | `BillingPurchaseManager` | ⚠️ SDK 已定义但未使用 |

### 5. Common API (ICommonApi.kt)

以下端点目前使用 Retrofit/Moshi 实现，但**在 Stainless SDK 中未定义**（需要添加到 stainless.yml）：

| Endpoint | Method | Stainless 定义 | 当前使用位置 | 状态 |
|----------|--------|----------------|--------------|------|
| `/api/v1/version/check` | POST | ❌ 未定义 | `MainViewModel` | ❌ SDK 中缺失 |

## 统计汇总

### 按状态分类

- **⚠️ SDK 已定义但未迁移**: **19 个端点**
  - 这些端点已经在 stainless.yml 中定义，SDK 应该支持，但代码中还在使用 Retrofit API
  - 需要迁移到 SDK Service 层

- **❌ SDK 中缺失**: **4 个端点**
  - `POST /api/v1/ai/agents/text-to-image` - 生成背景图片
  - `POST /api/v1/images` - 上传图片
  - `POST /api/v1/chat/completions/{agent_id}` - 发送消息（v1，但 v2 中有）
  - `POST /api/v1/version/check` - 版本检查

### 按优先级分类

#### 🔴 高优先级（核心功能，SDK 已支持但未迁移）

1. **Agent 相关**（6 个端点）
   - `GET /api/v1/ai/agents/recommend` - 推荐列表
   - `GET /api/v1/ai/agents/me` - 我的创建列表
   - `GET /api/v1/ai/agents/{agent_id}` - 获取详情
   - `POST /api/v1/ai/agents` - 创建
   - `PUT /api/v1/ai/agents/{agent_id}` - 更新
   - `DELETE /api/v1/ai/agents/{agent_id}` - 删除

2. **Chat 相关**（7 个端点）
   - `GET /api/v1/chats/` - 对话列表
   - `POST /api/v1/chats/` - 创建对话
   - `DELETE /api/v1/chats/{chat_id}` - 删除对话
   - `GET /api/v1/chats/agents/{agent_id}/messages` - 获取消息
   - `GET /api/v1/chats/agents/{agent_id}/settings` - 获取设置
   - `PUT /api/v1/chats/agents/{agent_id}/settings` - 更新设置
   - `POST /api/v1/chats/agents/{agent_id}/messages/{message_id}/voice` - 生成语音

3. **User 相关**（4 个端点）
   - `POST /api/v1/auth/google/login` - Google 登录
   - `GET /api/v1/users/me` - 获取用户信息
   - `GET /api/v1/users/deletion/check` - 检查用户删除状态
   - `POST /api/v1/users/delete-account` - 删除用户账户

4. **Subscription 相关**（2 个端点）
   - `GET /api/v1/subscription/plans` - 获取订阅计划
   - `POST /api/v1/subscription/verify` - 验证订阅

#### 🟡 中优先级（需要在 SDK 中添加）

1. **图片上传** - `POST /api/v1/images`
   - 当前在 IAgentApi 和 IUserApi 中都有，应该统一

2. **版本检查** - `POST /api/v1/version/check`
   - 用于检查应用更新

3. **V1 消息发送** - `POST /api/v1/chat/completions/{agent_id}`
   - 注意：v2 中有 `send_message`，可能需要迁移到 v2

#### 🟢 低优先级（较少使用或 SDK 中缺失）

1. **生成背景图片** - `POST /api/v1/ai/agents/text-to-image`

## 迁移任务

### 第一步：迁移高优先级端点（SDK 已支持）

1. **AgentService** - 完善并迁移所有 Agent 相关调用
   - 迁移 `ExplorePagingSource` → 使用 `AgentService.getRecommendAgents()`
   - 迁移 `AgentPagingSource` → 使用 `AgentService.getRecommendAgents()`
   - 迁移 `MainViewModel` → 使用 `AgentService.getMyAgents()` 和 `AgentService.getRecommendAgents()`
   - 迁移 `AgentInfoViewModel` → 使用 `AgentService.getAgentInfo()`
   - 迁移 `ChatViewModel` → 使用 `AgentService.getAgentInfo()`
   - 迁移 `CreateRoleActivity` → 使用 `AgentService.createAgent()` 和 `AgentService.updateAgent()`
   - 迁移 `MainViewModel.deleteAgent()` → 使用 `AgentService.deleteAgent()`

2. **ChatService** - 完善并迁移所有 Chat 相关调用
   - 迁移 `ChatRemoteDataSource` → 使用 `ChatService.getChatHistory()` 和 `ChatService.sendMessage()`
   - 迁移 `ChatViewModel` → 使用 `ChatService.getConversations()`, `ChatService.createConversation()`, `ChatService.getChatHistory()`, `ChatService.getChatSettings()`, `ChatService.updateChatSettings()`
   - 迁移 `TtsManager` → 使用 `ChatService.generateMessageVoice()`

3. **UserService** - 迁移 Google 登录和用户信息获取
   - 迁移 `LoginViewModel` → 使用 `AuthService.googleLogin()`
   - 迁移 `MainActivity` → 使用 `AuthService.googleLogin()`
   - 迁移 `SettingViewModel` → 使用 `UserService.getUserProfile()`, `UserService.checkDeletionEligibility()`, `UserService.deleteAccount()`
   - 迁移 `MySettingViewModel` → 使用 `UserService.getUserProfile()`

4. **SubscriptionService** - 迁移订阅计划获取和验证
   - 迁移 `BillingRemoteManager` → 使用 `SubscriptionService.getSubscriptionPlans()`
   - 迁移 `BillingPurchaseManager` → 使用 `SubscriptionService.verifySubscription()`

### 第二步：添加缺失的 SDK 端点

1. 在 `stainless.yml` 中添加：
   - `POST /api/v1/images` - 图片上传
   - `POST /api/v1/version/check` - 版本检查
   - `POST /api/v1/ai/agents/text-to-image` - 生成背景图片（如果需要）

2. 重新生成 SDK 并更新依赖

3. 创建缺失的 Service：
   - `CommonService` - 处理版本检查等通用功能

### 第三步：更新调用代码

将以下文件中的 Retrofit API 调用迁移到 SDK Service：

- `ChatRemoteDataSource` → 使用 `ChatService`
- `ExplorePagingSource` → 使用 `AgentService`
- `AgentPagingSource` → 使用 `AgentService`
- `ChatViewModel` → 使用 `ChatService`
- `MainViewModel` → 使用 `AgentService`, `CommonService`（需要创建）
- `LoginViewModel` → 使用 `AuthService`
- `SettingViewModel` → 使用 `UserService`
- `MySettingViewModel` → 使用 `UserService`
- `BillingRemoteManager` → 使用 `SubscriptionService`
- `BillingPurchaseManager` → 使用 `SubscriptionService`
- `CreateRoleActivity` → 使用 `AgentService`
- `AgentInfoViewModel` → 使用 `AgentService`
- `TtsManager` → 使用 `ChatService`
- `AvatarGenerateViewModel` → 使用 `AgentService`（需要添加生成背景图片方法）

## 注意事项

1. **数据模型转换**: SDK 返回的数据模型可能与现有 `AgentInfo`、`MsgInfo` 等不匹配，需要添加转换层
2. **错误处理**: SDK 的错误处理方式可能与 Retrofit 不同，需要统一错误处理逻辑
3. **分页参数**: SDK 的分页参数命名可能与 Retrofit 不同（如 `skip`/`limit` vs `page`/`page_size`）
4. **向后兼容**: 迁移过程中保持向后兼容，可以逐步迁移
5. **用户删除相关**: `UserService` 需要添加 `checkDeletionEligibility()` 和 `deleteAccount()` 方法，这些端点在 SDK 中已定义但 Service 层未实现

## 说明

- 生成的 SDK 似乎更专注于核心角色管理、身份验证和基本订阅功能
- Retrofit 实现包括额外功能，如聊天消息、图片生成、语音合成和更全面的用户管理功能
- 考虑这些额外端点是否应该添加到生成的 SDK 中，还是保持为自定义实现
- 某些端点可能是重复的，无论 SDK 使用情况如何都应该合并

## 总计

目前有**23 个独特的 API 端点**在 Android app 中未使用生成的 SDK：
- **19 个端点** SDK 已定义但未迁移（需要迁移到 SDK Service）
- **4 个端点** SDK 中缺失（需要在 stainless.yml 中添加）

## 相关文件

- `app/stainless.yml` - Stainless SDK 配置
- `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/services/` - SDK Service 层
- `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/` - Retrofit 接口定义
