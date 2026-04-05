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

## 6. 测试与验收计划

### 6.1 测试策略

- 以 feature/E2E 为主，单元测试为辅。
- 先验证主链路稳定，再扩展多模态与主动触达。
- 每阶段都包含"成功路径 + 失败路径 + 恢复路径"。

### 6.2 联合验收标准（DoD）

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

## 7. 风险清单与应对

| 风险 | 描述 | 应对策略 |
|---|---|---|
| WebSocket 链路抖动 | 弱网下断链频繁导致体验不稳定 | 心跳 + 退避重连 + 明确错误提示 |
| 跨端契约漂移 | Kotlin/Pydantic 字段不同步 | 双端同步 checklist + 契约评审 |
| 本地与远端状态不一致 | UI 与服务端结果短期分叉 | 以 Room 为单一可信源，网络只刷新本地 |
| 服务层膨胀 | endpoint 逻辑回流导致难维护 | 严格坚持 service 分层与 DI |
| 多能力耦合过高 | 语音/图像影响聊天主链路 | 能力插件化，主链路优先，失败隔离 |
| 影响 IntelliMate 存量逻辑 | iMate 改造误改已有路由、模型或事务路径 | iMate 表 `imate_` 前缀隔离 + API 向后兼容策略 + IntelliMate 回归清单强制执行 |

## 8. 组织协作与里程碑产出

### 8.1 协作机制

- 每个 Phase 产出三件套：
  - 设计文档（架构与契约）
  - 实现 PR（最小可验收增量）
  - 测试证据（命令输出、日志、必要截图）
- 评审节奏：
  - 技术评审关注分层与契约。
  - 产品评审关注陪伴体验与节奏控制。

### 8.2 里程碑交付物

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

## 9. 必须明确的实施边界（精简版）

- 路由与链路边界：
  - 聊天主路径仅使用 `WS /api/v1/chat/ws`。
  - `WS /api/v1/chat/ws/verify` 仅用于联调与验收，不写入聊天数据。
  - 非聊天能力继续复用既有 HTTP API。
- 数据与分流边界：
  - iMate 数据使用 `imate_` 前缀表，与 IntelliMate 存量数据隔离。
  - 分流依据为 `X-App-Id`（header）或 `client_app_id`（token claim）；命中 iMate 才进入 iMate 数据链路。
  - 未命中分流字段时默认走 IntelliMate 链路，避免污染存量数据。
- 跨端契约边界：
  - 每次协议变更必须同步更新 backend `app/schemas` 与 Android `core/data/api/model`。
  - 仅允许向后兼容扩展（新增字段或新增 endpoint），禁止破坏性变更。
- 工程分层边界：
  - `android_app/` 作为基础能力层，`imate_android/` 作为 iMate 业务封装层。
  - 后端坚持 endpoint -> service -> repository/model 分层，避免 endpoint 承载复杂业务。

## 10. 首批执行顺序（精简版）

- Step 1：冻结 v1 契约与错误码清单，并完成双端 schema 对齐。
- Step 2：打通 Android + backend 的 WebSocket 聊天主链路闭环。
- Step 3：完成分流与 `imate_` 数据隔离，确保不影响 IntelliMate 存量逻辑。
- Step 4：补齐联调与回归验收，进入陪伴状态层增量开发。

---

- 结论：该计划以"复用已验证架构 + 分阶段可验收交付"为主轴，优先确保聊天主链路稳定，再逐步叠加长期陪伴智能能力，能最大化降低重构风险并提升上线成功率。
