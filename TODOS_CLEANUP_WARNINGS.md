# TODOS_CLEANUP_WARNINGS

记录 `./gradlew :app:testDebugUnitTest`（Java 21、Gradle 8.14.3）输出的全部警告，用于后续清理。

## Kotlin/Gradle 配置
- `WARNING: Unsupported Kotlin plugin version.`  
  - **影响面**：`android_app` 根项目（`buildSrc` + type-safe accessors）。  
  - **措施**：统一 `embedded-kotlin`/`kotlin-dsl` 与项目使用的 Kotlin 版本（当前请求 `2.2.20`，但插件依赖 `2.0.21`）。
- `w: Language version 1.8 is deprecated and its support will be removed in a future version of Kotlin.`（出现两次于 `inty_sdk:buildSrc` 编译阶段）  
  - **措施**：将 `kotlinOptions.languageVersion` 升级到受支持版本（≥ 2.0）。

## inty_sdk/buildSrc
- `inty_sdk/buildSrc/src/main/kotlin/inty.kotlin.gradle.kts:27`  
  - **警告**：`'KOTLIN_1_8' is deprecated. Will be removed soon.`  
  - **措施**：改用新的 `KotlinVersion.KOTLIN_2_0`（或对应常量）并同步相关分支常量。
- `inty_sdk/buildSrc/src/main/kotlin/inty.kotlin.gradle.kts:28`  
  - **警告**：同上，第二处引用 `KOTLIN_1_8`。  
  - **措施**：同上一条。

## core/common
- `core/common/src/main/kotlin/ai/sxwl/android/common/analytics/GlobalExceptionHandler.kt:37:68`  
  - **警告**：`'val id: Long' is deprecated. Deprecated in Java.`  
  - **措施**：替换为推荐的 `Thread` 字段（如 `threadId`）或使用非弃用 API。

## app 模块（主 APK + 单测）
- `app/src/main/kotlin/com/ai/intellimate/agent/generate/AvatarGenerateActivity.kt:134:39`  
  - **警告**：`centerAlignedTopAppBarColors()` 已弃用，需改用 `topAppBarColors()`。
- `app/src/main/kotlin/com/ai/intellimate/agent/generate/CreateRoleActivity.kt:477:39`  
  - **警告**：同上。
- `app/src/main/kotlin/com/ai/intellimate/agent/report/ReportScreen.kt:121:35`  
  - **警告**：同上。
- `app/src/main/kotlin/com/ai/intellimate/agent/info/AgentInfoActivity.kt:46:24`  
  - **警告**：`getParcelableExtra(String)` 已在 Java 中弃用。  
  - **措施**：迁移到 `getParcelableExtra(String, Class<T>)` 或 `BundleCompat`.
- `app/src/main/kotlin/com/ai/intellimate/chat/ChatActivity.kt:91:24`  
  - **警告**：同上。
- `app/src/main/kotlin/com/ai/intellimate/profile/ModifyProfileActivity.kt:58:48`  
  - **警告**：同上。
- `app/src/main/kotlin/com/ai/intellimate/ui/components/VideoCacheManager.kt:168:25`  
  - **警告**：条件恒为 `true`。  
  - **措施**：检查逻辑/常量，移除无效判断。
- `app/src/main/kotlin/com/ai/intellimate/utils/UserProfileManager.kt:28:17`  
  - **警告**：`Check for instance is always 'true'.`  
  - **措施**：重构单例判定逻辑。
- `app/src/main/kotlin/com/ai/intellimate/utils/UserProfileManager.kt:29:17`  
  - **警告**：`Check for instance is always 'false'.`
- `app/src/main/kotlin/com/ai/intellimate/utils/UserProfileManager.kt:30:17`  
  - **警告**：`'when' is exhaustive so 'else' is redundant here.`  
  - **措施**：移除无效分支，提升可读性。
