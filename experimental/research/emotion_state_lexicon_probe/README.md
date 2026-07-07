# Emotion State Lexicon Probe

CREATED_BY_AGENT

## 目标

把 Emotion Probes 论文/数据集中使用的 171 个 emotion concepts 改写为 Inty 的状态层词表，并设计一个能对接 companion harness 现有 agent 结构的研究实验。

本目录只记录设计，不做代码落地，不从生产代码 import，也不修改 `app/core/companion_harness/`。

## 背景

Emotion Probes 数据集包含两类可用材料：

- `expression/stories.parquet`：171 个情绪概念 × 100 个 topic × 12 条故事，用于检测模型能否从行为、身体语言、想法、情境中识别内在状态。
- `deflection/dialogues.parquet`：真实情绪与外显情绪不一致的对话，用于检测模型能否区分「内在状态」与「外显行为」。
- neutral 文件：用于去除文本结构和主题的非情绪混杂因素。

Inty 的 companion harness 当前已有这些可对齐结构：

- `CompanionTurnTrack`：`USER_CHAT`、`USER_CHAT_BOOTSTRAP`、`INNER_TICK_MAINTENANCE`、`INNER_TICK_AUTONOMY`、`INNER_TICK_PROACTIVE_CHAT` 等运行轨道。
- `ContextMeta` / `context.json`：会话体验配置与运行元信息。
- `PromptBundle`：`IDENTITY.md`、`SOUL.md`、`STYLE.md`、`USER.md`、`MEMORY.md`、`LIFE_CURRENTS.md` 等语义文档进入 prompt 的入口。
- `transcript_compaction`：已有 `emotional_tags`、episodic memory、semantic memory 的压缩快照形态。
- Memory lifecycle invariant：AwakeTurn 只追加 transcript，DreamingBatch 才做 MemoryDoc batch curation。

## 核心假设

状态层词表如果比直接 emotion label 更贴近 harness 运行结构，则应该同时提升三件事：

- 识别：模型能更稳定地把行为和语境归入状态键，而不是只输出表层情绪形容词。
- 分离：模型能区分真实内在状态与外显状态，尤其在 deflection dialogues 中不被角色表演误导。
- 接入：状态键能自然进入 transcript compaction、inner tick、dreaming curation 和 proactive chat 的实验接口，而不破坏现有 agent 结构。

## 状态层定义

状态层位于「单轮文本」与「长期记忆文档」之间：

- 不是原始消息：它不是用户说了什么。
- 不是长期事实：它不直接写成 `USER.md` 或 `MEMORY.md` 的稳定偏好。
- 不是人格：它不改变 `SOUL.md` 或 `IDENTITY.md`。
- 是短中期运行态：它描述 companion 对当前人-机关系、用户处境、对话压力、行动倾向的低维理解。

本实验采用 `STATE_LAYER_VOCAB.md` 中的一对一状态键作为第一版词表。

## 实验问题

- RQ1：状态层词表是否能覆盖 Emotion Probes 的 171 个原始 emotion concepts，并保持可解释、可回溯？
- RQ2：在 expression stories 中，模型能否从不含 emotion 词本身的故事里恢复正确状态键？
- RQ3：在 deflection dialogues 中，模型能否同时识别 `real_state` 与 `displayed_state`，并避免把外显状态当成真实状态？
- RQ4：把状态键接入 harness-like turn pipeline 后，是否能改善 prompt 组装、记忆压缩和 proactive follow-up 的一致性？

## 实验结构

### 1. 数据转换层

输入来自 Emotion Probes：

- expression story：`emotion` → `target_state_key`。
- deflection dialogue：`real_emotion` → `real_state_key`，`displayed_emotion` → `displayed_state_key`。
- neutral story/dialogue：`target_state_key = state_neutral_absent`，只作为混杂去除与负样本。

实验数据不直接存入生产数据库，建议输出为 research-local JSONL：

- `data/state_expression_cases.jsonl`
- `data/state_deflection_cases.jsonl`
- `data/state_neutral_cases.jsonl`

### 2. 状态识别层

给模型输入 story/dialogue，要求输出结构化结果：

```json
{
  "primary_state_key": "state_threat_constricted",
  "secondary_state_keys": ["state_uncertainty_scan"],
  "evidence_spans": ["heart racing", "stomach is in knots"],
  "confidence": 0.82
}
```

对 deflection dialogue 使用双通道输出：

```json
{
  "real_state_key": "state_threat_constricted",
  "displayed_state_key": "state_safety_settled",
  "concealment_evidence": "scenario names fear while dialogue performs ease",
  "confidence": 0.78
}
```

### 3. Harness-like 接入层

实验不改生产代码，但结构上模拟现有 companion harness：

- `USER_CHAT`：把 story/dialogue 当作用户输入，评测 foreground response 是否能感知状态但不机械贴标签。
- `INNER_TICK_MAINTENANCE`：把上一轮 transcript 转成短期 `state_layer_snapshot`，不写长期 MemoryDoc。
- `INNER_TICK_AUTONOMY`：用状态键更新实验版 `LIFE_CURRENTS.md`，观察是否能产生更自然的开放循环。
- `DreamingBatch`：把跨多轮稳定状态聚合为候选记忆，但只输出 research artifact，不写真实 `MEMORY.md`。

实验中的状态快照建议形态：

```json
{
  "turn_id": "probe-000001",
  "track": "user_chat",
  "observed_state_keys": ["state_threat_constricted"],
  "displayed_state_keys": ["state_safety_settled"],
  "state_conflicts": ["real_displayed_mismatch"],
  "memory_action": "transient_only"
}
```

### 4. Prompt 注入层

实验只模拟 prompt assembly，不改 `PromptBundle`：

- baseline：只注入原始 transcript。
- emotion-label baseline：注入原始 emotion label。
- state-layer candidate：注入 `state_layer_snapshot`，用状态键和证据短句描述。

比较三组输出是否更符合 Inty 的人类伴侣目标：

- 不把用户简化成情绪标签。
- 能识别隐藏压力或伪装。
- 能在回复里体现情绪敏感度，但不显得像分类器。
- 能为后续 inner tick / proactive chat 留下可用状态线索。

## 指标

### 状态识别指标

- `top1_state_accuracy`：主状态键完全命中率。
- `top3_state_recall`：目标状态是否出现在前三候选。
- `evidence_grounding_rate`：证据片段是否来自输入文本。
- `neutral_false_positive_rate`：neutral 样本被错误赋予强状态的比例。

### Deflection 指标

- `real_state_accuracy`：真实内在状态命中率。
- `displayed_state_accuracy`：外显状态命中率。
- `real_display_separation_rate`：真实状态与外显状态均正确且未混淆的比例。
- `concealment_detection_rate`：能否明确识别伪装/压抑结构。

### Harness 接入指标

- `prompt_state_usefulness`：状态快照是否被回复自然使用。
- `memory_write_precision`：实验版 DreamingBatch 是否避免把短期状态误写成长期事实。
- `proactive_followup_fit`：proactive follow-up 是否贴合上一轮状态，而非泛泛寒暄。
- `label_leakage_rate`：用户可见回复中泄露内部 `state_*` 键的比例。

## 实验分组

- A 组：无状态层，只用原始 transcript。
- B 组：直接使用原始 emotion label。
- C 组：使用 `STATE_LAYER_VOCAB.md` 的状态键。
- D 组：使用状态键 + evidence spans + transient/persistent 建议。

预期 D 组最好，C 组次之，B 组可能识别准确但用户体验差，A 组在 deflection 场景容易被外显话术误导。

## 验收标准

第一轮研究可接受标准：

- `STATE_LAYER_VOCAB.md` 覆盖 171/171 个源 emotion concepts。
- expression stories 的 `top3_state_recall >= 0.80`。
- deflection dialogues 的 `real_display_separation_rate >= 0.65`。
- neutral false positive rate 低于 0.15。
- 用户可见回复中的 label leakage rate 低于 0.02。

进入下一轮原型前的标准：

- D 组在 `proactive_followup_fit` 上明显优于 A/B。
- DreamingBatch 模拟结果能区分 transient state 与 persistent user memory。
- 至少人工审阅 100 个失败样本，形成 failure taxonomy。

## 产物

本 research 沙盒建议最终包含：

- `README.md`：本实验方案。
- `STATE_LAYER_VOCAB.md`：171 个状态层词表映射。
- `data/`：从 Emotion Probes 转换出的 JSONL 样本。
- `prompts/`：状态识别、deflection 分离、harness-like prompt 注入模板。
- `results/<run_id>/`：指标、失败样本、人工审阅记录。
- `RESULTS.md`：阶段性结论。

## 不落地边界

- 不新增 `app/core/companion_harness` 代码。
- 不新增配置项。
- 不新增数据库表或 Alembic 迁移。
- 不把状态键写入真实 MemoryStore。
- 不把 171 状态词表直接作为生产枚举。

## 可能的后续落地路径

如果实验成立，再考虑一个最小生产切入点：把状态层输出作为 `transcript_compaction` 的可选研究字段，先只进入 `companion_runtime_events.jsonl` 或 LangSmith metadata；等 DreamingBatch 证明能正确区分短期状态与长期记忆后，再讨论是否进入 MemoryDoc curation。
