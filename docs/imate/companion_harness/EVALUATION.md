# Companion Evaluation: 评测一个 personal AI companion 的第一性原理

> 本文件由 AI（编码智能体）依据 repo 现有散点记录与公开科研文献综合生成（generated entirely by the coding agent）。
> 读者：思考「评什么、为什么这么评」的设计者与工程师；运营评测台操作见 [evaluation/](/evaluation/)。
> 用途：先立**第一性原理**（评测对象是什么、依据何在），再把工程化的分层与对照作为**次要落地说明**。
> 设计压缩在一处、以 pointer 传播：关系三轴定义在 [DESIGN.md](./DESIGN.md) 与 CRS Epic（#3341），定性信号锚点在 [DESIGN.md](./DESIGN.md)「成效判断」，本文不复制其措辞。
> 判断「某机制是否已实现」前**必须先读代码**（`evaluation/`、scripted CI 测试、REPL regression）。

## 第一性原理（First principle）

一个 personal AI companion 的价值 = 它为唯一配对用户**维系的关系质量与净福祉（wellbeing）**，并且只能从**用户亲历的主观现实**出发、由**跨时间的关系行为**佐证来衡量。

由此推出三条不可回避的判断：

- 评测对象**不是「回答对不对」**，而是关系科学已验证的一组 **latent relational constructs**（被理解、依恋安全、连接质量、关系变深、孤独缓解）。这些 construct 无法用一次 turn 的 pass/fail 表达。
- 评测的**金标准是用户的体验与福祉**，不是代理指标（DAU、消息条数、停留时长）。把代理当目标会触发 surrogation / Goodhart（Strathern 1997；Goodhart's law），并与「快感泵 vs 意义型福祉」的取向冲突（见 SPECULATIVE_IDEAS.md：eudaimonic 而非 hedonic；Ryan & Deci 2001）。
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
  - 来源：Gottman & Levenson；Sound Relationship House、bids for connection 与 repair attempts、正负比（Gottman & DeClaire 2001）。已在 SPECULATIVE_IDEAS.md 引用。
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

## 次要：工程化落地（instrumentation layers）

第一性原理要变成可在 CI / REPL 跑的检查，按「越底越可测、越顶越接近真价值」分四层；细节与状态在各 issue，不在本文展开。

- **L0 Deterministic invariants（CI 必过）**：format/protocol/safety、无 `[SILENT]` 泄漏、queue delivered、bootstrap 完成。守的是「管道」，不量陪伴。来源：FakeOpenAI scripted 测试。
- **L1 Behavioral eval（live LLM，report-only）**：scripted 场景下行为是否出现（tool 调用、proactive 文案、recall、repair）。随机性高，**只产报告不 block**。来源 #3606。
- **L2 Qualitative relationship signals（rubric / 人评）**：对 transcript 按上文 construct rubric 打分（PPR、表露深度、bid/repair）。来源 `evaluation/` 人评台、#457 对话评价数据集。
- **L3 Real-usage outcomes**：自愿回访 + 情绪收束 + 福祉量表 + 产品内 `companion_record_user_feedback`（`ComplaintCategory`→issue）。来源 #3323、`evaluation/` 分析页。

**方法论不变式（#3606）**：L0=regression（确定性，gate CI exit code）；L1–L3=eval（随机/定性，report-only）。让 live LLM 行为决定 CI 是反模式。

## Data / Trace readiness（现有记录能否支撑评测）

> 审计依据：`app/core/companion_harness/`（MemoryStore、transcript、runtime events、feedback）、`app/models/chat_history.py`、`evaluation/` 分析页后端。判断「是否已实现」仍须读代码。

### 一句话判断

- **对话内容侧 trace 基本完整且版本化留存**（可支撑 L1/L2 的**行为痕迹 + 第三方评判**）；**用户体验/福祉/纵向/交付侧信号有结构性缺口**——能评「对话行为」，暂不能评「陪伴成效」。

### 已有 trace 面（按真源）

- **Transcript JSONL**（`transcript.jsonl` / `transcript_inner_tick.jsonl`）→ Postgres `companion_memory_document_versions`（`document_kind=transcript*`）；append 语义 + **整文件版本化，旧版本全留**。逐轮字段：`role`, `content`, `ts`, `uuid`, `reply_to`, `source`, `trace_id`（Inty 侧）；assistant 可选 `significance_perception`, `turn_recall`（见 `companion/transcript_assistant_row.py`）。**无** `langsmith_trace_id`。
- **MemoryStore MemDoc 版本链**：`COMPANIONSHIP/USER/SOUL/MEMORY/STYLE/IDENTITY.md`、`context.json` 等每次 `write_document` INSERT 新版本 → 可**离线重建关系状态时间序列**。
- **Inner life**：`ai_private.jsonl`（monolog）、`tool_background.jsonl`（含 `elapsed_ms`）、`LIFE_CURRENTS.md`（AUTONOMY 整文件覆盖）。
- **Runtime events**（`.companion_runtime_events.jsonl`）：`user_signed_out`, `ws_conn_dropped`, LLM/tool 失败, `inner_tick_dreaming`（含 langsmith id）。
- **User feedback**（`.companion_user_feedback.jsonl`）：`ComplaintCategory` + 截断 `HarnessSnapshot`（`vcs_revision`, MemDoc tail, `langsmith_trace_id`）——**仅 complaint 类**，无独立 feedback 表。
- **App WS `chat_history`**：`message` + `meta_data`（含 `langsmith_trace_id`, `significance_perception`, `context_mode`, `user_msg_uuid`/`assistant_msg_uuid`）+ `created_at`；**无** `read_at`、无 per-message delivery。
- **Output queue**（`agentic_companion_output_queue`）：`delivered_at`, `delivery_attempt_count`, langsmith id。
- **LangSmith**：parent run（`agentic_companion_user_turn` 等）+ 完整 prompt/补全链；与 DB 行的关联见上，**不写入 transcript 行**。

### 按 EVALUATION 时间尺度：够不够

- **moment/turn（bid/repair, responsiveness）**：✅ 基本够——transcript 可重建逐轮接住/错过；`significance_perception` 为 AI 自评辅助。
- **session（PPR, disclosure）**：⚠️ 半够——表露内容在 transcript；**缺用户亲历自陈**（ESM/EMA、PPR 量表）。
- **weeks（亲密深度, relatedness, wellbeing）**：⚠️ 半够——MemDoc 版本链可离线推 penetration depth；**缺福祉/孤独量表**。
- **months（attachment, trust, retention）**：⚠️ 半够——`user_id` + `companion_bonds` + 时间戳可离线推算回访；**无一等 visit/return-interval 事件**，`users` 无 last-active。
- **guardrail（依赖/sycophancy/人际位移）**：❌ 基本缺——仅 complaint 反馈，无常规负向 outcome 采集。

### GAP（按阻塞程度）

- **P0/S0 — Trace 真源分裂（channel coverage）**：Telegram/Weixin **不写 `chat_history`**，只进 MemoryStore per-scope transcript；`evaluation/` 用户分析读 `chat_history` → **运营侧看不到这两通道对话**。→ issues/#3663
- **P0/S1 — 无 user-side self-report / affect / wellbeing**：PPR、UCLA Loneliness、IOS、依恋量表、ESM/EMA **均未采集**——EVALUATION 金标准信号的**核心缺口**。→ issues/#3664
- **P1/S1 — 无 read/delivery/reply-latency 于用户可见历史**：`chat_history` 无投递/已读；Performance 页 LLM 延迟依赖 legacy `meta_data.llm_invoke_time`，**companion harness 主路径未写** → 无法量「proactive 被接住 vs 被忽略」「响应体感」。→ issues/#3666
- **P1/S2 — 纵向 linkage 靠离线重建**：无专用 visit/return-interval 事件流。→ issues/#3665
- **P1/S2 — Provenance 不足**：transcript / `chat_history` 行**无 harness config hash / prompt slice 版本**；除 feedback snapshot 与 LangSmith 外难把成效**归因到 harness 改动**。→ issues/#3667
- **P2/S2 — LangSmith id 不在 transcript 行**：反查 trace 须经 `chat_history` 或 feedback，MemoryStore-only 通道不便。→ issues/#3668

### 现在能做 vs 不能做

- **能做**：基于 transcript + MemDoc 版本链的离线**内容侧**评测（bid/repair rubric、表露深度时间序列、AI 自评 significance）；App WS 路径可经 `chat_history.meta_data` 链 LangSmith。
- **不能做**：用户**体验/福祉**评测（缺自陈）；**全通道统一**纵向评测（真源分裂）；把成效**归因到 harness 版本**（缺 per-turn provenance）。

## 次要：与 task-agent 评测的对照、与现状

- 对照（succinct）：task agent（如 Terminal-Bench / Self-Harness, arXiv 2606.09498）有 deterministic verifier + i.i.d. task split，可单分数回归；companion **无 ground-truth verifier、path-dependent、n=1、信号慢**，故只能上文的纵向三角化。
- 现状 vs 缺口（诚实）：
  - 已具备：L0 scripted/infra gate、`evaluation/` 人评与分析台、`companion_record_user_feedback` 负反馈链路。
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
- [SPECULATIVE_IDEAS.md](./SPECULATIVE_IDEAS.md) — eudaimonic 取向、Gottman、north-star（回访+情绪收束）。
- `evaluation/` — 运营人评与行为分析台。
- Issues：#3341（CRS）、#3323（retention/trust）、#3606（regression vs eval）、#457（对话评价系统）、#72（本地 inty-eval）；trace readiness：#3663–#3668。
