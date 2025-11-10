# AGENTS.md · android_app/（Android 客户端）

本文件覆盖并补充根 `AGENTS.md`，仅适用于 `android_app/`。

## 平台与约束
- 仅支持竖屏（portrait）；无需考虑 landscape 兼容。

## 架构与网络
- 现有并行网络栈：Retrofit/Moshi 与 Inty SDK；避免新增第三套；复用统一鉴权/环境/日志配置，避免重复创建 `OkHttpClient`。
- 依赖版本集中于 `gradle/libs.versions.toml`；模块间尽量使用版本对齐。

## 构建
- `local`/`debug`/`release` 构建配置需保持继承关系一致；调试依赖不得泄露到发布变体。

## UI/性能
- Compose/Recyler 需避免无意义重组；图片与音频加载注意内存与缓存策略。

## Kotlin/Compose UI 规范

- 不要使用裸写的数值如 10.dp 而应该定义常量如：const val boxHeight = 10.dp
- 组件 UI 配置通过入参传递（提供合理默认值）；严禁在组件内部写 10.dp/10.sp/10.pt 等魔法值。
- 默认值应来自 `core/design` 的设计令牌（如 `Spacing`、`Radii`、`Elevation`、`IconSize`、`AnimationDurations`、`TextStyleTokens`）或 `MaterialTheme`。
- 优先使用 `MaterialTheme.colorScheme/typography`；需要扩展时通过 `CompositionLocal` 暴露自定义 tokens。
- 容器组件需转发子项常用样式参数（内边距/圆角/间距等），避免写死。
- 示例与推荐签名见根目录 `AGENTS.md` 的“Compose UI 规范”。
