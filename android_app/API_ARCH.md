# Android App API 调用架构设计

## 整体架构概览

Android app 采用**双网络栈并行架构**，存在两套并行的 API 调用系统：

1. **传统 Retrofit/Moshi 网络栈** (`NetServiceMgr` + `I*Api`)
2. **Inty SDK 网络栈** (`IntyNetworkManager` + `*Service`)

这种设计提供了向后兼容性和渐进式迁移能力，但存在配置不一致和重复创建客户端的问题。

## 核心组件分析

### 1. 网络层基础架构 (`library/network`)

#### 1.1 响应包装系统
- **`HttpResult<T>`**: 统一的响应包装器
  ```kotlin
  sealed class HttpResult<out T : Any> {
      data class Success<T>(val data: T) : HttpResult<T>()
      data class Failure(val message: String, val code: Int) : HttpResult<Nothing>()
  }
  ```

- **`HttpResponseCall`**: 自定义 Call 实现，将 Retrofit 的 `Call<T>` 转换为 `Call<HttpResult<T>>`
- **`HttpResponseCallAdapterFactory`**: Retrofit 适配器工厂，负责类型转换

#### 1.2 JSON 序列化系统
- **`MoshiResultTypeAdapterFactory`**: 自定义 Moshi 适配器
- 支持标准化的服务器响应格式：`{code, message, data}`
- 自动处理业务错误码和成功状态判断
- 支持空值处理和异常容错

#### 1.3 错误处理机制
- **`BusinessException`**: 业务异常定义
- **`GlobalErrorHandler`**: 全局错误处理器
- 统一的错误码映射和异常转换

### 2. 传统网络管理器 (`NetServiceMgr`)

#### 2.1 核心功能
```kotlin
object NetServiceMgr {
    private val okHttpClient: OkHttpClient
    private val moshi: Moshi
    private val retrofitNormal: Retrofit      // 带包装的响应
    private val retrofitNoWrapper: Retrofit   // 无包装的响应
}
```

#### 2.2 拦截器链设计
1. **`PerformanceInterceptor`**: 性能监控
   - Firebase Performance 集成
   - 请求耗时统计和慢请求检测

2. **`RetryInterceptor`**: 智能重试机制
   - 指数退避算法
   - 幂等性方法检查
   - 可重试状态码和异常类型过滤

3. **`AuthInterceptor`**: 认证拦截器
   - 自动添加 Authorization header
   - 401 状态码处理和自动登出

4. **`CachedDns`**: DNS 缓存
   - 5分钟缓存策略
   - 线程安全的缓存实现

#### 2.3 环境配置管理
- 支持多环境：local、debug、playdebug、release
- 动态 BaseURL 切换
- 环境相关的超时和重试配置

### 3. Inty SDK 网络管理器 (`IntyNetworkManager`)

#### 3.1 现代化架构设计
```kotlin
object IntyNetworkManager {
    private val clientCache = ConcurrentHashMap<String, IntyClient>()
    
    // 业务服务入口
    val auth: AuthService
    val user: UserService  
    val agent: AgentService
    val chat: ChatService
    val subscription: SubscriptionService
    val report: ReportService
}
```

#### 3.2 核心特性
- **客户端缓存**: 基于 API Key 和 BaseURL 的智能缓存
- **统一请求执行**: `executeRequest()` 方法提供统一的超时和错误处理
- **网络状态管理**: 集成 `NetworkStateManager` 进行网络状态监控
- **配置驱动**: 基于 `NetworkConfig` 的环境配置管理

#### 3.3 服务层封装
每个业务领域都有对应的 Service 对象，提供统一的 API 调用接口：
- **`AgentService`**: 智能体相关 API（推荐、详情、创建、更新、删除、关注）
- **`ChatService`**: 聊天相关 API（发送消息、获取历史、创建/删除对话）
- **`AuthService`**: 认证相关 API（游客创建、Google登录、Token验证）
- **`UserService`**: 用户相关 API（用户资料、头像上传、统计信息）
- **`SubscriptionService`**: 订阅相关 API（订阅计划、用户订阅状态）
- **`ReportService`**: 举报相关 API

### 4. 网络状态管理 (`NetworkStateManager`)

#### 4.1 功能特性
- 实时网络状态监控
- 网络类型检测 (WIFI、移动网络、以太网等)
- 网络连接状态回调
- 线程安全的回调管理

#### 4.2 状态枚举
```kotlin
enum class NetworkType {
    NONE, WIFI, MOBILE, ETHERNET, VPN, UNKNOWN
}
```

### 5. 配置管理系统 (`NetworkConfig`)

#### 5.1 环境配置
支持四种构建环境，每种环境都有独立的配置：
- **Local**: 本地开发环境（短超时、少重试）
- **Debug**: 调试环境（标准配置、详细日志）
- **PlayDebug**: Play 商店调试环境（长超时、多重试）
- **Release**: 生产环境（优化超时、关闭详细日志）

#### 5.2 配置项
- **超时配置**: 连接、写入、读取超时
- **重试配置**: 最大重试次数、延迟策略
- **连接池配置**: 最大连接数、保活时间
- **日志配置**: 请求日志、性能监控、Chucker 集成

## 数据模型设计

### 1. API 响应模型
- **`AgentInfo`**: 智能体信息模型，支持 Parcelable
- **`ApiResult<T>`**: 统一的 API 结果包装器
- **`HttpResult<T>`**: 网络层响应包装器

### 2. 请求模型
- **`CreateAgentRequest`**: 创建智能体请求
- **`SendMsgReq`**: 发送消息请求
- **各种响应模型**: 对应不同 API 的响应结构

### 3. 数据转换
- **CDN 图片处理**: `getCdnImageUrl()` 函数支持图片尺寸和质量调整
- **模型转换**: 业务模型与 Inty SDK 模型之间的转换

## 业务层架构

### 1. Repository 模式
- **`ChatRepositoryImpl`**: 聊天数据仓库实现
- **`BillingRepository`**: 支付相关数据仓库

### 2. UseCase 模式
- **`SendMessageUseCase`**: 发送消息用例
- **`LoadChatHistoryUseCase`**: 加载聊天历史用例
- **`SyncChatDataUseCase`**: 同步聊天数据用例

### 3. Domain 层
- **`ChatDomain`**: 聊天领域模型和业务逻辑

## 架构问题与改进建议

### 1. 当前问题
- **双网络栈冲突**: Retrofit 和 Inty SDK 同时存在，容易导致配置不一致
- **重复的 OkHttpClient 创建**: 两套系统各自创建客户端
- **错误处理不统一**: 两套系统有不同的错误处理机制
- **数据转换复杂**: Inty SDK 的数据结构与业务模型不匹配

### 2. 改进方向
- **统一网络栈**: 逐步迁移到 Inty SDK，废弃传统 Retrofit 实现
- **数据映射层**: 建立 Inty SDK 数据到业务模型的转换层
- **配置统一**: 统一网络配置管理
- **错误处理标准化**: 建立统一的错误处理机制

## 性能优化特性

### 1. 网络优化
- **连接池复用**: 5-10 个连接的连接池
- **DNS 缓存**: 5分钟 DNS 缓存策略
- **智能重试**: 指数退避重试机制
- **性能监控**: Firebase Performance 集成

### 2. 内存优化
- **客户端缓存**: 避免重复创建网络客户端
- **弱引用**: 使用 WeakReference 避免内存泄露
- **异步处理**: 性能监控使用独立线程池

### 3. 图片优化
- **CDN 集成**: 自动图片尺寸和质量优化
- **缓存策略**: 多级图片缓存机制

## 总结

Android app 的 API 调用架构采用了现代化的设计理念，通过多层抽象和统一封装提供了稳定可靠的网络通信能力。虽然存在双网络栈的架构问题，但整体设计考虑了性能、可维护性和扩展性，为后续的架构优化和功能扩展奠定了良好的基础。

关键优势：
- 统一的错误处理和响应包装
- 完善的性能监控和重试机制
- 灵活的环境配置管理
- 清晰的业务服务分层

需要改进：
- 统一网络栈实现
- 完善数据转换层
- 标准化错误处理
- 优化客户端缓存策略