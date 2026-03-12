# FR_MEMORY_COMPACTION_STRATEGY

## 目标

在 `experimental/agentic_ai_companion` 中引入**可控、可解释、低延迟**的记忆压缩机制，让 agent 在长对话中仍能保持：

- 对用户稳定偏好/画像的连续记忆；
- 对关键事件（episodic）的可追溯记忆；
- 对当前未完成需求（open loops）的主动跟进能力。

## Online Research（筛选结果）

对比了近期主流方案：

1. **MemGPT（虚拟上下文/分页）**  
   优点：扩展性强；缺点：实现复杂，工程开销高，且对当前终端原型偏重。  
   参考：<https://openreview.net/forum?id=0Kk142lP62>

2. **纯 running summary（单摘要滚动）**  
   优点：简单；缺点：细节丢失严重，用户长期偏好与事件可追溯性弱。  
   参考：<https://developers.openai.com/cookbook/examples/context_summarization_with_realtime_api>

3. **分层记忆（episodic + semantic）+ 检索路由/反思机制**  
   优点：在“压缩率、可解释性、召回质量”之间平衡最好，尤其适合 companion。  
   参考：  
   - HiMem（分层长期记忆）：<https://arxiv.org/html/2601.06377v1>  
   - RAPTOR（递归抽象检索）：<https://arxiv.org/abs/2401.18059>  
   - Generative Agents memory（importance/recency/reflection）：<https://aidoczh.com/langchain/api_reference/_modules/langchain_experimental/generative_agents/memory.html>  
   - MemoryBank（长期陪伴 + 遗忘曲线）：<https://arxiv.org/abs/2305.10250>

## 结论：当前原型最适合的机制

选择：**“分层混合压缩（episodic + semantic + running summary）”**，并保持实现为轻量 deterministic 版本。

原因：

1. **符合 companion 目标**：不仅要“记住事实”，还要“记住关系中的事件与情绪轨迹”。  
2. **可解释**：每条压缩结果都有结构化字段（summary/facts/open loops），便于调试和评测。  
3. **可渐进升级**：当前可先用规则提取；后续替换为 LLM 提取器，不改整体接口。  
4. **工程成本可控**：不需要先引入复杂外部存储和分页 runtime，即可在 prototype 中验证收益。

## 如何落地到本目录

### 新增模块

- `memory_compaction.py`
  - `CompactionConfig`: 压缩预算配置
  - `CompactionState`: 运行摘要 + 情节记忆 + 语义记忆
  - `ConversationCompactor`: 超预算时压缩历史，生成 memory snapshot system message

### 运行时接入点

- `repl.py`：在每轮用户输入后、发起 LLM 请求前调用 `maybe_compact(...)`
- `chat.py`：新增 CLI 开关，默认关闭，实验时开启：
  - `--enable-memory-compaction`
  - `--memory-max-context-chars`
  - `--memory-keep-recent-messages`
  - `--memory-max-messages-per-episode`

## 实验验证建议

1. 构造 30+ 轮长对话，观察是否触发压缩；
2. 对比开启/关闭压缩时的上下文字符量与回复一致性；
3. 专项验证 open loops 是否被持续追踪（例如“你提醒我下班后放松”）。
