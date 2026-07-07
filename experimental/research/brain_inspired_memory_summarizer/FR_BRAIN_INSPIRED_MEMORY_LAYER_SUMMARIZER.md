# Inty v2：脑启发式多层记忆总结器

> 目标：参考人脑不同记忆层（工作记忆、情景记忆、语义记忆、情绪显著性与离线巩固），为 `experimental/inty_v2_text_chat_prototype` 设计可渐进落地的多层记忆总结架构。  
> 对齐文档：`INTY_v2_DESIGN.md`、`INTY_v2_CORE_AGENTIC_COMPONENT_TECH_ARCHITECTURE.md`、`INTY_v2_CORE_AGENTIC_COMPONENT_TECH_PROTOTYPE.md`。  
> 范围：先服务**文本对话原型**（文件持久化、无数据库），但接口与分层命名保持可迁移到正式后端。

---

## 1. 设计成功标准（先于实现）

要认为该设计“有效”，至少满足以下可验证标准：

1. **层次清晰**：每层记忆有明确“输入、存储介质、更新频率、过期/保留策略、注入策略”。
2. **与现状兼容**：能直接映射到当前原型文件与模块（`transcript.jsonl`、`memory/daily`、`memory/YYYY-MM-DD.md`、`MEMORY.md`、`USER.md`、`SOUL.md`；`memory_update.py` / `prompts.py` / `orchestrator.py`）。
3. **可增量上线**：先不引入数据库也能实现“多层总结器核心价值”（减少遗忘、减少错记、提升跨天连续性）。
4. **可观测可验收**：有明确指标与测试步骤，能证明“该层是否真的被写入/读取/影响回复”。

---

## 2. 人脑记忆分层（工程抽象版）

下表是用于工程映射的“认知神经科学抽象层”，不是 1:1 生物学复制。

| 人脑层（抽象） | 核心功能 | 典型时间尺度 | 工程启示 |
|---|---|---|---|
| 感觉寄存（sensory buffer） | 短暂保留瞬时输入 | 毫秒到秒 | 输入先落“原始事件层”，避免过早总结丢细节 |
| 工作记忆（working memory） | 当前任务上下文维持与操作 | 秒到分钟 | 每轮 prompt 必带“短窗口对话上下文” |
| 情景记忆（episodic） | 带时间/场景线索的事件记忆 | 小时到天 | 保留按时间排序的对话事件，支持回放与纠错 |
| 语义记忆（semantic） | 抽象后的稳定知识/偏好 | 天到长期 | 将高价值重复信息固化成“长期事实层” |
| 自我/价值脚本（self-schema） | 稳定边界、价值、行为准则 | 长期稳定 | 将不可频繁抖动的“人格与底线”与事实层分离 |
| 情绪显著性调制（amygdala-like salience） | 提高高情绪/高风险事件保留优先级 | 编码时即时发生 | 增加显著性评分，驱动“何时入长期层” |
| 系统巩固（hippocampus→neocortex-like consolidation） | 离线重放、整合、去冲突 | 睡眠/离线周期 | 用异步/低频批处理做“日总结→长期定稿” |

---

## 3. Inty v2 原型中的多层映射（建议作为 v2 记忆主干）

### 3.1 现有文件层的重新命名（保持兼容）

| 层级 | 原型文件/结构 | 建议角色命名 | 更新时间 |
|---|---|---|---|
| L0 | 本轮用户输入 + 助手输出（内存态） | 感知/轮次缓冲（瞬时） | 每轮 |
| L1 | `transcript.jsonl` | 原始情景事件流 | 每轮追加 |
| L2 | `memory/daily/YYYY-MM-DD.md` | 当日事件账本 | 每轮追加 |
| L3 | `memory/YYYY-MM-DD.md` | 当日巩固摘要 | 每 N 轮重写 |
| L4 | `MEMORY.md` | 长期语义记忆 | 每轮/每 N 轮重写 |
| L5 | `USER.md` | 用户画像与偏好 | 每 N 轮重写 + 工具增量写 |
| L6 | `SOUL.md` | 价值与边界 | 低频重写（当前每轮，可下调） |

> 当前代码已具备 L1-L6 的基础形态；本提案重点是把这些层“系统化”，并补上显著性打分与分层注入策略。

### 3.2 与现有模块的直接对应

- `orchestrator.run_turn`: L0 组装、L1 追加、触发记忆管线。
- `memory_update_after_turn`: L2/L3/L4/L5/L6 巩固主流程。
- `prompts.build_system_prompt`: 读取/注入 L3/L4/L5/L6（及可选 L2）到回复模型。
- `.inty_v2_memory_pipeline.json`: 可继续作为“巩固节拍计数器”。

---

## 4. 脑启发式“多层总结器”核心机制

## 4.1 机制 A：显著性驱动（显著性门控编码）

### 为什么需要
人脑不会把所有事件等权存长期记忆；情绪强度、目标相关性、重复性会影响编码概率。

### 工程规则（建议）
对每一轮计算 `salience_score`（0~1），由以下因子线性/加权组成：

- `emotion_intensity`：用户显著情绪表达（积极/消极都可）。
- `novelty`：与现有 `MEMORY.md` / `USER.md` 的差异度。
- `commitment_signal`：承诺、约定、明确偏好（“以后都这样叫我”）。
- `boundary_signal`：安全边界、拒绝、不可做事项（优先写入 SOUL）。
- `recurrence`：近期多次重复提及（重复越多越应固化）。

按阈值路由：

- `score < t1`：仅保留在 L1/L2，不入 L4/L5/L6。
- `t1 <= score < t2`：候选进入 L3（日级摘要层）。
- `score >= t2`：直接触发 L4/L5/L6 更新（依类别落层）。

### 可执行默认值（v0）

为避免多实现漂移，先给一套默认可落地参数：

- 归一化公式：  
  `salience_score = Σ(w_i * f_i)`，其中 `f_i ∈ [0,1]`。
- 默认权重（总和 1.0）：
  - `w_emotion_intensity = 0.20`
  - `w_novelty = 0.20`
  - `w_commitment_signal = 0.25`
  - `w_boundary_signal = 0.25`
  - `w_recurrence = 0.10`
- 默认阈值：
  - `t1 = 0.35`
  - `t2 = 0.65`
- 强制优先规则（硬编码）：
  - 若 `boundary_signal >= 0.70`，无论总分如何，必须进入 L6（SOUL）候选。
  - 若 `commitment_signal >= 0.80` 且 `novelty >= 0.50`，至少进入 L5（USER）候选。

### 校准协议（避免拍脑袋）

- 每周抽样 100 条候选轮次，由人工标注“应/不应入长期层”。
- 以 F1 为目标调权重；`precision < 0.7` 优先提高 `t2`，`recall < 0.7` 优先降低 `t1`。
- 每次只改一个参数并记录变更日志（含前后指标），避免多变量混淆。

## 4.2 机制 B：分层巩固节拍（多时间尺度巩固）

建议将当前“基本每轮都策展”改成多节拍：

- **快节拍（每轮）**：L1、L2 必做；L4 可按需增量更新。
- **中节拍（每 N 轮）**：L3、L5 更新（当前已有环境变量）。
- **慢节拍（每 M 轮或每天）**：L6（SOUL）审慎更新，避免人格抖动。
- **超慢节拍（每周）**：对 L4/L5 去重、冲突修正、陈旧信息降权（可后续引入）。

### 可执行默认值（v0）

- `N = 12`（每 12 轮执行一次 L3/L5 巩固）。
- `M = 72`（每 72 轮执行一次 L6 审核式巩固）。
- 周级回顾：每 7 天执行一次（可由定时任务触发）。

### 新鲜度 SLO（防止过期）

- L4（MEMORY）目标最大陈旧度：`<= 30` 轮。
- L5（USER）目标最大陈旧度：`<= 24h` 或 `<= 100` 轮（先到先触发）。
- L6（SOUL）目标最大陈旧度：`<= 72h`，但边界事件必须“即刻候选、下个巩固周期必落盘”。

## 4.3 机制 C：记忆类型分流（按类型路由）

同一轮信息进入不同层：

- “事实/偏好/生活规律” → L5（USER）+ L4（MEMORY）。
- “关系大事/共同经历” → L3（日摘要）再沉淀到 L4。
- “边界/价值/不可逾越” → L6（SOUL）优先。
- “纯闲聊噪声” → L1/L2 即可，不必升层。

## 4.4 跨层冲突不变量（必须满足）

为避免“记忆自相矛盾”导致危险回复，定义以下硬约束：

1. **边界优先于偏好**：L6（SOUL）与 L5/L4 冲突时，L6 永远优先。
2. **新事实优先于旧事实**：同一 key 多版本冲突时，以最新且证据完整的一条为准。
3. **禁止同轮自相矛盾落盘**：若同一轮提取出互斥事实，必须先进入冲突队列，不得直接写入长期层。

### 冲突修复流程（写入前）

1. 候选阶段做冲突检测（例如 `preferred_name=宝贝` 与 `boundary=不要叫我宝贝`）。
2. 触发规则修复：
   - 将冲突项写入 `conflict_reason`。
   - 对被否决事实打 `superseded_by` 或 `invalidated_by_boundary=true`。
3. 仅修复后的候选允许进入 L4/L5/L6。
4. 审计日志必须可追溯到源轮次（见 §6 字段约定）。

---

## 5. 提示词注入策略（按层检索）

为避免上下文爆炸与记忆污染，注入时按层筛选而非“全塞”。

### 5.1 建议注入优先级（文本对话）

1. `SOUL.md`（L6，稳定约束，优先级最高）
2. `USER.md`（L5，用户偏好与相处协议）
3. `MEMORY.md`（L4，长期关系事实）
4. 当日 `memory/YYYY-MM-DD.md`（L3，当日主题）
5. 最近 `transcript` 窗口（L1，现场语境）
6. 原始日记（L2）只在需要“细节对账”时注入片段，不默认整段注入

### 5.2 上下文模式（`context_mode`）策略

- `intimate`: 可注入 L3/L4/L5/L6 全量（仍需长度上限）。
- 非 `intimate`: 默认降级 L3/L4 的私密细节，仅保留 L5/L6 的必要约束与通用偏好。

---

## 6. 数据结构建议（原型阶段可先文件化）

在不改数据库前提下，可新增一个轻量候选队列文件：

- `.inty_v2_salience_queue.jsonl`（建议）
  - 必需字段：
    - `turn_uuid`
    - `ts`
    - `salience_score`
    - `salience_factors`（各分量值，便于解释分数）
    - `type_tags`
    - `candidate_facts[]`
    - `candidate_boundaries[]`
    - `source_span`（源消息区间，如 transcript msg uuid 范围）
    - `evidence_snippet`（短证据文本）
    - `confidence`
    - `conflict_reason`（无冲突可为空）
    - `superseded_by`（若被后续事实覆盖）
    - `invalidated_by_boundary`（布尔）
  - 用途：给 L3/L4/L5/L6 巩固器做“有筛选的输入”，替代直接吃整段 raw 文本

这一步可显著降低 LLM 策展噪声，并让“为什么被记住”可审计。

---

## 7. 分阶段落地计划（对当前原型的最小侵入）

## 阶段一：仅加「显著性打分 + 路由」，不改现有文件契约

- 在 `memory_update.py` 中新增 `score_turn_salience(...)`。
- 生成候选事件并写 `.inty_v2_salience_queue.jsonl`。
- L3/L4/L5/L6 的 prompt 输入优先使用候选事件，再回退原文。

**验收**：同样轮次下，`MEMORY.md` 重复噪声下降，关键偏好命中率上升。

## 阶段二：将 SOUL 更新改为低频 + 触发式

- 默认不再每轮重写 SOUL；仅当 `boundary_signal`/`safety_signal` 触发或达到慢节拍。
- 维持已有禁用开关兼容。

**验收**：`SOUL.md` 日内变更次数明显下降，且边界条目不丢失。

## 阶段三：引入「周级回顾总结器」（可选）

- 每周对 L4/L5 做冲突合并、降权和归档摘要（仅文档层，不上向量库）。

**验收**：长期文档长度可控，冲突条目减少。

---

## 8. 测试与可观测建议

## 8.1 自动化测试（建议新增）

- `test_memory_salience_routing.py`
  - 断言高显著性轮次会进入候选队列并触发 L4/L5/L6 对应更新。
- `test_soul_update_triggered_only_by_boundary.py`
  - 断言无边界变更时 SOUL 不更新。
- `test_prompt_layer_injection_policy.py`
  - 断言不同 `context_mode` 下注入层集合符合策略。
- `test_memory_conflict_resolution.py`
  - 断言边界与偏好冲突时，边界优先、冲突项不会直接落盘。
- `test_memory_freshness_slo.py`
  - 断言超过 SLO 时会触发对应层刷新任务。

## 8.2 运行时日志字段（建议补充）

- `salience_score`
- `memory_route`（L2-only / L3 / L4 / L5 / L6）
- `consolidation_cycle`（fast / mid / slow）
- `memory_items_selected_n`（每层）

---

## 9. 与神经科学启发的一致性（简要）

- **系统巩固（类睡眠重放）**：对应本方案的中慢节拍总结（L2→L3→L4/L5/L6）。
- **情绪显著性调制**：对应 `salience_score` 与边界/情绪触发路由。
- **工作记忆容量受限**：对应提示词中只保留 `transcript` 窗口，不无限扩展。

> 说明：这里采用的是“工程启发”，不是对脑机制的严格生理建模。

---

## 10. 外部资料（用于本设计调研）

- 《自然·神经科学》：睡眠中系统记忆巩固的机制（2019）  
  https://www.nature.com/articles/s41593-019-0467-3
- 《神经元》：睡眠——服务于系统记忆巩固的脑状态（2023）  
  https://www.cell.com/neuron/fulltext/S0896-6273(23)00201-5
- 《神经科学年鉴》：杏仁核调节情绪唤醒经历记忆的巩固  
  https://annualreviews.org/content/journals/10.1146/annurev.neuro.27.070203.144157

---

## 11. 一句话收束

把 Inty v2 记忆从“单一总结文档”升级为“多时间尺度、按显著性路由、按类型分层注入”的记忆系统：既保留关系连续性，也降低噪声与人格漂移风险，并且可在当前文件化原型中渐进落地。

---

## 12. 实现清单 v0（文件级落地）

本节用于把本文直接转为工程任务；默认目标目录为 `experimental/inty_v2_text_chat_prototype/`。

### 12.1 `memory_update.py`

- [ ] 新增 `score_turn_salience(user_text: str, assistant_text: str, ...) -> SalienceScore`  
  - 输出总分 + 分项（`emotion_intensity`、`novelty`、`commitment_signal`、`boundary_signal`、`recurrence`）。
- [ ] 按 §4.1 默认权重与阈值实现路由（`t1/t2` + 强制优先规则）。
- [ ] 新增候选构建函数：`build_memory_candidates(...) -> MemoryCandidateEvent`。
- [ ] 写入 `.inty_v2_salience_queue.jsonl`（追加 JSONL，不覆盖）。
- [ ] 在 L4/L5/L6 重写前增加冲突检测与修复（§4.4）：
  - 冲突项标注 `conflict_reason`。
  - 被否决事实写 `superseded_by` 或 `invalidated_by_boundary=true`。
  - 未修复冲突不得进入长期层写入步骤。
- [ ] 巩固节拍接入默认值：
  - `N=12`（L3/L5）
  - `M=72`（L6）
  - 保持现有 env 变量可覆盖默认值。
- [ ] 增加新鲜度检查器（SLO）：
  - L4/L5/L6 超阈值时强制触发对应刷新。

### 12.2 `models.py`（或等价类型定义文件）

- [ ] 定义类型：
  - `SalienceScore`
  - `MemoryCandidateEvent`
  - `ConflictResolutionResult`
- [ ] 为候选事件数据结构增加可验证字段（§6 必需字段）。
- [ ] 保证 JSON 序列化字段稳定（便于日志/审计消费）。

### 12.3 `prompts.py`

- [ ] 调整注入策略与顺序，确保与 §5 一致：
  - `SOUL` > `USER` > `MEMORY` > 日摘要 > `transcript`。
- [ ] `context_mode != intimate` 时降级注入私密层内容。
- [ ] 支持“候选优先、原文回退”的记忆输入源选择。

### 12.4 `orchestrator.py`

- [ ] 在 `run_turn` 里补充可观测字段透传：
  - `memory_route`
  - `consolidation_cycle`
  - `memory_items_selected_n`
- [ ] 保持「助手落库唯一路径」不变（不得绕开现有约束）。

### 12.5 新增测试（`experimental/inty_v2_text_chat_prototype/tests/`）

- [ ] `test_memory_salience_routing.py`
- [ ] `test_memory_conflict_resolution.py`
- [ ] `test_soul_update_triggered_only_by_boundary.py`
- [ ] `test_memory_freshness_slo.py`
- [ ] `test_prompt_layer_injection_policy.py`

每个测试至少包含：
- 输入轮次（含冲突与覆盖场景）。
- 期望落层结果。
- 期望注入结果。
- 期望日志字段（最小集合）。

### 12.6 运行与灰度开关（环境变量）

- [ ] `INTY_V2_PROTO_MEMORY_LAYERING_ENABLED`（总开关）
- [ ] `INTY_V2_PROTO_SALIENCE_ENABLED`
- [ ] `INTY_V2_PROTO_CONFLICT_GUARD_ENABLED`
- [ ] `INTY_V2_PROTO_FRESHNESS_SLO_ENABLED`
- [ ] `INTY_V2_PROTO_MEMORY_N` / `INTY_V2_PROTO_SOUL_M`（覆盖默认节拍）

建议灰度顺序：
1. 仅记录分数与候选（不影响写入）
2. 打开路由（影响 L3/L4/L5）
3. 打开冲突守卫（影响 L4/L5/L6）
4. 打开 SLO 强刷

### 12.7 交付验收（完成定义）

- [ ] 在固定回放数据集上，`MEMORY.md` 重复行下降且关键偏好命中率上升。
- [ ] 冲突场景下不再出现“边界与偏好同时矛盾落盘”。
- [ ] `SOUL.md` 更新频率低于基线，但边界事件无漏记。
- [ ] 日志可追溯任一长期记忆项来源 turn（`source_span` + `evidence_snippet`）。
- [ ] 所有新增测试通过，且不破坏已有 `test_day_summary_interval.py` / `test_user_update_interval.py` / `test_soul_memory_update.py`。

