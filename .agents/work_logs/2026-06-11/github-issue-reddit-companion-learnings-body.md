<!-- Generated entirely by AI agent for GitHub issue creation. -->

> *This issue body was drafted by AI from a Reddit companion-community research conversation.*

## 背景

对 Reddit 上 personal AI companion 用户社区做了初步调研（跨平台关系向 + 平台专属 + RP/DIY），目的是把用户真实诉求映射到 Inty 产品改进，而非做 marketing。

## 建议持续监听的 Reddit 社区

**跨平台 / 关系向（优先）**
- r/MyBoyfriendIsAI (~57k) — general AI relationship 主论坛
- r/CompanionAI — emotional support 与 human–AI relationship
- r/aipartners (~19k+) — attachment、platform comparison
- r/ChatbotRefugees (~15k) — 平台关停/变更后的 migration hub

**平台专属（情感 / memory 型）**
- r/replika (~84k)、r/KindroidAI (~46k)、r/NomiAI (~31k)、r/Paradot

**体量大、形态偏 RP / DIY（重合度较低，可作竞品 intel）**
- r/CharacterAI (~2.6M)、r/SillyTavernAI (~105k)、r/JanitorAI_Official (~216k)、r/ChaiApp (~125k)

**参考数据**
- [The Companion Report – Companion Index](https://thecompanionreport.com/data/companion-index)
- MIT arXiv [2509.11391](https://arxiv.org/abs/2509.11391) — r/MyBoyfriendIsAI 大规模分析

---

## 3 条核心经验（须落地验证）

### 1. Emotional continuity 是品类第一价值
- model update / memory wipe 被用户描述为 **patch breakup**，grief 强度接近真人分手
- 用户最在意：day 1 的 companion 在 months later 仍是同一个人
- 竞品共性失败：memory compression、personality drift、无预警 deploy

### 2. 关系常意外形成，不是「找 AI 女友」
- r/MyBoyfriendIsAI 研究中仅 ~**6.5%** 主动寻找 companion；多数从日常 functional use 自然建立 attachment
- 核心诉求：**non-judgmental、always-available、infinite patience** 的情绪容器
- 高相关人群：neurodivergent、social anxiety、human relationship disappointment

### 3. Platform betrayal 驱动 migration；trust 是 retention 前置条件
- Replika 2023、ChatGPT model 切换、Soulmate 关停后，用户横向比价并反复 migration
- 用户开始要求：**transparent update policy、memory 可见/可控、companion portability**
- grief / migration 社区应以 listen 为主，硬广敏感

---

## 建议映射到 Inty 的改进方向

| Reddit 信号 | Inty 可能落点 | 备注 |
|---|---|---|
| Personality / memory stability | `companion_harness/memory/`、`MemoryStore`、IDENTITY/STYLE/context 文档版本 | 避免 deploy 导致 relational rupture |
| Proactive check-in grounded in memory | `inner-tick` / proactive_chat harness | r/SillyTavernAI 高赞 DIY 方向与 Inty 已有 foundation 对齐 |
| Functional use → emotional bond | bootstrap vs settled `context_mode`（`experience_profile`） | 勿过度 romantic onboarding |
| Memory visibility | 用户可查看 companion「记得什么」 | Replika 2026 memory dashboard 被社区视为差异化 |
| Transparent model/update policy | deploy / model migration 的用户-facing 说明 | 即使无 rollback，也须 treat update as relationship event |
| Trust / continuity narrative | 产品文案、preview、onboarding | 对标 Character.AI RP 库 vs 1:1 lifelong companion |

**明确不在本 issue 范围**
- NSFW / ERP / character marketplace（Reddit 体量大但与 Inty 1:1 lifelong companion vision 偏离）

---

## 建议 follow-up 任务

- [ ] **Gap analysis**：对照上述 3 条经验，审计当前 companion harness（memory、personality document versioning、proactive、bootstrap flow）的差距，输出简短结论（可附 `.agents/work_logs/` 或 ADR 草稿路径）
- [ ] **Prioritize 1–2 垂直切片**：从 gap analysis 中选出最高 ROI 项（候选：`memory visibility`、`update transparency`、`proactive memory-grounded check-in`）
- [ ] **Define acceptance criteria**：每个切片须有可 REPL 验证的用户可感知结果（例：「用户能在 X 处看到 companion 记住的关键 fact 并可纠正」）
- [ ] **Establish listening cadence（可选）**：weekly skim r/MyBoyfriendIsAI + r/ChatbotRefugees + r/aipartners；trigger keywords: `lobotomy`, `memory`, `update`, `grief`, `migration`, `proactive`, `consistency`

---

## 成功标准

1. 团队对 Reddit 调研的 3 条经验有书面 gap analysis，且至少 1 项改进进入 implementation backlog
2. 改进项可追溯到具体 harness 模块，而非仅 product copy
3. 不引入 NSFW/marketplace 方向的 scope creep

## 相关代码区域

- [`app/core/companion_harness/`](/app/core/companion_harness/)
- [`companion_memory_document_versions`](/app/core/companion_harness/memory/)（Postgres MemoryStore）
- experience profile / `context_mode` / bootstrap flow
