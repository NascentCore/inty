# Kotlin 代码异味报告

以下为在本仓库 Android 工程中检出的具有典型的 Kotlin 代码气味和改进建议。

## 1.非空强断言`!!`
- 代表位置：
  - `core/firebase/FCMService.kt:24-25`、`app/*` 多处（如 `AgentInfoActivity.kt`, `ChatActivity.kt`）
  - `library/utils/*`、`core/data/*` 有多处 `!!`
- 风险：运行期 `NullPointerException`，线上崩溃率高。
- 建议：使用安全调用 `?.`、`?:` 默认值、`requireNotNull` 带上下文信息，或在类型建模上保证非空。

## 2. 阻塞调用 `Thread.sleep`
- 代表位置：
  - `core/data/api/NetServiceMgr.kt:241,244`
- 风险：阻塞主线程/协程调度，造成卡顿或 ANR。
- 建议：使用 `delay`（协程）或重试/回退策略；UI 层避免长阻塞。

## 3. 广泛的 `catch (Exception)`
- 代表位置：`app/`, `core/*`, `library/*` 多文件（示例：`ChatViewModel.kt`, `MainViewModel.kt`, `AppUtils.kt`, `FirebaseManager.kt` 等）
- 风险：掩盖具体错误、难以定位；误拦系统异常。
- 建议：
  - 捕获具体异常；
  - 将失败映射为统一的 `Result`/`sealed class`；
  - 至少记录关键信息与 trace，必要时上报。

## 4. 标准输出打印/低层日志
- 代表位置：
  - `library/utils/LogUtils.kt:439` 使用 `Log.println`
- 风险：日志级别与采样不可控；
- 建议：统一封装日志 API，按环境与模块配置级别与采样；敏感信息脱敏。

## 5. `lateinit var` 潜在空引用
- 代表位置：
  - `AudioPreloadManager.kt`、`BillingRepository.kt` 等
- 风险：未初始化即访问触发 `UninitializedPropertyAccessException`。
- 建议：
  - 若允许缺省，改为可空类型并在使用处处理；
  - 或使用 `lazy`/构造注入保证时序。

## 6. 资源/上下文强制非空与路径 `!!`
- 代表位置：
  - `CreateRoleActivity.kt`、`MySettingViewModel.kt` 等对 `Uri.path!!`、`agentId!!`- 风险：设备碎片化场景容易崩溃。
- 建议：判空与失败分支回退，或统一包装为安全解析函数。

## 7.过度 try-catch 包裹
- 现象：工具类与 ViewModel 广泛覆盖`try { ... } catch (Exception)`
- 风险：失去失败信号通道，复杂度上升。
- 建议：在数据/网络层用 `Either/Result`，UI层消费状态驱动UI，减少异常控制流。

## 8.TODO/FIXME留存
- 代表位置：`ModifyProfileActivity.kt`、`ReportUI.kt`、`IntySetting.kt`、`ChatSessionManager.kt`、`ReportService.kt`等
- 建议：同Python部分，立项/关闭。

---

### 工程治理建议
- 启用`ktlint`/`detekt` 并在 CI 中开启严格模式（禁 `!!`、限制 `catch (Exception)`、阻止API检测）；
- 统一网络层（Retrofit/Moshi 与 Inty SDK 复用问题），收敛客户端与鉴权策略；
- 建立协程调度规范（IO/Main/Default），禁止主线程阻塞；
- 导入统一错误模型与UI状态（Loading/Success/Error）。