# IntelliMate Android app

- Do not try to test using Android emulator (the environment does not have KVM)
- Update [change logs](/android_app/docs/CHANGE_LOGS.md) and [user manual](/docs/INTELLIMATE.md) when add or modify user-facing features and/or beahaviors
- 新功能要添加 firebase 埋点来收集用户使用数据。
- 使用 [DataStore](https://developer.android.com/reference/kotlin/androidx/datastore/core/DataStore)，
  [MMKV](https://github.com/Tencent/MMKV) 已计划废弃
- 试用 [Room Database](https://developer.android.com/training/data-storage/room?hl=zh-cn) 在本地完成持久化数据存储
- 从后端拿到的数据结构中忽略不理解的数据类型，而不是报错，比如聊天消息类型出现了 AI User 以外的类型，直接忽略，这样在后端发布新功能时更加具有容错性。
- 为用户可见的 UI 元素取中英文对照名字，方便开发人员指代功能

## Design

- 主题主要分文颜色、字体、形状三大类，定义在 `android_app/core/design/src/main/kotlin/ai/sxwl/android/design/theme/Theme.kt`
- 颜色：使用MaterialTheme.colorScheme获取颜色，如MaterialTheme.colorScheme.primary获取主题色
- 字体：使用MaterialTheme.typography获取字体style，如Text(style = MaterialTheme.typography.titleMedium)
- 形状：使用MaterialTheme.shapes获取组件形状，如Surface(shape = MaterialTheme.shapes.medium)

## 一般指示

- When referring to concepts in Kotlin code, use the language conventions, and remind the user about that, so the user can understand what it refers to
- 颜色从MaterialTheme.colorScheme中根据具体作用取值，不应该直接使用具体颜色数值
- 界面元素尺寸、大小写入 `android_app/app/src/main/res/values/dimens.xml`，不要直接使用数字值、如 `10.sp` `10.dp` 之类的
- 用户可见的字符写入 `android_app/app/src/main/res/values/strings.xml`
  并以资源 ID 的形式在代码中使用
- 无需使用 linter 检查修改代码
- 对我提出的指示、完成基础要求，不要处理未提及的复杂场景，不要使用 defensive programming
- 优先使用 material 3 icons 和其他来自 material 3 的素材 https://fonts.google.com/icons?icon.query=generate&icon.size=24&icon.color=%231f1f1f&icon.platform=android
- 新增 UI Composeable 组件要有详细的注释说明其使用范围场景和预期视觉效果，及可配置项；关键配置项要编写为输入参数

## 适用范围与平台约束

- 仅支持竖屏（portrait）；无需考虑 landscape 兼容。
- Compose/Recycler 需避免无意义重组；图片与音频加载注意内存与缓存策略。
- 现有并行网络栈：Retrofit/Moshi 与 Inty SDK；避免新增第三套；复用统一鉴权/环境/日志配置，避免重复创建 `OkHttpClient`。

## Stainless 迁移冻结规则（FR_REMOVE_STAINLESS_SDK_MIGRATION_PLAN / Phase 0）

- 迁移期间禁止新增 `IntyNetworkManager`、`core/data/http/services/*`、`com.inty.api.*` 的运行时代码引用（`app` 与 `core` 模块均适用）。
- 新增或修改网络调用时，必须优先接入 `NetServiceMgr` + `I*Api` + `core/data/api/model` 本地 DTO。
- Code review 发现上述新增引用时，按阻断项处理，除非在同一变更中明确完成对应 Phase 的“迁移后删除”闭环。

## Explore 页面交互

- Explore 顶部栏支持双击手势，用于回到推荐列表第一页：需要同时滚动 `LazyVerticalGrid` 到索引 0 并触发 Paging 刷新，以确保展示第一屏数据。

## AI 使用规范（2025.10）

- 在 UI 中明确标识 AI 生成内容，符合 GB45438-2025。
- 禁止使用未经审核的模型；遵循欧盟 AI 法案与 OpenAI 指南，落实可解释性与内容审核。
- 处理用户数据时遵循 GDPR/CCPA，执行数据最小化、加密存储/传输，并提供删除、修改能力。
- 角色主页（`AgentInfoScreen`）已接入聊天记录中的 `generatedImage` 数据，必须展示 “AI-Generated Images” 画廊，并使用明确的 AI 标签提示用户内容来源；画廊数据通过 `ChatRepository.getMessagesFlow(agentId)` 提供的历史消息实时更新。

## Character Room 组件

- 本地角色元数据与能量值统一持久化在 `core/data/src/main/kotlin/ai/sxwl/android/data/character`。
- `CharacterDatabase` 为单库入口，`CharacterRepository` 负责暴露 `Flow` 订阅与同步方法，app 层通过 `DataModule.getCharacterRepository()` 获取实例。
- 聊天页通过 Room 统计 AI 回复次数并实时刷新顶部能量，禁止绕过仓库直接访问数据库。

## Kotlin / Compose UI 规范

- 禁止使用魔法值（如 `10.dp`）——将 UI 常量定义在 `core/design` token 或 `MaterialTheme` 中，通过入参传递并提供合理默认值。
- 容器组件应转发 padding/shape/间距；默认配色/字重基于 `MaterialTheme.colorScheme/typography` 或自定义 `CompositionLocal`。
- Activity/组件需要提供清晰的 `launch`/`onNavigate` 入参，避免在组件内部持有上下文。

## Android Studio

- 图片转换为 webp 格式：https://developer.android.com/studio/write/convert-webp?hl=zh-cn
