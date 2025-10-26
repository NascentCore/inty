## 架构概览与评估

### 范围
- **目标**：概述主要功能，描述当前架构，评估架构与功能的适配度，并列出主要架构问题及其影响。不包含修复方案。

### 功能概览
- **AI 聊天**：与智能体对话、历史消息、Keep Talking、TTS 语音播放。
- **智能体**：发现、关注、创建/编辑、举报。
- **鉴权**：游客创建、Google 登录。
- **订阅**：Google Play Billing 套餐与状态监控。
- **个人与设置**：用户资料、应用更新检查、偏好设置。
- **媒体**：图片加载（Coil）、音频播放（Media3/ExoPlayer）。

### 架构摘要
- **模块**：
  - `app`：Compose UI、多个 Activity、启动编排。
  - `core/data`：网络层（两套并存）、SDK 封装、计费仓库、聊天领域（仓库/用例）、本地设置（MMKV）。
  - `core/common`、`core/design`、`core/firebase`、`library/network`、`library/utils`：通用 UI、工具、分析与网络辅助。
- **UI 层**：Compose + MVVM（`BaseVM` + StateFlow）。多 Activity 导航 + 自定义底部栏；Navigation Compose 使用有限。
- **数据层**：
  - Retrofit/Moshi 栈：`NetServiceMgr` + `I*Api` 接口。
  - 生成 SDK 栈：`IntyNetworkManager` + `*Service` 门面，返回 `ApiResult`。
  - 本地存储使用 MMKV；无 Room；聊天持久化目前禁用。
- **编排**：`IntelliMateApp` 初始化网络与启动；`UnifiedStartupManager` 负责登录/游客、预加载、缓存与网络同步；`BillingRepository` 单例管理购买与状态。
- **媒体**：自定义 `AudioPlaybackManager`（Media3），设计模块配置图片加载。

### 适配性评估
- Compose + MVVM 的模块化整体匹配“聊天优先、富媒体”的产品形态。
- 但并行的两套网络栈、非标准化 DI、重度单例编排、以及关闭的持久化，削弱了可靠性、一致性与可测性；对强调长期陪伴与稳定体验的产品构成风险。

## 主要架构问题

### 1）两套网络栈并行且同时在用
- **问题**：Retrofit/Moshi（`NetServiceMgr` + `I*Api`）与生成 SDK（`IntyNetworkManager` + `*Service`）在同一功能内混用（如 `UnifiedStartupManager` 同时用 `AuthService` 和 `NetServiceMgr.getAgentApi()`）。
- **影响**：错误处理/日志不一致、环境配置重复、鉴权流程分叉、维护与测试成本上升、可观测性碎片化。

### 2）缺乏统一的依赖注入；以全局单例与手动装配为主
- **问题**：`ChatModule` 以全局对象装配仓库与用例；存在 `@Inject` 注解但无实际 DI 运行时（Hilt/Koin）接管；ViewModel 多为惰性拉取依赖。
- **影响**：测试替身注入困难、生命周期与作用域不清、依赖关系隐藏在单例内部、范围不一致。

### 3）`BaseVM` 中存在脱离生命周期的后台任务
- **问题**：自建 `backgroundScope` 与“持久化”协程，不受 `viewModelScope` 管控。
- **影响**：任务可能在界面销毁后继续执行，易引发泄漏、竞态与无效状态更新。

### 4）`AuthInterceptor` 的 401 处理脆弱
- **问题**：遇到 401 即登出并重启 App。
- **影响**：可能出现重启循环；对令牌过期或临时网络问题缺乏温和恢复；与 SDK 鉴权路径不一致。

### 5）计费初始化依赖固定延时并与 Activity 耦合
- **问题**：`MainActivity` 以 `delay(500)` 等“经验值”时序初始化与拉取套餐；监控从 Activity 启动。
- **影响**：启动流程脆弱、不同设备易竞态、计费生命周期与单一界面耦合。

### 6）聊天持久化被禁用，缺乏离线连续性
- **问题**：聊天消息本地持久化方法为 no-op，仅存分页标记。
- **影响**：冷启动缺上下文；离线与弱网体验差；网络负载增加。

### 7）导航混合：多 Activity + Compose，Navigation Compose 使用有限
- **问题**：大量通过 `Intent` 启动新 Activity，自定义底部导航；`NavHost` 使用较少。
- **影响**：返回栈复杂；深链/状态恢复困难；过多手工过渡与状态维护；导航用例测试性差。

### 8）OkHttp 客户端重复且配置不一致
- **问题**：`NetServiceMgr`、Media3 音频、Coil 图片各自创建 OkHttpClient，超时/拦截器不一致。
- **影响**：header/TLS/重试/日志/缓存策略不统一；难以施加跨切关注点。

### 9）重试拦截器使用阻塞休眠（且当前被注释）
- **问题**：`RetryInterceptor` 在拦截器里 `Thread.sleep`；当前未启用。
- **影响**：启用则阻塞 OkHttp 线程；即便禁用也造成“僵尸代码”与风险误解。

### 10）安全与日志合规隐患
- **问题**：访问令牌存于 MMKV，未见加密密钥管理；拦截器日志包含请求 URL 与鉴权上下文。
- **影响**：数据暴露风险、日志泄露风险；不利于敏感账户型产品合规。

### 11）ViewModel 到数据源的分层渗漏
- **问题**：如 `ChatViewModel` 既用领域用例处理消息，又直接调用 API 获取设置，绕过仓库/领域。
- **影响**：职责混淆、数据源替换困难、错误处理不一致。

### 12）重度依赖全局单例且内部持状态
- **问题**：`UnifiedStartupManager`、`BillingRepository`、`ChatSessionManager`、`AgentCacheManager` 等全局有状态与线程池。
- **影响**：隐式依赖、跨界面状态耦合、测试搭建复杂、与 UI 时序交互微妙。

### 13）网络热路径过度埋点
- **问题**：拦截器在每个请求与错误上报分析/崩溃信息。
- **影响**：性能开销；产生噪声（如把预期状态当错误）；隐私压力。

### 14）MMKV 以 JSON 存大列表且缺少容量/淘汰策略
- **问题**：智能体列表以 JSON 写入，只有 TTL 无容量上限。
- **影响**：存储膨胀、读写变慢、手工序列化脆弱。

### 15）以 Activity 为中心的自定义返回/手势处理
- **问题**：`MainActivity` 手写边缘滑动/返回处理。
- **影响**：不同设备/系统版本行为不一致；可能与系统手势冲突；维护成本高。

## 积极面
- **Compose + StateFlow**：在 ViewModel 中一致使用现代响应式模式。
- **模块化**：设计、工具、Firebase、数据与应用层拆分清晰。
- **媒体能力**：基于 Media3 的音频播放与焦点管理，图像/音频预加载策略积极。
- **计费仓库**：统一订阅状态与事件中心（虽存在生命周期耦合问题）。
