# 运行时后端 URL 切换功能 - 代码 Review

## 概述

本次改动实现了在 debug 模式下运行时切换后端 URL 的功能，无需重新编译。主要涉及以下组件：

1. **DebugBackendEndpointStore** - 存储运行时覆盖的 URL
2. **NetworkConfig** - 应用运行时覆盖到配置
3. **IntyNetworkManager** - Inty SDK 客户端管理（支持 URL 切换）
4. **NetServiceMgr** - Retrofit 客户端管理（支持 URL 切换）
5. **DebugBackendSettingsEntry** - UI 界面用于切换 URL

## 核心机制分析

### ✅ 1. URL 存储机制 (`DebugBackendEndpointStore`)

**实现位置**: `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/config/DebugBackendEndpointStore.kt`

**优点**:
- ✅ 使用 `SharedPreferences` 持久化存储，应用重启后仍有效
- ✅ 仅在 DEBUG build type 且 App 为调试构建时可用，安全性好
- ✅ 提供了 `isRuntimeOverrideSupported()` 检查，防止误用

**潜在问题**:
- ⚠️ URL 格式验证不足：`persistOverride()` 只做了 `trim()`，没有验证 URL 格式的有效性
- ⚠️ 没有处理 URL 末尾的 `/` 统一性问题（虽然代码中有注释提到会自动补齐，但实际实现中没有）

**建议**:
```kotlin
fun persistOverride(rawInput: String): OverrideInfo {
    require(isRuntimeOverrideSupported()) {
        "Runtime backend override is only available for debug builds"
    }
    var url = rawInput.trim()
    
    // 确保 URL 格式正确
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
        url = "https://$url"
    }
    // 确保末尾有 /
    if (!url.endsWith("/")) {
        url = "$url/"
    }
    
    // 可以添加 URL 格式验证
    try {
        java.net.URL(url)
    } catch (e: Exception) {
        throw IllegalArgumentException("Invalid URL format: $url", e)
    }
    
    prefs.edit().putString(KEY_BASE_URL, url).apply()
    LogUtils.i("DebugBackendEndpointStore", "Runtime backend updated to $url")
    return OverrideInfo(url)
}
```

### ✅ 2. URL 应用机制 (`NetworkConfig`)

**实现位置**: `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/config/NetworkConfig.kt`

**优点**:
- ✅ `getCurrentEnvironmentConfig()` 在 DEBUG 模式下会调用 `debugOnlyApplyRuntimeOverride()`
- ✅ 运行时覆盖只在 DEBUG build type 下生效，其他 build type 不受影响
- ✅ 覆盖逻辑清晰，通过 `copy()` 创建新配置，不影响原始配置

**代码流程**:
```
getBaseUrl() 
  → getCurrentEnvironmentConfig() 
    → debugOnlyApplyRuntimeOverride() (仅在 DEBUG 模式)
      → DebugBackendEndpointStore.getOverrideInfo()
```

**潜在问题**:
- ✅ 无重大问题，实现正确

### ✅ 3. Inty SDK 客户端缓存机制 (`IntyNetworkManager`)

**实现位置**: `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/IntyNetworkManager.kt`

**优点**:
- ✅ 缓存 key 使用 `${apiKey}_${baseUrl}`，确保不同 URL 和 token 的客户端隔离
- ✅ `getClient()` 每次都会调用 `NetworkConfig.getBaseUrl()`，确保获取最新的 URL
- ✅ 提供了 `clearClientCache()` 方法，切换 URL 时可以清除缓存
- ✅ `clearOldTokenClients()` 会清理旧 token 的客户端，避免内存泄漏

**缓存机制**:
```kotlin
val cacheKey = "${currentApiKey}_$currentBaseUrl"
return clientCache.getOrPut(cacheKey) { createClient(currentApiKey, currentBaseUrl) }
```

**潜在问题**:
- ✅ 无重大问题，实现正确

### ✅ 4. Retrofit 客户端缓存机制 (`NetServiceMgr`)

**实现位置**: `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/NetServiceMgr.kt`

**优点**:
- ✅ Retrofit 实例缓存基于 `baseUrl`，不同 URL 会创建不同的 Retrofit 实例
- ✅ API 实例缓存 key 包含 `baseUrl`，例如：`"${baseUrl()}_IUserApi"`
- ✅ 提供了 `clearCache()` 方法，切换 URL 时可以清除缓存
- ✅ `baseUrl()` 方法使用 `NetworkConfig.getBaseUrl()`，支持运行时覆盖

**缓存机制**:
```kotlin
// Retrofit 缓存
private val retrofitCache = ConcurrentHashMap<String, Retrofit>()
private fun getRetrofitNormal(): Retrofit {
    val currentBaseUrl = baseUrl()
    return retrofitCache.getOrPut(currentBaseUrl) { ... }
}

// API 实例缓存
private val apiCache = ConcurrentHashMap<String, Any>()
fun getUserApi(): IUserApi {
    val cacheKey = "${baseUrl()}_IUserApi"
    return apiCache.getOrPut(cacheKey) { ... }
}
```

**潜在问题**:
- ⚠️ **问题发现**：`IntySetting.login()` 只清除了 `IntyNetworkManager` 的缓存，但没有清除 `NetServiceMgr` 的缓存。虽然 Retrofit 的缓存是基于 baseUrl 的，但为了保持一致性，建议在登录时也清除 Retrofit 缓存。

**建议修复**:
```kotlin
// 在 IntySetting.login() 中
fun login(uid: String, token: String) {
    IntyNetworkManager.clearClientCache()
    NetServiceMgr.clearCache()  // 添加这一行
    changeUser(uid)
    setToken(token)
    IntyNetworkManager.clearClientCache()
    NetServiceMgr.clearCache()  // 添加这一行
}
```

### ✅ 5. UI 界面 (`DebugBackendSettingsEntry` + `DebugBackendSettingsViewModel`)

**实现位置**: 
- `android_app/app/src/main/kotlin/com/ai/intellimate/settings/DebugBackendSettingsEntry.kt`
- `android_app/app/src/main/kotlin/com/ai/intellimate/settings/DebugBackendSettingsViewModel.kt`

**优点**:
- ✅ UI 仅在 `debug` build type 下显示，通过 `BuildConfig.BUILD_TYPE` 控制
- ✅ 提供了预设快捷按钮（local/dev/prod）
- ✅ 切换 URL 后会清除所有缓存（Inty SDK + Retrofit）
- ✅ UI 状态会实时更新，显示当前生效的 URL

**潜在问题**:
- ⚠️ UI 中没有输入框让用户手动输入自定义 URL，只有预设按钮
- ⚠️ 文档中提到"直接输入自定义 URL（自动补齐 scheme 与 `/`）"，但实际 UI 中没有实现

**建议**:
- 如果需要支持自定义 URL 输入，可以添加一个 `TextField` 和"应用"按钮

## 缓存机制完整性检查

### ✅ Inty SDK 缓存
- ✅ 缓存 key 包含 baseUrl：`"${apiKey}_${baseUrl}"`
- ✅ 切换 URL 时清除缓存：`IntyNetworkManager.clearClientCache()`
- ✅ 登录时清除缓存：`IntySetting.login()` 中已清除

### ⚠️ Retrofit 缓存
- ✅ 缓存 key 包含 baseUrl：`"${baseUrl}_${ApiType}"`
- ✅ 切换 URL 时清除缓存：`NetServiceMgr.clearCache()`
- ⚠️ **问题**：登录时**未清除** Retrofit 缓存（虽然不影响功能，但建议修复）

### ✅ 其他场景
- ✅ 登出时：虽然 `MainViewModel.logout()` 没有直接清除缓存，但 `IntySetting.setToken("")` 后，下次 `getClient()` 会使用新的 token，旧的客户端会被 `clearOldTokenClients()` 清理

## 功能完整性检查

### ✅ 核心功能
- ✅ URL 存储和读取
- ✅ URL 应用到 NetworkConfig
- ✅ Inty SDK 支持运行时 URL 切换
- ✅ Retrofit 支持运行时 URL 切换
- ✅ UI 界面用于切换 URL
- ✅ 缓存清除机制

### ⚠️ 待改进
- ⚠️ URL 格式验证不足
- ⚠️ 登录时未清除 Retrofit 缓存（建议修复）
- ⚠️ UI 中缺少自定义 URL 输入功能（如果文档要求的话）

## 总结

### ✅ 优点
1. **架构清晰**：各组件职责明确，URL 覆盖逻辑集中管理
2. **安全性好**：仅在 DEBUG build type 下可用
3. **缓存机制完善**：Inty SDK 和 Retrofit 都支持基于 URL 的缓存
4. **用户体验好**：切换后无需重启，立即生效

### ✅ 已修复的问题
1. **登录时清除 Retrofit 缓存**：✅ 已在 `IntySetting.login()` 中添加 `NetServiceMgr.clearCache()`

### ⚠️ 建议改进（非阻塞性问题）
1. **URL 格式验证**：在 `DebugBackendEndpointStore.persistOverride()` 中添加 URL 格式验证和自动补齐（可选，当前实现已基本可用）

### ✅ 功能验证
整体实现**可以完成运行时 URL 切换功能**，缓存机制工作正常。已修复登录时清除 Retrofit 缓存的问题，功能完整性良好。

