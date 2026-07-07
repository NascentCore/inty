# 脑启发式记忆总结器：实验设计

## 目标

验证「脑启发式分层记忆」智能体能否：

1. 相比**短上下文基线**提升记忆问答准确率；
2. 在**更少上下文**下达到与**长上下文基线**相当的准确率。

## 假设

- **H1（准确率）**：`layered_memory` 准确率 **高于** `baseline_small_window`。
- **H2（上下文效率）**：`layered_memory` 平均每题上下文字符数 **少于** `baseline_large_window`。
- **H3（综合）**：`layered_memory` 在缩小上下文的同时仍保持较高准确率。

## 对照设置

- **合成、确定性对话**，包含：
  - 较早引入的记忆事实；
  - 一次覆盖（同一槽位、较新值）；
  - 较长干扰尾部，使早期事实滑出短窗口。
- 针对最终稳定事实的**确定性问答集**。
- **抽取形态全部为 LLM 式**：槽位、路由、情景输出均按真实 LLM 的 JSON 解析。捆绑基准对**数据集每一行**使用**固定 JSON 桩**（`main.benchmark_*_by_line`），故 `main.py run` **无需 API key**，且可复现。
- 配置 `OPENROUTER_API_KEY` / `OPENAI_API_KEY` 时，`extractor` 会调用真实 API：对 **语义**、**自我图式**、**情景**、**路由** 分别独立请求（如 `route_memory_categories_llm_default`）。

## 实验臂（Arms）

1. **`baseline_small_window`（小窗口基线）**  
   答题时仅可见最近 N 条用户话轮；**每条可见行**都走**槽位** LLM（桩或 API）。

2. **`baseline_large_window`（大窗口基线）**  
   可见**整段对话**；同样对**每一行**走槽位 LLM。

3. **`layered_memory`（分层记忆）**  
   与小窗口基线相同的短窗口 + 经显著性门控的**长期语义**存储；  
   **路由 LLM** 按轮选择子系统；情景缓冲 + **巩固**（高显著情景证据再经语义槽位 LLM；重复 `(key,value)` 晋升至长期记忆）。

## 指标

- **`accuracy`**：答对题数 / 总题数。
- **`avg_context_chars`**：平均每题用于上下文的字符数。
- **派生指标**：
  - `accuracy_gain_vs_small`
  - `context_reduction_vs_large`

## 成功标准（原型）

- `accuracy_gain_vs_small >= 0.30`
- `context_reduction_vs_large >= 0.40`
- `layered_memory_accuracy >= 0.80`

## 执行方式

- （可选）安装真实 LLM 依赖：`pip install -r research/brain_inspired_memory_summarizer/requirements.txt`
- 运行实验（确定性桩，**无需 API**）：
  - `python3 research/brain_inspired_memory_summarizer/main.py run`
- 运行实验（**真实模型**，需 `OPENROUTER_API_KEY` 或 `OPENAI_API_KEY`，可选 `INTY_MEMORY_EXTRACTOR_MODEL`）：
  - `python3 research/brain_inspired_memory_summarizer/main.py run --live-llm`
  - 进度日志输出到 **stderr**（默认 **INFO**；`-v` / `--verbose` 为 **DEBUG**，含 LLM 用户侧预览；`-q` 仅 **WARNING**）。最终指标 JSON 仍打印到 **stdout**。
  - 默认写入 `experiment_results_live.json` 与 `experiment_full_live.json`（HTTP 调用次数多；**非确定性**）。
- 运行测试：
  - `python3 -m unittest research/brain_inspired_memory_summarizer/test_main.py -v`
