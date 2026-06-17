# Companion Harness: 架构说明

## 概要（Executive Summary）

Companion Harness 一套完整的智能体框架，由 LLM 驱动：1 人 1 Inty，长期关系，体感上要像”活人“，而不是用完即弃的任务 Bot；是 Inty 理念和愿景的核心载体。

Companion Harness + LLM = Inty（陪伴智能体）；Inty + Memory = Personal Companion

大模型会说话，但不会**记得你、惦记你、在你沉默时仍过自己的日子（分享给你）**。
Harness 干的就是这件事：把 LLM 放进一套有节律、有记忆、有副作用的状态机里，让「聊天」变成「关系」。

Harness 要的是：**一段会延续的关系**——你不在时她也在虚拟空间生活，回来时还能接上，换 App 或微信还是同一个人。
我们认为 AI 突破现有局限成为长期伴侣的关键是：长期自主性，也就是产生用户预期以外的反馈；但这些行为和反馈始终以用户伴侣的视角呈现。

自主性体现在：

- Autonomy: agents have their own autonomous activities to build up their own identity and novelty.
- App、微信、Telegram, users can interact with agents through channels used by humans, all are consistent.

### 现状

以上是**目标态的理想设计**，不是现状清单。`companion_harness` 目前仍处于 **PROTOTYPE** 状态。

下文 **「实现对照（Prototype）」** 记录当前代码与目标图的差异；审阅架构时以该节 + 源码为准。

> **文档入口**：本文件即 companion harness 的 canonical 架构说明。历史链接 `ARCH.md` 重定向至此。

## 重要下一步工作

Only reference Epic GitHub issues. Do not include details.
State of the Epic GitHub issues are in the GitHub issues themselves.

### Telegram production integration

Epic [#3395](https://github.com/nascentcore/inty/issues/3395) — Telegram × Bots API 接入路径（Option A / B + channel tools）

### Companion Relationship System (CRS)

Epic [#3341](https://github.com/nascentcore/inty/issues/3341) — psychology × time frames × harness (SDCM: Attachment + Gottman moment + Social Penetration depth).

### 将智能体运行环境收束成可移植可迁移的组件

- [ ] 用于支持 autonomous companion，可以在用户不在线时持续运行，同时可以暂停和重启（如 token 预算不足时）— Epic [#3373](https://github.com/NascentCore/inty/issues/3373)

### 推理编排显式化（参考 [Pie](https://pie-project.org/) 研究）

Epic [#3393](https://github.com/nascentcore/inty/issues/3393) — turn program spec × prompt_stack stable/volatile seam × tool_background scratch working memory.

### 更稳固健壮的异步多层级任务执行系统

Epic [#3394](https://github.com/nascentcore/inty/issues/3394) — sub-tasks & sub-agents, fan-in / fan-out, async & parallel execution.

## 目标态

Companion Harness 的目标是为用户提供长期关系中的“虚拟活人”体验。后端内核必须提供长期实践中的关系演化机制，并在其框架内系统性添加次一级机制来支持个人陪伴。

### Concepts & naming

- agentic companion: the thing user interact with to form companionship with,
  it's an abstract union of various static and runtime data and mechanisms,
  including agentic loops, memory, llms, programed loops like inner-tick, etc.
  This concept is by nature vague at this point, as we are still evolving its design.
  - inner-tick: a programmed loop where the agentic companion periodically wakes up and use llm to perform
    some work.
- agentic loop: multi-turn reasoning with llm(s), multiple agentic loops forms the central mind model for
  simulating the thoughts and actions of an agentic companion. Agentic loop emits user-visible messages,
  and non-user-visible data for later process and eventually influences the later steps of generating
  user-visible messages (monolog & autonomy etc.).
- channel: abstract the medium through witch the user interact with the agentic companion.
  Right now we have the following channels:
  - Weixin/WeChat (IM)
  - Telegram (IM)
  - App (WebSocket)
- input & output queue: for buffering messages between user and agent.
- Interaction patterns:
  - proactive: proactively poking user from agent, a user-visible behavior pattern

## 目标架构图

```
                    ┌──────────────────────────────────────┐
                    │  Users side                          │
                    └───────────────────┬──────────────────┘
                                        │
                    ┌───────────────────▼──────────────────┐
                    │  Channel layer (Exo─runtime)         │
                    │  Realtime channel  │  IM channel     │
                    │  iMate App · REPL · WeChat · Telegram│
                    └───────────────────┬──────────────────┘
                                        │
                    ┌───────────────────▼──────────────────┐
                    │  Governance (minimal in prototype)   │
                    │  auth · usage · visible history ·    │
                    │  protocol adaptation                 │
                    └───────────────────┬──────────────────┘
                                        │
                    ┌───────────────────▼──────────────────┐
                    │        InputQueue & OutputQueue      │
                    └───────────────────┬──────────────────┘
                                        │
                    ┌───────────────────▼──────────────────┐   ┌────────────────────────────────────────┐
                    │  Companion Harness kernel            │◄─►│  Techno Core shared virtual world      │
                    │  relationship · memory · turns ·     │   │  ┌──────────────────────────────────┐  │
                    │  tools                               │   │  │ Living Sphere                    │  │
                    └───────────────────┬──────────────────┘   │  │ personal living space            │  │
                                        │                      │  └──────────────────────────────────┘  │
                                        │                      └────────────────────────────────────────┘
                    ┌───────────────────▼─────────────────┐
                    │  Persistence                        │
                    │  long─term memory & dialogue trace  │
                    │  Database, GCS for media data       │
                    └─────────────────────────────────────┘
```

### Harness 内核（职责展开）

```
┌─ Entry & orchestration ─────────────────────────────────────────────────┐
│  inbound events · session mgmt  ──►  track routing · turn orchestration │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─ Awake turns ───────────────────────────────────────────────────────────┐
│  turn programs  ──►  prompt assembly  ──►  LLM call  ──►  llm client    │
│  chat · greeting · proactive · autonomy · maintenance (monolog)         │
│  stable persona + volatile recent context                               │
└───┬────────────────────┬────────────────────┬───────────────────────────┘
    │                    │                    │
    ▼                    ▼                    ▼
 memory store ◄──── async tool execution   tool registry
    ▲                    │
    │                    │
    └──── Dreaming (end─of─day memory consolidation)

 inner tick (proactive · scheduled · autonomy · maintenance) ──► triggers turn programs
```

目标图中 **InputQueue & OutputQueue** 与 **Governance** 层在 prototype 中仅为部分落地（见下「传输路径」）。

## 实现对照（Prototype）

本节对齐 `app/core/companion_harness/` 与 `app/services/agentic_companion/` 的**当前行为**；目标态上文不变。

### Harness 包结构

`app/core/companion_harness/` 按职责分包（DESIGN 目标图未逐一列出）：

- `companion/` — turn 内核（`turn.py` → `_run_companion_turn_core`）、prompt 栈、WS `Coordinator`、inner-tick 调度常量
- `memory/` — MemoryStore、dreaming consolidation、transcript compaction
- `tools/` — tool registry、`tool_background` 异步工具线程
- `llm/`、`providers/` — OpenAI-compatible 调用与供应商适配
- `prompting/`、`experience_profile/` — `PromptBundle`、context mode / directives
- `runtime/` — `inner_tick_fire`、`dreaming_batch` 编排入口（harness 侧）
- `loop/` — **sidecar**：可互换 agentic loop 机制（`run_agentic_loop`）；**尚未**接入生产 `run_turn`（[#3369](https://github.com/NascentCore/inty/issues/3369)）
- `agentic_companion/` — Postgres `InputQueue` / `OutputQueue` 类型与 `AgenticCompanion`（agent-channel 路径，非主 WS）
- `agent_channel/` — `AgentScope`、guest agent kind

**服务层胶水**（transport，不在 harness 包内）：

- `app/services/agentic_companion/` — `session.Coordinator`、presence / scope inner-tick poll、downlink 泵
- `app/api/v1/endpoints/chat_ws.py` — WebSocket 上行入口
- `app/services/companion_chat_service.py` — HTTP/WS 对 harness 的 `run_companion_*` 门面

### 传输路径

两条并存路径，勿与目标图中央队列混为一谈：

- **生产 WebSocket / 微信（主路径）**
  - 上行：连接内联处理，不经 Postgres InputQueue
  - 下行：`Coordinator` + 进程内 `outbound_queue`（业务 outbound 队列，见 [GLOSSARY.md](./GLOSSARY.md)）
  - inner-tick：`inner_tick_poll`（需 signed-on presence）+ `scope_inner_tick_poll`（scope worker，无需在线）
- **Agent-channel（实验 / 服务路径）**
  - `agentic_companion/postgres_queue.py`：`InputQueue` drain → `run_agent_turn` → 可选 `OutputQueue`
  - **不**经过 `loop/agentic_loop.run_agentic_loop`；docstring 中 “AgenticLoop” 为目标态措辞

Governance（鉴权、订阅、用量）在 prototype 中最小化：inner-tick 路径可跳过 `subscription_service`；计费留在 `chat_ws` 用户轮。

### 双 LLM / tool_background

有工具的用户轮（及 maintenance / autonomy inner-tick）走 **foreground chat + background tool**：

- `TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL`（`turn_routes.py`）：前台定主回复，**不 await** `tool_background`
- maintenance / autonomy：**跳过** foreground envelope，直接进入 `tool_background`（`force_tools_first_round`）
- proactive / scheduled：**无工具**（`prompt_stack.companion_tools_for_turn` 对 proactive 返回 `[]`），单轮 `INNER_TICK_SYNC` 或 `CHAT_ONLY_SYNC`

详见 [GLOSSARY.md](./GLOSSARY.md) 前台/后台术语；Epic [#3393](https://github.com/nascentcore/inty/issues/3393) 规划 turn program 显式化。

### Inner-tick 双 poll 架构

目标态为单一 poll 链；**实现已拆为两条 loop**（[#3255](https://github.com/NascentCore/inty/issues/3255)）：

- **Presence poll**（`app/services/agentic_companion/inner_tick_poll.py`）：绑定 signed-on `Coordinator`；每 wake **至多一个**：`proactive → scheduled`
- **Scope worker poll**（`scope_inner_tick_poll.py`）：按 `(user_id, agent_id, chat_id)` scope 扫描；每 wake **至多一个**：`maintenance → autonomy → dreaming`

因此 **AUTONOMY 在 scope worker 中排在 MAINTENANCE 之后**（与旧 unified 文档顺序不同）。Dreaming 仅在 scope worker 触发，且为 **memory batch**（`run_dreaming_batch_for_session`），不产生 `CompanionTurnResult`。

Poll 周期（可配置，非 rhythm 本身）：

- WS：`companion_ws_proactive_chat_poll_seconds`（默认 60s）
- REPL：`INTY_V2_PROTO_INNER_TICK_SEC`（默认 90s，`inner_tick_schedule.py`）

Proactive **rhythm**（两次 proactive 尝试间隔）锚定 `transcript.jsonl` 最后 assistant `ts`，由 `proactive_chat.py` / `companion_ws_proactive_chat_base_idle_seconds`（默认 30s）驱动——与 worker poll 周期独立。

### Agentic loop（sidecar）

`loop/` 提供 `run_agentic_loop` + `one_llm` / `two_llm` mechanism 与 parity 测试；生产 spine 仍为 `companion/turn.py` 内 `_run_companion_turn_core`。收敛计划见 `docs/companion_harness/agentic_loop_lessons.md` 与 [#3369](https://github.com/NascentCore/inty/issues/3369)。

注意区分三种 “queue”：

- 业务 **outbound 队列**（WS 下行泵）
- `loop/output_queue.AgenticLoopOutputQueue`（单次 loop 流式输出）
- Postgres **OutputQueue**（agent-channel 持久化下行）

## 记忆模型

当前 companion 的「世界」主要由 MemoryStore 中的一组版本化 markdown 文档、transcript 和工具副作用构成，**还不是独立 world engine**（目标态见 [FR_WORLD_ENGINE.md](./FR_WORLD_ENGINE.md)）。

- `*.md` refer to semantic content
- `*.jsonl` refer to episodic content

TODO(memory-hierarchy-design): Design conceptual & logical memory hierarchy; replace `*.md` / `*.jsonl` stub below after !3405 closes (conversation options are candidates, not the spec).

## Turn 轨道：用户与智能体交互及慢周期后台数据处理支持 (Runtime Loops)

每个 `CompanionTurnTrack`（`companion/models.py`）对应一个 harness 入口（`run_companion_*_turn` / `run_inner_tick_autonomy`），最终汇入 `_run_companion_turn_core`（`turn.py`）；日志与 LangSmith 仍常写 `run_turn`。

`InnerTickActivity`（`MAINTENANCE` | `PROACTIVE_CHAT` | `AUTONOMY` | `DREAMING`）是 **poll / 路由轴**，与 `CompanionTurnTrack` **不是** 1:1：`INNER_TICK_SCHEDULED` 映射为 `InnerTickActivity.PROACTIVE_CHAT`（`turn_track.py`）；`DREAMING` 仅为 batch，从不出现在 turn result 上。

计划重命名：`INNER_TICK_MAINTENANCE` / `InnerTickActivity.MAINTENANCE` → `MONOLOG`（[#3400](https://github.com/NascentCore/inty/issues/3400)）。

- **`USER_CHAT` / `USER_CHAT_BOOTSTRAP`**
  - 触发：用户消息
  - 用户可见：是
  - 工具：全开（foreground + `tool_background`）
- **`IMPLICIT_SIGN_ON_GREETING`**
  - 触发：`user_signed_on` implicit signal
  - 用户可见：是
  - 工具：无
- **`INNER_TICK_PROACTIVE_CHAT`**
  - 触发：presence poll（idle rhythm 满足）
  - 用户可见：是（主动心跳）
  - 工具：无（chat-only）；可读 `LIFE_CURRENTS.md` hint
- **`INNER_TICK_SCHEDULED`**
  - 触发：presence poll + `schedule_queue` 到期
  - 用户可见：是（到期提醒文案由单轮 LLM 生成，非开放 tool loop）
  - transcript 行带 `scheduled: true`；`inner_tick_activity` 元数据可为 `proactive_chat`
- **`INNER_TICK_MAINTENANCE`** (monolog)
  - 触发：scope worker poll
  - 用户可见：否（prompt 契约 + scope 路径无 WS 下行；`ai_private_append` 写 `ai_private.jsonl`）
  - 工具：受限 inner-tick 集（`ai_private_append` 等，[#3420](https://github.com/NascentCore/inty/issues/3420) 已收窄）
- **`INNER_TICK_AUTONOMY`**
  - 触发：scope worker poll
  - 用户可见：否（`inner_tick_activity_suppresses_user_delivery`）；读写 `LIFE_CURRENTS.md`，开放工具集
  - 详见 [AUTONOMY.md](./AUTONOMY.md)
- **Dreaming（非 turn）**
  - 触发：scope worker poll
  - 用户可见：否；`consolidate_memory_during_dreaming` 修改 MemDoc
  - **部分落地**：`TODO(dreaming-day-rollup)` — 当日 rollup 仍以 `transcript.jsonl` 为主 gate，inner-tick / `ai_private` 全量合并未完成（[#3376](https://github.com/NascentCore/inty/issues/3376)）

**Awake vs Dreaming 相位**（与代码 / CI 一致）：awake turn 仅 append transcript / tool 副作用；MemoryDoc batch 策展仅在 dreaming。见 `turn_invariants.py`、`lifecycle_invariants.py`。

## Channels (could be extended to become a broader 'Exo-Runtime Design')

Channels are medium for user to interact with agents.
In other words, constructs between end users and the core-agentic-harness runtime.
They provide different content modality & representation formats, and conventions of interaction. It's like a social scenarios:
a bar is for casual encountering, coffee shop is for general friends, etc. Telegram, WhatsApp, Weixin all have different canonical types of interaction patterns.

Currently-supported channels:

- WebSocket（`CompanionRuntimeChannel.APP_WEBSOCKET`）
- Telegram
- WeChat/Weixin（代码枚举 `WECHAT_WEIXIN = "wechat_weixin"`）

Harness 内 channel 枚举在 `companion/runtime_channel.py`；exo-runtime 适配在 `app/services/agentic_companion/`、`backend/ops/`（微信/Telegram demo）。

Prototype：**单 presence**（单 tab / 单 wire）每对用户；无 multi-tab。

## 代码层技术选型（Tech Stack）

- Python 3.12（与仓库环境一致）。
- Pydantic v2
- LLM client (OpenAI-compatible), with [models catalog](/app/utils/models_catalog.py)
- Configs: `config.yaml` + `app/utils/config.py` / `app/core/config.py`。
- Persistency: PostgreSQL + SQLAlchemy；MemoryStore → `companion_memory_document_versions`
  - Alembic 迁移：`/backend/alembic/`
- Observability
  - LangSmith for llm call tracing
  - loguru logging
  - `/app/core/companion_harness/companion/runtime_events.py`
    agentic-native introspection, potentially useful for users to understand the agent's situation. It's like a person's health reports.

## 扩展设计

- [多 agent 世界引擎、sub-agent](/docs/companion_harness/FR_WORLD_ENGINE.md)。
