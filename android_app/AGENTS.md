# 代理。md · android_app/（Android 客户端）

本文件覆盖并补充根`AGENTS.md`，仅适用于 `android_app/`。

## 平台与约束
- 仅支持竖屏（portrait）；无需考虑横向兼容。

## 架构与网络
- 现有现存网络栈日志：Retrofit/Moshi 与 Inty SDK；避免新增第三套；复用统一鉴权/环境/配置，避免重复创建`OkHttpClient`。
- 依赖版本集中于 `gradle/libs.versions.toml`；模块间尽量使用版本对齐。

## 构建
- `local`/`debug`/`release`构建配置需要保持继承关系一致；依赖调试无法到达发布变体。

## UI/性能
- Compose/Recyler 需避免无意义重组；图片与音频加载注意内存与缓存策略。