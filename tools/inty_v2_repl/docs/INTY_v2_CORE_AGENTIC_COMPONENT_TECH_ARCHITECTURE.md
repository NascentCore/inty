# IntelliMate / Inty v2：核心 Agentic 组件 — 技术架构

> 对应产品与设计摘要：[INTY_v2_DESIGN.md](INTY_v2_DESIGN.md)。  
> **实现优先级**：文档前部描述 **仅核心 text chat** 的落地架构（用户文本入、流式文本出、会话持久化、提示词编排、与现有 Inty 管线对齐）。多模态、外向自治、完整记忆向量等放在 **后部扩展章节**，避免实现阶段范围膨胀。

---

## 1. 代码库技术选型（与仓库一致）

以下为当前主后端依赖与惯例（见仓库根目录 `requirements.txt`、`app/`、`backend/inty/`）；**核心 text chat 实现应优先使用这些组件**，不引入平行技术栈。

| 层次 | 选型 | 说明 |
|------|------|------|
| HTTP API | **FastAPI**（Starlette / Uvicorn） | `backend/inty/main.py` 挂载 `app/api/v1/router.py` |
| 请求/响应与配置 | **Pydantic**、**pydantic-settings** | `app/schemas` 与跨边界 DTO；配置与 [AGENTS.md](/AGENTS.md) 约定一致 |
| 关系型数据 | **SQLAlchemy 2.x**、**PostgreSQL** | `app/models`（或等价模块）与现有 `chats` / `chat_history` 等 |
| 迁移 | **Alembic** | 表结构变更走 alembic revision（见仓库根 `AGENTS.md` Alembic 节） |
| 向量检索（扩展） | **pgvector**（Python 侧 `pgvector` 包） | 仅在有长期记忆语义检索时启用，非 text chat 最小集必需 |
| CLI（运维/Worker/脚本） | **Cyclopts** | 仓库约定用 Cyclopts 做显式 `main.py` 入口 CLI；**不等同于** REST 路由层 |
| 异步与驱动 | **asyncpg** / **psycopg** 等 | 与现有会话、连接池用法保持一致 |
| 日志 | **loguru** 等（以现有模块为准） | 结构化字段见下文扩展章「可观测性」 |

**说明**：Android 与 HTTP API 共享的 JSON 合同变更时，仍需同步 **Kotlin API model** 与 **`app/schemas`**（仓库总 [AGENTS.md](/AGENTS.md) 约定）。

---

## 2. 核心 text chat：目标与边界

| 项 | 内容 |
|----|------|
| **范围** | 单轮/多轮 **纯文本** 对话；服务端 **流式输出** token（或等价 chunk）；消息 **落库** 到现有会话模型 |
| **会话模型** | 每个 `(user_id, companion_id)` 对应既有 **`chat_id` / thread**；不新增「每请求新建会话」的默认行为 |
| **编排** | 入站归一 → 鉴权 →（可选）幂等 → 写用户消息 → 拉取历史 → 装配系统提示（含 Agent/用户侧字段）→ 调 LLM → 流式返回并 **落库助手消息** |
| **显式不包含（属扩展）** | 图片/音频/视频、TTS、Live WebSocket、工具调用链、外向 push、pgvector 检索、独立 Media Pipeline |

---

## 3. 核心 text chat：逻辑分层（最小图）

```
Android App (text in / stream text out)
        │ HTTPS
        ▼
┌───────────────────────────────────────┐
│  FastAPI /api/v1/ …                   │
│  Auth · Rate limits · body → DTO      │
└───────────────────┬───────────────────┘
                    ▼
┌───────────────────────────────────────┐
│  Companion Control Plane（进程内模块）   │
│  Normalize → TextTurnInput            │
│  Resolve chat_id, agent_id, user_id │
└───────────────────┬───────────────────┘
                    ▼
┌───────────────────────────────────────┐
│  Text Turn Orchestrator               │
│  Persist user message                 │
│  Load history · Assemble prompt       │
│  LLM stream · Persist assistant msg   │
└───────────────────┬───────────────────┘
                    ▼
┌───────────────────────────────────────┐
│  PostgreSQL（SQLAlchemy）              │
│  chats · chat_history / messages · …  │
└───────────────────────────────────────┘
```

**要点**：助手消息 **唯一** 经 Orchestrator（或与现有 `chat` 端点等价路径）写入，避免重复实现写库逻辑。

---

## 4. 核心 text chat：契约（Pydantic）

### 4.1 入站（概念字段）

与完整版 `CanonicalTurnEvent` 对齐思路，但 **text chat 最小实现** 只需：

- `event_id`：可选；若要做幂等，建议 ULID/UUID（仓库已有 `python-ulid`），与 `user_id` + `chat_id` 联合唯一
- `user_id`、`chat_id`、`companion_id` / `agent_id`
- `text`：用户本轮纯文本
- `context_mode`：若短期未建表，可从 chat 类型或默认 `intimate` 推导

**幂等**：在 `chat_history`（或侧表）对 `(user_id, chat_id, event_id)` 唯一约束；重复 `event_id` **短路** 返回已生成结果，不重复调用 LLM。

### 4.2 提示词装配顺序（text chat）

与全文版一致的前缀（见 **§10.2**），但第 9 步「通道输出契约」在 text chat 下退化为：**仅文本、长度与风格约束**，无多模态 schema、无工具列表。

### 4.3 出站

- **流式**：HTTP 下采用当前 chat 端点已有模式（如 SSE/streaming JSON chunk），与 App 合同对齐
- **最终**：助手文本持久化；可选返回 `message_id` / 游标供客户端去重

---

## 5. 核心 text chat：数据与 ORM

最小集 **直接复用** 现有表（名称以代码为准）：

| 用途 | 说明 |
|------|------|
| `users` | 已有 |
| `agents` | companion 配置、角色卡字段 → 映射 IDENTITY/SOUL 来源 |
| `chats` | 会话元数据；未来可加 `context_mode` |
| `messages` / `chat_history` | 用户/助手文本轮次 |

新增列或表（幂等键、记忆项等）一律 **Alembic** 迁移 + SQLAlchemy model 更新。

---

## 6. 核心 text chat：一轮流水线

1. FastAPI 收请求 → **Pydantic** 校验 → 注入 `user_id`（auth）。
2. 归一为 **TextTurnInput**（内部 DTO）。
3. 若带 `event_id`：检查唯一约束 → 已处理则返回缓存结果。
4. **SQLAlchemy** 事务内写入用户消息。
5. 读取最近历史窗口（与现有 `PostgresChatMessageHistory` / 裁剪策略一致）。
6. 装配 prompt（**AgentManager** 或现有 Agent 服务；顺序见 §4.2 / §10.2）。
7. 调用 LLM **流式**生成；边生成边下发客户端。
8. 流结束 → 写入助手消息 → 提交事务。
9. **扩展**：记忆抽取、摘要等异步任务不在此路径阻塞（见 §11）。

**延迟**：首 token 前不做重检索或向量检索（text chat 最小集）。

---

## 7. 核心 text chat：代码落点

| 项 | 仓库锚点 |
|----|----------|
| 路由注册 | `app/api/v1/router.py` |
| 聊天入口 | `app/api/v1/endpoints/chat.py`（及关联 service） |
| 会话 CRUD | `app/api/v1/endpoints/chats.py` |
| Agent / 提示词 / LLM | `AgentManager` 与相关 `app` 服务（见 `backend/AGENTS.md`） |
| Schema | `app/schemas` |
| Model | `app/models`（或项目中等价目录） |

---

# 扩展章节（在核心 text chat 稳定后迭代）

以下对应 [INTY_v2_DESIGN.md](INTY_v2_DESIGN.md) 全文体验与 [experimental/agentic_companion_20260324/DESIGNS.md](../experimental/agentic_companion_20260324/DESIGNS.md)；**不阻塞** text chat 最小闭环。

---

## 8. 完整体验：架构目标对照

| v1 体验支柱（设计文档 §2） | 技术系统要点 |
|-----------------------------|-------------|
| 关系型对话主循环 | 每个 `(user_id, companion_id)` 一条主关系会话；持久 thread；提示词按层装配 |
| 双层记忆 | 日记层 + 长期记忆项；向量检索；异步演进 |
| 多模态表达 | `content_parts`；对象存储；TTS / 生图 / Live 经同一编排出口 |
| 私密 vs 体面上下文 | `context_mode` 驱动检索与注入策略 |
| 关心型主动 | 自治策略 + 状态机 + 预算/静默；push / 应用内 |
| 关系向安全 | SOUL + 不可信入站 + 危机分支 |
| 关系 onboarding | 用户–伴侣约定持久化；合并进 USER 层 |
| 在场感 | 流式 + 可选 `typing` / `thinking` / 媒体阶段事件 |

---

## 9. 完整逻辑分层（含多模态与自治）

```
┌─────────────────────────────────────────────────────────────┐
│  Clients (Android App primary)                               │
│  Chat UI · Voice · Media upload · Push receive               │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS (+ WS if used for live voice)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  API Gateway Layer (FastAPI /api/v1/...)                     │
│  Auth · Rate limits · 入站幂等（event_id）                     │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Companion Control Plane (in-process; optional extract)      │
│  Normalize → CanonicalTurnEvent · context_mode · enqueue jobs  │
└───────────────────────────┬─────────────────────────────────┘
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌────────────────┐  ┌───────────────────┐
│ Turn          │  │ Memory         │  │ Media             │
│ Orchestrator  │  │ Subsystem      │  │ Pipeline          │
│ Prompt · LLM  │  │ retrieve/evolve│  │ STT/TTS/image     │
│ Tool dispatch │  │ summary        │  │                   │
└───────┬───────┘  └────────┬───────┘  └─────────┬─────────┘
        └───────────────────┴─────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PostgreSQL · GCS 等 · pgvector                              │
└─────────────────────────────────────────────────────────────┘
                            ▲
┌───────────────────────────┴─────────────────────────────────┐
│  Autonomy Worker (push_worker 或独立进程)                     │
└─────────────────────────────────────────────────────────────┘
```

**设计要点**：外向主动生成后须与 **核心 text chat 相同** 的 `append_assistant_message`（或等价）写入历史，再 push；外向 **日/小时预算** 与 `autonomy_policy` 对齐。

---

## 10. 完整核心抽象与契约

### 10.1 规范入站事件（CanonicalTurnEvent）

与 [DESIGNS.md](../experimental/agentic_companion_20260324/DESIGNS.md) 一致的全量字段：`content_parts[]`（text/image/audio/video）、`client_signals`、`channel` 枚举等；**text chat 最小集** 为其真子集（§4）。

**幂等**：全量实现时对 `event_id` 持久层唯一约束 + 短路（同 §4.1）。

### 10.2 提示词装配顺序（冻结为代码常量顺序）

1. 系统核心行为与安全基座（含入站不可信说明）
2. `IDENTITY`
3. `SOUL`
4. `context_mode` 附加条款
5. `USER` 约定（onboarding）
6. 检索到的长期记忆片段（top-K）
7. 关系运行摘要（可选）
8. 近期对话窗口
9. 通道输出契约（多模态 schema、工具开关）

### 10.3 出站消息模型（多模态）

文本流式 + 附件 URL / job id；可选阶段事件（在场感）。

---

## 11. 扩展数据模型

在 §5 最小表基础上可增加：

| 实体 | 用途 |
|------|------|
| `memory_episodes` / 日记锚点 | 压缩与审计 |
| `memory_items` | 长期记忆 + **敏感度/标签**（`public_safe` 过滤） |
| `memory_embeddings` | pgvector |
| `relationship_summary` | 心跳刷新 |
| `user_companion_agreement` | onboarding |
| `autonomy_policy` / `autonomy_state` / `autonomy_log` | 自治 |
| `jobs` | 转写、记忆演进、TTS、生图；宜与 **`push_worker` 周期/DB 拉取** 对齐；重试与死信单独立规 |

用户纠偏 API：对 `memory_items` 列表/编辑/删除/降权。

---

## 12. 用户驱动全量流水线（同步 + 异步尾）

1. API → `CanonicalTurnEvent`。
2. 持久化用户消息（含媒体引用与 STT 若已有）。
3. `context_mode` → Memory retrieve（embedding + recency + pin；敏感标签过滤）。
4. Prompt assemble（§10.2）；记录 `prompt_version`。
5. LLM 流式 + **工具适配器**（生图/TTS/Live）→ 适配器调用 **Media Pipeline**，不在 Pipeline 内拼 prompt。
6. 持久化助手消息与附件。
7. **Enqueue** 记忆演进、摘要；失败重试见 §11 `jobs`。

**可观测性（请求路径）**：`request_id`、`event_id`、`prompt_version`、`context_mode`、`memory_item_ids` 等。

---

## 13. 自治心跳（Autonomy Worker）

周期扫描 → idle 分桶 → score 决策 → 内向（记忆整理/摘要）或外向（先 **写 chat_history** 再 push）→ `autonomy_log`。**默认** 外向关闭或极严预算。

---

## 14. 多模态与媒体

入站直传对象存储 → Media Pipeline（STT、截断等）；出站工具结果进消息附件；`live_chat` WebSocket 与 HTTP 共享会话/记忆策略（`endpoints/live_chat.py`）。

---

## 15. 安全与不可信入站

系统提示声明用户消息不可信；SOUL + policy 模块处理危机场景（规则/模型分级）。

---

## 16. 仓库映射（扩展能力）

| 能力 | 锚点 |
|------|------|
| HTTP API | `app/api/v1/router.py`，`chat.py`、`chats.py`、`agents.py` |
| Live / WS | `endpoints/live_chat.py` |
| Agent | `AgentManager`，`backend/AGENTS.md` |
| 周期任务 | `backend/push_worker/` |
| Schema / Android | `app/schemas` · `android_app/core/data/.../api/model` |

---

## 17. 明确不做（全产品级）

多第三方 IM、开放浏览器/Shell、Skill 市场、多智能体互发；工作助手与伴侣混用同一提示词且无 session 隔离。

---

## 18. 可观测性（汇总）

| 维度 | 内容 |
|------|------|
| 请求路径 | `request_id`、`event_id`、`prompt_version`、`context_mode`、`chat_id`、`memory_item_ids` |
| 自治 | `autonomy_log`；外向次数与冷却指标 |

---

## 19. 文档维护

- 体验变更以 [INTY_v2_DESIGN.md](INTY_v2_DESIGN.md) 为准。
- **核心 text chat**：更新 §1–§7 与 `app/api/ENDPOINTS.md`（若增端点）。
- **扩展能力**：同步 §8–§20 与 Alembic/model 变更。
- 若涉及记忆分层、巩固节拍、注入策略或“脑启发式多层总结器”方案，需同步更新 [researches/brain_inspired_memory_summarizer/FR_BRAIN_INSPIRED_MEMORY_LAYER_SUMMARIZER.md](../../../researches/brain_inspired_memory_summarizer/FR_BRAIN_INSPIRED_MEMORY_LAYER_SUMMARIZER.md)。

---

## 20. 参考架构（外部门户）

本节记录从 **其他 agent 类系统**（例如本地 Gateway + 多通道控制面类实现）抽象出的 **工程约束**，**不改变** §1 技术选型（FastAPI / PostgreSQL / SQLAlchemy 等）。用于在扩展 §8–§18 能力时避免「HTTP 一套、Worker 一套」的分叉实现。

### 20.1 单一控制面与会话写入

- **不变量**：助手侧对用户可见的文本（及未来多模态结果）应 **只经一条业务路径** 落库（与 §3、§6「Orchestrator 唯一写助手消息」一致）。
- **含义**：HTTP 聊天、未来 **Push / Autonomy Worker / 异步 job** 触发的回复，最终都应调用 **同一** `append_assistant_message`（或当前仓库等价抽象），而不是在各自模块里直接写 `messages` / `chat_history`。

### 20.2 非 HTTP 路径也要携带「控制面上下文」

- 当入站不经过 `/api/v1/...`（例如周期任务、内部队列）时，仍须解析并传递与线上一致的 **`user_id`、`chat_id`、`companion_id` / `agent_id`、`context_mode`**（及未来 `CanonicalTurnEvent` 的归一字段）。
- **目的**：避免「后台生成」与「用户当前会话」在记忆检索、提示词层、安全策略上 **脱节**。

### 20.3 幂等与同会话顺序

- **幂等**：与 §4.1、`event_id` 一致——对 **可能重试的副作用**（写用户消息、触发 LLM、写助手消息）在设计上区分：**用户轮次** 用 `event_id` 短路；内部触发可另设 `job_id` / `dedupe_key`，但 **不重复扣费、不重复对用户展示同一条助手消息**。
- **顺序**：若同一 `chat_id` 上可能 **并发**（用户正在聊 + push 插入），宜约定 **per-chat 串行**（队列或锁）或明确产品语义（例如「后到达者覆盖/丢弃」），并在 §6 流水线中写清。

### 20.4 编排分层（外层 vs LLM+工具）

- **外层（Orchestrator / Control Plane）**：鉴权、事务、历史加载、提示词装配（§10.2）、流式落库、重试与降级、记忆/job 入队、可观测性字段（§18）。
- **内层（单次模型调用）**：流式 token、可选 **工具调用循环**；工具适配器只通过 **明确接口** 调 Media / 外部 API，**不在** Pipeline 内拼系统提示词（与 §12 一致）。
- **目的**：换模型、加工具、加 failover 时 **少改事务与存储路径**。

### 20.5 工具列表：合并 → 策略过滤 → schema 适配

- 扩展 §12 时，建议 **先合并** 全部工具定义，再按 **会话/策略/提供商** 做过滤，再做多模型 **参数 schema 清洗**（避免每个工具分散 if/else）。
- 与 §17 边界一致：**不**因参考外部门户而引入浏览器/Shell/第三方 IM 等范围外能力。

### 20.6 Hook 与契约漂移

- **Hook**：记忆注入、审计、实验开关等优先挂在 **编排前后**（例如 `before_prompt`、`after_turn`），而非散落在 LLM 封装内部，便于测试与开关。
- **契约**：Android / Pydantic / 文档 **单一事实来源**（与 §1、§16 及仓库 AGENTS.md 约定一致），避免手写多份 JSON 合同。

### 20.7 与「明确不做」的关系

- §17 所列 **不做** 的产品能力（多第三方 IM、开放浏览器与 Skill 市场等）**不因本节参考而放宽**；本节仅借用其 **控制面与编排** 的工程经验。
