## Firebase Remote Config 分层 A/B 测试极简示例

此示例展示：
- 本地随机生成用户画像（性别、年龄段、会员分层）。
- 将画像写入 Firebase Analytics User Property，使 Firebase Remote Config 条件可依据这些属性生效。
- 拉取 Remote Config 参数，回调当前实验变体与主题色。

### 依赖
在应用模块 `build.gradle` 中添加：

```
implementation(platform("com.google.firebase:firebase-bom:33.4.0"))
implementation("com.google.firebase:firebase-analytics")
implementation("com.google.firebase:firebase-config")
```

项目级脚本需启用 Google Services 插件，并放置有效的 `google-services.json`。

### 使用步骤
1. 在 `Application` 或首个 `Activity` 中调用：
   ```kotlin
   FirebaseAbTestDemo.initialize(applicationContext) { result ->
       // 根据 result.variant / result.themeColor 决定 UI 或逻辑
   }
   ```
2. 首次启动会生成用户画像并写入 Analytics User Property，随后触发 Remote Config 拉取。
3. 在 Firebase Console > Remote Config 中创建参数：`profile_variant`、`profile_theme_color`，并基于 `profile_gender`、`profile_age_bracket`、`profile_segment` 定义条件，即可向不同分层用户下发差异配置。

> 调试可执行 `adb shell setprop debug.firebase.analytics.app <包名>` 打开 Firebase Debug View，实时查看用户属性与 Remote Config 命中情况。
