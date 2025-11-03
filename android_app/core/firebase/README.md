# firebase - Firebase 集成

本模块提供 Firebase Analytics 和 Crashlytics 的集成功能。

## 功能特性

- ✅ Firebase Analytics 事件追踪
- ✅ Firebase Crashlytics 崩溃报告
- ✅ 自动初始化
- ✅ 用户行为追踪
- ✅ 自定义事件和属性
- ✅ 非致命错误记录

## 使用方法

### 1. 自动初始化

Firebase 服务会在应用启动时自动初始化，无需手动调用。

### 2. 记录事件

```kotlin
// 记录简单事件
FirebaseManager.logEvent("button_clicked")

// 记录带参数的事件（推荐使用 safeEventParams）
FirebaseManager.logEvent(
    "purchase_completed",
    FirebaseManager.safeEventParams(
        "product_id" to "premium_subscription",
        "price" to 9.99,
        "currency" to "USD"
    )
)

// 使用预定义事件
FirebaseManager.logEvent(FirebaseManager.Events.LOGIN)
```

#### 参数验证和规范化

`FirebaseManager` 自动验证和规范化事件参数：

- ✅ **参数名验证**：自动验证参数名是否符合 Firebase 规范（字母开头，只包含字母、数字、下划线，长度 ≤ 40）
- ✅ **参数名规范化**：不符合规范的参数名会被自动规范化（调试模式下会有警告）
- ✅ **参数值长度限制**：字符串值自动截断为 100 字符（调试模式下会有警告）
- ✅ **参数数量限制**：每个事件最多 25 个参数，超出部分会被忽略

**推荐使用 `safeEventParams`**，它会自动处理参数验证和规范化：

```kotlin
FirebaseManager.logEvent(
    "my_event",
    FirebaseManager.safeEventParams(
        "agent_id" to agent.id,
        "agent_name" to agent.name,
        "user_type" to if (isVip) "vip" else "free",
        "timestamp" to System.currentTimeMillis()
    )
)
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
- `LOGIN`: 用户登录（Firebase 内置事件）
- `USER_LOGOUT`: 用户登出
- `chat_started`: 开始聊天（第一次发送消息时触发）
- `MESSAGE_SENT`: 发送消息
- `MESSAGE_SEND_SUCCESS`: 消息发送成功
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
5. **自定义参数需要在 Firebase 控制台注册**：未注册的参数不会在报告中显示
    - 导航至：Analytics > 事件 > 管理自定义定义
    - 注册后可能需要 24-48 小时数据才会显示
    - 详细参数列表见：`bizops/FIREBASE_PARAMETERS_REGISTRATION.md`
6. **参数命名规范**：
    - 必须以字母开头
    - 只能包含字母、数字、下划线
    - 长度限制：最多 40 个字符
7. **参数值限制**：
    - 字符串值：最多 100 个字符（超长会被自动截断）
    - 每个事件：最多 25 个参数

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
