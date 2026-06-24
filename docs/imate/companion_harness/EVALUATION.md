# Companion Evaluation: 如何评测一个 personal AI companion

> 本文件由 AI（编码智能体）依据 repo 现有散点记录综合生成（generated entirely by the coding agent）。
> 用途：把散落在 DESIGN.md、SPECULATIVE_IDEAS.md、CRS Epic 与若干 issue 里的评测立场，**收敛成一处**，供 `app/core/companion_harness/` 的评测机制持续实现时参照。
> 本文描述的是**评测方法论的目标态与判断**，不是现状清单；判断「某层是否已实现」之前，**必须先读代码**（`evaluation/`、REPL regression、scripted CI 测试）。
> 设计压缩在一处、以 pointer 传播：定性信号锚点在 [DESIGN.md](./DESIGN.md)「成效判断」，关系三轴在 [DESIGN.md](./DESIGN.md) 与 CRS Epic（#3341），本文不复制其措辞。

## Problem definition

评测 personal AI companion 与评测 task agent（如 Terminal-Bench 那类）本质不同：companionship 的价值是**长期情感联结**，它具有四条让传统评测失效的属性。

- No deterministic verifier：陪伴质量是**定性**的（被懂、被惦记、关系在变深），没有 task agent 那种 pass/fail ground truth。
- Path-dependent：1 人 1 Inty 的关系是**有状态、逐轮累积**的，memory 与姿态随历史漂移，无法像独立 task 那样「每次全新环境」重跑。
- Single-subject（n=1）：每段关系只属于一个用户，无法在同一用户上做破坏性 A/B。
- Slow signal：最有意义的信号（自愿回访、关系变深）要**数天到数周**才显形，远慢于一次 turn。

因此评测不能是「单一分数」，只能是**按可测性 × 时间尺度的分层三角验证**。这一判断已隐含在 repo 多处记录中（见文末 Pointers），本文将其显式化。

## Objectives

- 给出 companion 评测的**分层框架**，让每一类检查各安其位、不互相冒充。
- 钉死一条**方法论不变式**：deterministic regression 与 stochastic model-behavior eval 必须分层，前者 gate CI、后者只产报告（来源 #3606）。
- 把每层信号**映射到 CRS 关系三轴**，使评测与关系模型同源。
- 诚实标注**现状 vs 目标**，让后续实现知道缺口在哪。
- Out of scope：具体打分 rubric 文案、benchmark 数据集清单、运营报表字段（属实现细节，落在 `evaluation/` 与各 issue）。

## Bird's eye view: four evaluation layers

按「越往下越可测、越往上越接近真正的陪伴价值」排列。下层便宜可靠但量不到陪伴，上层量到陪伴但慢且被混淆。

```evaluation-layers
                   closer to real companionship value (slow, confounded)
        ^   +---------------------------------------------------------+
        |   | L3  Real-usage outcomes                                 |
        |   |     voluntary return / emotional closure / recall /     |
        |   |     proactive-felt-as-caring ; in-product feedback      |
        |   +---------------------------------------------------------+
        |   | L2  Qualitative relationship signals (rubric / human)   |
   timescale|     judged against CRS axes on transcripts              |
   & value  +---------------------------------------------------------+
        |   | L1  Behavioral eval (live LLM, REPORT-ONLY)             |
        |   |     scripted scenarios ; tool-use / proactive / recall  |
        |   +---------------------------------------------------------+
        |   | L0  Deterministic invariants (CI, MUST-PASS)            |
        |   |     format / protocol / safety / queue / bootstrap      |
        v   +---------------------------------------------------------+
            cheaper, reliable, repeatable (fast) -- but only guards plumbing

   ====================  the regression / eval firewall  ====================
   L0 gates exit code.  L1-L3 produce reports, never block CI (issue #3606).
```

## The four layers

### L0 — Deterministic invariants（CI 必过，确定性）

- 评什么：与 LLM 内容无关、可机器判定的契约——output format/schema、protocol 不变量（无 `[SILENT]` 泄漏）、safety 子句、queue delivered、bootstrap 完成、tool-call 无错。
- 信号源：FakeOpenAI scripted 测试（如 `test_harness_orchestration_scripted_llm`、`test_turn_proactive_structured`）+ REPL live driver 的 infra-only pass gate。
- Gate 语义：**唯一会 block CI / exit code 的层**。
- 局限：只守「管道」，**完全量不到陪伴质量**——L0 全绿不代表 Inty 像活人。

### L1 — Behavioral eval（live LLM，report-only）

- 评什么：真实 LLM 在 scripted 场景下**是否表现出目标行为**——是否按 prompt 调用工具、proactive 文案是否得体、是否 recall 过往、是否做 bid/repair。
- 信号源：REPL regression 的 eval smoke、`evaluation/` 单角色聊天与会话评测。
- Gate 语义：**只写报告，不 block exit 0**（#3606 的核心结论：pass/fail 一旦取决于 live LLM 行为，就是 model eval 而非 regression）。
- 局限：随机性高，需重复采样；衡量「行为出现与否」，不等于「关系变好」。

### L2 — Qualitative relationship signals（rubric / 人评）

- 评什么：DESIGN.md「成效判断」四信号——正确引用表露、成功 bid/repair、主动触达被感知为惦记、人格/记忆稳定——对 transcript 由人或 LLM-judge 按 rubric 打分。
- 信号源：`evaluation/` 人评台（`EvaluationPage`/`ScoreSelector`）；scripted 多轮对话数据集（issue #457 形态：固定 system prompt + 多轮依次进行）。
- Gate 语义：**质量报告与趋势**，非硬门；LLM-judge 需 pairwise + 重复降噪，避免 Goodhart。
- 局限：当前是 aspirational——rubric 与判分机制**尚未系统落地**。

### L3 — Real-usage outcomes（最终代理，慢且被混淆）

- 评什么：north-star 行为结果——**自愿跨周回访、情绪收束**（来源 SPECULATIVE_IDEAS：拒绝以 DAU / 消息条数为度量），以及产品层 trust/continuity（#3323：day-1 continuity、functional-use→attachment、platform-betrayal→migration）。
- 信号源：产品内 `companion_record_user_feedback`（`ComplaintCategory` → GitHub issue，天然负反馈输入）+ `evaluation/` 用户行为分析页（`UserAnalyticsPage`、`PerformanceAnalyticsPage`、`ReportFeedbackPage`）。
- Gate 语义：长期 proxy，看趋势，不进 CI。
- 局限：信号慢、被关系 path-dependence 与外部因素混淆，n=1 难归因。

## 与 CRS 关系三轴的映射

评测信号与关系模型同源：每层信号都应能落到某条 CRS 轴（轴定义见 [DESIGN.md](./DESIGN.md) 与 CRS Epic #3341），这样「评测推动什么」与「harness 演化什么」一致。

- Gottman moment（interaction，快）→ 逐轮 bid/repair 与连接质量，主要在 L1/L2 观测。
- Social Penetration depth（intimacy，中）→ 正确回忆并引用表露、话题解锁，主要在 L2 观测，L3 间接印证。
- Attachment posture（disposition，慢）→ 人格/记忆稳定、proactive 被感知为惦记，主要在 L3（回访、信任）观测。

## 方法论不变式：regression 与 eval 必须分层

- 单一不变式（来源 #3606）：**L0 = regression（deterministic，gate CI）；L1–L3 = eval（stochastic/qualitative，report-only）**。
- 反模式：让 live LLM 的行为决定 CI exit code——会把不可重复的 model eval 伪装成 regression，导致与被测改动无关的随机 fail。
- 推论：新增 companion 行为的**确定性覆盖**应优先用 FakeOpenAI scripted 表达；live/judge 路径只产趋势报告。

## Current state vs target（诚实声明）

- 已具备（现状）：L0 的 scripted/infra gate、`evaluation/` 人评与分析台、`companion_record_user_feedback` 负反馈链路、REPL regression 的 infra pass gate。
- 缺口（目标）：L2 的 rubric 与 LLM-judge 判分机制**未系统落地**；L1 缺**可复现的 scenario-replay**（冻结 agent 快照 + 脚本化模拟用户）以解决 path-dependence；issue #457 的对话评价系统仍是雏形。
- 落地顺序建议（P/S）：
  - P1/S1：scenario-replay + frozen-snapshot 基建（无它则 L1/L2 无法可复现回归）。
  - P1/S1：补全 L0 deterministic gates（format/safety/tool-error/persona-leak）。
  - P2/S1：L2 pairwise rubric-judge，rubric 锚定 CRS 三轴。
  - P2/S2：以 `companion_record_user_feedback` 的 `ComplaintCategory` 做首版 weakness 输入。

## Pointers / See also

- [DESIGN.md](./DESIGN.md) — 「成效判断」定性信号（评测的权威锚点）与关系三轴。
- [SPECULATIVE_IDEAS.md](./SPECULATIVE_IDEAS.md) — north-star 度量哲学（回访 + 情绪收束，非 DAU），Gottman / eudaimonic。
- [GLOSSARY.md](./GLOSSARY.md) — 关系轴与方向术语。
- `evaluation/` — 运营向人评与行为分析台（PM/运营读者）。
- Issues：#3341（CRS Epic）、#3323（retention/trust）、#3606（regression vs eval 分层）、#457（对话评价系统）、#72（本地 inty-eval）。
- Code：FakeOpenAI scripted 测试（`tests/app/core/companion_harness/companion/`）、REPL regression（`.cursor/skills/inty-repl-regression`）、`companion_record_user_feedback` 工具。
