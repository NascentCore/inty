# IntelliMate Android app

本文件覆盖并补充根 `AGENTS.md`，仅适用于 `android_app/`。

## 一般指示

- 颜色常亮写入 `android_app/core/design/src/main/kotlin/ai/sxwl/android/design/theme/Color.kt`，不要直接使用 Hex 值、如 `0xFAB...` 之类的 RGB 颜色值
- 界面元素尺寸、大小写入 `android_app/app/src/main/kotlin/com/ai/intellimate/ui/ui_configs.kt`，不要直接使用数字值、如 `10.sp` `10.dp` 之类的
- URL 定义为常量写入 `app/src/main/kotlin/com/ai/intellimate/ui/ui_configs.kt`
- 用户可见的字符写入 `android_app/app/src/main/res/values/strings.xml`
  并以资源 ID 的形式在代码中使用
- 无需使用 linter 检查修改代码
- 对我提出的指示、完成基础要求，不要处理未提及的复杂场景，不要使用 defensive programming
- 优先使用 material 3 icons 和其他来自 material 3 的素材 https://fonts.google.com/icons?icon.query=generate&icon.size=24&icon.color=%231f1f1f&icon.platform=android
- 代码注释使用简体中文
- 默认日志登记是 debug
- 新增 UI Composeable 组件要有详细的注释说明其使用范围场景和预期视觉效果，及可配置项；关键配置项要编写为输入参数

## 适用范围与平台约束

- 仅支持竖屏（portrait）；无需考虑 landscape 兼容。
- Compose/Recycler 需避免无意义重组；图片与音频加载注意内存与缓存策略。
- 现有并行网络栈：Retrofit/Moshi 与 Inty SDK；避免新增第三套；复用统一鉴权/环境/日志配置，避免重复创建 `OkHttpClient`。

## Explore 页面交互

- Explore 顶部栏支持双击手势，用于回到推荐列表第一页：需要同时滚动 `LazyVerticalGrid` 到索引 0 并触发 Paging 刷新，以确保展示第一屏数据。

## AI 使用规范（2025.10）

- 在 UI 中明确标识 AI 生成内容，符合 GB45438-2025。
- 禁止使用未经审核的模型；遵循欧盟 AI 法案与 OpenAI 指南，落实可解释性与内容审核。
- 处理用户数据时遵循 GDPR/CCPA，执行数据最小化、加密存储/传输，并提供删除、修改能力。
- 角色主页（`AgentInfoScreen`）已接入聊天记录中的 `generatedImage` 数据，必须展示 “AI-Generated Images” 画廊，并使用明确的 AI 标签提示用户内容来源；画廊数据通过 `ChatRepository.getMessagesFlow(agentId)` 提供的历史消息实时更新。

## Kotlin / Compose UI 规范

- 禁止使用魔法值（如 `10.dp`）——将 UI 常量定义在 `core/design` token 或 `MaterialTheme` 中，通过入参传递并提供合理默认值。
- 容器组件应转发 padding/shape/间距；默认配色/字重基于 `MaterialTheme.colorScheme/typography` 或自定义 `CompositionLocal`。
- Activity/组件需要提供清晰的 `launch`/`onNavigate` 入参，避免在组件内部持有上下文。
