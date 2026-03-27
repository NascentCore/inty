# FR: Inty v2 陪伴优先的上下文边界设计（Companion-First Context Bounding）

> 范围：`experimental/inty_v2_text_chat_prototype`。  
> 目的：在控制 context rot 的同时，不牺牲 Inty v2 的核心体验——**响应速度**与**情感深度**。  
> 相关外部研究：Chroma Context Rot、Chroma Context-1 Agent Harness、Anthropic Contextual Retrieval、Anthropic Compaction。

---

## 1. 设计意图（Intent）

### 1.1 产品定位优先级（必须保持）

Inty v2 是陪伴 AI，不是通用助理。默认优先级固定为：

1. **响应速度**（低延迟、自然续聊）
2. **情感深度**（被理解、关系连续性）
3. 事实正确性与全面性（按用户意图触发增强）

结论：所有“助理型”检索技术都只能作为“能力增强层”，不能反客为主导致对话变慢、变硬、变机械。

### 1.2 问题定义

当前原型在 `intimate` 模式下会将多份记忆文档注入 system，随着时间增长易出现：

- 上下文膨胀（成本与延迟上升）
- 中段信息利用率下降（lost-in-the-middle）
- 干扰信息增多（context rot）

因此需要一个**有边界的上下文编排器**，而不是继续扩大窗口。

### 1.3 设计目标

- **Bounded by default**：每轮严格 token 预算，不依赖“模型号称超长窗口”。
- **Emotion anchored**：关系核心信息（边界、称呼、偏好、情感线索）优先保留。
- **Intent gated rigor**：仅在“事实型问题”上提升检索强度；闲聊不走重检索。
- **Progressive adoption**：可在当前文件化原型渐进落地，不要求先上 DB。

---

## 2. 采用技术与取舍（What to Adopt, What to Trim）

## 2.1 采用：Anthropic Contextual Retrieval（裁剪后）

采用点：

- 语义 + 词法混合召回（hybrid retrieval）
- 候选重排（rerank）后再注入
- 限制“注入包”大小，降低噪声

取舍：

- 不追求“覆盖所有相关文档”，优先“足够好且快”
- 陪伴轮次默认低 `top_k`，避免检索主导对话

## 2.2 采用：Conversation Compaction（增强情感保真）

采用点：

- 周期性压缩历史（summary/compaction）
- 维持短窗口对话可续接

取舍：

- 压缩时保留情感轨迹字段（心境变化、关系事件、边界变化），不做纯事实摘要
- 禁止把全部细节都挤进摘要，避免“冷冰冰档案化”

## 2.3 采用：Context-1 Agent Harness（轻量形态）

采用点：

- observe-reason-act 的检索回路思想
- token 预算可见性
- 软阈值/硬阈值治理
- 自编辑上下文（prune）
- 去重与“已见 chunk 排除”

取舍：

- 默认不走多跳复杂检索；仅在事实型意图或用户明确要求深挖时启用
- 不引入重型多 agent 编排；先在单进程原型内实现轻量 memory harness

---

## 3. Companion-First 上下文边界策略（目标态）

## 3.1 全局 token 预算（每轮）

建议默认预算（可配）：

- `TOTAL_INPUT_BUDGET_TOKENS = 6500`
- `OUTPUT_RESERVE_TOKENS = 1200`
- `USABLE_INPUT_BUDGET_TOKENS = 5300`

分配建议：

- 安全基座 + 关系契约（IDENTITY/SOUL 核心）: 1100
- USER 核心画像：700
- Memory pack（检索注入包）：1200
- Transcript 窗口：2000
- 机动余量：300

规则：

- 超限时先裁剪 Memory pack，再裁剪 transcript 老消息；
- 不裁剪底线/边界/关系核心承诺。

## 3.2 双路径响应

- **Path A（默认，陪伴快聊）**：单次轻检索或零检索，直接回复。
- **Path B（事实增强）**：触发 hybrid retrieval + rerank + 可选一轮 prune 后回复。

意图判定触发词（示例）：

- 事实型：比较、统计、列出依据、精确日期、原文核对、是否包含、给出处
- 陪伴型：情绪表达、关系互动、安慰、日常闲聊、轻主题聊天

## 3.3 Memory pack 结构

每轮注入不再是“整篇 MEMORY.md”，而是固定小包：

1. `core_anchor`（必带，短）：边界、称呼、禁忌、稳定偏好
2. `emotion_anchor`（必带，短）：近几轮情绪状态与互动目标
3. `situational_facts`（按需）：与当前问题最相关的事实片段（top-k）
4. `fresh_delta`（可选）：当日新变化（限制条数）

约束：

- 总条数建议 `6~10`
- 单条建议 `60~180 tokens`
- 去重（语义近似 + 文本近似）

## 3.4 检索与重排

候选生成：

- lexical（BM25/关键词）
- semantic（embedding）
- pinned（core anchors）

融合与重排：

- RRF 融合候选
- rerank 分数 = relevance + salience + recency - contradiction_penalty - redundancy_penalty

多样性约束：

- 同一类型片段最多 2 条
- 同一来源文档最多 2 条

## 3.5 自编辑上下文（prune）

当 token 使用超过软阈值时，允许（或自动触发）prune：

- 移除低分片段
- 移除重复片段
- 保留 core/emotion anchors

硬阈值后：

- 禁止新增检索结果
- 仅允许 prune 或直接生成最终回复

## 3.6 去重与排重探索

为每轮维护 `seen_chunk_ids`：

- 后续检索默认排除已见 chunk
- 减少反复取回同样内容，提升探索效率与响应速度

---

## 4. 分阶段实施计划（Plan）

## Phase 0：观测与护栏（无行为变更）

目标：先量化再改行为。

实施：

- 增加每轮 token 构成日志（各 section 占比）
- 增加候选记忆统计（召回数、去重后数、最终注入数）
- 增加延迟拆分（检索耗时/模型耗时）

验收：

- 能稳定输出每轮 context 体积画像
- 无用户可见行为变化

## Phase 1：硬预算 + transcript token 窗口

目标：先把“无上限增长”变成“稳定上限”。

实施：

- 引入总预算与 section quota
- transcript 从“按消息条数”改为“按 token”
- 超限裁剪顺序固定（memory -> transcript old）

验收：

- 超长会话下输入 token 波动收敛
- 延迟尾部（p95）下降或不升

## Phase 2：Companion-first memory pack（轻检索）

目标：把整篇记忆注入替换为小包注入。

实施：

- 生成 `core_anchor + emotion_anchor + situational_facts + fresh_delta`
- 上线 hybrid retrieval + 基础 rerank
- 默认 `top_k` 小值（陪伴优先）

验收：

- 回复情感连贯性不下降
- context 体积显著下降

## Phase 3：软/硬阈值 + prune + seen 排重

目标：引入 Context-1 风格主动治理能力。

实施：

- token 可见性
- soft/hard threshold 机制
- prune 动作 + seen 排重过滤

验收：

- 长会话下检索噪声比例下降
- 中后段轮次回复质量更稳定

## Phase 4：意图门控的事实增强路径

目标：把助理型能力限定在需要时触发。

实施：

- intent gate（事实型触发深一档检索）
- 陪伴型维持快路径

验收：

- 陪伴型平均响应时间保持目标
- 事实型问题可用性提升

---

## 5. 计划审查（Plan Review）

## 5.1 审查维度

每个 phase 合并前必须通过以下审查：

1. **体验审查**：回复是否仍自然、有温度、非“检索报告体”。
2. **性能审查**：是否引入明显延迟回归。
3. **记忆审查**：核心关系信息是否被错误裁剪。
4. **风险审查**：是否出现“为了准确性牺牲陪伴感”。

## 5.2 量化门槛（建议）

- p95 响应时延：不高于基线 +15%
- 平均输入 token：较基线下降 25% 以上（长会话场景）
- 情感连续性人工评分：不低于基线
- 事实型任务命中率：不低于基线（Phase 4 需高于基线）

## 5.3 Go / No-Go 规则

- 任一阶段若“情感连续性下降”且无补偿收益，**No-Go**。
- 任一阶段若 p95 延迟显著恶化且无法通过参数回调修复，**No-Go**。
- 阶段性功能可由 env flag 一键关闭并回退到旧路径。

## 5.4 回滚策略

- 所有新行为必须挂在独立开关下（默认灰度）
- 保留旧 prompt 拼装路径，直到新路径完成两轮稳定观察

---

## 6. 与当前原型的对齐点（落地提示）

- 现有 `memory_update` 的日记/当日总结/长期策展可作为 compaction 基础，不推翻重做。
- 现有 transcript 窗口策略可演进为 token 窗口策略。
- 现有 system prompt 拼装可改为“注入 memory pack”而非整篇记忆注入。

---

## 7. 一句话结论

这份方案不是把 Inty v2 改造成“检索型助理”，而是把助理领域的上下文治理技术改造为**陪伴优先**版本：在 bounded context 下保持快、暖、稳，同时在需要时再提升事实能力。
