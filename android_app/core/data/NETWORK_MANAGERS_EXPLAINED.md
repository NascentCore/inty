# 网络管理器说明：NetServiceMgr vs IntyNetworkManager

## 概述

项目中存在**双网络栈并行架构**，两个网络管理器分别管理不同的 API 调用方式：

1. **`NetServiceMgr`** - 传统 Retrofit/Moshi 网络栈
2. **`IntyNetworkManager`** - Inty SDK 网络栈（Stainless 生成）

## 详细对比

### 1. NetServiceMgr（传统 Retrofit 栈）

#### 用途
管理基于 **Retrofit + Moshi** 的传统网络请求，用于**已有功能的维护和兼容**。

#### 核心功能
```kotlin
object NetServiceMgr {
    // 提供 Retrofit API 接口实例
    fun getUserApi(): IUserApi
    fun getAgentApi(): IAgentApi
    fun getChatApi(): IChatApi
    fun getSubscriptionApi(): ISubscriptionApi
    fun getCommonApi(): ICommonApi
    
    // 获取当前 baseUrl（支持运行时切换）
    fun baseUrl(): String
    
    // 清除缓存（URL 切换或登录状态变化时）
    fun clearCache()
}
```

#### 技术栈
- **网络库**: Retrofit 3.0.0
- **序列化**: Moshi + KotlinJsonAdapterFactory
- **响应包装**: `HttpResult<T>` (Success/Failure)
- **错误处理**: `GlobalErrorHandler` + `BusinessException`

#### 使用场景
主要用于**已有功能的维护**，例如：
- `ExplorePagingSource` - 推荐智能体列表
- `ChatRemoteDataSource` - 聊天消息获取和发送
- `ChatViewModel` - 聊天设置相关 API
- `AgentInfoViewModel` - 智能体详情（部分 API）
- `SettingViewModel` - 用户删除账号

#### 响应格式
```kotlin
// 返回 HttpResult 包装
suspend fun exploreAgents(...): HttpResult<AgentInfoResponse>

// 使用方式
when (val result = NetServiceMgr.getAgentApi().exploreAgents(...)) {
    is HttpResult.Success -> { /* 处理成功 */ }
    is HttpResult.Failure -> { /* 处理失败 */ }
}
```

---

### 2. IntyNetworkManager（Inty SDK 栈）

#### 用途
管理基于 **Stainless 生成的 Inty SDK** 的现代化网络请求，用于**新功能开发**。

#### 核心功能
```kotlin
object IntyNetworkManager {
    // 获取 IntyClient 实例（支持缓存和 URL 切换）
    fun getClient(): IntyClient
    
    // 业务服务入口（推荐使用这些，而不是直接使用 getClient()）
    val auth: AuthService      // 认证相关
    val user: UserService      // 用户相关
    val agent: AgentService    // 智能体相关
    val chat: ChatService      // 聊天相关
    val subscription: SubscriptionService  // 订阅相关
    val report: ReportService  // 举报相关
    
    // 网络状态管理
    val networkState: NetworkStateManager
    
    // 统一的请求执行（带超时和错误处理）
    suspend fun <T> executeRequest(
        operation: String,
        config: RequestConfig? = null,
        apiCall: suspend () -> T
    ): ApiResult<T>
    
    // 清除客户端缓存
    fun clearClientCache()
}
```

#### 技术栈
- **网络库**: Stainless 生成的 Inty SDK（基于 OkHttp）
- **序列化**: SDK 内置（自动生成）
- **响应包装**: `ApiResult<T>` (Success/Error)
- **错误处理**: SDK 内置错误处理

#### 使用场景
主要用于**新功能开发**，例如：
- `UserService` - 用户资料管理（新实现）
- `AuthService` - 认证相关（新实现）
- `SubscriptionService` - 订阅管理（新实现）
- `ReportService` - 举报功能（新实现）

#### 响应格式
```kotlin
// 通过 Service 层封装，返回 ApiResult
suspend fun getProfile(): ApiResult<UserProfile>

// 使用方式
when (val result = IntyNetworkManager.user.getProfile()) {
    is ApiResult.Success -> { /* 处理成功 */ }
    is ApiResult.Error -> { /* 处理失败 */ }
}
```

---

## 两者关系

### 1. 并行存在，职责分离

```
┌─────────────────────────────────────────┐
│         应用层 (ViewModel/Repository)    │
└─────────────────────────────────────────┘
              │              │
              ▼              ▼
    ┌─────────────────┐  ┌──────────────────┐
    │  NetServiceMgr  │  │ IntyNetworkManager│
    │  (Retrofit 栈)  │  │  (SDK 栈)        │
    └─────────────────┘  └──────────────────┘
              │              │
              ▼              ▼
    ┌─────────────────┐  ┌──────────────────┐
    │  I*Api 接口      │  │  *Service 服务  │
    │  (手动定义)      │  │  (SDK 生成)     │
    └─────────────────┘  └──────────────────┘
```

### 2. 共享基础设施

两者都使用：
- **`UnifiedOkHttpClient`** - 统一的 OkHttpClient 实例
- **`NetworkConfig`** - 统一的环境配置和 baseUrl 管理
- **`DebugBackendEndpointStore`** - 运行时 URL 切换支持

### 3. 缓存机制

#### NetServiceMgr 缓存
```kotlin
// Retrofit 实例缓存（基于 baseUrl）
private val retrofitCache = ConcurrentHashMap<String, Retrofit>()

// API 接口实例缓存（基于 baseUrl + API 类型）
private val apiCache = ConcurrentHashMap<String, Any>()

// 缓存 key 格式: "${baseUrl()}_IUserApi"
```

#### IntyNetworkManager 缓存
```kotlin
// IntyClient 实例缓存（基于 apiKey + baseUrl）
private val clientCache = ConcurrentHashMap<String, IntyClient>()

// 缓存 key 格式: "${apiKey}_${baseUrl}"
```

### 4. URL 切换协调

当切换 URL 时，两者都需要清除缓存：

```kotlin
// DebugBackendSettingsViewModel.applySelectedOverride()
IntyNetworkManager.clearClientCache()  // 清除 SDK 缓存
NetServiceMgr.clearCache()             // 清除 Retrofit 缓存
```

---

## 使用指导原则

根据 `AGENTS.md` 的指导：

### ✅ 已有功能改善修改
- **继续使用 NetServiceMgr**，不进行迁移
- 例如：`ExplorePagingSource`、`ChatRemoteDataSource` 等

### ✅ 新功能开发
- **优先使用 IntyNetworkManager**，使用 SDK 生成的服务
- 例如：新的用户管理、订阅功能等

### ⚠️ 注意事项

1. **不要混用**：同一个功能不要同时使用两套网络栈
2. **错误处理不同**：
   - NetServiceMgr: `HttpResult<T>`
   - IntyNetworkManager: `ApiResult<T>`
3. **响应格式不同**：
   - NetServiceMgr: 需要手动处理 `{code, message, data}` 格式
   - IntyNetworkManager: SDK 自动处理

---

## 实际使用示例

### NetServiceMgr 使用示例

```kotlin
// ExplorePagingSource.kt
class ExplorePagingSource {
    private suspend fun loadFromNetwork(page: Int, pageSize: Int): NetworkResult {
        val result = NetServiceMgr.getAgentApi().exploreAgents(
            page = page,
            pageSize = pageSize,
            sort_seed = sortSeed.toString(),
        )
        
        return when (result) {
            is HttpResult.Success -> NetworkResult.Success(result.data)
            is HttpResult.Failure -> NetworkResult.Error(result.message)
        }
    }
}
```

### IntyNetworkManager 使用示例

```kotlin
// UserService.kt
object UserService {
    suspend fun getProfile(): ApiResult<UserProfile> {
        return IntyNetworkManager.executeRequest("getUserProfile") {
            val response = IntyNetworkManager.getClient()
                .api().v1().users().profile().me()
            ApiResult.Success(response)
        }
    }
}

// 在 ViewModel 中使用
class ProfileViewModel {
    fun loadProfile() {
        launchBackground {
            when (val result = IntyNetworkManager.user.getProfile()) {
                is ApiResult.Success -> { /* 更新 UI */ }
                is ApiResult.Error -> { /* 处理错误 */ }
            }
        }
    }
}
```

---

## 未来规划

根据 `AGENTS.md` 和 `API_ARCH.md`：

### 🟡 目标架构
- **统一到单一网络栈**（优先使用 Inty SDK）
- **标准化错误处理和日志**
- **统一鉴权和环境管理**
- **整合监控和性能指标**

### 🔴 已知问题
- 错误处理机制不统一（`HttpResult` vs `ApiResult`）
- 环境配置和鉴权流程分叉
- OkHttpClient 重复创建（已通过 `UnifiedOkHttpClient` 解决）
- 日志和监控分散

---

## 总结

| 特性 | NetServiceMgr | IntyNetworkManager |
|------|---------------|-------------------|
| **用途** | 已有功能维护 | 新功能开发 |
| **技术栈** | Retrofit + Moshi | Stainless 生成的 SDK |
| **响应包装** | `HttpResult<T>` | `ApiResult<T>` |
| **缓存机制** | Retrofit + API 实例 | IntyClient 实例 |
| **缓存 key** | `${baseUrl}_${ApiType}` | `${apiKey}_${baseUrl}` |
| **URL 切换** | ✅ 支持 | ✅ 支持 |
| **服务封装** | 手动定义 `I*Api` | SDK 生成 `*Service` |
| **推荐使用** | 已有功能 | 新功能 |

两者**并行存在**，通过共享基础设施（`UnifiedOkHttpClient`、`NetworkConfig`）实现统一的环境配置和 URL 切换功能。

