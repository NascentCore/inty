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

### 验收

- 工程无 `com.inty.api` 依赖；
- 工程无 `IntyNetworkManager` 与 `core/data/http/services/*` 引用；
- 全量编译通过。

---

## 验证与测试计划

## 编译验证（每阶段至少执行）

- `./gradlew :core:data:compileDebugKotlin`
- `./gradlew :app:compileDebugKotlin`

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

## 任务拆分建议（可直接用于 issue）

1. `[Phase1] Retrofit 模型与接口补齐`
2. `[Phase2] app 层调用迁移（登录/版本/Explore/Report/Boost）`
3. `[Phase3] 聊天域迁移（生图/清消息/类型签名）`
4. `[Phase4] 移除 Stainless 依赖与死代码`
5. `[Docs] 更新 android_app/docs 与 AGENTS 说明`
