# Kotlin Workflow TODOs

- [ ] **自动化模块映射**：`ci_android_app.yaml` 的测试任务解析依赖手工 `case`，新建模块会被漏测。重写为基于 `settings.gradle.kts`/`gradlew projects` 的映射，并在无法匹配时回退到执行完整 `./gradlew testDebugUnitTest`。
- [ ] **优化 Gradle 缓存策略**：停止缓存 `android_app/**/build` 目录，切换到 `gradle/actions/setup-gradle@v3` 或最小化到 `~/.gradle/{caches,wrapper}` 与 `android_app/.gradle`，避免缓存污染与浪费配额。
- [ ] **补充静态检查任务**：在 CI 中追加 `lintDebug`、`detekt`/`ktlint` 或等价 `./gradlew check`，并把这些 job 设为 PR 必须通过，提前拦截资源、Compose、风格类问题。
