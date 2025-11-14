# firebase - Firebase 集成

本模块提供 Firebase Analytics、Crashlytics、Performance 和 Remote Config 的集成功能。

## 功能特性

- ✅ Firebase Analytics 事件追踪
- ✅ Firebase Crashlytics 崩溃报告
- ✅ Firebase Performance 性能监控
- ✅ Firebase Remote Config 远程配置
- ✅ A/B 测试支持
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

### 7. Remote Config 远程配置

#### 7.1 设置默认值

在应用启动时设置 Remote Config 的默认值，确保在网络不可用时也能正常工作：

```kotlin
// 在 Application 或 ViewModel 的初始化中
FirebaseManager.setRemoteConfigDefaults(
    mapOf(
        "max_file_size_mb" to 10L,
        "enable_new_feature" to false,
        "welcome_message" to "欢迎使用应用！",
        "api_timeout_seconds" to 30.0
    )
)
```

#### 7.2 获取并激活配置

从 Firebase 服务器获取最新配置并立即激活：

```kotlin
// 在协程中调用
lifecycleScope.launch {
    val hasNewConfig = FirebaseManager.fetchAndActivateRemoteConfig()
    if (hasNewConfig) {
        // 配置已更新，刷新 UI
        updateUIWithNewConfig()
    }
}
```

#### 7.3 获取配置值

```kotlin
// 获取字符串值
val welcomeMessage = FirebaseManager.getRemoteConfigString("welcome_message")

// 获取布尔值
val isFeatureEnabled = FirebaseManager.getRemoteConfigBoolean("enable_new_feature")

// 获取长整型值
val maxFileSizeMB = FirebaseManager.getRemoteConfigLong("max_file_size_mb")

// 获取双精度浮点值
val timeoutSeconds = FirebaseManager.getRemoteConfigDouble("api_timeout_seconds")
```

#### 7.4 分步获取和激活（高级用法）

如果需要更精细的控制，可以分步进行：

```kotlin
lifecycleScope.launch {
    // 1. 先获取配置（不激活）
    val fetchSuccess = FirebaseManager.fetchRemoteConfig()

    if (fetchSuccess) {
        // 2. 在合适的时机激活配置
        val activateSuccess = FirebaseManager.activateRemoteConfig()
        if (activateSuccess) {
            // 配置已激活，更新 UI
            updateUIWithNewConfig()
        }
    }
}
```

#### 7.5 实际使用示例

```kotlin
// 在 ModifyProfileActivity 中使用 Remote Config 配置文件大小限制
class ModifyProfileActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        lifecycleScope.launch {
            // 获取并激活配置
            FirebaseManager.fetchAndActivateRemoteConfig()

            // 使用配置值
            val maxSizeMB = FirebaseManager.getRemoteConfigLong("max_file_size_mb")
            val maxSizeBytes = maxSizeMB * 1024 * 1024

            // 使用配置值进行文件大小检查
            // ...
        }
    }
}
```

### 8. A/B 测试

Firebase Remote Config 与 Firebase A/B Testing 集成，可以轻松进行 A/B 测试。

#### 8.1 在 Firebase Console 中设置 A/B 测试

1. 打开 Firebase Console，进入 **A/B Testing**
2. 创建新实验，选择 **Remote Config** 作为实验类型
3. 选择要测试的参数（例如：`button_color_variant`）
4. 定义变体：
    - **Control（对照组）**: `control`
    - **Variant A**: `variant_a`
    - **Variant B**: `variant_b`
5. 设置目标用户和指标（如点击率、转化率等）
6. 启动实验

#### 8.2 在代码中使用 A/B 测试

```kotlin
// 获取 A/B 测试变体
val buttonVariant = FirebaseManager.getRemoteConfigString("button_color_variant")

// 根据变体显示不同的 UI
when (buttonVariant) {
    "variant_a" -> {
        // 显示变体 A 的 UI
        Button(colors = ButtonDefaults.buttonColors(containerColor = Color.Blue))
    }
    "variant_b" -> {
        // 显示变体 B 的 UI
        Button(colors = ButtonDefaults.buttonColors(containerColor = Color.Red))
    }
    else -> {
        // 显示对照组（默认）的 UI
        Button(colors = ButtonDefaults.buttonColors(containerColor = Color.Purple))
    }
}

// 记录 A/B 测试曝光事件（用于分析）
FirebaseManager.logEvent(
    "ab_test_exposure",
    FirebaseManager.safeEventParams(
        "experiment_name" to "button_color_test",
        "variant" to buttonVariant
    )
)
```

#### 8.3 A/B 测试最佳实践

1. **设置默认值**：始终为 A/B 测试参数设置默认值，确保实验未启动时应用仍能正常工作
2. **记录曝光事件**：在用户看到测试变体时记录曝光事件，用于分析
3. **记录转化事件**：在用户完成目标操作时记录转化事件（如点击、购买等）
4. **等待配置激活**：在应用启动时获取并激活配置，确保用户看到正确的变体

```kotlin
// 完整的 A/B 测试流程示例
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        lifecycleScope.launch {
            // 1. 获取并激活配置
            FirebaseManager.fetchAndActivateRemoteConfig()

            // 2. 获取 A/B 测试变体
            val variant = FirebaseManager.getRemoteConfigString("button_color_variant")

            // 3. 记录曝光事件
            FirebaseManager.logEvent(
                "ab_test_exposure",
                FirebaseManager.safeEventParams(
                    "experiment_name" to "button_color_test",
                    "variant" to variant
                )
            )

            // 4. 根据变体显示 UI
            setContent {
                MyApp(variant = variant)
            }
        }
    }
}
```

### 9. Remote Config 配置管理

#### 9.1 更新配置设置

```kotlin
// 动态调整获取间隔（例如：调试模式下实时获取）
if (BuildConfig.DEBUG) {
    FirebaseManager.updateRemoteConfigSettings(
        minFetchIntervalSeconds = 0L // 每次调用都获取最新配置
    )
} else {
    FirebaseManager.updateRemoteConfigSettings(
        minFetchIntervalSeconds = 3600L // 生产环境：1小时
    )
}
```

#### 9.2 检查最后获取时间

```kotlin
val lastFetchTime = FirebaseManager.getRemoteConfigLastFetchTime()
if (lastFetchTime > 0) {
    val timeSinceLastFetch = System.currentTimeMillis() - lastFetchTime
    Log.d("RemoteConfig", "距离上次获取配置已过去: ${timeSinceLastFetch / 1000}秒")
}
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
- `CHAT_STARTED`: 开始聊天（第一次发送消息时触发）
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

## Remote Config 配置说明

### 获取间隔设置

- **调试模式**：`minimumFetchIntervalInSeconds = 0`（每次调用都获取最新配置，便于测试）
- **生产环境**：`minimumFetchIntervalInSeconds = 3600`（1小时，避免频繁请求）

### 默认值的重要性

**强烈建议**为所有 Remote Config 参数设置默认值，原因：

1. 网络不可用时应用仍能正常工作
2. 首次启动时立即使用默认值，无需等待网络请求
3. 配置获取失败时使用默认值作为降级方案

### 配置获取时机

建议在以下时机获取配置：

1. **应用启动时**：在 `Application.onCreate()` 或主 Activity 的 `onCreate()` 中
2. **应用进入前台时**：在 `onResume()` 中（可选，用于获取最新配置）
3. **用户手动刷新时**：提供刷新按钮让用户主动获取最新配置

### Firebase Console 配置步骤

1. 打开 Firebase Console，进入 **Remote Config**
2. 添加参数：
    - **参数键**：例如 `max_file_size_mb`
    - **默认值**：例如 `10`
    - **数据类型**：选择 String、Number 或 Boolean
3. 添加条件（用于 A/B 测试）：
    - 点击参数旁的 **条件** 按钮
    - 创建条件（如随机百分比、用户属性等）
    - 为不同条件设置不同的值
4. 发布配置：点击 **发布更改** 使配置生效

### 10. Remote Config 自定义信号条件

#### 10.1 什么是自定义信号条件

**自定义信号（Custom Signals）** 是 Firebase Remote Config 的高级条件类型，允许你基于 **Firebase
Analytics 的自定义事件或用户属性** 来动态分配参数值。

与传统的条件（如随机百分比、用户属性）不同，自定义信号可以：

- 基于用户行为（如完成特定事件、达到某个等级）
- 基于用户属性（如订阅状态、用户类型）
- 实现更精细的个性化配置

#### 10.2 使用场景

**适用于 AI 情感聊天应用的场景：**

1. **基于用户活跃度**：为活跃用户（发送消息数 > 100）启用高级功能
2. **基于订阅状态**：为 VIP 用户提供不同的配置值
3. **基于用户行为**：为完成首次聊天的用户启用引导功能
4. **基于用户属性**：为不同地区的用户提供本地化配置

#### 10.3 实施步骤

##### 步骤 1：在应用中设置用户属性或记录事件

首先，确保在应用中设置了相关的用户属性或记录了相关事件：

```kotlin
// 示例 1：设置用户属性（订阅状态）
FirebaseManager.setUserProperty(
    FirebaseManager.UserProperties.SUBSCRIPTION_LEVEL,
    "premium" // 或 "free", "plus"
)

// 示例 2：设置用户属性（用户类型）
FirebaseManager.setUserProperty(
    FirebaseManager.UserProperties.USER_TYPE,
    "vip" // 或 "free"
)

// 示例 3：记录自定义事件（消息发送数）
FirebaseManager.logEvent(
    "message_sent",
    FirebaseManager.safeEventParams(
        "message_count" to totalMessageCount,
        "agent_id" to agentId
    )
)

// 示例 4：记录自定义事件（聊天完成）
FirebaseManager.logEvent(
    FirebaseManager.Events.CHAT_STARTED,
    FirebaseManager.safeEventParams(
        "is_first_chat" to isFirstChat,
        "agent_id" to agentId
    )
)
```

##### 步骤 2：在 Firebase Console 中创建自定义信号条件

1. **打开 Firebase Console**
    - 进入 **Remote Config** > **条件** 标签页
    - 点击 **"创建条件"** 或 **"Add condition"**

2. **选择条件类型**
    - 选择 **"自定义信号"** 或 **"Custom signal"**

3. **配置条件规则**

   **示例 A：基于用户属性（订阅状态）**
   ```
   条件名称: VIP 用户
   条件类型: 自定义信号
   信号类型: 用户属性
   属性名称: subscription_level
   运算符: 等于
   值: premium
   ```

   **示例 B：基于用户属性（用户类型）**
   ```
   条件名称: 免费用户
   条件类型: 自定义信号
   信号类型: 用户属性
   属性名称: user_type
   运算符: 等于
   值: free
   ```

   **示例 C：基于事件参数（消息数量）**
   ```
   条件名称: 活跃用户
   条件类型: 自定义信号
   信号类型: 事件参数
   事件名称: message_sent
   参数名称: message_count
   运算符: 大于
   值: 100
   ```

4. **支持的运算符**
    - **等于** (`==`)：精确匹配
    - **不等于** (`!=`)：不匹配
    - **大于** (`>`)：数值比较
    - **大于等于** (`>=`)：数值比较
    - **小于** (`<`)：数值比较
    - **小于等于** (`<=`)：数值比较
    - **包含** (`contains`)：字符串包含
    - **不包含** (`not contains`)：字符串不包含

##### 步骤 3：将条件应用到 Remote Config 参数

1. **编辑 Remote Config 参数**
    - 在参数列表中，找到要配置的参数（如 `auto_enable_keep_talking`）
    - 点击参数行的 **"条件"** 列

2. **添加条件值**
    - 点击 **"添加值"** 或 **"Add value"**
    - 选择你创建的自定义信号条件
    - 为该条件设置特定的参数值

3. **完整示例：基于订阅状态的配置**

   ```
   参数: auto_enable_keep_talking
   
   默认值: false
   
   条件 1: VIP 用户（subscription_level == "premium"）
   值: true
   
   条件 2: 免费用户（subscription_level == "free"）
   值: false
   ```

##### 步骤 4：发布配置

1. 点击 **"发布更改"** 或 **"Publish changes"**
2. 配置会在几分钟内生效

#### 10.4 实际应用示例

##### 示例 1：基于订阅状态配置功能开关

**场景**：为 VIP 用户默认启用 "Keep Talking" 功能

```kotlin
// 1. 在用户登录或订阅状态变更时设置用户属性
fun onUserLogin(user: User) {
    FirebaseManager.setUserProperty(
        FirebaseManager.UserProperties.SUBSCRIPTION_LEVEL,
        user.subscriptionLevel // "premium", "plus", "free"
    )
}

// 2. 在 Firebase Console 中创建条件：
//    条件名称: VIP 用户
//    信号类型: 用户属性
//    属性名称: subscription_level
//    运算符: 等于
//    值: premium

// 3. 在 Remote Config 参数中应用条件：
//    参数: auto_enable_keep_talking
//    默认值: false
//    VIP 用户条件: true

// 4. 在应用中读取配置（代码已自动处理）
//    SettingStateManager.initializeFromRemoteConfig() 会自动应用配置
```

##### 示例 2：基于用户活跃度配置功能

**场景**：为活跃用户（发送消息数 > 100）启用新功能

```kotlin
// 1. 在发送消息时记录事件
fun onMessageSent(agentId: String, totalMessageCount: Int) {
    FirebaseManager.logEvent(
        FirebaseManager.Events.MESSAGE_SENT,
        FirebaseManager.safeEventParams(
            "message_count" to totalMessageCount,
            "agent_id" to agentId
        )
    )
}

// 2. 在 Firebase Console 中创建条件：
//    条件名称: 活跃用户
//    信号类型: 事件参数
//    事件名称: message_sent
//    参数名称: message_count
//    运算符: 大于
//    值: 100

// 3. 在 Remote Config 参数中应用条件：
//    参数: enable_advanced_features
//    默认值: false
//    活跃用户条件: true

// 4. 在应用中读取配置
lifecycleScope.launch {
    FirebaseManager.fetchAndActivateRemoteConfig()
    val enableAdvanced = FirebaseManager.getRemoteConfigBoolean("enable_advanced_features")
    if (enableAdvanced) {
        // 启用高级功能
    }
}
```

##### 示例 3：基于地区配置本地化内容

**场景**：为不同地区的用户提供不同的欢迎消息

```kotlin
// 1. 在应用启动时设置用户地区属性（已自动设置）
//    FirebaseManager.setDeviceInfo() 会自动设置 user_region

// 2. 在 Firebase Console 中创建多个条件：
//    条件 1: 美国用户（user_region == "US"）
//    条件 2: 日本用户（user_region == "JP"）
//    条件 3: 欧洲用户（user_region in ["GB", "DE", "FR"]）

// 3. 在 Remote Config 参数中应用条件：
//    参数: welcome_message
//    默认值: "Welcome to Inty!"
//    美国用户条件: "Welcome to Inty! Start chatting now."
//    日本用户条件: "Intyへようこそ！チャットを始めましょう。"
//    欧洲用户条件: "Bienvenue sur Inty! Commencez à discuter."

// 4. 在应用中读取配置
val welcomeMessage = FirebaseManager.getRemoteConfigString("welcome_message")
```

#### 10.5 注意事项

1. **数据延迟**
    - 用户属性或事件需要先发送到 Firebase Analytics
    - 通常需要几分钟到几小时才能在 Remote Config 条件中使用
    - 建议在设置用户属性后等待一段时间再测试

2. **条件匹配**
    - 如果用户同时满足多个条件，Remote Config 会使用**第一个匹配的条件**
    - 建议按优先级顺序排列条件

3. **默认值**
    - 始终设置默认值，确保不满足任何条件时应用仍能正常工作
    - 默认值会在网络不可用或条件未匹配时使用

4. **测试建议**
    - 使用 Firebase Console 的 **"测试设备"** 功能进行测试
    - 在调试模式下设置 `minimumFetchIntervalInSeconds = 0` 以实时获取配置
    - 使用 `FirebaseManager.getAllRemoteConfigValues()` 查看所有配置值

5. **用户属性命名**
    - 用户属性名称必须与 Firebase Analytics 中注册的属性名称完全一致
    - 建议使用 `FirebaseManager.UserProperties` 中定义的常量

6. **事件参数**
    - 事件参数条件基于最近的事件数据
    - 如果用户从未触发过该事件，条件不会匹配

#### 10.6 调试和验证

```kotlin
// 1. 查看所有 Remote Config 值（调试模式）
if (AppUtils.isAppDebug()) {
    val allValues = FirebaseManager.getAllRemoteConfigValues()
    LogUtils.d("RemoteConfig", "所有配置值: $allValues")
}

// 2. 验证用户属性是否已设置
FirebaseManager.setUserProperty("test_property", "test_value")
// 在 Firebase Console > Analytics > User Properties 中验证

// 3. 验证事件是否已记录
FirebaseManager.logEvent("test_event", mapOf("test_param" to "test_value"))
// 在 Firebase Console > Analytics > Events 中验证

// 4. 检查配置获取时间
val lastFetchTime = FirebaseManager.getRemoteConfigLastFetchTime()
LogUtils.d("RemoteConfig", "最后获取时间: $lastFetchTime")
```

#### 10.7 最佳实践

1. **使用预定义的用户属性常量**
   ```kotlin
   // ✅ 推荐：使用预定义常量
   FirebaseManager.setUserProperty(
       FirebaseManager.UserProperties.SUBSCRIPTION_LEVEL,
       "premium"
   )
   
   // ❌ 不推荐：硬编码字符串
   FirebaseManager.setUserProperty("subscription_level", "premium")
   ```

2. **在关键时机设置用户属性**
    - 用户登录时：设置用户类型、订阅状态
    - 订阅状态变更时：更新订阅等级
    - 应用启动时：设置设备信息、地区信息

3. **合理使用条件优先级**
    - 将更具体的条件放在前面
    - 将通用条件放在后面
    - 默认值放在最后

4. **监控和优化**
    - 定期检查条件匹配率
    - 根据数据调整条件规则
    - 使用 A/B 测试验证配置效果

## 版本信息

- Firebase BOM: 34.5.0
- Firebase Analytics: 最新版本
- Firebase Crashlytics: 最新版本
- Firebase Performance: 最新版本
- Firebase Remote Config: 最新版本

## 参考文档

- [Firebase Remote Config 官方文档](https://firebase.google.com/docs/remote-config)
- [Firebase A/B Testing 官方文档](https://firebase.google.com/docs/ab-testing)
- [Remote Config 最佳实践](https://firebase.google.com/docs/remote-config/best-practices)

## Cursor Summary

- 目录用途: 集成 Firebase Analytics、Crashlytics、Performance 和 Remote Config，并封装常用追踪/崩溃上报/远程配置接口。
- 关键类:
  - `FirebaseInitializer`: 应用启动自动初始化入口。
  - `FCMService`: Firebase Cloud Messaging 服务。
  - `FirebaseManager`: 事件日志、用户属性、异常上报、远程配置等统一封装。
- 使用方式: 模块自动初始化，业务侧按需调用 `FirebaseManager` API 进行埋点、异常收集和远程配置获取。
