# AGENTS.md · android_app/（Android 客户端）

本文件覆盖并补充根 `AGENTS.md`，仅适用于 `android_app/`。

## 适用范围与平台约束
- 仅支持竖屏（portrait）；无需考虑 landscape 兼容。
- Compose/Recycler 需避免无意义重组；图片与音频加载注意内存与缓存策略。
- 现有并行网络栈：Retrofit/Moshi 与 Inty SDK；避免新增第三套；复用统一鉴权/环境/日志配置，避免重复创建 `OkHttpClient`。

## AI 使用规范（2025.10）
- 在 UI 中明确标识 AI 生成内容，符合 GB45438-2025。
- 禁止使用未经审核的模型；遵循欧盟 AI 法案与 OpenAI 指南，落实可解释性与内容审核。
- 处理用户数据时遵循 GDPR/CCPA，执行数据最小化、加密存储/传输，并提供删除、修改能力。

## 技术栈（2025.10）
- Kotlin 2.2.20 + Jetpack Compose 2025.10，架构统一为 MVVM/MVI（`State + Intent + Event`），ViewModel 继承 `BaseViewModel<IState, IIntent, IEvent>`。
- 协程 1.10.2 + Flow、Retrofit 3.0.0 + OkHttp 5.2.1、Coil 3.3.0、MMKV 2.2.4、Firebase 34.1.0、Media3 1.8.0、CameraX 1.5.1。
- 使用原生 Intent 导航系统，依赖注入统一采用 Koin。
- 依赖版本集中在 `gradle/libs.versions.toml`，模块间尽量使用版本对齐。

## 包结构与文件命名
- 包结构保持：
  ```
  com.ai.inty/
  ├── activities/      # Activity
  ├── viewmodels/      # ViewModel
  ├── ui/
  │   ├── screens/     # 页面级 Compose
  │   ├── components/  # 可复用组件
  │   └── theme/       # 主题
  ├── beans/           # 数据模型
  ├── net/             # 网络
  ├── utils/           # 工具
  └── billing/         # 计费
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
- 推荐类/组件模板：
  ```kotlin
  /** 描述 */
  class ChatActivity : BaseActivity() {
      companion object {
          fun launch(context: Context, param: String) =
              context.startActivity(Intent(context, ChatActivity::class.java).putExtra("param", param))
      }
      private val viewModel: ChatViewModel by viewModels()
  }

  class ChatViewModel : BaseViewModel<ChatState, ChatIntent, ChatEvent>() {
      override fun createInitialState(): ChatState = ChatState()
      override suspend fun processIntent(intent: ChatIntent) = when (intent) {
          is ChatIntent.SendMessage -> handleSendMessage(intent)
          ChatIntent.LoadMessages -> handleLoadMessages()
      }
  }
  ```
- Compose 示例：
  ```kotlin
  @Composable
  fun ChatScreen(
      modifier: Modifier = Modifier,
      viewModel: ChatViewModel = viewModel(),
      onNavigateToLogin: () -> Unit = {}
  ) {
      val state by viewModel.state.collectAsState()
      val event by viewModel.events.collectAsState()

      LaunchedEffect(event) {
          when (event) {
              ChatEvent.NavigateToLogin -> onNavigateToLogin()
              is ChatEvent.ShowError -> ToastUtils.showToast(event.message)
              null -> Unit
          }
          viewModel.clearEvent()
      }

      // UI 实现
  }
  ```

## 网络与依赖注入规范
- API 需通过 Retrofit 接口定义并返回统一包装，例如：
  ```kotlin
  interface IChatApi {
      @POST("chat/send")
      suspend fun sendMessage(@Body request: SendMessageRequest): HttpResult<SendMessageResponse>
  }
  ```
- Koin 统一集中管理：
  ```kotlin
  val networkModule = module {
      single<IChatApi> { get<Retrofit>().create(IChatApi::class.java) }
      single<Retrofit> { provideRetrofit() }
  }
  val viewModelModule = module {
      viewModel { ChatViewModel(get()) }
  }
  ```
- 在 `Application` 中 `startKoin { modules(appModule) }`，使用 `by inject<T>()`/`by viewModels()` 获取依赖；测试场景使用 `declareMock<T>()`。

## 协程与状态管理
- UI 使用 `launchUI`，后台任务 `launchBackground`，网络请求在 `Dispatchers.IO`；统一 `SupervisorJob + CoroutineExceptionHandler`，避免全局作用域。
- 状态通过 `StateFlow`，事件使用 `SharedFlow`；状态更新调用 `updateState { copy(...) }`，一次性事件使用 `sendEvent(event)` 并及时 `clearEvent`。

## 错误处理与日志
- 网络错误统一使用 `HttpResult`，业务错误使用 `BusinessErrorCodes`；用户提示统一 `ToastUtils.showToast`。
- 所有协程需显式处理异常；日志遵循 Android Log 或约定第三方库配置，敏感信息不可明文输出。

## 测试策略
- 单元测试：JUnit + MockK；UI 测试：Espresso；集成测试：Koin 测试容器；Compose 测试工具覆盖交互。
- 测试文件以 `Test` 结尾；集成自动化流水线，关键路径需有性能测试。

## 性能优化
- Compose 使用 `remember`/`derivedStateOf`、`key` 和 `LazyColumn`/`LazyVerticalGrid`；避免在 Compose 中直接发起耗时操作。
- 图片加载使用 Coil `AsyncImage` 并配合懒加载/预加载策略；`Modifier.drawWithContent` 优化绘制。
- 关注应用大小、启动时间、电池与碳足迹；监控内存/GC 压力。

## 安全与合规
- 敏感信息使用 MMKV 加密，密钥放于 Android Keystore；网络强制 HTTPS + 证书锁定，支付走 Google Play Billing。
- Firebase Auth + Credential Manager 负责认证；实施代码混淆、反调试、RASP、生物识别等防护。
- 严格遵循 OWASP Mobile Top 10；所有 AI 能力需通过内容审核并提供用户透明度。

## 构建与发布
- 构建依赖统一由 `build-logic` 模块提供；混淆规则维护在 `proguard-rules.pro`。
- 发布流程：`release` 构建 → 签名 → 使用 `google-services.json` 配置 Firebase；上线前确保事件埋点同步更新。

## 禁止事项
- 禁用 TheRouter、EasyLog、全局可变单例（除非确有必要）、未审核 AI 模型、过时 Android API。
- 禁止在 UI 线程执行耗时操作、Compose 中直接发网络请求、无异常处理的协程、在 Activity 内写业务逻辑或硬编码字符串/数字。
- 忽视无障碍要求、AI 标识或数据隐私法规视为严重违规。

## 最佳实践
- 组件保持单一职责、参数化、浅层级；使用 `Modifier` 链和 `@Stable/@Immutable` 优化。
- 状态不可变、通过 `copy` 更新并及时释放资源；持续监控 AI 模型表现，确保可解释性与用户同意。
- 采用绿色软件原则与可持续云资源，跟踪碳足迹。

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
