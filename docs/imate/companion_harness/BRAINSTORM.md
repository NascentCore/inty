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

## GitHub issues（扩展上下文）

- **issues/3692** — [Epic] Brainstorm 收敛：situational activation × eval-anchored prompt 组装（含完整讨论脉络 + [transcript gist](https://gist.github.com/yxzhao6/6a7b9ff7d29b21ef772f0a72d90e7aa0)）
- **issues/3693** — Facet/tag schema：tagged MemDoc store（FS-skin）
- **issues/3694** — Per-turn selection-decision trace（self-instrumenting activation）
- **issues/3695** — Research：behavior slice activation 与 affect-as-cue weighting

## References

仓内：

- [DESIGN.md](./DESIGN.md) — CRS 三轴、「成效判断」、autonomy/dynamism。
- [EVALUATION.md](./EVALUATION.md) — 第一性原理、latent constructs、L0–L3、net-wellbeing veto、proxy/Goodhart 警示。
- [MEMORY_PROJECTION.md](./MEMORY_PROJECTION.md) — 形状（resident → associative → decay）可用，determinism dogma 已弃。
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
