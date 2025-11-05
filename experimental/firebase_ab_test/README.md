## Firebase Remote Config A/B 测试示例

- **目标**：演示如何在 Android 客户端通过 Firebase Remote Config 控制实验分组，并使用 Firebase Analytics 记录曝光与点击事件。
- **文件结构**：
  - `FirebaseAbTestSample.kt`：核心示例代码，展示 Remote Config 初始化、参数读取与事件埋点。
  - `gradle_dependencies.gradle`：参考依赖清单，可复制到项目 `build.gradle`。
- **使用方式**：
  1. 在 Firebase 控制台创建 Remote Config 参数，例如 `new_feature_enabled`（布尔）与 `cta_button_color`（字符串）。
  2. 将 `gradle_dependencies.gradle` 内容合并到现有 Android 模块的 `build.gradle`。
  3. 将 `FirebaseAbTestSample.kt` 中的逻辑嵌入应用启动流程与界面代码，并按需调整包名。
  4. 在 Firebase A/B Testing 面板启动实验，分配变体并设置指标（如 `cta_clicked` 事件）。
  5. 使用 Android Studio 的 Firebase DebugView 验证事件是否带有实验参数。
- **注意事项**：
  - 为防止默认值缺失导致的空指针，示例中通过 `setDefaultsAsync` 提供兜底配置。
  - 在正式实验前，可将 `minimumFetchIntervalInSeconds` 设置为较小数值（如 0）以便调试；上线前再调回安全值。
  - Analytics 事件建议在参数中附带实验分组，便于后续在 BigQuery 或控制台中进行分组分析。
