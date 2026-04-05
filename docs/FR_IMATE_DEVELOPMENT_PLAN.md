# FR_IMATE_DEVELOPMENT_PLAN

## 1. 文档定位

- 本文档定义 iMate(or IntelliMate 2.0) 新版从 0 到 1 的完整开发计划，目标是在 IntelliMate Android app 与 inty backend 已验证架构基础上，交付稳定、可扩展、可观测的"智能体陪伴体验"。
- 本文档是需求评审、技术设计、实现拆分、测试验收、发布复盘的统一基线。

## 2. 背景与约束

### 2.1 已验证经验复用边界

- Android 端复用：
  - Room 作为聊天与角色相关本地持久化核心。
  - DataStore 作为用户偏好与配置持久化核心。
  - 统一网络栈与统一鉴权、环境切换、日志链路。
- Backend 端复用：
  - FastAPI + SQLAlchemy + Pydantic 数据契约。
  - endpoint -> service -> repository 分层模式。
  - 依赖通过 `app/api/deps.py` + Depends 注入，避免 endpoint 直接绑定全局单例。
  - 面向新版 Android app 的各项功能，凡能依赖 `app/` 现有 API 路由与 HTTP path 实现则优先复用；数据层采用 iMate 独立模型与表，统一使用 `imate_` 前缀与 IntelliMate 区分。
- Chat 通信复用：
  - app + backend 使用 WebSocket 主链路。
  - chat 路径仅提供 WebSocket，不提供 HTTP fallback。

### 2.2 新版 iMate(or IntelliMate 2.0) 的核心目标

- 体验目标：
  - 实时对话感知更强：输入到首 token/首句反馈延迟降低。
  - 长期陪伴连续性更强：跨会话记忆和关系状态持续可用。
  - 低负担与高可控并存：用户可控频率、可控触达、可控隐私边界。
- 工程目标：
  - 聊天主链路稳定运行，无明显丢消息、错序、重复响应。
  - 客户端离线可读、弱网可恢复、重连可追溯。
  - 后端可扩展到多能力（文本、语音、图像）而不破坏主链路。

### 2.3 非目标（当前计划不做）

- 不在第一阶段引入全新并行网络栈或事件总线。
- 不在第一阶段做全面多端统一（仅 Android + backend 主链路先收敛）。
- 不做大规模架构重写，优先"复用验证过的组件 + 小步迭代"。
- 不允许因 iMate 改造破坏 IntelliMate 既有接口语义、数据读写行为和线上稳定性。

## 3. 总体方案（目标架构）

### 3.1 Android 总体架构

- 分层：
  - UI/ViewModel 层：状态展示、用户意图采集。
  - Repository 层：统一业务编排，屏蔽网络与本地细节。
  - Local DataSource（Room）：消息、会话状态、角色关联数据。
  - Remote DataSource（WebSocket + 功能型 HTTP API）：请求发送、响应解析、错误映射。
  - Store（DataStore）：用户设置、聊天配置、实验开关、运行时端点策略。
- 核心原则：
  - Offline-First：UI 只读本地状态，网络仅刷新本地。
  - 单一可信源：聊天消息以 Room 为准，避免 UI 直接依赖网络瞬态数据。
  - 连接复用：WebSocket 连接按 token 维度复用，支持多 iMate(or IntelliMate 2.0) 会话复用单连接。

### 3.2 Backend 总体架构

- 分层：
  - API endpoint 层：协议解析、鉴权、参数校验、响应封装。
  - Service 层：聊天主流程编排、会话管理、策略执行、用量统计。
  - Repository/Model 层：SQLAlchemy 持久化与查询。
  - Schema 层：Pydantic 契约定义和跨端数据一致性。
- 核心原则：
  - endpoint 薄层化，业务逻辑下沉 service。
  - 依赖注入统一化，支持 WebSocket 聊天与功能 API 共用 service 对象。
  - 在 `app/services` 中产品化复用 `experimental/inty_v2_text_chat_prototype` 的聊天体验编排能力。
  - 错误语义清晰：鉴权错误、业务限制、系统异常明确分级。

### 3.3 Chat 主链路（WebSocket Only）

- 连接入口：
  - 生产端点：`/api/v1/chat/ws`（落库）。
  - 校验端点：`/api/v1/chat/ws/verify`（不落消息，仅联调验证）。
- 协议约束：
  - 文本帧 JSON，结构与现有 chat completion 请求/响应同构。
  - 客户端心跳 `ping`，服务端回 `pong`，服务端空闲超时自动断链。
  - 当前阶段采用"一发一收"顺序模型，防止并发响应错配。
- 故障处理：
  - WebSocket 不可用时仅做重连与错误展示，不切 HTTP chat 路径。
  - 非聊天能力继续使用现有 HTTP API，不受聊天链路策略影响。

## 4. 关键数据与契约规划

### 4.1 跨端契约治理原则

- Kotlin DTO 与 Pydantic Schema 必须双向同步版本。
- 新增字段默认向后兼容：客户端对未知字段忽略，不因新字段崩溃。
- API 返回错误信息统一英文，业务错误码稳定可枚举。
- 不修改 IntelliMate 既有契约含义；若必须扩展，仅允许新增字段或新增 endpoint，禁止破坏性变更。

### 4.2 Android 本地数据模型规划

- Room 数据域：
  - Chat message：消息内容、角色、状态、媒体信息、时间与排序键。
  - Sync state：分页游标、是否有更多、初次加载状态、最近同步时间。
  - Character relation：角色元信息、能量/互动计数等陪伴状态。
- DataStore 数据域：
  - 聊天展示偏好（字体、流式显示、自动语音等）。
  - 网络策略开关（WebSocket 模式、调试后端端点）。
  - 伴随体验策略开关（功能灰度、A/B 实验标记）。

### 4.3 Backend 业务数据规划

- iMate 核心表（统一 `imate_` 前缀）：
  - `imate_chats`：用户与 iMate(or IntelliMate 2.0) 会话关系。
  - `imate_chat_history`：用户消息、AI 回复、多模态元数据。
  - `imate_chat_settings`：会话级行为配置（语言、语音、模式）。
- 元数据增强方向：
  - 模型配置、提示词、生成耗时、重连原因、业务动作埋点。
  - 陪伴相关状态（关系阶段、记忆触发结果）在不破坏主链路的前提下增量扩展。

## 5. 分阶段开发路线图

## 5.1 Phase 0 - 基线冻结与契约冻结

- 目标：
  - 明确 iMate(or IntelliMate 2.0) 的跨端契约 baseline 和变更流程。
  - 冻结 Android/Backend 最小可运行链路。
- 交付：
  - 契约清单（请求、响应、错误码、心跳、超时语义）。
  - 架构决策记录（WebSocket 一发一收、离线优先、service 分层）。
- 验收：
  - 评审通过后作为后续所有开发的 source of truth。

## 5.2 Phase 1 - 聊天主链路 MVP（WebSocket + Room + Service 分层）

- Android：
  - 打通发送-响应-落库-渲染闭环。
  - 建立 WebSocket 会话管理、请求串行队列、断线重连策略。
  - chat 路径仅走 WebSocket，不提供 HTTP fallback。
- Backend：
  - 稳定 `/chat/ws` 与 `/chat/ws/verify`。
  - 复用 `app/api/v1/endpoints` 现有路由入口与 SQLAlchemy/Alembic 工程模式；iMate 数据表使用 `imate_` 前缀独立管理。
  - 将聊天流程统一收敛到 `app/services`，并引入 `inty_v2 prototype` 聊天体验编排逻辑。
  - 落库与不落库路径分离清晰。
- 验收：
  - 同连接支持不同 `agent_id` 顺序对话。
  - 心跳与空闲断链机制可验证。
  - WebSocket 单链路语义稳定，无 HTTP chat fallback 依赖。

## 5.3 Phase 2 - 长期陪伴状态层（记忆与关系状态）

- Android：
  - Room 增加陪伴状态读模型（关系阶段、最近互动摘要等）。
  - UI 从本地读状态，避免网络直连抖动。
- Backend：
  - service 层增加记忆提取与关系状态更新编排。
  - 状态写入与读取均走 SQLAlchemy + Pydantic 契约。
- 验收：
  - 同用户多次会话可体现连续状态变化。
  - 状态变更可追踪、可回溯、可灰度关闭。

## 5.4 Phase 3 - 体验增强（语音/图像/主动触达）

- 在不破坏 Phase 1 主链路的前提下增量接入：
  - 语音回复策略、图像生成、业务动作提示。
  - 稀疏主动触达（基于状态和节奏规则）。
- 验收：
  - 多模态能力可开关、可限流、可回滚。
  - 核心聊天稳定性指标不回退。

## 5.5 Phase 4 - 生产化与规模化

- 能力：
  - 观测看板、告警分级、压测与容量基线。
  - 灰度发布策略、回滚预案、数据迁移预案。
- 验收：
  - 有明确 SLO 与应急机制。
  - 新版本上线后可快速定位链路问题并回滚。

## 6. 详细任务拆分（可执行）

### 6.1 Android 工作流

- 数据层：
  - 统一 `Repository -> Room + Remote` 编排。
  - 完善消息状态机（SENDING/SUCCESS/FAILED）。
  - 保证排序键稳定与更新幂等。
- 连接层：
  - WebSocket 连接复用、心跳、重连退避、token 切换重建连接。
  - 请求级串行互斥，确保一发一收。
- 设置层：
  - DataStore 承载聊天偏好、WebSocket 开关、调试端点开关。
  - 迁移 MMKV 历史项到 DataStore（必要时）。
- UI 层：
  - 全量从 Room Flow 读取消息。
  - 清晰区分发送中、失败、已送达状态。

### 6.2 Backend 工作流

- API 层：
  - 聊天路径仅定义 WebSocket 语义，非聊天能力维持现有 HTTP API。
  - 鉴权、错误码、断链原因保持可观测。
- Service 层：
  - 聊天主流程编排（会话获取、限额检查、模型选择、响应封装、context/prompt 组装）。
  - 复用 `experimental/inty_v2_text_chat_prototype` 的体验要素（上下文装配、转录窗口、心跳语义）并在生产 service 中实现。
  - 语音/业务动作/记忆投递作为可插拔阶段。
- Repository/Model 层：
  - 优化 chat 与 settings 查询路径，减少重复查询与竞态。
  - iMate 使用独立 SQLAlchemy model（表名统一 `imate_` 前缀），并通过可复用 repository 模式避免分叉实现风格。
  - 关键写操作保持事务边界明确。
- DI 与可测试性：
  - endpoint 通过 Depends 注入 service，测试通过 dependency_overrides 替换。

### 6.3 跨端契约与联调工作流

- 维护跨端字段映射表（Kotlin DTO <-> Pydantic）。
- 每次协议变更必须同步：
  - backend `app/schemas`
  - android `core/data/api/model`
- 为 WebSocket 增设固定联调 checklist：
  - 鉴权成功/失败
  - ping/pong
  - 一发一收顺序
  - 多 agent 复用同连接
  - 无 HTTP fallback 条件下的重连与错误提示

## 7. 测试与验收计划

### 7.1 测试策略

- 以 feature/E2E 为主，单元测试为辅。
- 先验证主链路稳定，再扩展多模态与主动触达。
- 每阶段都包含"成功路径 + 失败路径 + 恢复路径"。

### 7.2 Android 测试清单

- Room/DataStore：
  - 本地读写一致性、用户隔离、缓存失效后重读正确性。
- WebSocket：
  - chat 路径强制 WS 的行为验证。
  - 多 agent 同连接会话正确路由。
  - 断线重连后不丢消息。
- UI：
  - 发送中/失败/重试状态一致。
  - 离线历史可读、恢复联网后可同步。

### 7.3 Backend 测试清单

- API 功能测试：
  - `/chat/ws`、`/chat/ws/verify` 的协议与稳定性验证。
  - 非聊天 HTTP API（设置、图片、语音、业务动作）回归可用。
- service 流程测试：
  - 限额、鉴权、模型切换、业务动作、错误映射、prototype 体验编排一致性。
- 数据一致性测试：
  - `imate_chats`/`imate_chat_history`/`imate_chat_settings` 事务行为。
  - 重试场景下幂等行为。

### 7.4 联合验收标准（DoD）

- 功能：
  - 用户可稳定完成"输入 -> AI 输出 -> 本地持久化 -> 历史回看"闭环。
- 稳定：
  - 常见弱网场景下无明显消息丢失/重复/错序。
- 可观测：
  - 能定位请求 ID、agent_id、session_id 对应链路日志。
- 可恢复：
  - WS 故障时可通过重连恢复或明确失败提示，不走 HTTP chat fallback。
- 不回归：
  - IntelliMate 既有主流程（登录、设置、历史消息、现有 chat 路径）行为与稳定性不受 iMate 变更影响。

## 8. 风险清单与应对

| 风险 | 描述 | 应对策略 |
|---|---|---|
| WebSocket 链路抖动 | 弱网下断链频繁导致体验不稳定 | 心跳 + 退避重连 + 明确错误提示 |
| 跨端契约漂移 | Kotlin/Pydantic 字段不同步 | 双端同步 checklist + 契约评审 |
| 本地与远端状态不一致 | UI 与服务端结果短期分叉 | 以 Room 为单一可信源，网络只刷新本地 |
| 服务层膨胀 | endpoint 逻辑回流导致难维护 | 严格坚持 service 分层与 DI |
| 多能力耦合过高 | 语音/图像影响聊天主链路 | 能力插件化，主链路优先，失败隔离 |
| 影响 IntelliMate 存量逻辑 | iMate 改造误改已有路由、模型或事务路径 | iMate 表 `imate_` 前缀隔离 + API 向后兼容策略 + IntelliMate 回归清单强制执行 |

## 9. 组织协作与里程碑产出

### 9.1 协作机制

- 每个 Phase 产出三件套：
  - 设计文档（架构与契约）
  - 实现 PR（最小可验收增量）
  - 测试证据（命令输出、日志、必要截图）
- 评审节奏：
  - 技术评审关注分层与契约。
  - 产品评审关注陪伴体验与节奏控制。

### 9.2 里程碑交付物

- Phase 0：
  - `FR_IMATE_DEVELOPMENT_PLAN.md`（本文件）
  - 契约冻结记录
- Phase 1：
  - WebSocket 主链路 PR
  - Android WS 切换与本地持久化验证报告
- Phase 2：
  - 陪伴状态层 PR
  - 连续会话体验验证报告
- Phase 3/4：
  - 多模态增强 PR
  - 生产化压测与运维手册

## 10. 建议的首批执行顺序（从明天即可开工）

- Step 1：冻结 v1 契约和错误码清单（1 个 PR，仅文档和 schema 对齐）。
- Step 2：打通 Android WS 主链路并移除 chat HTTP fallback 假设（1-2 个 PR）。
- Step 3：完成 backend WS 主链路 service 编排，复用 `app/` 路由与 SQLAlchemy/Alembic 工程模式，按 `imate_` 前缀建设 iMate 独立模型，接入 prototype 体验逻辑并补齐关键 feature tests（1-2 个 PR）。
- Step 4：补齐联调 checklist 与自动化回归（1 个 PR）。
- Step 5：进入陪伴状态层增量开发（后续迭代）。

## 11. iMate(or IntelliMate 2.0) Android v1 对应后端实现框架

### 11.1 Android 代码目录分层（新增约束）

- 新版 Android app 代码放置在 `imate_android/`。
- `android_app/` 作为 Android 基础能力层，提供可复用基础代码与库函数（data/core/library 等）。
- `imate_android/` 作为 iMate(or IntelliMate 2.0) 应用封装层，在 `android_app/` 之上组装业务与产品体验。
- 目录关系目标：
  - `android_app/ : imate_android/` 对应后端 `app/ : backend/inty/` 的分层关系。
  - 基础能力沉淀在底层目录，产品特定实现在上层目录，避免双向耦合与重复造轮子。
- 工程约束：
  - 共有能力优先下沉 `android_app/`，`imate_android/` 优先组合调用而非复制实现。
  - `imate_android/` 禁止反向要求 `android_app/` 依赖其业务代码。

### 11.2 范围前提（对应新版 iMate(or IntelliMate 2.0) Android）

- Android 产品范围：
  - iMate(or IntelliMate 2.0)（从 IntelliMate 演进的 agentic companion AI）。
  - 首批功能：Google 登录、Email+Password 登录（Google Play reviewer 场景）、Settings 页面、Basic chat。
- 后端原则：
  - 凡新版 Android 功能可直接依赖 `app/` 现有 API 路由与 HTTP path，则直接复用。
  - 聊天主路径保持 WebSocket-only，不提供 HTTP chat fallback。

### 11.3 需要实现/复用的 HTTP endpoints 与 WS endpoints

- Auth（登录）：
  - `POST /api/v1/auth/google/login`
    - 复用现有端点；同一端点支持两种入参模式：
      - Google `id_token` 登录。
      - `email + password` 登录（已在端点内分支处理，满足 reviewer 登录场景）。
    - 实施前提：
      - reviewer 使用的账号需预先在数据库中创建为 `AuthType.EMAIL` 且已写入密码哈希。
      - 该方案用于登录，不包含独立 email 注册流程。
- User Settings（设置页）：
  - `GET /api/v1/settings/`
  - `PUT /api/v1/settings/`
  - `GET /api/v1/users/me`（用于设置页展示当前用户资料）。
  - `PUT /api/v1/users/profile`（若设置页包含资料编辑则复用）。
- Basic chat（基础聊天）：
  - `WS /api/v1/chat/ws`（生产聊天主链路，落库）。
  - `WS /api/v1/chat/ws/verify`（联调与验收链路，不落聊天消息）。
  - `GET /api/v1/chats/agents/{agent_id}/messages`（拉取历史消息）。
  - `GET /api/v1/chats/agents/{agent_id}/settings`、`PUT /api/v1/chats/agents/{agent_id}/settings`（聊天设置）。
- 路由归属与分流策略（强制）：
  - 复用现有路径不等于复用 IntelliMate 存量数据表；iMate 请求必须分流到 `imate_` 前缀表。
  - 分流判定字段固定为 `X-App-Id`（header）或 `client_app_id`（token claim）；取值为 `imate_android` 时走 iMate 数据链路。
  - 未携带分流字段时默认按 IntelliMate 链路处理，禁止写入 iMate 表，避免污染存量逻辑。
  - `verify` 端点始终不落库，仅用于协议与体验联调验证。
- 版本与门控（建议纳入首批）：
  - `POST /api/v1/version/check`（写入 `users.last_android_app_version_code`，支持后续功能门控）。

### 11.4 数据库部署（PostgreSQL + SQLAlchemy）

- 部署拓扑：
  - `dev` 与 `prod` 分离数据库实例（最小可行：同 VM 不同库；推荐：独立实例）。
  - 主库 PostgreSQL 16。
  - 可选只读副本（`async_replica_url`）承接读多写少查询，主链路写入仍走主库。
- 访问层：
  - 统一通过 `app/db/session.py` 的 SQLAlchemy async engine 访问。
  - 连接池参数由 `config.yaml` 注入（pool_size/max_overflow/pool_timeout 等）。
- 变更管理：
  - 所有 schema 变更走 Alembic migration。
  - iMate 新增独立 ORM 模型与 migration，表名统一 `imate_` 前缀。
- 运维基线：
  - 自动备份（每日全量 + 增量 WAL）。
  - 监控：连接数、慢查询、锁等待、复制延迟（若启用副本）。

### 11.5 第三方存储系统部署（对象存储）

- 媒体对象存储：
  - 使用 GCS，`dev`/`prod` 使用独立 bucket（避免环境污染）。
  - 服务账号统一通过 `app.gcp_service_account_key` 注入。
- 访问路径：
  - 后端写入 GCS 原始对象路径。
  - 客户端访问使用 CDN 域名（Cloudflare）进行分发与缓存。
- 安全策略：
  - bucket 最小权限（仅服务账号可写）。
  - URL 访问策略统一在后端转换，避免客户端拼接存储内部路径。
- 测试策略：
  - test 环境可使用 fake GCS（`use_fake_gcs: true`）保证可重复测试。

### 11.6 iMate 后端分层架构设计（本期落地版）

| 层级 | 目标 | 复用现有能力 | 新增实现（iMate v1） | 边界约束 |
|---|---|---|---|---|
| Interface 层（HTTP + WebSocket） | 对 Android 暴露稳定契约与实时链路 | `app/api/v1/endpoints/auth.py`、`settings.py`、`chats.py`、`chat.py` | `chat.py` 内补全 iMate 专用 WS 会话语义（会话上下文、断链原因、观测字段） | chat 仅 WS，不提供 HTTP fallback |
| Application 层（Service 编排） | 聚合业务流程与策略，不承载协议细节 | `app/services/chat_service.py`、`subscription_service.py`、`voice_service.py`、`user_service.py` | 新增 `app/services/imate/` 子域服务（会话编排、记忆编排、关系状态编排） | endpoint 仅做校验与转发，禁止回流复杂业务 |
| Domain/Data 层（Repository + Model） | 保证会话、消息、设置、陪伴状态的一致性 | `app/services/*_service.py` 中现有 CRUD 模式、`app/db/session.py` | 新增 iMate 独立 ORM 与 repository，表统一 `imate_` 前缀（关系阶段、记忆命中、触达节奏） | 所有 schema 变更必须走 Alembic |
| Infra 层（模型/存储/观测） | 对接 LLM、GCS、日志与指标 | `app/core/*`、`app/services/gcs_service.py`、现有日志体系 | 统一 `trace_id/request_id/session_id/agent_id/user_id` 观测字段 | 不在本期引入新消息总线 |

### 11.7 Interface 层设计（HTTP/WS 与 iMate app 对接）

- 路由复用与职责划分：
  - Auth：复用 `POST /api/v1/auth/google/login`，同端点支持 `id_token` 与 `email+password`。
  - Settings：复用 `GET/PUT /api/v1/settings/`、`GET /api/v1/users/me`、`PUT /api/v1/users/profile`。
  - Chat：复用 `WS /api/v1/chat/ws` 与 `WS /api/v1/chat/ws/verify`，历史消息和 chat settings 继续走 `chats.py` HTTP 查询/更新。
- 路由分流规则（避免影响 IntelliMate）：
  - endpoint 层仅负责识别 `X-App-Id`/`client_app_id` 并选择 service 分支，不在 endpoint 内混写业务逻辑。
  - iMate 分支只读写 `imate_` 前缀表；IntelliMate 分支继续使用既有表与既有事务路径。
  - 任一请求若分流上下文缺失或非法，按 IntelliMate 默认链路处理并记录 warning 级日志，不做隐式 iMate 落库。
- WS 协议规范（iMate v1）：
  - 入站统一 `ChatWebSocketRequest`，出站统一 `APIResponse + agent_id`。
  - 心跳机制固定为 `ping/pong`，服务端空闲超时关闭连接。
  - 同连接允许多 `agent_id` 顺序复用，但同一时刻仅处理一个请求（严格一发一收）。
- 接口错误分层：
  - 认证错误：401/4001（WS close reason unauthorized）。
  - 业务错误：subscription limit、guest login required 等稳定业务码。
  - 系统错误：500，返回统一英文 message，并打结构化日志。

### 11.8 数据库封装与迁移设计（SQLAlchemy + Alembic）

- Repository 组织：
  - 沿用 `endpoint -> service -> repository/model`，避免 endpoint 直接写 SQL。
  - 在 `app/services/imate/` 下引入 iMate 子域 repository façade，封装跨表事务（`imate_chats` + `imate_chat_history` + `imate_companion_state`）。
- 事务边界：
  - 聊天主流程最小事务：`用户消息入库 -> AI 回复入库 -> 使用量记录`。
  - 非关键旁路（如投递提醒、语音附加）失败不回滚主回复，按独立事务提交。
- Alembic 迁移策略：
  - 新增字段默认 nullable + 默认值，先兼容旧客户端，再分阶段收紧约束。
  - migration 脚本必须包含回滚路径与数据回填说明。
- 读写策略：
  - 主链路写入只走主库。
  - 历史分页/设置读取可逐步切到只读副本（若启用 `async_replica_url`）。

### 11.9 AI 核心能力设计（聊天 WS 体验编排）

- 聊天编排管线（Service）：
  - Step 1: 鉴权与用户态加载（用户、订阅、agent、chat settings）。
  - Step 2: 会话定位（`get_or_create_chat_by_agent` -> `session_id`）。
  - Step 3: 上下文组装（最近窗口 + 必要记忆 + user_time_context）。
  - Step 4: 模型选择（订阅态 + feature gate + agent 配置）。
  - Step 5: 模型调用（复用现有 agent manager），并标准化 content/content_parts。
  - Step 6: 回包封装（choices、usage、business_actions、source_imate_id）。
  - Step 7: 后处理（可选语音、记忆提醒、业务动作投递）。
- 体验设计难点与解法：
  - 难点 A - 首 token 反馈慢：优先优化上下文窗口裁剪与模型路由，减少阻塞式附加逻辑。
  - 难点 B - 断线重连后的一致性：客户端重连后以消息历史为准，服务端保持消息写入幂等。
  - 难点 C - 多能力耦合导致主链路抖动：语音/图片/记忆投递全部插件化，失败不影响文本主回复。
  - 难点 D - 多 agent 同连接路由：响应体强制回传 `agent_id`，客户端按 `agent_id` 分发落库。
- 可观测性基线：
  - 每次请求都记录 `request_id/session_id/agent_id/user_id/model/latency_ms`。
  - 关键阶段打点：鉴权、上下文组装、模型调用、落库、后处理。

### 11.10 非 AI 辅助能力设计（登录/鉴权/设置等）

- 登录与鉴权：
  - 复用 `auth.py` 既有登录链路，不新增并行 auth endpoint。
  - Token 发行、用户恢复、订阅恢复保持现有逻辑，iMate 仅补充 reviewer 账号运维流程。
- 用户资料与设置：
  - 复用 `users`、`settings` 既有 endpoint 与 schema，iMate 不拆分第二套 profile/settings 模型。
  - 设置变更事件仅更新当前用户作用域，不跨用户广播。
- 版本门控与灰度：
  - 继续用 `users.last_android_app_version_code` + `feature_gating.py` 控制能力开关。
  - 新能力默认关闭，按版本与白名单逐步打开。
- 安全与审计：
  - 管理后台相关 endpoint 仍要求 superuser。
  - 鉴权失败、敏感设置变更、订阅限制触发需保留审计日志。

### 11.11 实施顺序（按本期最小可交付）

- Iteration 1 - Interface 稳定化：
  - 固化 WS 协议与错误码；补齐 `/ws`、`/ws/verify` 联调清单与自动化测试。
- Iteration 2 - Service 分层收敛：
  - 将 iMate chat 编排逻辑收敛到 `app/services/imate/`，endpoint 保持薄层。
- Iteration 3 - 数据层扩展：
  - 新增陪伴状态相关表与 migration，完成 repository façade 与事务边界落地。
- Iteration 4 - 非 AI 能力对齐：
  - 联调登录、鉴权、设置、历史消息拉取，形成 Android v1 完整闭环验收。
- Iteration 5 - IntelliMate 不回归验证：
  - 对 IntelliMate 既有登录、设置、历史消息、聊天链路执行最小回归，作为上线前强制门禁。

---

- 结论：该计划以"复用已验证架构 + 分阶段可验收交付"为主轴，优先确保聊天主链路稳定，再逐步叠加长期陪伴智能能力，能最大化降低重构风险并提升上线成功率。
