# Firebase Remote Config AB 测试 Demo

## 📝 概述

这是一个最小化的 Firebase Remote Config AB 测试演示项目，展示了如何在 Android 应用中使用 Firebase Remote Config 进行 AB 测试。

## 🎯 用户变更请求

创建一个使用 Firebase Remote Config (https://firebase.google.com/docs/remote-config) 进行 AB 测试的最小 Android 应用 demo。

## ✅ 实现内容

### 1. 依赖配置

- **gradle/libs.versions.toml**：添加了 `firebase-config` 依赖
- **app/build.gradle.kts**：在应用模块中引入 Firebase Remote Config 依赖

### 2. 核心代码

#### 文件结构
```
app/src/main/kotlin/com/ai/intellimate/remoteconfig/
├── RemoteConfigManager.kt      # Remote Config 管理类（单例）
├── AbTestDemoActivity.kt       # Demo 展示页面 Activity
├── AbTestDemoViewModel.kt      # ViewModel（管理 UI 状态）
├── AbTestDemoScreen.kt         # Compose UI 界面
└── README.md                   # 详细使用文档
```

#### 功能特性

1. **RemoteConfigManager**：
   - 统一管理 Remote Config 实例
   - 支持配置初始化和获取
   - 提供便捷的配置读取方法
   - 支持多种数据类型（String, Boolean, Long, Double）

2. **AB 测试参数**：
   - `button_color`：按钮颜色（十六进制字符串）
   - `button_text`：按钮文本
   - `feature_enabled`：功能开关（布尔值）
   - `welcome_message`：欢迎消息

3. **UI 展示**：
   - ✅ 配置状态指示器
   - 📝 实时显示所有配置参数
   - 🎨 动态渲染 AB 测试的 UI 元素（按钮颜色、文本）
   - 🔄 支持手动刷新配置
   - ⚠️ 错误处理和显示

### 3. Activity 注册

在 `AndroidManifest.xml` 中注册了 `AbTestDemoActivity`，可以独立启动测试。

## 🚀 如何使用

### 方式 1：通过代码启动

在任意 Activity 中添加：

```kotlin
val intent = Intent(this, AbTestDemoActivity::class.java)
startActivity(intent)
```

### 方式 2：通过 ADB 命令启动

```bash
adb shell am start -n com.ai.intellimate/.remoteconfig.AbTestDemoActivity
```

### 方式 3：添加到主界面（可选）

可以在主界面添加一个按钮来启动 demo：

```kotlin
Button(onClick = {
    val intent = Intent(context, AbTestDemoActivity::class.java)
    context.startActivity(intent)
}) {
    Text("查看 AB 测试 Demo")
}
```

## 🔧 Firebase 配置步骤

### 1. 准备 Firebase 项目

1. 访问 [Firebase Console](https://console.firebase.google.com/)
2. 选择或创建你的项目
3. 下载 `google-services.json` 并放置在 `android_app/app/` 目录

### 2. 在 Firebase Console 中创建参数

进入 **Remote Config** 页面，创建以下参数：

| 参数键 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `button_color` | String | `#FF6200EE` | 按钮颜色（十六进制） |
| `button_text` | String | `点击我` | 按钮显示文本 |
| `feature_enabled` | Boolean | `false` | 功能开关 |
| `welcome_message` | String | `欢迎使用我们的应用！` | 欢迎消息 |

### 3. 创建 AB 测试实验

1. 点击 **实验** 标签
2. 点击 **创建实验** → **Remote Config**
3. 设置实验名称和描述
4. 配置受众（例如 50% 的用户）
5. 创建变体组：
   - **对照组 A**：使用默认值
   - **实验组 B**：修改 `button_color` 为 `#FF03DAC5`，`button_text` 为 `立即体验`
6. 设置目标指标
7. 启动实验

### 4. 运行并测试

1. 构建并运行应用
2. 启动 `AbTestDemoActivity`
3. 观察配置获取和显示效果
4. 点击 **刷新按钮** 可重新获取配置

## 📊 代码示例

### 初始化 Remote Config

```kotlin
// 在 Application 或 Activity 中初始化
RemoteConfigManager.initialize(
    fetchIntervalSeconds = 0  // 开发环境：0，生产环境：3600
)
```

### 获取配置

```kotlin
// 获取并激活配置
val activated = RemoteConfigManager.fetchAndActivate()

// 读取字符串配置
val buttonColor = RemoteConfigManager.getString("button_color")

// 读取布尔配置
val featureEnabled = RemoteConfigManager.getBoolean("feature_enabled")
```

### 在 Compose 中使用

```kotlin
val buttonColor = remember { RemoteConfigManager.getString("button_color") }
val buttonText = remember { RemoteConfigManager.getString("button_text") }

Button(
    onClick = { /* ... */ },
    colors = ButtonDefaults.buttonColors(
        containerColor = parseColor(buttonColor)
    )
) {
    Text(buttonText)
}
```

## 📱 Demo 界面预览

界面包含以下区域：

1. **配置状态卡片**：显示是否成功获取远程配置
2. **欢迎消息卡片**：展示 `welcome_message` 参数
3. **按钮 AB 测试卡片**：动态渲染按钮颜色和文本
4. **功能开关卡片**：展示 `feature_enabled` 开关状态
5. **所有配置卡片**：列出所有配置键值对
6. **刷新按钮**：手动刷新配置

## 🎓 关键知识点

### 1. Remote Config 工作原理

- 应用启动时从 Firebase 服务器获取配置
- 配置会被缓存在本地
- 通过 `minimumFetchIntervalInSeconds` 控制获取频率
- 支持默认值，确保离线时应用正常工作

### 2. AB 测试流程

1. **定义假设**：例如"绿色按钮比紫色按钮有更高的点击率"
2. **创建实验**：在 Firebase Console 中创建 AB 测试
3. **收集数据**：Firebase 自动收集数据
4. **分析结果**：查看实验报告，选择最佳变体
5. **推广获胜者**：将获胜变体应用到所有用户

### 3. 最佳实践

- ✅ 始终设置默认值
- ✅ 合理设置获取间隔（生产环境不要设为 0）
- ✅ 不要存储敏感信息
- ✅ 单一变量原则：每次只测试一个变量
- ✅ 足够的样本量和时间周期

## 🔍 测试验证

### 本地测试

1. 使用条件配置为测试设备设置特定值
2. 清除应用数据后重新安装
3. 使用不同的用户 ID 测试分组

### 调试信息

在 Logcat 中搜索 `FirebaseRemoteConfig` 可以看到详细的调试日志。

## 📚 参考资源

- [Firebase Remote Config 官方文档](https://firebase.google.com/docs/remote-config)
- [Android Remote Config 快速入门](https://firebase.google.com/docs/remote-config/get-started?platform=android)
- [Firebase AB 测试指南](https://firebase.google.com/docs/ab-testing)
- [详细使用文档](android_app/app/src/main/kotlin/com/ai/intellimate/remoteconfig/README.md)

## 🎯 下一步扩展

基于此 demo，可以进行以下扩展：

1. **集成 Analytics**：记录用户行为，分析 AB 测试效果
2. **实时配置更新**：使用 `addOnConfigUpdateListener` 监听变化
3. **条件配置**：基于用户属性、地区、应用版本等设置不同配置
4. **配置分组**：管理多个 AB 测试参数
5. **自动化测试**：编写单元测试验证配置逻辑

## 📝 实现细节

### 代码规范

- ✅ 使用 Kotlin 协程处理异步操作
- ✅ 遵循 MVVM 架构模式
- ✅ 使用 Jetpack Compose 构建 UI
- ✅ 单一职责原则：配置管理与 UI 分离
- ✅ 错误处理和默认值机制

### 性能考虑

- 使用单例模式避免重复初始化
- 配置缓存机制减少网络请求
- 异步获取配置，不阻塞主线程
- 支持离线模式（使用默认值）

## 🐛 故障排查

### 问题 1：配置始终是默认值

**原因**：
- Firebase 项目未正确配置
- `google-services.json` 文件缺失或不正确
- 网络连接问题

**解决方案**：
1. 检查 Firebase Console 中的配置
2. 确认 `google-services.json` 在正确位置
3. 检查网络权限和连接

### 问题 2：获取配置失败

**原因**：
- 获取间隔限制
- Firebase 配额限制
- 网络异常

**解决方案**：
1. 开发时将 `fetchIntervalSeconds` 设为 0
2. 检查 Firebase 使用配额
3. 查看 Logcat 错误日志

### 问题 3：AB 测试不生效

**原因**：
- 实验未启动
- 用户不在目标受众中
- 配置未发布

**解决方案**：
1. 在 Firebase Console 确认实验状态
2. 检查受众定位设置
3. 确保已点击"发布更改"

## ✨ 总结

这个 demo 提供了一个完整的、可运行的 Firebase Remote Config AB 测试示例，包含：

- ✅ 完整的依赖配置
- ✅ 封装良好的管理类
- ✅ 美观的 UI 展示
- ✅ 详细的使用文档
- ✅ 最佳实践示例

可以直接在项目中使用，也可以作为学习和扩展的基础。
