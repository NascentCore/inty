# 网络管理器说明（Retrofit 单栈）

## 概述

当前 Android 数据层仅保留 **`NetServiceMgr` + Retrofit + Moshi** 单网络栈。

- Stainless 相关运行时代码（`IntyNetworkManager`、`core/data/http/services/*`、`ApiResult` 桥接）已移除；
- 业务调用统一通过 `I*Api` + `HttpResult<T>` 路径；
- URL 切换与登录态变更只需要清理 `NetServiceMgr` 缓存。

## 当前架构

```
┌─────────────────────────────────────────┐
│         应用层 (ViewModel/Repository)    │
└─────────────────────────────────────────┘
                  │
                  ▼
          ┌─────────────────┐
          │  NetServiceMgr  │
          │ (Retrofit 栈)   │
          └─────────────────┘
                  │
                  ▼
          ┌─────────────────┐
          │   I*Api 接口     │
          │   + HttpResult  │
          └─────────────────┘
```

## NetServiceMgr 核心能力

```kotlin
object NetServiceMgr {
    fun getUserApi(): IUserApi
    fun getAgentApi(): IAgentApi
    fun getChatApi(): IChatApi
    fun getSubscriptionApi(): ISubscriptionApi
    fun getCommonApi(): ICommonApi
    fun getReportApi(): IReportApi
    fun clearCache()
}
```

## 使用规则

1. 新增或修改网络调用时，统一接入 `NetServiceMgr` + `I*Api`；
2. 业务层统一处理 `HttpResult.Success` / `HttpResult.Failure`；
3. 禁止新增 `IntyNetworkManager`、`com.inty.api.*`、`core/data/http/services/*` 运行时代码引用。

## 维护提示

- 本文档用于说明当前单栈架构，不再适用“NetServiceMgr vs IntyNetworkManager”对比语义；
- 若未来网络层演进，请同步更新本文件与 `android_app/docs/FR_REMOVE_STAINLESS_SDK_MIGRATION_PLAN.md`。

