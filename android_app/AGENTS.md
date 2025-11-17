# AGENTS.md · android_app/（Android 客户端）

本文件覆盖并补充根 `AGENTS.md`，仅适用于 `android_app/`。

## 一般指示

- 颜色常量应该都写入：`android_app/core/design/src/main/kotlin/ai/sxwl/android/design/theme/Color.kt`，
  不要使用如 `0xFAB...` 之类的 RGB 颜色值

## 架构状态说明

**重要：** 本文档同时包含当前实现状态和目标架构指导。请注意区分：

- 🟢 **当前实现**：已在代码库中实施的架构模式和技术栈
- 🟡 **目标架构**：规划中的架构改进目标
- 🔴 **已知问题**：详见 `ARCH_CRITIQUES.md` 中的架构问题分析

### 当前架构概况

- **UI 层**：Compose + BaseVM + StateFlow/SharedFlow
- **数据层**：Repository/UseCase 模式 + DataModule 手动依赖注入
- **网络层**：双网络栈并存（Retrofit + Inty SDK）
- **导航**：多 Activity + 自定义导航
- **存储**：MMKV（聊天持久化当前禁用）

## 适用范围与平台约束

- 仅支持竖屏（portrait）；无需考虑 landscape 兼容。
- Compose/Recycler 需避免无意义重组；图片与音频加载注意内存与缓存策略。
- 现有并行网络栈：Retrofit/Moshi 与 Inty SDK；避免新增第三套；复用统一鉴权/环境/日志配置，避免重复创建 `OkHttpClient`。

## AI 使用规范（2025.10）

- 在 UI 中明确标识 AI 生成内容，符合 GB45438-2025。
- 禁止使用未经审核的模型；遵循欧盟 AI 法案与 OpenAI 指南，落实可解释性与内容审核。
- 处理用户数据时遵循 GDPR/CCPA，执行数据最小化、加密存储/传输，并提供删除、修改能力。

## 技术栈（2025.11）

- 🟢 **当前实现**：Kotlin 2.2.21 + Jetpack Compose 2025.11.00，架构为 Repository/UseCase + BaseVM + StateFlow/SharedFlow
- 🟢 **当前实现**：协程 1.10.2 + Flow、Retrofit 3.0.0 + OkHttp 5.3.0、Coil 3.3.0、MMKV 2.2.4、Firebase 34.5.0、Media3 1.8.0
- 🟢 **当前实现**：使用原生 Intent 导航系统，DataModule 手动依赖注入
- 🟡 **目标架构**：迁移到 Koin 依赖注入，统一网络栈
- 依赖版本集中在 `gradle/libs.versions.toml`，模块间尽量使用版本对齐。

## 包结构与文件命名

- 🟢 **当前实现** 包结构：

```text
  com.ai.intellimate/
  ├── agent/           # Agent 相关功能
  ├── audio/           # 音频管理
  ├── chat/            # 聊天功能
  ├── explore/         # 发现页面
  ├── login/           # 登录注册
  ├── messages/        # 消息列表
  ├── profile/         # 个人资料
  ├── settings/        # 设置
  ├── ui/
  │   ├── components/  # 可复用组件
  │   └── screens/     # 页面组件（较少使用）
  ├── utils/           # 工具类
  ├── vip/             # 会员相关
  └── notifications/   # 推送通知
```

- Activity 结尾 `Activity`，ViewModel 结尾 `ViewModel`，Screen 结尾 `Screen`。通用组件使用 PascalCase，例如 `ChatTopBar.kt`。
- 避免新建平行目录层级；遵循模块化边界与 `core/design` token 目录约定。

## 构建与配置

- `local`/`debug`/`playdebug`/`release` 构建类型保持继承链一致，调试依赖不得泄露到发布变体。
- `gradle.properties` 管理全局开关，`build-logic` 承载共用 Gradle 插件/脚本；版本由 `libs.versions.toml` 控制。
- 发布构建使用 `release` 变体，测试用 `playdebug`，本地调试 `local`。

## Kotlin / Compose UI 规范

- 禁止使用魔法值（如 `10.dp`）——将 UI 常量定义在 `core/design` token 或 `MaterialTheme` 中，通过入参传递并提供合理默认值。
- 容器组件应转发 padding/shape/间距；默认配色/字重基于 `MaterialTheme.colorScheme/typography` 或自定义 `CompositionLocal`。
- Activity/组件需要提供清晰的 `launch`/`onNavigate` 入参，避免在组件内部持有上下文。

### 🟢 当前实现模板

```kotlin
  /** Activity 描述 */
  class ChatActivity : BaseActivity() {
      companion object {
          fun launch(context: Context, param: String) =
              context.startActivity(Intent(context, ChatActivity::class.java).putExtra("param", param))
      }
      private val viewModel: ChatViewModel by viewModels()
      
      override fun getPageName(): String = "ChatPage"
  }

  /** ViewModel 使用 BaseVM + StateFlow 模式 */
  class ChatViewModel : BaseVM() {
      private val _messages = MutableStateFlow<List<Message>>(emptyList())
      val messages = _messages.asStateFlow()
      
      private val _isLoading = MutableStateFlow(false)
      val isLoading = _isLoading.asStateFlow()
      
      // 使用 Repository/UseCase 模式
      private val chatRepository: ChatRepository = DataModule.getChatRepository()
      private val sendMessageUseCase = DataModule.sendMessageUseCase
      
      fun sendMessage(content: String) {
          launchBackground {
              try {
                  val result = sendMessageUseCase(agentId, content)
                  // 处理结果
              } catch (e: Exception) {
                  LogUtils.e("Send message failed: ${e.message}")
              }
          }
      }
  }
```

### 🟢 Compose 组件示例

```kotlin
  @Composable
  fun ChatScreen(
      modifier: Modifier = Modifier,
      viewModel: ChatViewModel = viewModel(),
      onNavigateToLogin: () -> Unit = {}
  ) {
      val messages by viewModel.messages.collectAsState()
      val isLoading by viewModel.isLoading.collectAsState()

      // UI 实现
      LazyColumn {
          items(messages) { message ->
              MessageItem(message = message)
          }
      }
  }
```

### 🟡 目标架构（MVI 模式）

考虑未来迁移到 MVI 模式以提高状态管理的一致性和可测试性。

## 网络与依赖注入规范

### 🟢 当前实现：DataModule 手动依赖注入
- Repository/UseCase 通过 DataModule 获取：
  ```kotlin
  class ChatViewModel : BaseVM() {
      // 直接从 DataModule 获取依赖
      private val chatRepository: ChatRepository = DataModule.getChatRepository()
      private val sendMessageUseCase = DataModule.sendMessageUseCase
      private val loadChatHistoryUseCase = DataModule.loadChatHistoryUseCase
  }
  
  // DataModule 提供全局单例
  object DataModule {
      private val _chatRepository: ChatRepository by lazy {
          ChatRepositoryImpl(_chatLocalDataSource, _chatRemoteDataSource)
      }
      
      val sendMessageUseCase: SendMessageUseCase by lazy { 
          SendMessageUseCase(_chatRepository) 
      }
      
      fun getChatRepository(): ChatRepository = _chatRepository
  }
  ```

### 🟢 当前网络层：双栈并存
- Retrofit 栈（经典用法）：
  ```kotlin
  interface IChatApi {
      @POST("chat/send")
      suspend fun sendMessage(@Body request: SendMessageRequest): HttpResult<SendMessageResponse>
  }
  
  // 通过 NetServiceMgr 获取
  private val chatApi by lazy { NetServiceMgr.getChatApi() }
  ```
- Inty SDK 栈（生成的 SDK）：
  ```kotlin
  // 通过 IntyNetworkManager 获取
  private val authService by lazy { IntyNetworkManager.getAuthService() }
  ```

### 🟡 目标架构：迁移到 Koin
计划迁移到 Koin 依赖注入以提高可测试性和依赖管理的一致性。

## 🔴 双网络栈架构（需要重构）

### 当前状况
项目中并存两套网络栈，导致维护复杂性和不一致性：

#### 1. Retrofit 栈（传统方式）
```kotlin
// 通过 NetServiceMgr 获取 API 接口
private val chatApi: IChatApi by lazy { NetServiceMgr.getChatApi() }
private val agentApi: IAgentApi by lazy { NetServiceMgr.getAgentApi() }

// 返回 HttpResult 包装
suspend fun sendMessage(request: SendMessageRequest): HttpResult<SendMessageResponse>
```

#### 2. Inty SDK 栈（生成的 SDK）
```kotlin
// 通过 IntyNetworkManager 获取服务
private val authService by lazy { IntyNetworkManager.getAuthService() }
private val userService by lazy { IntyNetworkManager.getUserService() }

// 返回 ApiResult 包装
suspend fun login(request: LoginRequest): ApiResult<LoginResponse>
```

### 使用指导原则
由于当前双栈并存，遵循以下原则选择合适的网络栈：

1. **已有功能改善修改**：仍使用已有的网络栈，不进行修改
3. **新功能开发**：使用 Inty SDK 栈

### 🔴 已知问题
- 错误处理机制不统一（`HttpResult` vs `ApiResult`）
- 环境配置和鉴权流程分叉
- OkHttpClient 重复创建，配置不一致
- 日志和监控分散，可观测性差

### 🟡 重构计划
- 统一到单一网络栈
- 标准化错误处理和日志
- 统一鉴权和环境管理
- 整合监控和性能指标

## 协程与状态管理
- 🟢 **当前实现**：UI 使用 `launchUI`，后台任务 `launchBackground`，网络请求在 `Dispatchers.IO`；统一 `SupervisorJob + CoroutineExceptionHandler`，通过 BaseVM 管理
- 🟢 **当前实现**：状态通过 `StateFlow`，一次性事件可使用 `SharedFlow`；状态更新使用 `_state.value = newState` 或 `_state.update { ... }`
- 🔴 **已知问题**：BaseVM 中存在脱离生命周期的 `backgroundScope`，可能导致内存泄漏

## 错误处理与日志
- 🟢 **当前实现**：网络错误使用 `HttpResult`，业务错误使用 `BusinessErrorCodes`；用户提示使用 `ToastUtils.showToast` 或 `NetworkErrorHandler.showNetworkAwareError`
- 🟢 **当前实现**：日志使用 `LogUtils`，Firebase Crashlytics 记录异常；敏感信息不可明文输出
  ```kotlin
  try {
      val result = sendMessageUseCase(agentId, content)
      when (result) {
          is HttpResult.Success -> {
              // 处理成功
          }
          is HttpResult.Failure -> {
              NetworkErrorHandler.showNetworkAwareError(result.message)
              LogUtils.e("API failed: ${result.message}")
          }
      }
  } catch (e: Exception) {
      LogUtils.e("Unexpected error: ${e.message}")
      FirebaseManager.recordException(e)
  }
  ```

## 测试策略
- 🟢 **当前实现**：单元测试：JUnit + MockK；UI 测试：Espresso + Compose 测试工具
- 🟡 **目标架构**：引入 Koin 测试容器用于依赖注入测试
- 测试文件以 `Test` 结尾；集成自动化流水线，关键路径需有性能测试
  ```kotlin
  class ChatViewModelTest {
      private val mockRepository = mockk<ChatRepository>()
      private val mockUseCase = mockk<SendMessageUseCase>()
      
      @Test
      fun `send message success`() = runTest {
          // 当前需要手动模拟 DataModule，未来迁移到 Koin 后可简化
          every { DataModule.getChatRepository() } returns mockRepository
          
          val viewModel = ChatViewModel()
          // 测试逻辑
      }
  }
  ```

## 性能优化
- Compose 使用 `remember`/`derivedStateOf`、`key` 和 `LazyColumn`/`LazyVerticalGrid`；避免在 Compose 中直接发起耗时操作。
- 图片加载使用 Coil `AsyncImage` 并配合懒加载/预加载策略；`Modifier.drawWithContent` 优化绘制。
- 关注应用大小、启动时间、电池与碳足迹；监控内存/GC 压力。

## 构建与发布
- 构建依赖统一由 `build-logic` 模块提供；混淆规则维护在 `proguard-rules.pro`。
- 发布流程：`release` 构建 → 签名 → 使用 `google-services.json` 配置 Firebase；上线前确保事件埋点同步更新。

## 最佳实践
- 组件保持单一职责、参数化、浅层级；使用 `Modifier` 链和 `@Stable/@Immutable` 优化。
- 状态不可变、通过 `copy` 更新并及时释放资源；持续监控 AI 模型表现，确保可解释性与用户同意。
- UI 组件不要使用裸写的常量值，而应该使用集中定义的常量，如：
  ```kotlin
  private object Config {
    val ChipSpacing = 16.dp
    ...
  }
  Arrangement.spacedBy(Config.ChipSpacing),
  ```

## Firebase 事件（events）
- 与用户行为相关的事件以行为命名：
  ```kotlin
  const val MESSAGE_TO_IMAGE_GENERATION_BUTTON_CLICKED = "message_to_image_generation_button_clicked"
  ```
- 系统语义事件仍按语义命名：
  ```kotlin
  const val MESSAGE_TO_IMAGE_GENERATION_SUCCESS = "message_to_image_generation_success"
  const val MESSAGE_TO_IMAGE_GENERATION_FAILURE = "message_to_image_generation_failure"
  const val IMAGE_GENERATION_LIMIT_REACHED = "image_generation_limit_reached"
  ```
- 事件名调整后需同步更新 `../bizops/FIREBASE_BUSINESS_EVENTS.md`。
