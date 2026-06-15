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
- Interaction patterns:
  - proactive: proactively poking user from agent, a user-visible behavior pattern

## 系统实现规范

- 失败应显性：各类错误应该显式呈现给用户、后端日志、异常等等；目的：有助于原型开发期间解决基础性问题

## 目标架构图

下图以 Companion Harness 为中枢，描述用户如何经各渠道触达同一 Inty，以及内核与虚拟世界、持久化记忆如何衔接；下一节展开 Harness 内部职责划分。

```
                    ┌────────────────────────────────────-─┐
                    │  Users & dev entry                   │
                    │  iMate App · REPL · WeChat · Telegram│
                    └───────────────────┬───────────────-──┘
                                        │
                    ┌───────────────────▼─────────────-────┐
                    │  Channel layer (Exo-runtime)         │
                    │  Realtime channel  │  IM channel     │
                    └───────────────────┬──────────────-───┘
                                        │
                    ┌───────────────────▼─────────────-────┐
                    │  Access & governance                 │
                    │  auth · usage · visible history ·    │
                    │  protocol adaptation                 │
                    └───────────────────┬─────────────-────┘
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         │                              │                              │
  ┌──────▼──────┐    ┌──────────────────▼──────────────────┐   ┌───────▼───────┐
  │ Living      │◄──►│  Companion Harness kernel           │◄─►│ Techno Core   │
  │ Sphere      │    │  relationship · memory · turns ·    │   │ shared virtual│
  │ personal    │    │  tools                              │   │ world         │
  │ living space│    └──────────────────┬──────────────────┘   └───────────────┘
  └─────────────┘                       │     virtual worlds (synthetic stimuli)
                                        │
                    ┌───────────────────▼─────────────────┐
                    │  Persistence                        │
                    │  long-term memory & dialogue trace  │
                    └─────────────────────────────────────┘
```

### Harness 内核（职责展开）

```
┌─ Entry & orchestration ────────────────────────────────────----─────────┐
│  inbound events · session mgmt  ──►  track routing · turn orchestration │
└────────────────────────────────────┬───────────────────────────────--───┘
                                     │
                                     ▼
┌─ Awake turns ─────────────────────────────────────────────────----──────┐
│  turn programs  ──►  prompt assembly  ──►  LLM call  ──►  model gateway │
│  chat · greeting · proactive · autonomy · maintenance                   │
│  stable persona + volatile recent context                               │
└───┬────────────────────┬────────────────────┬──────────────────----─────┘
    │                    │                    │
    ▼                    ▼                    ▼
 memory store ◄────  background tools     tool registry
    ▲                    │
    │                    │
    └──── Dreaming (end-of-day memory consolidation)

 inner tick (proactive · scheduled · autonomy · maintenance) ──► triggers turn programs
```

### 回合运行时（端到端）

```
User (App / WeChat / Telegram / REPL)
              │
              ▼
      channel adapter
              │
              ▼
 access layer (auth · governance · visible history)
              │
              ▼
       inbound queue
              │
              ▼
 Companion Harness (session · memory · orchestration)
              │
              ├─────────────────────────────┐
              │                             │
              ▼                             ▼
      turn execution ◄────────────────►  memory store
 read memory · assemble prompt · call model    ▲
              │                                │
              ├────► background tools · inner tick · dreaming ──►│
              │
              ├────► observability (call traces · runtime introspection)
              │
              ▼
      outbound queue
              │
              ▼
      channel adapter
              │
              ▼
             user
```

## 记忆模型

当前 companion 的「世界」主要由 MemoryStore 中的一组版本化 markdown 文档、transcript 和工具副作用构成，**还不是独立 world engine**（目标态见 [FR_WORLD_ENGINE.md](./FR_WORLD_ENGINE.md)）。

- `*.md` refer to semantic content
- `*.jsonl` refer to episodic content

TODO(memory-hierarchy-design): Design conceptual & logical memory hierarchy; replace `*.md` / `*.jsonl` stub below after !3405 closes (conversation options are candidates, not the spec).

## Turn 轨道：用户与智能体交互及慢周期后台数据处理支持 (Runtime Loops)

`CompanionTurnTrack`（`companion/models.py`）与 `run_turn` 一一对应；inner-tick 活动由 `InnerTickActivity` 区分。

- **`USER_CHAT` / `USER_CHAT_BOOTSTRAP`**
  - 触发：用户消息
  - 用户可见：是
- **`IMPLICIT_SIGN_ON_GREETING`**
  - 触发：`user_signed_on` 隐式问候
  - 用户可见：是
- **`INNER_TICK_PROACTIVE_CHAT`**
  - 触发：idle poll
  - 用户可见：是（主动心跳）
- **`INNER_TICK_SCHEDULED`**
  - 触发：定时队列
  - 用户可见：视配置
- **`INNER_TICK_MAINTENANCE`**
  - 触发：idle poll
  - 用户可见：否（维护型；目标态收窄为 Autonomy，见 `AUTONOMY.md`）
- **Dreaming（非 turn）**
  - 触发：idle poll
  - 用户可见：否（`InnerTickActivity.DREAMING`）

工具开启时，in-turn 路由固定为 `ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL`：前台 chat envelope 先返回用户可见文本，`tool_background` 在独立线程继续工具轮（`turn_routes.py`）。

## Channels (could be extended to become a broader 'Exo-Runtime Design')

Channels are medium for user to interact with agents.
In other words, constructs between end users and the core-agentic-harness runtime.
They provide different content modality & representation formats, and conventions of interaction. It's like a social scenarios:
a bar is for casual encountering, coffee shop is for general friends, etc. Telegram, WhatsApp, Weixin all have different canonical types of interaction patterns.

Currently-supported channels:

- Websocket
- Telegram
- Weixin/WeChat

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
