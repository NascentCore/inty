# Firebase Remote Config AB 测试演示

本演示展示了如何在 Android 应用中使用 Firebase Remote Config 进行 AB 测试。

## 功能概述

- **远程配置管理**: 使用 Firebase Remote Config 管理应用配置
- **AB 测试**: 支持不同用户看到不同的界面和功能
- **实时更新**: 无需发布新版本即可更新配置
- **事件追踪**: 使用 Firebase Analytics 追踪 AB 测试效果

## 项目结构

```
android_app/app/src/main/kotlin/com/ai/intellimate/abtest/
├── ABTestConfig.kt          # Remote Config 配置管理
├── ABTestManager.kt         # AB 测试管理器
├── ABTestViewModel.kt       # UI 状态管理
├── ABTestDemoScreen.kt      # 演示界面
├── ABTestDemoActivity.kt    # 演示 Activity
└── ABTestModule.kt          # 依赖注入模块
```

## 配置参数

### Remote Config 参数

| 参数名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `welcome_button_color` | String | "blue" | 欢迎按钮颜色 (blue/red/green/purple) |
| `welcome_button_text` | String | "开始体验" | 欢迎按钮文本 |
| `show_premium_banner` | Boolean | true | 是否显示高级功能横幅 |
| `chat_ui_style` | String | "modern" | 聊天界面样式 |
| `feature_flag_new_ui` | Boolean | false | 是否启用新 UI 功能 |

### Firebase Analytics 事件

| 事件名 | 描述 | 参数 |
|--------|------|------|
| `ab_test_initialized` | AB 测试初始化 | 所有配置参数 |
| `ab_test_button_clicked` | 按钮点击 | button_type, button_color, button_text |
| `ab_test_ui_style_changed` | UI 样式变更 | ui_style, new_ui_enabled |

## 使用方法

### 1. 启动演示

```kotlin
val intent = Intent(this, ABTestDemoActivity::class.java)
startActivity(intent)
```

### 2. 获取配置

```kotlin
val abTestConfig = ABTestModule.getABTestConfig()
val buttonColor = abTestConfig.getWelcomeButtonColor()
val buttonText = abTestConfig.getWelcomeButtonText()
```

### 3. 记录事件

```kotlin
val abTestManager = ABTestModule.getABTestManager()
abTestManager.logButtonClicked("welcome")
```

## Firebase Console 配置

### 1. 创建 Remote Config

1. 打开 [Firebase Console](https://console.firebase.google.com/)
2. 选择项目
3. 进入 Remote Config 页面
4. 添加上述配置参数

### 2. 设置条件

可以为不同用户群体设置不同的配置值：

```json
{
  "welcome_button_color": {
    "default_value": "blue",
    "conditions": [
      {
        "name": "新用户",
        "expression": "user.userProperties['is_new_user'] == true",
        "value": "green"
      },
      {
        "name": "VIP用户",
        "expression": "user.userProperties['is_vip'] == true",
        "value": "purple"
      }
    ]
  }
}
```

### 3. 发布配置

1. 配置完成后点击"发布更改"
2. 配置将在几分钟内生效

## 代码示例

### 基本使用

```kotlin
class MyActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // 初始化 AB 测试
        val abTestManager = ABTestModule.getABTestManager()
        abTestManager.initializeABTest()
        
        // 获取配置
        val config = ABTestModule.getABTestConfig()
        val buttonColor = config.getWelcomeButtonColor()
        
        // 应用配置到 UI
        updateUI(buttonColor)
    }
}
```

### 在 Compose 中使用

```kotlin
@Composable
fun MyScreen() {
    val viewModel = remember { ABTestViewModel() }
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    
    // 根据配置显示不同内容
    Button(
        colors = ButtonDefaults.buttonColors(
            containerColor = when (uiState.buttonColor) {
                "red" -> Color.Red
                "green" -> Color.Green
                "purple" -> Color.Magenta
                else -> Color.Blue
            }
        )
    ) {
        Text(uiState.buttonText)
    }
}
```

## 最佳实践

### 1. 配置管理

- 为每个配置参数设置合理的默认值
- 使用有意义的参数名称
- 定期清理不再使用的配置

### 2. 条件设置

- 使用用户属性进行精确的用户分群
- 避免过于复杂的条件表达式
- 测试条件表达式的正确性

### 3. 事件追踪

- 为每个重要的用户行为添加事件追踪
- 使用一致的参数命名规范
- 定期分析事件数据

### 4. 性能优化

- 设置合适的缓存时间（默认1小时）
- 避免频繁的配置获取
- 在应用启动时预加载配置

## 故障排除

### 常见问题

1. **配置不生效**
   - 检查 Firebase Console 中的配置是否正确发布
   - 确认应用有网络连接
   - 检查缓存时间设置

2. **事件不显示**
   - 确认 Firebase Analytics 已正确初始化
   - 检查事件参数格式是否正确
   - 等待几分钟让数据同步

3. **条件不匹配**
   - 检查用户属性是否正确设置
   - 验证条件表达式语法
   - 使用调试模式测试条件

### 调试技巧

```kotlin
// 启用调试模式
val configSettings = FirebaseRemoteConfigSettings.Builder()
    .setMinimumFetchIntervalInSeconds(0) // 开发时设为0
    .build()
remoteConfig.setConfigSettingsAsync(configSettings)

// 打印所有配置
val allConfigs = abTestConfig.getAllConfigs()
Log.d("ABTest", "Current configs: $allConfigs")
```

## 扩展功能

### 1. 添加新配置

1. 在 `ABTestConfig.kt` 中添加新的获取方法
2. 在 `setDefaultValues()` 中设置默认值
3. 在 Firebase Console 中添加对应参数
4. 在 UI 中使用新配置

### 2. 自定义事件

```kotlin
// 在 ABTestManager 中添加新事件
fun logCustomEvent(eventName: String, parameters: Map<String, Any>) {
    analytics.logEvent(eventName) {
        parameters.forEach { (key, value) ->
            param(key, value)
        }
    }
}
```

### 3. 配置验证

```kotlin
fun validateConfig(): Boolean {
    val config = abTestConfig.getAllConfigs()
    return config.isNotEmpty() && config.values.none { it.toString().isEmpty() }
}
```

## 相关文档

- [Firebase Remote Config 官方文档](https://firebase.google.com/docs/remote-config)
- [Firebase Analytics 官方文档](https://firebase.google.com/docs/analytics)
- [Android AB 测试最佳实践](https://firebase.google.com/docs/remote-config/use-cases)