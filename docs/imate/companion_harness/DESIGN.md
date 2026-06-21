# Companion Harness: 架构说明

> 本文描述的是 agentic companion 的**目标态理想设计**，不是现状清单。
> `companion_harness` 目前仍处于 **PROTOTYPE** 状态，可以不考虑向前兼容。
> 编码智能体与工程师在判断「某部分是否已实现」之前，**必须先读 `app/core/companion_harness/` 代码**，不要以本文为实现依据。
> 本文用途：为 `app/core/companion_harness/` 的持续实现提供方向指引。

## 概要（Executive Summary）

Companion Harness 是一套基于 LLM 的智能体框架，来运行一个 Inty 实体是 Inty 理念和愿景（1 人 1 Inty，长期关系，Inty 给用户的体感上像”活人“，而不是用完即弃的任务 Bot）的载体。

Companion Harness + LLM = Inty（陪伴智能体）；
Inty + Memory = Personal Companion（即用户通过长期与 Inty 交互形成陪伴的实体）。

Companion Harness 干的就是这件事：把 LLM 放进一套有节律、有记忆、有副作用的状态机里，让「聊天」变成「关系」，即：用户与智能体体验、演化一段关系的框架。
Companion Harness 提供了**活着的关系**的存在框架；在此之上，iMate 作为一款产品，是为用户提供一个**真心为你**的心灵港湾，或者说是为 Inty 与用户提供的一个完整的陪伴体验，类似于某种为了人的情感幸福而存在的一种服务（highly visionary/unclear）。

## Mind Model（心智模型）

Mind Model 是一种**实现范式**：用 LLM **物化（materialize）心理学研究发现的人类机制**来模拟一个人，并把这种「人格（personhood）」**显形（manifest）**出来——当前经由文本，很快扩展到其他 GenAI 模态（图像、语音），最终落到 humanoid robot。

当前的物化形态是两类相互喂养的过程：

- **Outward loop（对外）**：此刻 Inty 说出口的话——user chat、greeting、proactive。
- **Inner life（内在）**：用户看不见、却塑造后续话术的私下活动——对当轮的 appraisal（significance / recall）、monolog（ai_private）、autonomy、dreaming。
  - 「自主性」与「在你沉默时仍过自己的日子（惦记你）」就来自 inner life；实现细节见代码与 [GLOSSARY.md](./GLOSSARY.md)，本文不内联。

Tracked work index (TODO tags ↔ GitHub issues): [`TRACKED_WORK.md`](./TRACKED_WORK.md).

## 目标态：内核与产品

Companion Harness 的目标是为长期关系中陪伴用户的**虚拟活人**提供一个完整自洽的存在环境。
在此之上叠加面向特定人群的**产品功能**，实现陪伴价值用户可感知。产品/商业化不是 harness prototype 的实现关注点（见 [AGENTS.md](/app/core/companion_harness/AGENTS.md) non-goals）。
多 agent 世界引擎与 sub-agent 详见 [FR_WORLD_ENGINE.md](./FR_WORLD_ENGINE.md)。

### Domain concepts

- relationship: 本框架的**第一类核心概念**——单一用户与单一 Inty 之间持续演化、被持久化的那段 bond，是整篇文档的锚。
  - 当前工作假设（current working decomposition，CRS 将验证、非心理学 spec）按三个时间尺度拆为三轴：
    - Attachment posture：disposition 层，慢，用户如何寻求/回避亲近，Inty 取何种依恋姿态。
    - Social Penetration depth：intimacy 层，中速，相互自我表露走到多深、解锁了哪些话题。
    - Gottman moment：interaction 层，快，逐轮的连接质量（bid / 错过 / rupture / repair）。
- agentic companion: 用户与之建立陪伴关系的对象，是各种静态/运行时数据与机制的抽象集合（agentic loop、memory、llms、inner-tick 等程序化循环）。当前概念仍模糊，设计在演进中。
  - inner-tick: 一个程序化循环，companion 周期性醒来并用 LLM 做一些工作。
- agentic loop: 与 LLM 的多轮推理；多个 agentic loop 组成模拟思考与行动的 central mind model。既产出用户可见消息，也产出非用户可见数据（monolog、autonomy 等），影响后续可见话术。
- channel: 用户与 agentic companion 交互的媒介抽象；当前有 Weixin/WeChat (IM)、Telegram (IM)、App (WebSocket)。
- input & output queue: 在用户与 agent 之间缓冲消息。
- Prompt slice: 当轮注入 LLM 的 system 文本块；可 1:1 来自 MemDoc，也可仅来自包内模板或 Python 组装（见 [MEMORY_STORE.md](./MEMORY_STORE.md)）。
- Living Sphere / Techno Core: 见 [LIVING_SPHERE.md](./LIVING_SPHERE.md)——LivingSphere 是用户可改写的私密虚拟小家，TechnoCore 是只读的集体居留层。
- Interaction patterns:
  - proactive: 由 agent 主动搭话，一种用户可见的行为模式。

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

## 记忆模型 / 关系状态

当前 companion 的「世界」主要由 MemoryStore 中的一组版本化 markdown 文档、transcript 和工具副作用构成，**还不是独立 world engine**（目标态见 [FR_WORLD_ENGINE.md](./FR_WORLD_ENGINE.md)）。
relationship state 今天**隐含**在这些 MemDoc 里；CRS 的职责是把它收成显式、第一类的状态。记忆细节见 [MEMORY_STORE.md](./MEMORY_STORE.md) 与 [MEMORY_PROJECTION.md](./MEMORY_PROJECTION.md)，本文不展开字段。

- `*.md` refer to semantic content
- `*.jsonl` refer to episodic content

**闭环（一句话）**：行为产生 relationship 信号 → consolidation 把信号写入 memory → prompt activation 把状态读回，塑造下一拍行为；activation 是 consolidation 的读侧逆操作，同一段 relationship，两个方向。

闭环落地受一条 memory phase 不变式约束：**awake turn 只追加 transcript 与 tool 副作用，不做 MemDoc 整编；MemDoc curation 只在 dreaming 批处理里发生**。该不变式由代码与 CI 守护（权威定义见 [`companion/AGENTS.md`](/app/core/companion_harness/companion/AGENTS.md) 的 Memory phase invariants），本文不复述细节。

- time frames：agent 的时间感，三个嵌套 horizon，决定各轴更新与 consolidation 的节律。
  - session rhythm：当轮节拍、沉默/quiet 间隔。
  - diurnal cycle：醒/眠日界，门控 dreaming。
  - relationship history：关系已持续多久、里程碑、「一周没聊了」。
- axis → mechanism 映射（current working hypothesis，请读代码确认是否已接通）：
  - Gottman moment → 逐轮 appraisal 信号（significance perception / turn recall）。
  - Social Penetration depth → dreaming / memory consolidation。
  - Attachment posture → 长寿命语义记忆与 prompt 姿态。

TODO(memory-hierarchy-design): Design conceptual & logical memory hierarchy; replace `*.md` / `*.jsonl` stub above after !3405 closes (conversation options are candidates, not the spec).

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
- `AUTONOMY`（见 [AUTONOMY.md](./AUTONOMY.md)）
  - 触发：inner-tick
  - 用户可见：否（非直接）
- **Dreaming（非 turn）**
  - 触发：inner-tick
  - 用户可见：否（`InnerTickActivity.DREAMING`）非直接，会修改 MemDoc 从而影响后续聊天

## Channels

Channels 是同一段持续 relationship 的**可互换显形面（manifestation surface）**，不是各自独立的对话：同一份 relationship state、memory 与 mind 驱动每一个 channel，channel 只在模态与交互惯例上不同。
就像社交场景：bar 适合萍水相逢，coffee shop 适合一般朋友——Telegram、WhatsApp、Weixin 各有其惯用的交互模式。
关系的连续性与身份归属在 harness 内核（不在单 channel）；跨 channel 的身份解析见 [FR_CROSS_CHANNEL_USER_IDENTITY.md](./FR_CROSS_CHANNEL_USER_IDENTITY.md)。

Currently-supported channels:

- Websocket
- Telegram
- Weixin/WeChat

## 成效判断（What "good" looks like）

不是指标，是 relationship 模型应当推动的**定性信号**（current working stance，将由 prototype 修正）；评测机制见 [evaluation/](/evaluation/)。

- 用户**跨周回访、持续再投入**（retention，最终代理指标）。
- Inty **正确回忆并引用过往表露**（penetration depth 在起作用）。
- **成功的 bid / repair**（Gottman moment 质量）。
- **主动触达让人觉得被惦记，而非被打扰**。

## 重要下一步工作

LLM 会说话，但不会**记得你、惦记你、在你沉默时仍过自己的日子（分享给你）**，无法成为伴侣。
我们认为突破的关键是：**长期自主性**，也就是产生用户预期以外的反馈（这些行为和反馈始终以用户伴侣的视角呈现）。
这是让 AI 成为物理世界活人（5-10 年业界的整体进展）之前最可行的技术方案。
自主性体现在：

- Dynamism: prompt slices keeps changing, chat appears very dynamic.
- Self-directed activities: agents have their own autonomous activities to build up their own identity and novelty.
- Real-world channels: App、Weixin/WeChat、Telegram, users can interact with agents through channels used by humans, all are consistent.

据此，单一最重要的下一步是 Companion Relationship System (CRS)。

### CRS (Companion Relationship System)

CRS 是把今天**隐含在 MemDoc 里**的 relationship state，收成显式、第一类 harness 状态的那套机制，让所有 autonomous activity 与 channel delivery 都围绕同一段关系演化。

- 一句话职责：把 relationship state、time frames、memory consolidation、prompt activation 收束成**同一套**机制（上行 consolidation 与下行 activation 共用同一份关系状态）。
- In-scope（CRS 拥有）：
  - 显式 relationship state 模型（三轴：Attachment posture / Social Penetration depth / Gottman moment）。
  - time frames（session rhythm / diurnal cycle / relationship history）对各轴更新与 consolidation 节律的门控。
  - consolidation（写侧）与 prompt activation（读侧）的对称投影。
- Out-of-scope（CRS 不碰）：channel 适配与传输、API governance、商业化/计费、world engine 多 agent 编排（见 [FR_WORLD_ENGINE.md](./FR_WORLD_ENGINE.md)）。
- 成功判据：见上文「成效判断」——回访再投入、正确回忆表露、成功 bid/repair、主动触达被感知为惦记。
- 现状诚实声明：三轴 → mechanism 的映射（见上文「记忆模型 / 关系状态」）仍是 working hypothesis，**是否已接通须读代码确认**；这是 CRS 将验证的核心假设，而非既成事实。

Epic [#3341](https://github.com/nascentcore/inty/issues/3341) — psychology × time frames × harness (SDCM: Attachment + Gottman moment + Social Penetration depth).

## 文档地图 / See also

- [GLOSSARY.md](./GLOSSARY.md) — 术语与方向（上行/下行、前台/后台、节拍/模式）。
- [MEMORY_STORE.md](./MEMORY_STORE.md) — MemoryStore 工作区状态层：MemDoc 与 prompt slice、持久化表。
- [MEMORY_PROJECTION.md](./MEMORY_PROJECTION.md) — prompt 作为版本化 slice 空间的确定性投影。
- [AUTONOMY.md](./AUTONOMY.md) — inner-tick `AUTONOMY` 轨道与 `LIFE_CURRENTS.md`。
- [LIVING_SPHERE.md](./LIVING_SPHERE.md) — 用户–伴侣私密虚拟小家与只读 TechnoCore。
- [FR_WORLD_ENGINE.md](./FR_WORLD_ENGINE.md) — 多 agent 世界引擎、harness 作为 actor supervisor、sub-agent。
- [FR_CROSS_CHANNEL_USER_IDENTITY.md](./FR_CROSS_CHANNEL_USER_IDENTITY.md) — 跨 channel 身份解析到单一 canonical user。
- [SPECULATIVE_IDEAS.md](./SPECULATIVE_IDEAS.md) — 仅供灵感的点子集。
