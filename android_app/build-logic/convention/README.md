＃ 习俗

## Cursor 摘要

- 目录用途: 自定义 Gradle 插件与构建约定集合，统一 Android/Kotlin/Compose 工程配置。
- 关键插件/扩展：
  - __保留__1__：`AndroidApplicationPlugin`、`AndroidLibraryPlugin`、`AndroidApplicationComposePlugin`、`AndroidLibraryComposePlugin`、`AndroidFeaturePlugin`、`AndroidFeatureComposePlugin`、`AndroidApplicationFlavorPlugin`。
  - Compose/导航：`NavigationComposePlugin`、`AndroidComposeExt`。
  - Kotlin/JVM：`JvmLibraryPlugin`、`KotlinAndroidExt`。
  - 发布/配置: `MavenPublishPlugin`、`ProjectConfig`、`ProjectExt`、`HeartFlavorExt`、`SignKeyConfig`。
- 作用: 以代码化的方式下沉构建细节，减少各模块重复配置，保证构建一致性。
