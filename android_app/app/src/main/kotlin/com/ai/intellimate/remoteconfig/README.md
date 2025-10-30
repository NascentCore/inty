# Firebase Remote Config AB 测试 Demo

这是一个使用 Firebase Remote Config 进行 AB 测试的最小可行示例。

## 📋 功能特性

本 demo 展示了以下核心功能：

1. **Remote Config 初始化**：配置获取间隔和默认值
2. **远程配置获取**：从 Firebase 服务器获取最新配置
3. **AB 测试参数**：
   - `button_color`：按钮颜色（字符串，支持十六进制颜色值）
   - `button_text`：按钮文本（字符串）
   - `feature_enabled`：功能开关（布尔值）
   - `welcome_message`：欢迎消息（字符串）
4. **实时配置更新**：支持刷新配置而无需重启应用

## 🏗️ 项目结构

```
remoteconfig/
├── RemoteConfigManager.kt      # Remote Config 管理类
├── AbTestDemoActivity.kt       # Demo Activity
├── AbTestDemoViewModel.kt      # ViewModel
├── AbTestDemoScreen.kt         # Compose UI
└── README.md                   # 本文档
```

## 🚀 快速开始

### 1. Firebase 项目配置

#### 1.1 下载配置文件

1. 访问 [Firebase Console](https://console.firebase.google.com/)
2. 选择你的项目（或创建新项目）
3. 在项目设置中下载 `google-services.json`
4. 将文件放置在 `android_app/app/` 目录下

#### 1.2 启用 Remote Config

1. 在 Firebase Console 中，点击左侧菜单的 **Remote Config**
2. 点击 **开始使用** 或 **创建配置**

### 2. 创建 AB 测试参数

在 Firebase Console 的 Remote Config 中创建以下参数：

| 参数键 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `button_color` | String | `#FF6200EE` | 按钮颜色（十六进制） |
| `button_text` | String | `点击我` | 按钮显示文本 |
| `feature_enabled` | Boolean | `false` | 功能开关 |
| `welcome_message` | String | `欢迎使用我们的应用！` | 欢迎消息 |

### 3. 设置 AB 测试实验

#### 3.1 创建实验

1. 在 Firebase Console 中，点击 **Remote Config** → **实验**
2. 点击 **创建实验** → **Remote Config**
3. 填写实验信息：
   - **实验名称**：例如 "按钮颜色 AB 测试"
   - **描述**：实验目的描述
   - **应用**：选择你的 Android 应用

#### 3.2 配置受众

- **目标用户**：选择目标用户群体（例如 50% 的用户）
- **目标设备**：选择 Android 设备

#### 3.3 设置变体

创建两个变体组：

**对照组（A组）：**
- `button_color`: `#FF6200EE`（紫色）
- `button_text`: `点击我`

**实验组（B组）：**
- `button_color`: `#FF03DAC5`（青色）
- `button_text`: `立即体验`

#### 3.4 设置目标指标

选择你想要跟踪的指标（例如：点击率、留存率等）

#### 3.5 启动实验

点击 **开始实验** 即可启动 AB 测试。

### 4. 运行 Demo

#### 4.1 启动 Activity

在代码中启动 `AbTestDemoActivity`：

```kotlin
val intent = Intent(context, AbTestDemoActivity::class.java)
context.startActivity(intent)
```

#### 4.2 通过 ADB 启动

也可以通过 ADB 命令直接启动：

```bash
adb shell am start -n com.ai.intellimate/.remoteconfig.AbTestDemoActivity
```

#### 4.3 查看效果

应用会自动从 Firebase 获取配置，并显示：
- ✅ 配置获取状态
- 📝 各个参数的当前值
- 🎨 使用远程配置的 UI 元素
- 🔄 刷新配置按钮

## 🔧 核心代码说明

### RemoteConfigManager

负责管理 Remote Config 的单例对象：

```kotlin
// 初始化（通常在 Application.onCreate 中调用）
RemoteConfigManager.initialize(fetchIntervalSeconds = 0)

// 获取并激活配置
val activated = RemoteConfigManager.fetchAndActivate()

// 读取配置值
val buttonColor = RemoteConfigManager.getString("button_color")
val featureEnabled = RemoteConfigManager.getBoolean("feature_enabled")
```

### 配置获取间隔

```kotlin
// 开发环境：0 秒（立即获取）
RemoteConfigManager.initialize(fetchIntervalSeconds = 0)

// 生产环境：3600 秒（1小时）
RemoteConfigManager.initialize(fetchIntervalSeconds = 3600)
```

## 📊 AB 测试最佳实践

### 1. 实验设计

- **单一变量原则**：每次实验只测试一个变量
- **足够的样本量**：确保每组至少有几百个用户
- **运行足够时间**：至少运行 1-2 周以收集足够数据

### 2. 配置缓存

```kotlin
// Remote Config 会缓存配置，减少网络请求
// 可以设置最小获取间隔
val configSettings = remoteConfigSettings {
    minimumFetchIntervalInSeconds = 3600 // 1小时
}
```

### 3. 默认值

始终为每个参数设置默认值，确保在网络不可用时应用仍能正常工作：

```kotlin
private val defaultConfig = mapOf(
    ConfigKeys.BUTTON_COLOR to "#FF6200EE",
    ConfigKeys.BUTTON_TEXT to "点击我",
    // ...
)
```

### 4. 配置版本控制

在 Firebase Console 中，Remote Config 会自动保存版本历史，可以随时回滚到之前的配置。

## 🐛 常见问题

### Q1: 配置没有更新？

**答**：检查以下几点：
1. 确保已在 Firebase Console 中发布配置
2. 检查 `minimumFetchIntervalInSeconds` 设置
3. 尝试清除应用数据后重新安装

### Q2: 获取配置失败？

**答**：
1. 检查网络连接
2. 确认 `google-services.json` 配置正确
3. 查看 Logcat 日志中的错误信息

### Q3: 如何测试不同的配置变体？

**答**：在 Firebase Console 的 Remote Config 页面，可以使用"条件"功能为特定用户（例如测试设备）设置不同的配置值。

## 📚 相关文档

- [Firebase Remote Config 官方文档](https://firebase.google.com/docs/remote-config)
- [Firebase AB 测试指南](https://firebase.google.com/docs/ab-testing)
- [Android Remote Config 快速入门](https://firebase.google.com/docs/remote-config/get-started?platform=android)

## 🎯 后续扩展

可以基于此 demo 进行以下扩展：

1. **与 Analytics 集成**：记录用户行为，分析 AB 测试效果
2. **条件配置**：基于用户属性、应用版本等设置不同配置
3. **实时更新**：使用 `addOnConfigUpdateListener` 监听配置变化
4. **配置模板**：创建配置模板以便快速复制

## 📝 注意事项

1. **生产环境配置**：
   - 将 `fetchIntervalSeconds` 设置为合理的值（如 3600）
   - 避免频繁获取配置，以免影响性能和配额

2. **敏感信息**：
   - 不要在 Remote Config 中存储敏感信息（如 API 密钥）
   - Remote Config 的配置对所有用户可见

3. **配额限制**：
   - Firebase 免费版有配额限制
   - 详见 [定价页面](https://firebase.google.com/pricing)

## 🤝 贡献

如有问题或建议，欢迎提交 Issue 或 Pull Request。
