# FR_IMATE_DEVELOPMENT_PLAN

## 1. 文档定位

- 本文档定义 iMate 新版从 0 到 1 的完整开发计划，目标是在 IntelliMate Android app 与 inty backend 已验证架构基础上，交付稳定、可扩展、可观测的"智能体陪伴体验"。
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
- Chat 通信复用：
  - app + backend 使用 WebSocket 主链路。
  - 维持 HTTP completion 作为灰度和故障回退链路。

### 2.2 新版 iMate 的核心目标

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

## 3. 总体方案（目标架构）

### 3.1 Android 总体架构

- 分层：
  - UI/ViewModel 层：状态展示、用户意图采集。
  - Repository 层：统一业务编排，屏蔽网络与本地细节。
  - Local DataSource（Room）：消息、会话状态、角色关联数据。
  - Remote DataSource（HTTP + WebSocket）：请求发送、响应解析、错误映射。
  - Store（DataStore）：用户设置、聊天配置、实验开关、运行时端点策略。
- 核心原则：
  - Offline-First：UI 只读本地状态，网络仅刷新本地。
  - 单一可信源：聊天消息以 Room 为准，避免 UI 直接依赖网络瞬态数据。
  - 连接复用：WebSocket 连接按 token 维度复用，支持多 iMate 会话复用单连接。

### 3.2 Backend 总体架构

- 分层：
  - API endpoint 层：协议解析、鉴权、参数校验、响应封装。
  - Service 层：聊天主流程编排、会话管理、策略执行、用量统计。
  - Repository/Model 层：SQLAlchemy 持久化与查询。
  - Schema 层：Pydantic 契约定义和跨端数据一致性。
- 核心原则：
  - endpoint 薄层化，业务逻辑下沉 service。
  - 依赖注入统一化，支持 WebSocket 与 HTTP 共用 service 对象。
  - 错误语义清晰：鉴权错误、业务限制、系统异常明确分级。

### 3.3 Chat 主链路（WebSocket 优先）

- 连接入口：
  - 生产端点：`/api/v1/chat/ws`（落库）。
  - 校验端点：`/api/v1/chat/ws/verify`（不落消息，仅联调验证）。
- 协议约束：
  - 文本帧 JSON，结构与现有 chat completion 请求/响应同构。
  - 客户端心跳 `ping`，服务端回 `pong`，服务端空闲超时自动断链。
  - 当前阶段采用"一发一收"顺序模型，防止并发响应错配。
- 故障回退：
  - WebSocket 不可用时可切回 HTTP completion。
  - 回退路径保持同一数据契约，减少 UI 分叉逻辑。

## 4. 关键数据与契约规划

### 4.1 跨端契约治理原则

- Kotlin DTO 与 Pydantic Schema 必须双向同步版本。
- 新增字段默认向后兼容：客户端对未知字段忽略，不因新字段崩溃。
- API 返回错误信息统一英文，业务错误码稳定可枚举。

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

- 核心表沿用并增强：
  - `chats`：用户与 iMate 会话关系。
  - `chat_history`：用户消息、AI 回复、多模态元数据。
  - `chat_settings`：会话级行为配置（语言、语音、模式）。
- 元数据增强方向：
  - 模型配置、提示词、生成耗时、fallback 原因、业务动作埋点。
  - 陪伴相关状态（关系阶段、记忆触发结果）在不破坏主链路的前提下增量扩展。

## 5. 分阶段开发路线图

## 5.1 Phase 0 - 基线冻结与契约冻结

- 目标：
  - 明确 iMate V2 的跨端契约 baseline 和变更流程。
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
  - 保持 HTTP fallback 可切换。
- Backend：
  - 稳定 `/chat/ws` 与 `/chat/ws/verify`。
  - 将聊天流程统一复用 `agent_chat_completions` 主服务逻辑。
  - 落库与不落库路径分离清晰。
- 验收：
  - 同连接支持不同 `agent_id` 顺序对话。
  - 心跳与空闲断链机制可验证。
  - WebSocket 与 HTTP 两路径业务语义一致。

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
  - 统一 WebSocket 与 HTTP 语义。
  - 鉴权、错误码、断链原因保持可观测。
- Service 层：
  - 聊天主流程编排（会话获取、限额检查、模型选择、响应封装）。
  - 语音/业务动作/记忆投递作为可插拔阶段。
- Repository/Model 层：
  - 优化 chat 与 settings 查询路径，减少重复查询与竞态。
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
  - fallback 到 HTTP

## 7. 测试与验收计划

### 7.1 测试策略

- 以 feature/E2E 为主，单元测试为辅。
- 先验证主链路稳定，再扩展多模态与主动触达。
- 每阶段都包含"成功路径 + 失败路径 + 回退路径"。

### 7.2 Android 测试清单

- Room/DataStore：
  - 本地读写一致性、用户隔离、缓存失效后重读正确性。
- WebSocket：
  - debug 开关切换 WS/HTTP。
  - 多 agent 同连接会话正确路由。
  - 断线重连后不丢消息。
- UI：
  - 发送中/失败/重试状态一致。
  - 离线历史可读、恢复联网后可同步。

### 7.3 Backend 测试清单

- API 功能测试：
  - `/chat/ws`、`/chat/ws/verify`、`/chat/completions/{agent_id}` 对齐。
- service 流程测试：
  - 限额、鉴权、模型切换、业务动作、错误映射。
- 数据一致性测试：
  - chat/chat_history/chat_settings 事务行为。
  - 重试场景下幂等行为。

### 7.4 联合验收标准（DoD）

- 功能：
  - 用户可稳定完成"输入 -> AI 输出 -> 本地持久化 -> 历史回看"闭环。
- 稳定：
  - 常见弱网场景下无明显消息丢失/重复/错序。
- 可观测：
  - 能定位请求 ID、agent_id、session_id 对应链路日志。
- 可回退：
  - WS 故障时可快速切回 HTTP，不影响基础聊天可用性。

## 8. 发布与运维计划

### 8.1 灰度策略

- 阶段灰度开关：
  - `ws_chat_enabled`
  - `memory_state_enabled`
  - `proactive_touch_enabled`
- 先内部测试 -> 小流量 -> 全量发布。

### 8.2 观测指标

- 客户端指标：
  - WS 连接成功率、重连次数、消息发送失败率、回退触发率。
- 后端指标：
  - WS 活跃连接数、平均会话时长、请求耗时分位、错误码分布。
- 体验指标：
  - 首响应耗时、会话完成率、次日留存、有效对话轮次。

### 8.3 回滚预案

- 客户端：
  - 远程开关关闭 WS，立即回退 HTTP。
- 后端：
  - 路由级开关关闭 `/ws` 新能力或切换到 verify 模式。
- 数据：
  - 新增字段保持兼容，不阻断老版本读取。

## 9. 风险清单与应对

| 风险 | 描述 | 应对策略 |
|---|---|---|
| WebSocket 链路抖动 | 弱网下断链频繁导致体验不稳定 | 心跳 + 退避重连 + HTTP fallback |
| 跨端契约漂移 | Kotlin/Pydantic 字段不同步 | 双端同步 checklist + 契约评审 |
| 本地与远端状态不一致 | UI 与服务端结果短期分叉 | 以 Room 为单一可信源，网络只刷新本地 |
| 服务层膨胀 | endpoint 逻辑回流导致难维护 | 严格坚持 service 分层与 DI |
| 多能力耦合过高 | 语音/图像影响聊天主链路 | 能力插件化，主链路优先，失败隔离 |

## 10. 组织协作与里程碑产出

### 10.1 协作机制

- 每个 Phase 产出三件套：
  - 设计文档（架构与契约）
  - 实现 PR（最小可验收增量）
  - 测试证据（命令输出、日志、必要截图）
- 评审节奏：
  - 技术评审关注分层与契约。
  - 产品评审关注陪伴体验与节奏控制。

### 10.2 里程碑交付物

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

## 11. 建议的首批执行顺序（从明天即可开工）

- Step 1：冻结 v1 契约和错误码清单（1 个 PR，仅文档和 schema 对齐）。
- Step 2：打通 Android WS 主链路并保留 HTTP fallback（1-2 个 PR）。
- Step 3：完成 backend WS/HTTP 统一 service 编排与关键 feature tests（1-2 个 PR）。
- Step 4：补齐联调 checklist 与自动化回归（1 个 PR）。
- Step 5：进入陪伴状态层增量开发（后续迭代）。

---

- 结论：该计划以"复用已验证架构 + 分阶段可验收交付"为主轴，优先确保聊天主链路稳定，再逐步叠加长期陪伴智能能力，能最大化降低重构风险并提升上线成功率。
