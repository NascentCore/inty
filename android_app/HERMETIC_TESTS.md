# HERMETIC_TESTS

本文件梳理了 `android_app` Kotlin 代码库中可在完全隔离（Hermetic）环境下测试的关键功能点。这些逻辑不依赖远程 URL、网络堆栈或真实系统服务，只需要 JVM/Compose/Robolectric 等本地测试工具即可验证。

## 通用策略

- 充分利用 Robolectric 或 AndroidX Test 提供的 `ApplicationProvider`，为需要 `Context`/`Resources` 的工具类（例如 `BillingErrorHandler`）提供环境。
- 对依赖 `IntySetting` 这类单例存储的模块，可在测试前注入/替换为内存版实现，或使用临时的 `SharedPreferences` 文件，并在 `@After` 中清理。
- 含协程的类（例如 `OpeningPlayState`）建议搭配 `runTest` + `StandardTestDispatcher`，必要时使用 `advanceUntilIdle()` 观察状态。
- Compose 相关逻辑可通过 `createComposeRule()` 或 `runBlockingTest` 结合 `LazyPagingItemsStub` 进行验证，无需真正绘制到屏幕。

## 可进行 Hermetic 测试的功能点

### 1. 聊天文本格式化
- **位置**：`app/src/main/kotlin/com/ai/intellimate/utils/ChatTextFormatter.kt`
- **原因**：纯字符串 → `AnnotatedString` 转换逻辑，不依赖 Android 框架或网络。
- **建议用例**：
  - 普通文本不含括号时保持原样。
  - 嵌套括号（含中英文括号）应逐段渲染为斜体，顺序正确。
  - 括号不匹配、含 emoji/多字节字符时不应崩溃，emoji 不被拆分。

### 2. 开场白播放状态管理
- **位置**：`app/src/main/kotlin/com/ai/intellimate/audio/OpeningPlayState.kt`
- **原因**：仅使用内存 `MutableMap` + `Mutex`，协程环境可由测试调度器提供。
- **建议用例**：
  - `openingPlayed`/`agentOpeningPlayed` 的写读一致性。
  - `openingPlayedAsync` 在并发场景下不会遗漏记录。
  - `clearAgentPlayed`/`clearAllPlayed` 能释放状态，后续查询返回 `false`。

### 3. 头像生成状态管理
- **位置**：`app/src/main/kotlin/com/ai/intellimate/utils/AvatarManager.kt`
- **原因**：封装于对象内的纯内存状态，无外部依赖。
- **建议用例**：
  - `setGeneratedAvatarUrl` 与 `setGeneratedAvatarUrls` 之间的互斥关系（单图/多图切换时清理旧状态）。
  - `setGenerationPrompt` 应将 `isGenerating` 置为 `true`，`setGenerationError` 会停用并记录错误。
  - `getGenerationError` 读取后自动清空，避免重复提示。
  - `clearAllAvatarData` 可重置所有字段（含 `chatBackgroundUrl`、`selectedImageIndex`）。

### 4. Agent 缓存读写与过期逻辑
- **位置**：`app/src/main/kotlin/com/ai/intellimate/utils/AgentCacheManager.kt`
- **原因**：序列化逻辑使用 Moshi + `IntySetting`（可替换为内存实现），无网络调用。
- **建议用例**：
  - `cacheAgents`/`getCachedAgents`、`cacheChatAgents`/`getCachedChatAgents` 能往返保持顺序与字段。
  - 伪造时间戳验证 `isCacheExpired`、`isUserCreatedCacheExpired` 的 30 分钟失效策略。
  - `removeAgent` 同时影响推荐与自建缓存；`clearCache` 清除所有键。
  - `getCacheStats` 返回的计数与过期标记与当前缓存一致。

### 5. 缓存提供者的更新策略
- **位置**：`app/src/main/kotlin/com/ai/intellimate/utils/AgentCacheProviderImpl.kt`、`RecommendedAgentCacheProviderImpl.kt`
- **原因**：基于缓存内容与登录态的布尔逻辑，可通过替换 `AgentCacheManager`/`IntySetting` 为假实现来驱动。
- **建议用例**：
  - 缓存为空或已过期时 `shouldUpdateFromNetwork()` 返回 `true`；缓存有效且已登录时返回 `false`。
  - `refreshChatAgents()` / `refreshRecommendedAgents()` 会调用 `UnifiedStartupManager` 对应方法（可使用 `mockkObject` 验证）。

### 6. 会话列表排序与隐藏规则
- **位置**：`app/src/main/kotlin/com/ai/intellimate/messages/MessagesViewModel.kt`
- **原因**：`processConversationsWithPinHide`、`checkAndUnhideConversations`、`setConversationReaded` 等方法仅处理集合和本地状态。
- **建议用例**：
  - 构造多条 `ConversationItem`，验证排序顺序：固定置顶 → 时间倒序 → 隐藏的仅在 `shouldShow()` 返回 `true` 时出现。
  - 模拟 `IntySetting` 标记隐藏/置顶，调用 `checkAndUnhideConversations` 后应自动取消隐藏并触发刷新。
  - `setConversationReaded` 会立刻把对应会话 `isNew` 置 `false`，其余条目不受影响。

### 7. 聊天消息/会话数据模型辅助方法
- **位置**：`core/data/src/main/kotlin/ai/sxwl/android/data/api/model/ChatBeans.kt`
- **原因**：`MsgInfo`/`ConversationItem` 的扩展方法为纯 Kotlin 逻辑。
- **建议用例**：
  - `MsgInfo.isOpening()`、`hasGeneratedImage()`、`getGeneratedImageWidth()/Height()` 在不同 `meta_data` 输入下返回正确布尔/数值。
  - `ConversationItem.shouldShow()`：结合伪造的 `IntySetting`（是否隐藏/是否有新消息）验证自动展示逻辑；`convertToAgentInfo()` 复制字段与删除标记。

### 8. Agent 展示资源选择
- **位置**：`core/data/src/main/kotlin/ai/sxwl/android/data/api/model/AgentBean.kt`
- **原因**：`imageAspectRatio` 及多种 `get*Avatar/Background`/`getAlbumImage`/`getOriginShowImage` 只做字符串拼接与 fallback。
- **建议用例**：
  - 当背景为空、头像存在时 `getAlbumImage()` 应回退到 `getLargeAvatar()`。
  - 当头像和背景均为空时返回 `null`，不会抛异常。
  - `getOriginShowImage()` 优先背景，再兜底头像。

### 9. 用户称谓推断
- **位置**：`core/data/src/main/kotlin/ai/sxwl/android/data/api/model/UserBean.kt`
- **原因**：`UserProfile.pronouns()` 只基于枚举值返回字符串。
- **建议用例**：
  - 输入 `MALE`/`FEMALE`/其他值分别返回 `He/Him`、`She/Her`、`They/Them`。
  - `gender == null` 或未知字符串时默认 `They/Them`。

### 10. HTTP/网络错误文案映射
- **位置**：`app/src/main/kotlin/com/ai/intellimate/utils/HttpErrorHandler.kt`
- **原因**：简单的 code → message 映射，完全脱离 Android。
- **建议用例**：
  - 覆盖 400/401/403/404/429/500/502 等，确认与 `operation` 相关的定制文案。
  - `handleGeneralException` 针对 timeout/network/json 关键字返回特定提示；其余走操作名称前缀。

### 11. 网络错误提示的取消感知
- **位置**：`app/src/main/kotlin/com/ai/intellimate/utils/NetworkErrorHandler.kt`
- **原因**：基于字符串判定，唯一依赖的 `ToastUtils` 可在 Robolectric 下替换为验证调用的 fake。
- **建议用例**：
  - 包含 “cancelled/cancel” 的错误信息不触发 Toast；其他错误会调用 Toast。
  - `handleNetworkException` 遇到 `CancellationException` 返回 `"Request cancelled"` 并不触发提示。

### 12. 会员计费错误提示
- **位置**：`app/src/main/kotlin/com/ai/intellimate/utils/BillingErrorHandler.kt`
- **原因**：映射 `BillingErrorCode` → 字符串资源，全部逻辑本地可控。
- **建议用例**：
  - 针对 `ShowError`/`PurchaseFailed`/`SkuDetailsQueryFailed` 事件分别验证：用户主动操作会调用 Toast、后台自动操作只记录日志。
  - `GooglePlayServiceError` 事件在缺少 `Activity` 时回退到 `ShowError` 逻辑；提供 `Activity` 时根据错误码弹框或 Toast。
  - 错误信息含 `%s` 时传入的 `detailMessage` 能正确格式化；格式化失败时退化为 “message: detail”。

### 13. 加载状态可视化逻辑
- **位置**：`app/src/main/kotlin/com/ai/intellimate/explore/ExploreLoadingStates.kt`
- **原因**：Compose 纯 UI 逻辑，可在 `ComposeTestRule` 下通过伪造的 `LazyPagingItems` 状态验证，完全不触网。
- **建议用例**：
  - `append` 处于 `LoadState.Loading` 且 `showLoadMoreLoading = true` 时才渲染进度条；当 `isRefreshing = true` 时不渲染。
  - `append` 为 `NotLoading` 且 `endOfPaginationReached = true`、列表非空、`refresh` 已完成时才显示 “No more data”。
  - `append` 为 `Error` 时渲染错误提示。

---

以上条目可作为编写 Hermetic 测试的落点。新增业务逻辑时，若同样满足“仅依赖本地状态/资源”，也应在此文档补充，方便持续扩展可自动化验证的范围。***
