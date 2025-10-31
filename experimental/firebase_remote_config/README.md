# Firebase Remote Config AB 测试演示

这是一个独立的 Android 应用演示，展示如何使用 Firebase Remote Config 进行 AB 测试。

## 功能特性

- ✅ Firebase Remote Config 集成
- ✅ AB 测试变体支持（control, variant_a, variant_b）
- ✅ 远程配置动态获取和缓存
- ✅ Compose UI 展示不同的测试变体
- ✅ 配置刷新功能

## 项目结构

```
firebase_remote_config/
├── app/
│   ├── build.gradle.kts          # 应用构建配置
│   ├── google-services.json       # Firebase 配置文件（需要从 Firebase Console 下载）
│   └── src/main/
│       ├── AndroidManifest.xml
│       └── java/com/example/firebaseremoteconfig/
│           ├── MainActivity.kt          # 主 Activity
│           ├── RemoteConfigManager.kt   # Remote Config 管理类
│           └── ABTestVariant.kt         # AB 测试变体定义
└── README.md
```

## 设置步骤

### 1. 创建 Firebase 项目

1. 访问 [Firebase Console](https://console.firebase.google.com/)
2. 创建新项目或选择现有项目
3. 添加 Android 应用，包名设置为：`com.example.firebaseremoteconfig`
4. 下载 `google-services.json` 文件
5. 将 `google-services.json` 放置在 `app/` 目录下

### 2. 配置 Remote Config 参数

在 Firebase Console 中，导航到 **Remote Config** 部分，添加以下参数：

#### 参数 1: `button_color_variant`
- **默认值**: `control`
- **说明**: 控制按钮颜色的 AB 测试变体
- **可能的值**: 
  - `control` - 默认紫色按钮
  - `variant_a` - 蓝色按钮
  - `variant_b` - 红色按钮

#### 参数 2: `welcome_message`
- **默认值**: `欢迎使用应用！`
- **说明**: 欢迎消息文本
- **类型**: String

#### 参数 3: `enable_new_feature`
- **默认值**: `false`
- **说明**: 是否启用新功能
- **类型**: Boolean

### 3. 设置 AB 测试条件（可选）

在 Firebase Console 的 Remote Config 中，你可以为不同用户设置不同的参数值：

1. 点击参数旁的 **条件** 按钮
2. 创建新条件，例如：
   - **条件名称**: "10% 用户变体 A"
   - **条件类型**: "随机百分比"
   - **百分比**: 10%
   - **值**: `variant_a`

3. 再创建一个条件：
   - **条件名称**: "10% 用户变体 B"
   - **条件类型**: "随机百分比"
   - **百分比**: 10%
   - **值**: `variant_b`

4. 确保默认值（其他 80% 用户）为 `control`

### 4. 构建和运行

```bash
cd experimental/firebase_remote_config
./gradlew assembleDebug
```

或者使用 Android Studio 打开项目并运行。

## 使用方法

1. **首次启动**: 应用会自动获取并应用 Remote Config 的默认值
2. **查看变体**: 主界面会显示当前用户分配的按钮颜色变体
3. **刷新配置**: 点击"刷新配置"按钮可以手动获取最新的远程配置
4. **测试不同变体**: 在 Firebase Console 中修改参数值并发布，然后刷新应用查看效果

## Remote Config 参数说明

### `button_color_variant`
控制按钮颜色的 AB 测试变体：
- `control`: 紫色按钮（默认）
- `variant_a`: 蓝色按钮
- `variant_b`: 红色按钮

### `welcome_message`
欢迎消息文本，可以在不发布新版本的情况下更改应用中的文本内容。

### `enable_new_feature`
布尔值，用于控制是否启用新功能。这对于逐步推出新功能非常有用。

## 开发注意事项

### 配置获取间隔

在 `RemoteConfigManager.kt` 中，`minimumFetchIntervalInSeconds` 控制配置获取的最小间隔：

- **开发环境**: 设置为 `0`，每次调用都获取最新配置
- **生产环境**: 设置为 `3600`（1小时），避免频繁请求

### 默认值

始终为所有 Remote Config 参数设置默认值，确保在网络不可用或配置未获取时应用仍能正常工作。

### 错误处理

在实际应用中，应该：
1. 检查网络连接
2. 处理配置获取失败的情况
3. 记录配置获取和分析事件（用于 AB 测试数据分析）

## 扩展建议

1. **添加 Analytics 事件**: 在获取配置时记录事件，用于分析不同变体的效果
2. **添加更多 AB 测试场景**: 例如不同的 UI 布局、文案、功能开关等
3. **添加用户属性条件**: 基于用户属性（如地区、语言、用户等级）分配不同变体
4. **集成 A/B Testing**: 使用 Firebase A/B Testing 功能进行更高级的测试和分析

## 详细测试指南

📖 **查看 [TESTING_GUIDE.md](./TESTING_GUIDE.md) 获取详细的测试步骤说明**

测试指南包含：
- ✅ 完整的环境准备步骤
- ✅ Firebase 项目设置详细流程
- ✅ Remote Config 参数配置说明
- ✅ AB 测试条件设置步骤
- ✅ 应用构建和运行指南
- ✅ 不同变体测试方法
- ✅ 故障排查指南
- ✅ 测试场景清单

## 参考文档

- [Firebase Remote Config 文档](https://firebase.google.com/docs/remote-config)
- [Firebase Remote Config API](https://firebase.google.com/docs/reference/android/com/google/firebase/remoteconfig/FirebaseRemoteConfig)
- [Firebase A/B Testing](https://firebase.google.com/docs/ab-testing)
