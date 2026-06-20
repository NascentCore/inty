# Companion Harness: 架构说明

## 概要（Executive Summary）

Companion Harness 一套完整的智能体框架，由 LLM 驱动：1 人 1 Inty，长期关系，体感上要像”活人“，而不是用完即弃的任务 Bot；是 Inty 理念和愿景的核心载体。

Companion Harness + LLM = Inty（陪伴智能体）；Inty + Memory = Personal Companion

Companion Harness 干的就是这件事：把 LLM 放进一套有节律、有记忆、有副作用的状态机里，让「聊天」变成「关系」，即：用户与智能体体验、演化一段关系的框架。
Companion Harness 提供了**活着的关系**的存在框架；在此之上，iMate 作为一款产品，是为用户提供一个**真心为你**的心灵港湾。

### 现状

以上是**目标态的理想设计**，不是现状清单。`companion_harness` 目前仍处于 **PROTOTYPE** 状态。

## 重要下一步工作

LLM 会说话，但不会**记得你、惦记你、在你沉默时仍过自己的日子（分享给你）**，无法成为伴侣。
我们认为突破的关键是：**长期自主性**，也就是产生用户预期以外的反馈（这些行为和反馈始终以用户伴侣的视角呈现）。
这是让 AI 成为物理世界活人（5-10 年业界的整体进展）之前最可行的技术方案。
自主性体现在：

- Dynamism: prompt slices keeps changing, chat appears very dynamic.
- Self-directed activities: agents have their own autonomous activities to build up their own identity and novelty.
- Real-world channels: App、Weixin/WeChat、Telegram, users can interact with agents through channels used by humans, all are consistent.

据此，单一最重要的下一步是 Companion Relationship System (CRS)：
把 relationship state、time frames、memory consolidation 和 prompt activation 收束成同一套 harness 机制，
让所有 autonomous activity 与 channel delivery 都围绕同一段关系演化。

Epic [#3341](https://github.com/nascentcore/inty/issues/3341)
psychology × time frames × harness (SDCM: Attachment + Gottman moment + Social Penetration depth).

Tracked work index (TODO tags ↔ GitHub issues): [`TRACKED_WORK.md`](./TRACKED_WORK.md).

## 目标态：内核与产品

Companion Harness 的目标是为长期关系中陪伴用户的**虚拟活人**提供一个完整自洽的存在环境。
在此之上，需要叠加面向特定人群的**产品功能**，来实现陪伴的商业化体验，即**陪伴价值用户可感知、用户有付费意愿**。
如 [多 agent 世界引擎、sub-agent](/docs/companion_harness/FR_WORLD_ENGINE.md)。

### Domain concepts

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

```bird's-eye view
┌──────────────────────────────────────┐
│  Users side                          │
└───────────────────┬──────────────────┘
                    │
┌───────────────────▼──────────────────┐
│  Gateways (formerly Channel)         │
│  Realtime channel  │  IM channel     │
│  iMate App · REPL · WeChat · Telegram│
└───────────────────┬──────────────────┘
                    │
┌───────────────────▼──────────────────┐
│  API governance (minimal)            │
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
  - 触发：`user_signed_on` implicit signal
  - 用户可见：是
- **`PROACTIVE_CHAT`**
  - 触发：idle poll
  - 用户可见：是（主动心跳）
- **`SCHEDULED`**
  - 触发：定时队列
  - 用户可见：Determined by the agentic loop (executing the scheduled task)
- **`MAINTENANCE`** (monolog)
  - 触发：idle poll
  - 用户可见：否
- `AUTONOMY`
  - 触发：inner-tick
  - 用户可见：否（非直接）
- **Dreaming（非 turn）**
  - 触发：inner-tick
  - 用户可见：否（`InnerTickActivity.DREAMING`）非直接，会修改 MemDoc 从而影响后续聊天

## Channels (could be extended to become a broader 'Exo-Runtime Design')

Channels are medium for user to interact with agents.
In other words, constructs between end users and the core-agentic-harness runtime.
They provide different content modality & representation formats, and conventions of interaction. It's like a social scenarios:
a bar is for casual encountering, coffee shop is for general friends, etc. Telegram, WhatsApp, Weixin all have different canonical types of interaction patterns.

Currently-supported channels:

- Websocket
- Telegram
- Weixin/WeChat
