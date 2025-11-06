## Firebase Remote Config 分层 A/B 测试 Demo

本示例展示如何在 Android 应用中使用 Firebase Remote Config，基于本地随机生成的用户 Profile 设置 Firebase Analytics User Property，从而在 Firebase 控制台中为不同分层用户下发差异化配置。

### 目标
- 在应用启动时生成用于分层的随机用户画像（如性别、年龄段、付费类型）。
- 将画像信息写入 Firebase Analytics User Property，供 Remote Config 条件匹配。
- 拉取 Remote Config 参数，根据配置决定界面或逻辑分支。

### 必备依赖
在模块级 `build.gradle` 中引入：

```
implementation(platform("com.google.firebase:firebase-bom:33.4.0"))
implementation("com.google.firebase:firebase-analytics")
implementation("com.google.firebase:firebase-config")
implementation("com.google.firebase:firebase-installations")
```

项目级 `build.gradle` 需启用 Google Services 插件，并在模块级脚本中添加 `apply plugin: "com.google.gms.google-services"`。

### 使用方式
1. 将 `FirebaseAbTestDemo.initialize(applicationContext)` 放入 `Application.onCreate()` 或首页 `Activity` 的 `onCreate()`。
2. 首次运行会初始化 Firebase、生成用户画像并设置 Analytics User Property。
3. Remote Config 拉取成功后，可通过 `FirebaseAbTestDemo.observeFeatureFlag()` 查看当前生效的实验配置。
4. 在 Firebase Console > Remote Config 中，创建参数并基于 Analytics User Property（如 `profile_gender`、`profile_age_bracket`、`profile_segment`）定义条件，即可针对不同用户配置差异化值。

### 目录结构
- `FirebaseAbTestDemo.kt`：核心示例代码，完成画像生成、属性上报与 Remote Config 拉取。
- `README.md`：当前说明文件。

> **提示**：Remote Config 条件依赖 Analytics User Property 生效，Analytics 需要一定时间（通常数分钟）才能在控制台中展示新用户属性。测试阶段可借助 Debug View (`adb shell setprop debug.firebase.analytics.app <package>`) 即时验证。
