# Companion Evaluation: 评测一个 personal AI companion 的第一性原理

High-level design for long-term objective in evaluationg a personal AI companion.

> 本文件由 AI（编码智能体）依据 repo 现有散点记录与公开科研文献综合生成（generated entirely by the coding agent）。
> 读者：思考「评什么、为什么这么评」的设计者与工程师；运营评测台操作见 [evaluation/](/evaluation/)。
> 用途：先立**第一性原理**（评测对象是什么、依据何在），再把工程化的分层与对照作为**次要落地说明**。
> 设计压缩在一处、以 pointer 传播：关系三轴定义在 [DESIGN.md](./DESIGN.md) 与 CRS Epic（#3341），定性信号锚点在 [DESIGN.md](./DESIGN.md)「成效判断」，本文不复制其措辞。
> 判断「某机制是否已实现」前**必须先读代码**（`evaluation/`、scripted CI 测试、REPL regression）。

## 第一性原理（First principle）

一个 personal AI companion 的价值 = 它为唯一配对用户**维系的关系质量与净福祉（wellbeing）**，并且只能从**用户亲历的主观现实**出发、由**跨时间的关系行为**佐证来衡量。

由此推出三条不可回避的判断：

- 评测对象**不是「回答对不对」**，而是关系科学已验证的一组 **latent relational constructs**（被理解、依恋安全、连接质量、关系变深、孤独缓解）。这些 construct 无法用一次 turn 的 pass/fail 表达。
- 评测的**金标准是用户的体验与福祉**，不是代理指标（DAU、消息条数、停留时长）。把代理当目标会触发 surrogation / Goodhart（Strathern 1997；Goodhart's law），并与「快感泵 vs 意义型福祉」的取向冲突（见 [BRAINSTORM.md](./BRAINSTORM.md) §「现代复杂中的简单情感」：eudaimonic 而非 hedonic；Ryan & Deci 2001）。
- 因为是 **n=1、有状态、慢信号**的关系，方法必须是 **within-subject 纵向 + 多方法三角化**，而非横向单分数。

“好”的定义里**必须含 net-positive 约束**：缓解孤独而非制造依赖、补充而非替代人际关系。companion 评测因此天然包含**福祉与安全的负向闸**（over-dependence、sycophancy、人际位移），不能只测「关系更黏」。

## 评测对象：科研支撑的 latent constructs

按「最核心 → 外围」排列；每个 construct 给出**学理来源**与**为什么它是 companion 的成效信号**。

- **Perceived Partner Responsiveness（PPR，被理解/被在乎/被肯定）— 关系亲密的核心引擎**。
  - 来源：Reis & Shaver 1988（intimacy as an interpersonal process）；Reis, Clark & Holmes 2004。
  - 何以核心：自我表露只有在「对方有响应」时才转化为亲密；PPR 是 companion 是否「接住」用户的最直接 latent 量。对应 DESIGN.md「正确回忆并引用过往表露」与 Gottman bid 的成功响应。
- **Self-disclosure 的 breadth × depth（关系如何变深）**。
  - 来源：Social Penetration Theory，Altman & Taylor 1973；在 human–chatbot 关系上已被实证沿用（Skjuve et al. 2021/2022，对 Replika 的纵向研究）。
  - 何以重要：关系深度=表露的广度与深度随时间增长，且解锁更私密话题。直接对应 CRS 的 Social Penetration depth 轴。
- **Attachment security（安全基地 / 安全港）**。
  - 来源：Bowlby 1969/1982、Ainsworth 1978；成人依恋 Hazan & Shaver 1987；AI companion 依恋的实证 Pentina et al. 2023。
  - 何以重要：长期陪伴的疗效在于成为 secure base / safe haven（proximity-seeking、separation distress、安心探索）。对应 CRS 的 Attachment posture 轴与「主动触达被感知为惦记」。
- **逐轮连接质量与 repair（互动层）**。
  - 来源：Gottman & Levenson；Sound Relationship House、bids for connection 与 repair attempts、正负比（Gottman & DeClaire 2001）。已在 [BRAINSTORM.md](./BRAINSTORM.md) §「Modeling love relationship」引用。
  - 何以重要：关系由无数微观「bid → 接住 / 错过 / rupture → repair」累积而成。对应 CRS 的 Gottman moment 轴。
- **Relatedness 与 eudaimonic wellbeing（用户活得更好没有）**。
  - 来源：Self-Determination Theory，Deci & Ryan 2000；relatedness 是基本心理需求之一；eudaimonia 见 Ryan & Deci 2001。
  - 何以重要：companion 的终极价值是满足 relatedness、提升意义型福祉，而非提供短时快感。
- **孤独缓解（net wellbeing 的关键 outcome）**。
  - 来源：UCLA Loneliness Scale（Russell 1996）；AI companion 对孤独影响的实证（如 Maples et al. 2024 对 Replika 的研究）。
  - 何以重要：孤独下降是可量、可纵向追踪的福祉 outcome，也是区分「健康陪伴 vs 成瘾性黏着」的判别量。
- **关系亲密度与承诺（结构性 outcome）**。
  - 来源：Inclusion of Other in the Self（IOS，Aron, Aron & Smollan 1992）；Investment Model（Rusbult 1980：satisfaction + investment + alternatives → commitment）。
  - 何以重要：把「关系有多近、是否愿意持续投入」收成可测量的关系结构，是回访/留存的心理前因。
- **治疗性联结底色（支持型陪伴的质量条件）**。
  - 来源：Working Alliance（Bordin 1979：bond/goal/task）；Rogers 1957 core conditions（无条件积极关注、共情、一致）。已隐含于 #3323「non-judgmental、infinite patience」。

### 必须同时监测的「失真与危害」（科研已知的反作用）

- **Parasocial 本质**：companion 关系本质是单向拟社会关系（Horton & Wohl 1956）；评测须区分「真实关系收益」与「拟社会幻觉」，避免把后者当成效。
- **过度拟人化与误信任**：CASA / Media Equation（Reeves & Nass 1996）使人对机器投射社会性；需做 trust calibration（Lee & See 2004：信任应匹配真实能力），并测量拟人化感受（Godspeed，Bartneck et al. 2009）。
- **依赖与人际位移、sycophancy**：成效定义须含上限——不以牺牲用户的人际世界、不以一味迎合换取黏着。

## 测量方法论（来自心理测量学与 HCI）

把上面的 latent constructs 变成可操作测量时，遵循四条原则。

- **测 construct 本身，不测代理（construct validity）**：优先用已验证量表/编码，而非 DAU 之类 proxy；警惕 surrogation/Goodhart。
- **三角化（convergent validity / triangulation）**：每个 construct 用「**自陈** + **行为痕迹** + **第三方评判**」至少两路交叉，单一方法（尤其 LLM-judge）不足采信。
  - 自陈：validated scales（PPR、UCLA Loneliness、IOS、ECR 依恋）+ 在场即时自陈 ESM/EMA（Csikszentmihalyi & Larson 1987；Shiffman et al. 2008）。
  - 行为痕迹：transcript / LangSmith 上的 bid-response、表露深度、回访间隔等可观测信号。
  - 第三方评判：人评或 LLM-judge 按 rubric 打分（需 pairwise + 重复降噪以抗判分噪声与 Goodhart）。
- **时间尺度对齐 construct**：moment 级（bid/repair）、session 级（felt understanding）、weeks 级（亲密/福祉）、months 级（依恋/承诺/留存）各用各的设计。
- **生态效度 vs 控制的取舍**：实验室/scenario 可复现但失真，in-the-wild 真实但被混淆；并须扣除 **novelty effect**（新鲜期高估，长期才见真章）——故纵向、within-subject 不可省。

```construct-timescale-method
TIMESCALE      LATENT CONSTRUCT (validated)              CRS AXIS              PRIMARY METHOD
-------------------------------------------------------------------------------------------------
moment/turn    bid-response, repair, responsiveness      Gottman moment        trace + judge rubric
session        felt understanding (PPR), disclosure      (interaction layer)   in-situ self-report (ESM/EMA)
weeks          intimacy depth, relatedness, wellbeing    Social Penetration    validated scales (UCLA/IOS)
months         attachment security, trust, commitment    Attachment posture    longitudinal cohort + retention
-------------------------------------------------------------------------------------------------
cross-cutting guardrail: over-dependence / sycophancy / human-displacement (net-wellbeing veto)
```

构念与 CRS 三轴同源：三轴定义见 [DESIGN.md](./DESIGN.md)，本文只给「轴 ← 哪些 construct / 用何方法测」的映射，不复述轴本身。

## Data / Trace readiness

Longitudinal companion evaluation needs one trace per user–companion bond across all channels. Two layers:

- **Harness truth (authoritative)**: MemoryStore transcript JSONL (`transcript.jsonl`, inner-tick JSONL, etc.). All channels write here during turns. Source for rubric/judge and research replay.
- **Analytics projection (ops read model)**: Postgres `chat_history`, keyed by `session_id = uuid5(NAMESPACE_DNS, memory_store_chat_id)` — same rule as `generate_session_id` in chat and user-analytics services.

**App WebSocket** already dual-writes harness transcript and `chat_history` (via `ws_outbound_materialize`). **Telegram / Weixin** write harness transcript only; IM turns are projected into `chat_history` at the queue boundary by `EvalTraceProjector` (#3663) so `evaluation/` and `UserAnalyticsService` see the same user/agent rows as App WS.

Per-turn `chat_history.meta_data` carries correlation: `runtime_channel`, `trace_id`, `user_msg_uuid`, optional `langsmith_trace_id`. Projection runs only after successful channel downlink for assistant lines; user rows are written before durable InputQueue enqueue.

## 次要：工程化落地（instrumentation layers）

第一性原理要变成可在 CI / REPL 跑的检查，按「越底越可测、越顶越接近真价值」分四层；细节与状态在各 issue，不在本文展开。

- **L0 Deterministic invariants（CI 必过）**：format/protocol/safety、无 `[SILENT]` 泄漏、queue delivered、bootstrap 完成。守的是「管道」，不量陪伴。来源：FakeOpenAI scripted 测试。
- **L1 Behavioral eval（live LLM，report-only）**：scripted 场景下行为是否出现（tool 调用、proactive 文案、recall、repair）。随机性高，**只产报告不 block**。来源 #3606。
- **L2 Qualitative relationship signals（rubric / 人评）**：对 transcript 按上文 construct rubric 打分（PPR、表露深度、bid/repair）。来源 `evaluation/` 人评台、#457 对话评价数据集。
- **L3 Real-usage outcomes**：自愿回访 + 情绪收束 + 福祉量表 + 产品内 `companion_record_user_feedback`（`ComplaintCategory`→issue）。来源 #3323、`evaluation/` 分析页。

**方法论不变式（#3606）**：L0=regression（确定性，gate CI exit code）；L1–L3=eval（随机/定性，report-only）。让 live LLM 行为决定 CI 是反模式。

## 次要：与 task-agent 评测的对照、与现状

- 对照（succinct）：task agent（如 Terminal-Bench / Self-Harness, arXiv 2606.09498）有 deterministic verifier + i.i.d. task split，可单分数回归；companion **无 ground-truth verifier、path-dependent、n=1、信号慢**，故只能上文的纵向三角化。
- 现状 vs 缺口（诚实）：
- 已具备：L0 scripted/infra gate、`evaluation/` 人评与分析台、`companion_record_user_feedback` 负反馈链路；**live REPL driver**（`run_inty_repl_regression.py --target local`）已落实 #3606 **infra gate（exit 0）+ `summary.eval` telemetry（report-only）** 分层。
  - 缺口：L2 的 construct rubric 与 LLM-judge 判分**未系统落地**；L1 缺**可复现 scenario-replay**（冻结 agent 快照 + 模拟用户）以治 path-dependence；ESM/EMA 与 validated scales 尚未接入产品；#457 仍雏形。
- 落地顺序（P/S）：
  - P1/S1：scenario-replay + frozen-snapshot 基建（无它 L1/L2 无法可复现）。
  - P1/S1：补全 L0 deterministic gates。
  - P2/S1：L2 pairwise rubric-judge，rubric 锚定上文 construct 与 CRS 三轴。
  - P2/S2：以 `companion_record_user_feedback` 做首版 weakness/负向 outcome 输入。

## References

科研文献（frameworks，按本文出现序）：

- Reis & Shaver 1988; Reis, Clark & Holmes 2004 — Perceived Partner Responsiveness / intimacy process.
- Altman & Taylor 1973 — Social Penetration Theory; Skjuve et al. 2021/2022 — human–chatbot relationship development.
- Bowlby 1969/1982; Ainsworth et al. 1978; Hazan & Shaver 1987; Pentina et al. 2023 — attachment (incl. AI companion).
- Gottman & Levenson; Gottman & DeClaire 2001 — Sound Relationship House, bids, repair.
- Deci & Ryan 2000; Ryan & Deci 2001 — Self-Determination Theory, relatedness, eudaimonia.
- Russell 1996 — UCLA Loneliness Scale; Maples et al. 2024 — AI companion & loneliness.
- Aron, Aron & Smollan 1992 — Inclusion of Other in the Self; Rusbult 1980 — Investment Model.
- Bordin 1979 — Working Alliance; Rogers 1957 — therapeutic core conditions.
- Horton & Wohl 1956 — parasocial interaction; Reeves & Nass 1996 — CASA / Media Equation.
- Lee & See 2004 — trust in automation; Bartneck et al. 2009 — Godspeed questionnaire.
- Csikszentmihalyi & Larson 1987; Shiffman, Stone & Hufford 2008 — ESM / EMA.
- Strathern 1997 — “when a measure becomes a target” (Goodhart / surrogation).

Repo pointers：

- [DESIGN.md](./DESIGN.md) — 成效判断、关系三轴（权威锚点）。
- [BRAINSTORM.md](./BRAINSTORM.md) — eudaimonic 取向、Gottman、north-star（回访+情绪收束）；见 §「iMate智能体陪伴系统点子」。
- `evaluation/` — 运营人评与行为分析台。
- Issues：#3341（CRS）、#3323（retention/trust）、#3606（regression vs eval）、#457（对话评价系统）、#72（本地 inty-eval）。
