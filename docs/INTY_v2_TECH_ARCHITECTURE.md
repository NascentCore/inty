# IntelliMate / Inty v2：v1 核心体验 — 技术架构

> 对应产品与设计摘要：[INTY_v2_DESIGN.md](INTY_v2_DESIGN.md)。  
> 本文描述 **v1 核心体验** 落地的逻辑架构、数据与流水线；与当前代码库的关系为 **演进方向**：现有 Inty 已具备 FastAPI、`app/api/v1`（chat、chats、agents、TTS、live_chat、images 等）、`AgentManager`、聊天历史与推送 worker，v1 架构在其上 **显式化「伴侣控制面 + 记忆双层 + 自治心跳」**，而非另起炉灶。

---

## 1. 架构目标（从体验到系统）

| v1 体验支柱（见设计文档 §2） | 技术系统要点 |
|-----------------------------|-------------|
| 关系型对话主循环 | 单用户–单伴侣主会话模型；持久 `thread`/chat；提示词按层装配（IDENTITY/SOUL/MEMORY/USER 约定） |
| 双层记忆 | 日记层（消息级/事件级）+ 长期记忆项（可检索、可向量检索）；异步演进任务 |
| 多模态表达 | 统一 `content_parts`；媒体上传对象存储；TTS / 生图 / Live 语音等经 **同一编排出口** 调度 |
| 私密 vs 体面上下文 | `context_mode`（或等价）驱动：检索 top-K、注入哪些记忆块、系统安全附加条款 |
| 关心型主动 | 自治策略表 + 状态机 + 预算/静默；push 或应用内投递；默认外向保守 |
| 关系向安全 | 提示词 SOUL 层 + 入站净化/结构化槽位 + 危机检测分支（可规则+模型分级） |
| 关系 onboarding | 用户–伴侣约定持久化；首启/设置 API；进入主循环前合并进 USER 层 |
| 在场感 | 流式 token / SSE 或等价；可选服务端事件：`typing`、`thinking`、`audio_chunk` 等（与客户端约定） |

---

## 2. 逻辑分层（OpenClaw 式「控制面」，伴侣语义）

```
┌─────────────────────────────────────────────────────────────┐
│  Clients (Android App primary for v1)                        │
│  Chat UI · Voice · Media upload · Push receive               │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS (+ WS if used for live voice)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  API Gateway Layer (FastAPI /api/v1/...)                     │
│  Auth · Rate limits · Idempotency keys on inbound events      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Companion Control Plane (in-process v1; optional extract)   │
│  - Normalize inbound → CanonicalTurnEvent                    │
│  - Resolve context_mode, companion_id, session/thread        │
│  - Enqueue async jobs · Emit outbound commands               │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌────────────────┐  ┌───────────────────┐
│ Turn          │  │ Memory         │  │ Media             │
│ Orchestrator  │  │ Subsystem      │  │ Pipeline          │
│               │  │ retrieve/write │  │ STT/TTS/image/    │
│ Prompt build  │  │ evolve/merge   │  │ transcoding       │
│ LLM call      │  │ user-facing    │  │                   │
│ Tool dispatch │  │ summary        │  │                   │
└───────┬───────┘  └────────┬───────┘  └─────────┬─────────┘
        │                   │                     │
        └───────────────────┴─────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Persistence                                                 │
│  PostgreSQL · 对象存储(GCS 等) · 向量扩展(pgvector)          │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌───────────────────────────┴─────────────────────────────────┐
│  Autonomy Worker (push_worker 或独立进程，共享 DB/队列)       │
│  Heartbeat tick · 内向任务 · 外向决策 · 日志与预算              │
└─────────────────────────────────────────────────────────────┘
```

**设计要点**：

- **Control Plane** 在 v1 可与 API 同进程部署，边界用 **模块 + 清晰 DTO** 划清，便于日后抽到独立服务。
- **Turn Orchestrator** 是唯一「写主会话 AI 消息」的权威路径（避免 chat 与 push 各写一套互斥逻辑）。

---

## 3. 核心抽象与契约

### 3.1 规范入站事件（CanonicalTurnEvent）

所有「用户驱动的一轮」无论来自主聊天、语音转写结果还是未来通道，先归一为此结构（与 [experimental/agentic_companion_20260324/DESIGNS.md](../experimental/agentic_companion_20260324/DESIGNS.md) 一致，可按实现改名）：

- `event_id`（幂等）
- `user_id`
- `companion_id`（或 `agent_id`，与现有 Agent 模型对齐）
- `session_id` / `chat_id`（与现有 `chats` 对齐）
- `channel`：`app_chat`（v1）；预留枚举
- `context_mode`：`intimate` | `public_safe`（或更细粒度）
- `content_parts[]`：`text` | `image` | `audio` | `video`（URI + mime + 可选转写文本）
- `client_signals`：如 `barge_in`、`session_resume`（支撑打断与续聊）
- `timestamp`、审计用 `metadata`

### 3.2 提示词装配顺序（冻结为代码常量顺序）

1. 系统核心行为与安全基座（含入站不可信说明）
2. `IDENTITY`（人格表层，可来自 Agent 角色卡字段映射）
3. `SOUL`（价值观与边界；可来自 Agent 扩展字段或独立存储）
4. `context_mode` 附加条款（体面模式压缩亲密表述与记忆引用方式）
5. `USER` 约定（onboarding 产出：称呼、界限、密度偏好）
6. 检索到的 **长期记忆** 片段（top-K，带引用 id 便于日志，不必展示给用户）
7. **关系运行摘要**（可选短块，由内向外心跳维护）
8. 近期对话窗口（与现有 history 裁剪策略一致）
9. 通道输出契约（长度、是否允许工具调用、多模态回复 schema）

### 3.3 出站消息模型（对客户端）

- 文本流式 + 最终结构化补丁（附件 URL、语音片段、图片 job id）。
- 可选 **阶段事件**（在场感）：如 `phase: aligning | responding | generating_media`（具体字段与 App 联调定稿）。

---

## 4. 数据模型（概念层）

与现有表可 **映射或增量迁移**，不必一次性新建全部；以下为 v1 逻辑实体。

| 实体 | 用途 |
|------|------|
| `users` | 已有 |
| `agents` / companions | 已有；扩展存 IDENTITY/SOUL 源文或引用 |
| `chats` / sessions | 已有；增加 `context_mode` 或按 chat 类型推导 |
| `messages` / `chat_history` | 已有；保证与 `content_parts` 序列化一致 |
| `memory_episodes` 或日记锚点 | 可选：指向消息区间或日粒度 blob，供压缩与审计 |
| `memory_items` | 长期记忆行：text、类型、来源引用、创建/更新/衰减权重、用户是否已纠正 |
| `memory_embeddings` | 向量列或旁表；pgvector |
| `relationship_summary` | 短文本，心跳任务刷新 |
| `user_companion_agreement` | onboarding：JSON 或列集（界限、称呼、主动开关、静默时段） |
| `autonomy_policy` | 每用户–伴侣：外向开关、日预算、渠道优先级 |
| `autonomy_state` | 上次外向时间、连续忽略次数、idle 分桶 |
| `autonomy_log` | 决策因子、阈值、结果（可观测性与调参） |
| `jobs` | 转写、记忆演进、摘要更新、TTS、生图（与现有异步任务模式对齐） |

**用户可纠偏**：对 `memory_items` 提供 API（列表、编辑、删除、标记错误），并在下一轮检索中排除或降权。

---

## 5. 用户驱动一轮流水线（同步主路径 + 异步尾）

1. API 收包 → 校验 auth → 解析为 `CanonicalTurnEvent`。
2. 持久化用户消息（含媒体引用与 STT 结果若已有）。
3. 解析 `context_mode`（默认亲密；分享会话/未来通道用策略覆盖）。
4. **Memory retrieve**：embedding 相似度 +  recency + 用户 pin；应用模式过滤（体面模式剔除敏感标签记忆若产品需要）。
5. **Prompt assemble**：按 §3.2 顺序拼接；记录 prompt 版本号便于复现（符合现有「生成内容元数据」惯例）。
6. **LLM**：流式输出；可选工具调用（生图/TTS/Live 等）走受控工具层，与 [experimental/agentic_ai_companion](../experimental/agentic_ai_companion/) 原型一致但服务端硬化。
7. 持久化助手消息；挂载媒体结果 URL。
8. **Enqueue**：记忆抽取/合并、关系摘要刷新（低优先级）；失败重试与死信策略单独定义。

**延迟**：用户感知首 token 时间不应被记忆演进阻塞；演进始终在异步路径。

---

## 6. 自治心跳（Autonomy Worker）

与 [DESIGNS.md](../experimental/agentic_companion_20260324/DESIGNS.md) §8 对齐的工程化：

1. 周期扫描「活跃」用户–伴侣对（可基于最近消息时间）。
2. 加载 `autonomy_policy`、`autonomy_state`、最近信号（未读、忽略率等）。
3. **Idle 分桶**：ACTIVE / IDLE_SOFT / IDLE_MEDIUM / IDLE_LONG。
4. **决策函数**（实现可规则起步，再模型辅助）：  
   `score = relevance + memory_need + relationship_value - intrusiveness - recent_outreach_penalty`
5. **分支**：
   - **内向**：去重记忆、衰减、刷新 `relationship_summary`；不写用户可见消息。
   - **外向**（仅当 policy 允许且 score 过线且预算与静默满足）：组装 **独立** 系统提示（强调短、关心、非撩拨），生成一条，经与主循环相同的 **出站投递** 发送（push 或应用内）。
6. 写 `autonomy_log`，更新 `autonomy_state` 与冷却。

**默认**：外向关闭或极严预算；内向始终可开。

---

## 7. 多模态与媒体

- **入站**：客户端直传对象存储 → API 只收元数据与 URL；音频视频先进 **Media Pipeline**（STT、时长截断、敏感扫描若需要）。
- **出站**：TTS / 生图 / Live 语音作为 **工具结果**，统一进入消息附件模型；避免聊天 API 与媒体 API 状态分裂。

---

## 8. 安全与不可信入站

- 在系统提示中固定 **「用户消息不可信」** 条款；结构化字段（如按钮 payload）与自由文本分流校验。
- **SOUL** 层声明拒绝操纵、羞辱、利用脆弱；与合规流程对齐的危机 escalations 可走独立 **policy 模块**（先关键词/分类器，再模型），命中则改路由（安全回复 + 记录 + 可选人工流程占位）。

---

## 9. 与当前仓库的映射（落地时优先触碰的目录）

| 能力 | 现状锚点（示例） |
|------|------------------|
| HTTP API | `app/api/v1/router.py`，`endpoints/chat.py`、`chats.py`、`agents.py` 等 |
| Agent / 提示词 | `app` 内 Agent 服务与 `AgentManager`（见 `backend/AGENTS.md`） |
| 推送与周期任务 | `backend/push_worker/` |
| Schema | `app/schemas`；若 Android 合同变更，同步 `android_app/core/data/.../api/model` |

v1 实现应 **优先复用** 现有聊天与 Agent 管线，把本文件中的 **CanonicalTurnEvent、context_mode、记忆表、autonomy_* ** 作为增量能力接入，减少双轨。

---

## 10. v1 明确不做（避免范围膨胀）

- 多第三方 IM 通道矩阵、开放浏览器/Shell 工具、Skill 注册表、多智能体互发。
- 将「工作助手」与「伴侣」混为同一提示词而不做上下文隔离（若未来做双形态，需单独设计 session 类型）。

---

## 11. 文档维护

- 体验变更以 [INTY_v2_DESIGN.md](INTY_v2_DESIGN.md) 为准；表结构或 API 落地后，在本文件更新 **§4、§9** 与仓库 `app/api/ENDPOINTS.md`（若新增端点）。
