# Firebase Remote Config AB 测试演示

这是一个使用 Firebase Remote Config 进行 AB 测试的最小演示。

## 功能说明

演示页面展示了一个按钮，按钮的颜色由 Firebase Remote Config 控制。通过配置不同的变体，可以实现 AB 测试：

- **变体 A**: 蓝色按钮
- **变体 B**: 红色按钮
- **变体 C**: 绿色按钮

## 使用步骤

### 1. 在 Firebase Console 中配置 Remote Config

1. 打开 [Firebase Console](https://console.firebase.google.com/)
2. 选择你的项目
3. 进入 **Remote Config** 页面
4. 添加新参数：
   - **参数键**: `button_color_variant`
   - **数据类型**: String
   - **默认值**: `blue`

### 2. 设置 AB 测试条件（可选）

你可以通过条件来对不同用户组显示不同的配置：

#### 示例：50/50 测试

1. 创建两个条件：
   - **条件 A** (蓝色组):
     - 条件类型: Random percentile
     - 值: 0-50
   - **条件 B** (红色组):
     - 条件类型: Random percentile
     - 值: 51-100

2. 为参数设置条件值：
   - 默认值: `blue`
   - 条件 A: `blue`
   - 条件 B: `red`

3. 发布配置

#### 示例：基于用户属性的测试

1. 创建条件：
   - 条件类型: User property
   - 用户属性: `user_type`
   - 值: `premium`

2. 设置条件值：
   - 默认值: `blue`
   - Premium 用户: `green`

### 3. 在应用中查看演示

#### 方法 1: 通过 Intent 启动演示 Activity

```kotlin
val intent = Intent(context, RemoteConfigAbTestActivity::class.java)
context.startActivity(intent)
```

#### 方法 2: 直接使用 Composable 组件

```kotlin
@Composable
fun MyScreen() {
    RemoteConfigAbTestDemo()
}
```

### 4. 配置 AndroidManifest.xml（如果使用 Activity）

在 `AndroidManifest.xml` 中添加：

```xml
<activity
    android:name=".demo.RemoteConfigAbTestActivity"
    android:label="Remote Config AB Test Demo"
    android:exported="false" />
```

## 代码说明

### Remote Config 获取

```kotlin
// 从服务器获取最新配置
FirebaseManager.fetchRemoteConfig()

// 读取配置值
val variant = FirebaseManager.getRemoteConfigString(
    key = "button_color_variant",
    defaultValue = "blue"
)
```

### 记录 AB 测试事件

```kotlin
// 记录用户分组
FirebaseManager.logEvent(
    eventName = "ab_test_assigned",
    parameters = mapOf(
        "experiment_name" to "button_color_test",
        "variant" to variant
    )
)

// 记录用户交互
FirebaseManager.logEvent(
    eventName = "ab_test_button_clicked",
    parameters = mapOf(
        "experiment_name" to "button_color_test",
        "variant" to variant,
        "click_count" to clickCount
    )
)
```

## 在 Firebase Analytics 中分析结果

1. 打开 Firebase Console > Analytics > Events
2. 查看以下事件：
   - `ab_test_assigned`: 用户被分配到的实验组
   - `ab_test_button_clicked`: 用户点击按钮的次数

3. 创建自定义报告比较不同变体的表现：
   - 点击率（click rate）
   - 用户参与度
   - 其他业务指标

## 最佳实践

1. **设置默认值**: 始终为 Remote Config 参数设置合理的默认值，确保在网络不可用时应用仍能正常工作

2. **缓存策略**: 
   - 调试模式：0 秒（立即获取）
   - 发布模式：3600 秒（1小时）

3. **错误处理**: 使用 try-catch 处理配置获取失败的情况

4. **记录事件**: 记录用户分组和关键交互事件，便于后续分析

5. **测试**: 在发布前测试所有变体，确保 UI 正常显示

## 扩展使用

你可以将 Remote Config 用于：
- UI 样式测试（颜色、布局、字体）
- 功能开关（启用/禁用新功能）
- 文案测试（按钮文字、提示信息）
- 数值调整（超时时间、重试次数）
- 多语言内容测试

## 注意事项

- Remote Config 配置的更改不会立即生效，需要等待缓存过期或主动调用 `fetchRemoteConfig()`
- 在生产环境中，建议使用合理的缓存时间（如 1 小时）以避免频繁请求
- 确保在 Firebase Console 中正确配置了条件，否则所有用户都会看到默认值