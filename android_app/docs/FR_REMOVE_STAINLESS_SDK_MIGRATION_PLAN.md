# FR_REMOVE_STAINLESS_SDK_MIGRATION_PLAN

## 背景与目标

### 背景

当前 Android 端同时存在两套 API 调用路径：

1. 现有非-Stainless 路径：`NetServiceMgr` + Retrofit + Moshi + `HttpResult`
2. Stainless 路径：`IntyNetworkManager` + `core/data/http/services/*` + `com.inty.api.*`

双轨并行导致以下问题：

- 同一业务域中出现混用，调试与回归复杂度高；
- 错误处理模型不统一（`HttpResult` 与 `ApiResult` 并存）；
- 类型来源不统一（本地 model 与 SDK model 并存）；
- 依赖与构建链路复杂，迁移边界不清晰。

### 本次总体目标

在不改变业务功能的前提下，移除 Android app 对 Stainless 自动生成 SDK 的使用，统一到现有的非-Stainless 框架：

- 网络调用统一为 Retrofit 接口（`I*Api`）；
- 返回结果统一为 `HttpResult<T>`；
- 数据模型统一到 `core/data/api/model`；
- 逐步移除 `IntyNetworkManager`、`core/data/http/services/*`、`com.inty.api.*` 引用。

---

## 范围定义

### In Scope

- Android app 与 core/data 模块中所有运行时业务调用链；
- Retrofit 接口与本地数据模型补齐；
- Stainless 相关依赖与代码路径清理；
- 对应文档与规则更新。

### Out of Scope

- 后端 API 行为重构；
- 大规模 UI 改造；
- 与本需求无关的性能专项优化。

---

## 迁移原则

1. 单一网络栈：只保留 Retrofit 路径。
2. 单一错误模型：业务调用统一返回 `HttpResult`。
3. 单一类型来源：禁止在业务层直接使用 `com.inty.api.*` 类型。
4. 小步提交：分阶段迁移、每阶段可独立验证、可独立回滚。
5. 兼容优先：迁移过程中优先“行为一致”，再做代码清理。

---

## 分阶段计划

### 阶段状态总览（截至 2026-03-27）

- ✅ Phase 0：已执行（本次提交补齐盘点清单、迁移映射、冻结规则）。
- ✅ Phase 1：已完成（`93f881d8771e5db21fe391eb9baa4ef73ed23957`）。
- ✅ Phase 2：已完成（`a6a5bfd5604949f850be73584c9060adc4cae35c`）。
- ✅ Phase 3：已完成（本次提交：聊天域改为 Retrofit + 本地 DTO + HttpResult）。
- ✅ Phase 4：已完成（构建/代码/仓库治理清理已落地，文档与门禁已对齐）。

## Phase 0 - 盘点与冻结（准备阶段）

### 目标

- 建立完整调用清单；
- 冻结新增 Stainless 依赖。

### 任务

1. 盘点所有 `IntyNetworkManager`、`core/data/http/services/*`、`com.inty.api.*` 引用。
2. 输出迁移映射表（调用点 -> 目标 Retrofit 接口/本地模型）。
3. 在评审约定中明确：迁移期间不允许新增 Stainless 调用。

### 交付物

- 引用清单与迁移映射表（本文件附录可维护）。

### TODO（Phase 0）

- [x] 盘点所有 `IntyNetworkManager`、`core/data/http/services/*`、`com.inty.api.*` 引用（见附录 A）。
- [x] 输出迁移映射表（调用点 -> 目标 Retrofit 接口/本地模型，见附录 B）。
- [x] 在评审约定中明确冻结：迁移期间不允许新增 Stainless 调用（见 `android_app/AGENTS.md` 新增规则）。

---

## Phase 1 - 能力补齐（先补齐 Retrofit 侧能力）

### 目标

让非-Stainless 路径具备一对一替换能力，避免“边迁移边缺接口”。

### 任务

1. 在 `core/data/api/model` 新增 Retrofit 所需 DTO：
   - Character Theme 相关类型（替代 `AgentService.CharacterThemeItem`）；
   - Report 相关请求与原因枚举（替代 `ReportCreateParams`）；
   - Chat Image Generation 相关类型（替代 `ChatService.ChatImageGenerationResult`）；
   - Version Reminder Action 本地枚举（替代 `VersionCheckResponse.Data.ReminderAction`）。
2. 扩展 Retrofit 接口：
   - `IUserApi`：补齐 `getMe`、`updateProfile`（若现有业务已用新路径）；
   - `IChatApi`：补齐消息生图、清空消息等现有业务已用能力；
   - 新增 `IReportApi` 并接入 `NetServiceMgr`；
   - `IAgentApi` 补齐当前服务层封装过的关键能力（如榜单、主题区、能量点更新等）。
3. 确认 `NetServiceMgr` 暴露完整 API 获取入口（含 cache key 与 clear 逻辑）。

### 验收

- Retrofit 接口可覆盖当前所有 Stainless 运行时能力；
- app/core/data 编译通过（不改业务调用点也能通过）。

### TODO（Phase 1）

- [x] 补齐 `core/data/api/model` 中 Character Theme / Report / Chat Image / Version Reminder Action 相关 DTO。
- [x] 补齐 `IUserApi`、`IChatApi`、`IReportApi`、`IAgentApi` 的迁移所需接口。
- [x] `NetServiceMgr` 暴露完整 API 入口并接入 `IReportApi`。
- [x] 对应实现已落地并合入：`93f881d8771e5db21fe391eb9baa4ef73ed23957`。

---

## Phase 2 - app 层调用迁移（先迁 UI/VM 主流程）

### 目标

将 app 模块对 `services/*`、`IntyNetworkManager`、`com.inty.api.*` 的直接依赖迁出。

### 任务

1. 登录/版本检查路径迁移到 Retrofit；
2. Explore/Theme、Boost、Report、UserProfile 等页面逻辑迁移到 Retrofit；
3. `AgentCacheManager`、`ExploreThemeSections`、相关单测改用本地 DTO；
4. 删除 app 模块对 `com.inty.api.*` 的 import。

### 验收

- `android_app/app` 模块无 `IntyNetworkManager` 调用；
- `android_app/app` 模块无 `com.inty.api.*` 引用；
- 关键业务流程可用（登录、Explore、Report、Boost）。

### TODO（Phase 2）

- [x] 登录/版本检查路径迁移到 Retrofit 侧调用链。
- [x] Explore/Theme、Boost、Report、UserProfile 等 app 层主流程迁移。
- [x] app 模块移除 `com.inty.api.*` 直接 import，`IntyNetworkManager` 直接引用迁出到 core/data 协调层。
- [x] 对应实现已落地并合入：`a6a5bfd5604949f850be73584c9060adc4cae35c`。

---

## Phase 3 - core/data 聊天域迁移

### 目标

清理 core/data 中残留的 Stainless 依赖，特别是聊天域。

### 任务

1. `ChatRemoteDataSource`：
   - 用 Retrofit 替代 `ChatService.messageGenerateImage(...)`；
   - 用 Retrofit 替代 `IntyNetworkManager.getClient().async()` 清消息；
2. `ChatRepository` / `ChatUseCases` / `RoomImpl`：
   - 类型签名改为本地 DTO；
   - 错误模型统一回 `HttpResult`；
3. 移除对 `core/data/http/services/ChatService` 的类型依赖。

### 验收

- `core/data/chat/**` 无 Stainless 引用；
- 聊天生图与清消息功能行为与迁移前一致。

### TODO（Phase 3）

- [x] `ChatRemoteDataSource.messageGenerateImage()` 不再调用 `core/data/http/services/ChatService`，改为直接走 `NetServiceMgr.getChatApi().generateMessageImage(...)`。
- [x] `ChatRepository` / `ChatUseCases` / `RoomImpl` 类型签名从 `ChatService.ChatImageGenerationResult` 迁移为 `core/data/api/model` 本地 DTO。
- [x] 聊天域统一错误模型到 `HttpResult`，移除 `ApiResult` 桥接逻辑。
- [x] 清理 `core/data/http/services/ChatService.kt` 与相关异常类型引用。
- [x] 对应实现已落地并合入：本次提交。

---

## Phase 4 - 删除 Stainless 依赖与死代码清理

### 目标

从构建与源码层彻底移除 Stainless 路径。

### 任务

1. 构建层移除：
   - 删除 `libs.inty.kotlin` 依赖；
   - 删除 `includeBuild("library/inty_sdk")`；
   - 清理 `libs.versions.toml` 中对应条目。
2. 代码层移除：
   - 删除 `IntyNetworkManager`；
   - 删除 `core/data/http/services/*`；
   - 删除 `ModelConverters` 等仅服务 Stainless 的桥接代码；
   - 清理 `NetServiceMgr` 注释中“新功能优先 IntyNetworkManager”等过时描述。
3. 仓库治理层移除（submodule 与工程配置）：
   - 移除 `.gitmodules` 中 `android_app/library/inty_sdk` 条目；
   - 清理 `.prettierignore` 中 `android_app/library/inty_sdk`；
   - 清理 `.github/workflows/ci_android_app.yaml` 中 `android_app/library/inty_sdk` 影响范围映射；
   - 删除已废弃的 `tools/scripts/update_inty_sdk_submodule.sh`（原 submodule 更新入口）；
   - 更新 `android_app/README.md` 中 `git submodule update --init --recursive` 的 Android `inty_sdk` 指引。

### 验收

- 工程无 `com.inty.api` 依赖；
- 工程无 `IntyNetworkManager` 与 `core/data/http/services/*` 引用；
- 工程无 `android_app/library/inty_sdk` 的 submodule/CI/脚本/README 残留引用；
- 全量编译通过。

### TODO（Phase 4）

- [x] 构建层移除 `libs.inty.kotlin` 与 `includeBuild("library/inty_sdk")`。
- [x] 删除 `IntyNetworkManager`、`core/data/http/services/*`、`ModelConverters` 等 Stainless 专用代码。
- [x] 删除 `proguard-rules.pro` 中 `com.inty.api.*` keep 规则。
- [x] 清理 `NetServiceMgr` 与其他文档中的“双栈并行/新功能优先 IntyNetworkManager”过时描述。
- [x] 以 `rg "IntyNetworkManager|com\\.inty\\.api\\." android_app/{app,core}` 作为收尾门禁，确保运行时代码零引用（仅文档残留）。
- [x] 以 `rg "includeBuild\\(\"library/inty_sdk\"\\)|implementation\\(libs\\.inty\\.kotlin\\)|inty-kotlin\\s*=\\s*\\{\\s*group\\s*=\\s*\"com\\.inty\\.api\"" android_app` 作为构建层收尾门禁，确保依赖零残留（仅迁移文档快照字段）。
- [x] 以 `rg "android_app/library/inty_sdk|library/inty_sdk" .github/workflows/ci_android_app.yaml android_app/README.md .gitmodules .prettierignore` 作为仓库治理收尾门禁，确保 submodule 零残留。

---

## 验证与测试计划

## 编译验证（每阶段至少执行）

- `./gradlew :core:data:compileDebugKotlin`
- `./gradlew :app:compileDebugKotlin`

## 静态门禁（Phase 4 收尾必跑）

- `rg "IntyNetworkManager|com\\.inty\\.api\\." android_app/{app,core}`
- `rg "includeBuild\\(\"library/inty_sdk\"\\)|implementation\\(libs\\.inty\\.kotlin\\)|inty-kotlin\\s*=\\s*\\{\\s*group\\s*=\\s*\"com\\.inty\\.api\"" android_app`
- `rg "android_app/library/inty_sdk|library/inty_sdk" .github/workflows/ci_android_app.yaml android_app/README.md .gitmodules .prettierignore`

## 重点回归（按阶段选择）

1. 登录（Google / Email）；
2. 版本检查更新提示；
3. Explore 列表与主题专区；
4. Report（含图片上传）；
5. Boost 榜单与加分同步；
6. 聊天生图与清空消息。

## 建议补充自动化

- 对 Explore / Report / Boost 的已有单测做必要类型迁移；
- 为聊天生图路径补充 data 层回归测试（若当前缺失）。

---

## 风险与应对

### 风险 1：接口行为不一致

- 现象：服务层原有逻辑中含隐式转换，迁移后出现字段空值/默认值差异。
- 应对：先补“映射函数单测”，再替换调用点。

### 风险 2：错误码语义变化

- 现象：`ApiResult.Error` 到 `HttpResult.Failure` 映射后 code/message 不一致。
- 应对：统一保留后端业务 code，维护映射表并回归关键弹窗逻辑。

### 风险 3：迁移跨度大导致冲突

- 现象：多人并行开发与大批量重命名冲突。
- 应对：按 Phase 拆分小 PR，先能力补齐再调用迁移。

---

## 回滚策略

1. 阶段内回滚：每个 Phase 独立 PR，可按 PR 粒度回退；
2. 紧急回滚：保留迁移前标签（tag）与关键 commit；
3. 功能开关：必要时可临时保留旧路径并通过开关切回（仅短期，不长期并存）。

---

## 完成定义（Definition of Done）

满足以下全部条件视为本 FR 完成：

1. Android 运行时调用链全部使用 Retrofit 非-Stainless 框架；
2. app 与 core/data 不再引用 `IntyNetworkManager`；
3. app 与 core/data 不再引用 `com.inty.api.*`；
4. Stainless 相关依赖已从构建配置移除；
5. 关键业务回归通过；
6. 文档与目录级规范已更新并通过自查。

---

## 附录 A - 引用清单（2026-03-27 快照）

### A.1 app 模块运行时

- `android_app/app/src/main`：`IntyNetworkManager` / `com.inty.api.*` 引用为 0（符合 Phase 2 验收）。

### A.2 core/data 模块运行时状态

- `android_app/core/data/src/main`：`IntyNetworkManager` / `core/data/http/services/*` / `com.inty.api.*` 运行时代码引用为 0（Phase 4 完成）。
- `NetworkStackCoordinator` 与 `IntySetting` 已统一到 `NetServiceMgr.clearCache()`。
- 历史双栈说明文档已改为 Retrofit 单栈描述。

### A.3 构建层状态

- `android_app/settings.gradle.kts` 中 `includeBuild("library/inty_sdk")` 已删除；
- `android_app/app/build.gradle.kts` 与 `android_app/core/data/build.gradle.kts` 中 `implementation(libs.inty.kotlin)` 已删除；
- `android_app/gradle/libs.versions.toml` 中 `inty-kotlin` 版本与别名已删除；
- `android_app/app/proguard-rules.pro` 中 `com.inty.api.*` keep 规则已删除。

### A.4 仓库治理层状态

- `.gitmodules` 中 `android_app/library/inty_sdk` 条目已移除（文件已删除）；
- `.prettierignore` 中 `android_app/library/inty_sdk` 与 `ops_web_ui/inty_sdk` 已移除；
- `.github/workflows/ci_android_app.yaml` 中 `android_app/library/inty_sdk` 变更触发映射已移除；
- `tools/scripts/update_inty_sdk_submodule.sh` 已删除（此前为废弃 no-op，避免误操作主仓库）；
- `android_app/README.md` 已移除 Android submodule 初始化指引。

## 附录 B - Phase 0 迁移映射表（调用点 -> Retrofit / 本地模型）

| 当前调用点（Stainless） | 目标 Retrofit 接口 | 目标本地模型 | 归属阶段 |
| --- | --- | --- | --- |
| `AuthService.googleLogin` | `IUserApi.loginByGoogle` | `GoogleLoginRequest/GoogleLoginResponse` | Phase 4（删除旧服务层） |
| `UserService.getUserProfile / updateUserProfile` | `IUserApi.getMe / updateProfile` | `UserProfile`、`UserProfileUpdateRequest` | Phase 4 |
| `UserService.uploadAvatar`、`ReportService.uploadImage` | 统一到 Retrofit 上传接口（现有 `IUserApi.uploadAvatar`，必要时抽 `ICommonApi`） | `UploadAvatarResponse` 或统一上传响应 DTO | Phase 4 |
| `AgentService.*`（推荐/详情/创建/更新/榜单/主题） | `IAgentApi.*` | `AgentInfo`、`CharacterThemeItem`、`AgentEnergyPointsUpdateRequest` | Phase 4 |
| `SubscriptionService.*` | `ISubscriptionApi.getSubscriptionPlans / verifySubscription` | `SubscriptionPlansResponse`、`SubscriptionVerifyRequest/Response` | Phase 4 |
| `VersionService.checkAppUpgrade` | `ICommonApi.checkAppUpgrade`（必要时补齐请求参数） | `AppVersionRsp.AppVersionData`、`VersionReminderAction` | Phase 4 |
| `ReportService.createReport`（旧签名） | `IReportApi.createReport`（已具备） | `ReportCreateRequest`、`ReportReasonCode`、`ReportTargetType`、`ReportRequestType` | Phase 4（删除旧签名） |
| `ChatService.messageGenerateImage` | `IChatApi.generateMessageImage` | `ChatImageGenerationRequest/ApiResponse/Payload` | 已完成（Phase 3） |
| `ChatRepository/UseCases/RoomImpl` 对 `ChatService.ChatImageGenerationResult` 的类型依赖 | `ChatRemoteDataSource` 直接返回本地 DTO（由 `IChatApi` 结果映射） | 新增/复用 `core/data/api/model` 聊天生图结果 DTO | 已完成（Phase 3） |
| `NetworkStackCoordinator` / `IntySetting` 调 `IntyNetworkManager.clearClientCache` | 仅保留 `NetServiceMgr.clearCache`（及必要的统一协调入口） | 无 | Phase 4 |
| `ModelConverters` 中 `IntyAgent/IntyUser` 转换 | 删除（迁移完成后不再需要） | 统一使用 `core/data/api/model` | Phase 4 |
| `.gitmodules` / `.prettierignore` / `ci_android_app.yaml` / `android_app/README.md` 中 `android_app/library/inty_sdk` 残留 | 移除 submodule 配置与工程侧引用 | 无 | Phase 4 |

---

## 任务拆分建议（可直接用于 issue）

1. `[Phase0][Done] 盘点与冻结（引用清单 + 迁移映射 + 评审规则）`
2. `[Phase1][Done] Retrofit 模型与接口补齐`
3. `[Phase2][Done] app 层调用迁移（登录/版本/Explore/Report/Boost）`
4. `[Phase3][Done] 聊天域迁移（生图/清消息/类型签名）`
5. `[Phase4][Done] 移除 Stainless 依赖、submodule 与死代码`
6. `[Docs][Done] 清理双栈历史文档，统一为 Retrofit 单栈描述`
