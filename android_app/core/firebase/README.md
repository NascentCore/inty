# firebase - Firebase 集成

本模块提供 Firebase Analytics 和 Crashlytics 的集成功能。

## 功能特性

- ✅ Firebase Analytics 事件追踪
- ✅ Firebase Crashlytics 崩溃报告
- ✅ 自动初始化
- ✅ 用户行为追踪
- ✅ 自定义事件和属性
- ✅ 非致命错误记录
- ✅ Remote Config 远程参数与 AB 测试

## 使用方法

### 1. 自动初始化

Firebase 服务会在应用启动时自动初始化，无需手动调用。

### 2. 记录事件

```kotlin
// 记录简单事件
FirebaseManager.logEvent("button_clicked")

// 记录带参数的事件
FirebaseManager.logEvent(
    "purchase_completed", mapOf(
        "product_id" to "premium_subscription",
        "price" to 9.99,
        "currency" to "USD"
    )
)

// 使用预定义事件
FirebaseManager.logEvent(FirebaseManager.Events.USER_LOGIN)
```

### 3. 设置用户属性

```kotlin
// 设置用户ID
FirebaseManager.setUserId("user123")

// 设置用户属性
FirebaseManager.setUserProperty(FirebaseManager.UserProperties.USER_TYPE, "premium")
FirebaseManager.setUserProperty(FirebaseManager.UserProperties.SUBSCRIPTION_LEVEL, "gold")
```

### 4. 记录异常

```kotlin
try {
    // 可能出错的代码
    riskyOperation()
} catch (e: Exception) {
    // 记录非致命错误
    FirebaseManager.recordException(e)
}
```

### 5. 记录自定义日志

```kotlin
FirebaseManager.log("用户完成了重要操作")
```

### 6. 设置自定义键值对

```kotlin
FirebaseManager.setCustomKey("app_version", "1.0.0")
FirebaseManager.setCustomKey("user_level", 5)
FirebaseManager.setCustomKey("is_premium", true)
```

### 7. Remote Config 与 AB 测试（最小示例）

Remote Config 会在应用启动时通过 `FirebaseInitializer` 自动初始化并 `fetchAndActivate`。可直接通过 `RemoteConfigManager` 读取参数。

```kotlin
// 读取头像大小上限（MB），默认 10
val maxSizeMB = RemoteConfigManager.getLong(
    RemoteConfigManager.KEY_PROFILE_AVATAR_MAX_SIZE_MB,
    10L,
)

// 读取 AB 变体："A" | "B"
val variant = RemoteConfigManager.getString(
    RemoteConfigManager.KEY_AB_PROFILE_AVATAR_MESSAGE_VARIANT,
    "A",
)

if (variant.equals("B", ignoreCase = true)) {
    // 展示 B 方案的 UI 或提示
}
```

在 Firebase Console 中：
- 创建 Remote Config 参数 `profile_avatar_max_size_mb`（如 10/5 等值）
- 创建参数 `ab_profile_avatar_message_variant`，设置实验的变体为 A/B
- 使用 Firebase A/B Testing 以该参数为实验维度，分流用户并观察指标

## 测试功能

### 测试崩溃报告

```kotlin
// 触发测试崩溃（仅用于开发环境）
CrashlyticsTest.triggerTestCrash()
```

### 测试事件记录

```kotlin
// 记录测试事件
CrashlyticsTest.logTestEvent("test_event", mapOf("test_param" to "test_value"))

// 记录测试异常
CrashlyticsTest.recordTestException(Exception("Test exception"))
```

## 预定义事件

- `APP_OPEN`: 应用打开
- `USER_LOGIN`: 用户登录
- `USER_LOGOUT`: 用户登出
- `CHAT_STARTED`: 开始聊天
- `MESSAGE_SENT`: 发送消息
- `AI_RESPONSE_RECEIVED`: 收到AI回复
- `PROFILE_UPDATED`: 更新资料
- `SETTINGS_CHANGED`: 设置变更

## 预定义用户属性

- `USER_TYPE`: 用户类型
- `SUBSCRIPTION_LEVEL`: 订阅等级
- `APP_VERSION`: 应用版本
- `DEVICE_TYPE`: 设备类型

## 注意事项

1. 确保 `google-services.json` 文件已正确配置
2. 在发布版本中移除测试崩溃代码
3. 遵循隐私政策，合理收集用户数据
4. 避免记录敏感信息
5. Debug 构建最小拉取间隔为 0 秒；Release 为 3600 秒

## 配置说明

Firebase 服务通过以下方式自动初始化：

1. `FirebaseInitializer` 类实现 `Initializer` 接口
2. 在 `AndroidManifest.xml` 中配置自动初始化
3. 应用启动时自动调用初始化方法

## 版本信息

- Firebase BOM: 34.1.0
- Firebase Analytics: 最新版本
- Firebase Crashlytics: 最新版本

## Cursor Summary

- 目录用途: 集成 Firebase Analytics 与 Crashlytics，并封装常用追踪/崩溃上报接口。
- 关键类:
  - `FirebaseInitializer`: 应用启动自动初始化入口。
  - `FCMService`: Firebase Cloud Messaging 服务。
  - `FirebaseManager`: 事件日志、用户属性、异常上报等统一封装。
- 使用方式: 模块自动初始化，业务侧按需调用 `FirebaseManager` API 进行埋点与异常收集。
