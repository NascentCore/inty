# Android App API 调用架构设计（Retrofit 单栈）

## 整体架构概览

Android app 当前采用 **Retrofit/Moshi 单网络栈**：

1. 统一入口：`NetServiceMgr`
2. 统一接口：`I*Api`（如 `IUserApi`、`IAgentApi`、`IChatApi`）
3. 统一结果模型：`HttpResult<T>`

Stainless 相关运行时代码（`IntyNetworkManager`、`core/data/http/services/*`、`com.inty.api.*`）已从 Android 运行时路径移除。

## 核心组件

### 1) 网络基础层（`library/network`）

- `HttpResult<T>`：统一成功/失败响应包装；
- `HttpResponseCallAdapterFactory`：Retrofit 调用适配；
- `MoshiResultTypeAdapterFactory`：标准响应结构反序列化；
- `GlobalErrorHandler` / `BusinessException`：统一错误处理。

### 2) 网络管理器（`NetServiceMgr`）

- 基于 Retrofit + Moshi 管理 API 实例；
- 提供 `getUserApi()`、`getAgentApi()`、`getChatApi()`、`getSubscriptionApi()`、`getCommonApi()`、`getReportApi()`；
- 通过 `clearCache()` 在 URL 切换与登录态变更时统一清理缓存。

### 3) 网络状态与配置

- `NetworkStateManager`：网络状态监控；
- `NetworkConfig`：按构建类型管理 baseUrl、超时、重试等配置；
- `UnifiedOkHttpClient`：统一 OkHttp 基础设施，避免重复构建客户端。

## 业务层调用约束

1. 新增或修改网络调用时，统一通过 `NetServiceMgr` + `I*Api`；
2. 业务层统一处理 `HttpResult.Success` / `HttpResult.Failure`；
3. 禁止新增 `IntyNetworkManager`、`com.inty.api.*`、`core/data/http/services/*` 的运行时代码引用。

## 迁移状态

- Android 构建层已移除 `libs.inty.kotlin`、`includeBuild("library/inty_sdk")`；
- 运行时代码已移除 Stainless 服务门面与桥接转换；
- 文档治理以 `android_app/docs/FR_REMOVE_STAINLESS_SDK_MIGRATION_PLAN.md` 为准。
