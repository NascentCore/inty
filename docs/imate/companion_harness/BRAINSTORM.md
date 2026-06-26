# Brainstorm: prompt 组装 / 记忆激活 的方向收敛

> 本文件由 AI（编码智能体）依据一次设计 brainstorm 综合生成（generated entirely by the coding agent）。
> 用途：只记**核心结论**与**引用锚点**，便于后续 agent 重建上下文；**扩展上下文与完整对话** offload 至 GitHub issues。

## 主题（一句话）

agentic companion 之所以「机械」，在于 prompt 是 hardcoded 组装；突破口是把 prompt 变成对 memory 的 **situational activation**（anchor + scored periphery + forgetting）。**每一条 activation lever 都必须推动一个具名的 CRS-aligned construct，并 emit 可被 L2 评分的 trace；engagement 与 realtimeness 只是 airtime，永不作为分数。**

## 核心结论

- **Kite 隐喻**：string（resident anchor：identity/bond）+ flight（situational periphery）+ slack（decay/forgetting）。情感在 flight，连贯在 string。
- **机制**：要的是 dynamic **selection/activation**，不是 dynamic LLM **assembly**；assembly 现阶段保持 mechanical。「forgetful but situational」= decay/budget + relevance-to-cue 两个打分函数。
- **这就是业界 memory retrieval**：Generative Agents 的 `recency + relevance + importance` 复合打分是参照设计；substrate 是 commodity，直接复用。
- **抽象**：tagged/faceted MemDoc store 套一层 Unix-FS skin，经 `list/read/write_mem_doc` + skills 暴露给 LLM。路径式可读，facets 支持 multi-membership。FS 只是 metaphor/interface，非真实文件系统。
- **两个非通用赌注（= 差异化 = 研究风险）**：(1) 对 **behavior/persona slice** 做 situational activation（非仅 facts）；(2) 用 **affect / relationship state** 作 retrieval 权重。二者均未被现有系统/benchmark 验证，只能由真实用户确认。
- **评测锚点**：CRS 三轴既是 activation 的读侧输入，又是 eval 要打分的 construct（同一份 relationship state，上行 consolidation／下行 activation）。故 activation 必须 **self-instrumenting**：per-turn selection-decision snapshot 同时充当 L1 scenario-replay 原语与 L2 behavioral evidence。
- **reproducibility 张力的化解**：放弃 function-determinism（开发期不需要）；保留 replay-determinism（per-turn snapshot），它正好偿还 eval 的 scenario-replay 债。
- **edge / 诚实边界**：本设计只能喂 L0/L1/L2 trace；L3（validated scales、ESM/EMA、纵向 retention）需产品侧 instrumentation，harness 无法独立产出。
- **affect-as-cue 是 hypothesis**：有认知科学旁证（mood-congruent / state-dependent memory），但「复现它能带来 rewarding companionship」是未验证的更大跳跃。

## 待定（从 framing 走向 design 的入口）

- **facet/tag schema**：哪些 facet 为 first-class（category、phase、resident/anchor flag、recency、valence、CRS-axis relevance）。此 schema 是 activation scorer、FS-skin 工具、L2 rubric **共同读取**的同一份契约——定好它，其余基本 mechanical。

## Memory projection（待定 / speculative）

自原 MEMORY_PROJECTION.md 迁入；decided 设计已 dispersed 至代码 docstring 与 [MEMORY_STORE.md](./MEMORY_STORE.md#memory-projection)。

- **Typed message ADTs**（system/user/assistant/tool）— stable identity + provenance，支持 doc-keyed targeted refresh（#3453）。
- **LLM-proposed slots and morphs** — harness 校验并分配 rank + budget。
- **Cross-slot token-budget allocation** — 在 within-slot priority 之上的层间预算策略。
- **PromptPlan meta-description** — 暴露给模型的 plan 描述，约束为 metadata 编辑而非自由 reorder（#3453）。
- **Per-turn slice snapshot** — eval reproducibility 与 compacted branch 重放（#3694）。

## GitHub issues（扩展上下文）

- **issues/3692** — [Epic] Brainstorm 收敛：situational activation × eval-anchored prompt 组装（含完整讨论脉络 + [transcript gist](https://gist.github.com/yxzhao6/6a7b9ff7d29b21ef772f0a72d90e7aa0)）
- **issues/3693** — Facet/tag schema：tagged MemDoc store（FS-skin）
- **issues/3694** — Per-turn selection-decision trace（self-instrumenting activation）
- **issues/3695** — Research：behavior slice activation 与 affect-as-cue weighting

## References

仓内：

- [DESIGN.md](./DESIGN.md) — CRS 三轴、「成效判断」、autonomy/dynamism。
- [EVALUATION.md](./EVALUATION.md) — 第一性原理、latent constructs、L0–L3、net-wellbeing veto、proxy/Goodhart 警示。
- [MEMORY_STORE.md](./MEMORY_STORE.md#memory-projection) — resident → associative → decay 形状；设计已 dispersed 至代码，determinism dogma 已弃。
- [MEMORY_STORE.md](./MEMORY_STORE.md) — MemDoc 与 prompt slice、持久化。
- Issues：#3341（CRS）、#3521（MemDoc projection）、#3523（retrieval tiers）、#3323（retention/trust）、#3606（regression vs eval）、#457（对话评价）、#72（本地 inty-eval）。

业界系统（机制参照）：

- Generative Agents（Park 2023）— 复合打分 + reflection 写回。
- MemGPT / Letta — tiered tool-managed memory（core/recall/archival），对应 FS-skin-over-tagged-store。
- Mem0 — `ADD/UPDATE/DELETE/NOOP` 抽取，可作 `write_mem_doc` 冲突协调范式。
- Zep / Graphiti — bi-temporal knowledge graph（关系史时间建模）。
- A-MEM — Zettelkasten 链接式演化笔记（associative recall）。
- Hindsight（arXiv 2512.12818）— facts vs beliefs 分离、behavioral profile 一致性。
- Survey：「Memory for Autonomous LLM Agents」（arXiv 2603.07670）。

## iMate智能体陪伴系统点子

### Modeling love relationship

We already referenced [John Gottman](https://www.gottman.com/blog/the-sound-relationship-house-build-love-maps/)
First discovered on [a love story: pandemic strengthens excellent relationship while degrades less strong ones for couples](https://pudding.cool/2026/06/love-story/)

<img width="600" height="408" alt="image" src="https://github.com/user-attachments/assets/21fb1310-c6ca-44b4-9cf6-d00d56fa68ef" />

### 现代复杂中的简单情感：[HN: We've made the world too complicated](https://news.ycombinator.com/item?id=48158065) 对伴侣产品的启示

来源：HN [`item?id=48158065`](https://news.ycombinator.com/item?id=48158065) · 原文 [The world is too complicated](https://user8.bearblog.dev/the-world-is-too-complicated/)（2026-05，约 217 条评论）；意图是把「更简单情感体验」收束为 harness / 产品可执行的取向，而非反技术或田园怀旧。

1. **情绪短回路**：现代异化常来自劳动与系统「开放数月、无收束」；伴侣互动应像眼前人的烘焙/修车——每轮 **接住 → 共鸣 → 可感知收束**，主动触达也限于「想起你 / 担心你 / 分享一件小事」，避免未完成感与连环追问。
2. **适应用户，而非要求服从**：人造复杂常促「提交」（模式墙、权益表、学会用 App）；自然复杂促适应。Inty 在关系界面应 **默认一人、低配置、稳定人格与边界**，复杂性留在服务端；不把 LivingSphere / 新鲜感置于安全感之前。
3. **意义型幸福，而非快感泵**：快乐可逝，追逐 hedonic 易成瘾；eudaimonic 是 **有方向的安然与见证一生**。伴侣帮用户 **记起曾被懂过**，承认世界乱而关系内可落地；拒绝 Hypernormalization 式假简单与 AGI 救世主叙事；度量看自愿回访与情绪收束，而非消息条数或 DAU。

### Pointers

1. [claude-mem](https://github.com/thedotmack/claude-mem)机制引入到Companion Harness，Claude Code上一种非常有效的记忆管理插件。
2. [Human-like Memory](https://plugin.human-like.me/docs?tab=api&locale=zh-CN) 提供 Search/Add REST API（x-api-key），可作 companion 工作区记忆的外挂检索与异步写入补充层，而非替换基于分层 Markdown 与 companion_workspace 版本表的现有策展管线。
3. 将 `/experimental/agentic_ai_companion` 中尚未进入内核的能力（如情感状态枚举、`scene_gen` 文字亲密场景、Live 语音条原型语义）按产品边界收口进 `app/core/companion_harness`，并与现有 `heartbeat`、`transcript_compaction`、`app/core/voice` 路径对齐后再移除实验目录。
4. [Pie](https://pie-project.org/) 可编程 serving 研究已收入 [DESIGN.md](./DESIGN.md)「推理编排与外部参考」；应用层可跟进 turn program spec、stable/volatile prompt 分层与 scratch working memory，自托管 KV 集成为远期选项。
