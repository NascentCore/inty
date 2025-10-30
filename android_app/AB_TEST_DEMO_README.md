# Firebase Remote Config AB 测试演示

这是一个完整的 Firebase Remote Config AB 测试演示，展示了如何在 Android 应用中使用 Firebase Remote Config 进行 A/B 测试。

## 🚀 快速开始

### 1. 运行演示

```bash
# 构建并运行应用
./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk

# 启动 AB 测试演示
adb shell am start -n com.ai.intellimate/.abtest.ABTestDemoActivity
```

### 2. 在代码中使用

```kotlin
// 启动演示 Activity
val intent = Intent(this, ABTestDemoActivity::class.java)
startActivity(intent)

// 或者在现有界面中集成
ABTestLauncher() // Compose 组件
```

## 📁 项目结构

```
android_app/app/src/main/kotlin/com/ai/intellimate/abtest/
├── ABTestConfig.kt              # Remote Config 配置管理
├── ABTestManager.kt             # AB 测试管理器和事件追踪
├── ABTestViewModel.kt           # UI 状态管理
├── ABTestDemoScreen.kt          # 演示界面 UI
├── ABTestDemoActivity.kt        # 演示 Activity
├── ABTestModule.kt              # 依赖注入模块
├── ABTestLauncher.kt            # 快速启动组件
└── ABTestIntegrationExample.kt  # 集成示例
```

## 🔧 功能特性

### ✅ 已实现功能

- [x] Firebase Remote Config 集成
- [x] 配置参数管理（按钮颜色、文本、功能开关等）
- [x] 实时配置更新
- [x] Firebase Analytics 事件追踪
- [x] 完整的演示界面
- [x] 错误处理和加载状态
- [x] 配置缓存和性能优化
- [x] 详细的文档和示例

### 🎯 AB 测试参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `welcome_button_color` | String | "blue" | 欢迎按钮颜色 |
| `welcome_button_text` | String | "开始体验" | 欢迎按钮文本 |
| `show_premium_banner` | Boolean | true | 是否显示高级功能横幅 |
| `chat_ui_style` | String | "modern" | 聊天界面样式 |
| `feature_flag_new_ui` | Boolean | false | 新 UI 功能开关 |

### 📊 事件追踪

| 事件 | 描述 | 参数 |
|------|------|------|
| `ab_test_initialized` | AB 测试初始化 | 所有配置参数 |
| `ab_test_button_clicked` | 按钮点击 | button_type, button_color, button_text |
| `ab_test_ui_style_changed` | UI 样式变更 | ui_style, new_ui_enabled |

## 🛠️ 配置步骤

### 1. Firebase Console 配置

1. 打开 [Firebase Console](https://console.firebase.google.com/)
2. 选择你的项目
3. 进入 Remote Config 页面
4. 添加上述配置参数
5. 设置条件（可选）
6. 发布配置

### 2. 条件设置示例

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

## 💡 使用示例

### 基本使用

```kotlin
// 获取配置
val config = ABTestModule.getABTestConfig()
val buttonColor = config.getWelcomeButtonColor()

// 记录事件
val manager = ABTestModule.getABTestManager()
manager.logButtonClicked("welcome")
```

### Compose 集成

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

### 快速启动

```kotlin
// 在任意 Activity 中
context.launchABTestDemo()

// 或在 Compose 中
ABTestLauncher()
```

## 🔍 调试和测试

### 调试模式

```kotlin
// 启用调试模式（开发时）
val configSettings = FirebaseRemoteConfigSettings.Builder()
    .setMinimumFetchIntervalInSeconds(0) // 立即获取
    .build()
remoteConfig.setConfigSettingsAsync(configSettings)
```

### 查看配置

```kotlin
val allConfigs = abTestConfig.getAllConfigs()
Log.d("ABTest", "Current configs: $allConfigs")
```

### 测试条件

1. 在 Firebase Console 中设置测试条件
2. 使用调试模式立即获取配置
3. 验证配置是否正确应用

## 📈 最佳实践

### 1. 配置管理

- 为每个参数设置合理的默认值
- 使用有意义的参数名称
- 定期清理不再使用的配置

### 2. 条件设置

- 使用用户属性进行精确分群
- 避免过于复杂的条件表达式
- 测试条件表达式的正确性

### 3. 事件追踪

- 为重要用户行为添加事件追踪
- 使用一致的参数命名规范
- 定期分析事件数据

### 4. 性能优化

- 设置合适的缓存时间
- 避免频繁的配置获取
- 在应用启动时预加载配置

## 🐛 故障排除

### 常见问题

1. **配置不生效**
   - 检查 Firebase Console 配置是否正确发布
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

## 📚 相关文档

- [Firebase Remote Config 官方文档](https://firebase.google.com/docs/remote-config)
- [Firebase Analytics 官方文档](https://firebase.google.com/docs/analytics)
- [Android AB 测试最佳实践](https://firebase.google.com/docs/remote-config/use-cases)
- [项目详细配置文档](./FIREBASE_REMOTE_CONFIG_AB_TEST_DEMO.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个演示项目！

## 📄 许可证

本项目遵循 MIT 许可证。