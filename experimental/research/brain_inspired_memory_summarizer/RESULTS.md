# 脑启发式记忆总结器：一次运行结果摘要

本文档概括一次**本地可复现**的基准运行。记忆抽取为 **LLM 形态的 JSON**（无基于正则的槽位解析）。默认 `main.py run` 使用按**数据集原句**索引的**确定性 JSON 桩**，**不需要** API key。

## 如何复现

```bash
cd research/brain_inspired_memory_summarizer
python3 main.py run
```

默认情况下，进度（逐轮 ingest、QA、使用 `--live-llm` 时的 LLM 耗时等）输出到 **stderr**。`-v` 更详细，`-q` 几乎静默。若只要 JSON：`python3 main.py run 2>/dev/null` 或 `2>run.log`。

**真实 API（验证模型能力）**：设置 `OPENROUTER_API_KEY` 或 `OPENAI_API_KEY` 后：

```bash
python3 main.py run --live-llm
```

在线运行默认输出：`experiment_results_live.json`、`experiment_full_live.json`。单次完整基准预计**数十次** HTTP 调用（可见行 × 基线臂 + 每轮路由 + 分层侧的语义/自我/情景等）。结果随模型与温度变化（本实验代码中 `temperature=0`）。

## 输出文件（桩运行）

| 文件 | 内容 |
|------|------|
| [experiment_results.json](experiment_results.json) | 汇总指标 |
| [experiment_full.json](experiment_full.json) | 指标 + 每轮路由/抽取轨迹 + 逐题 QA |

自定义路径示例：`python3 main.py run --out /tmp/metrics.json --full-out /tmp/full.json`。

## 本次运行设置

- **窗口大小**（小窗口基线 + 分层侧工作记忆类比）：**2** 条用户行
- **抽取方式**：`llm_only_benchmark_stubs`（见 `experiment_full.json` → `settings`）
- **数据集**：单条情节 `ep-001`（合成对话：早先事实、覆盖、长尾干扰）

## 汇总指标

| 臂 | 准确率 | 平均每题上下文字符 |
|----|--------|-------------------|
| 小窗口基线 | 0%（0/6） | 26 |
| 大窗口基线 | 100%（6/6） | 144 |
| 分层记忆 | 100%（6/6） | 39 |

派生说明：

- **`use_live_llm`**：本文件对应桩运行为 `0`；在线运行见 `experiment_results_live.json` 中为 `1`。
- **相对小窗的准确率提升**：+100%（分层 1.0 − 小窗 0.0）
- **相对大窗的上下文缩减**：约少 **72.9%** 字符/题
- **分层长期槽位**（ingest 后）：6 个 key（`preferred_name`、`city`、`pet`、`rest_day`、`coffee_preference`、`boundary`）

## 抽取轨迹里有什么

见 `experiment_full.json` → `extraction_traces_by_episode` → `ep-001`，每一轮用户话轮包含：

1. **`routed_categories`**：该句的**路由** JSON 选中的子系统（`semantic` / `episodic` / `self_schema`）。
2. **`semantic_candidates` / `self_schema_candidates`**：按路由分别跑的**语义**与**自我图式**槽位 JSON（桩表 `main.benchmark_slot_json_by_line`）。
3. **`episodic_events`**：路由含 `episodic` 时的情景 JSON（`main.benchmark_episodic_json_by_line`）。
4. **`semantic_long_term_after_turn`**：置信度门槛与边界/称呼冲突处理后的分层长期语义状态。

## 逐题 QA（短上下文下的「回忆」）

`qa_per_question` 中：仅可见最近 **两** 行用户话时，**小窗口基线**对每个槽位答 **不知道**（早期事实已滑出窗口）。**分层**智能体从长期语义记忆回答，六道题均与**期望**一致，且上下文远小于大窗口基线。

## 注意

- 桩运行仅保证**脚本化基准**一致；**开放域**需真实 API 与在线模型。
- 设置 `OPENROUTER_API_KEY` 或 `OPENAI_API_KEY` 后，可不经桩直接调用 `extract_semantic_candidates_llm_default`、`route_memory_categories_llm_default` 等；实验时可向 `LayeredMemoryAgent` / `NaiveWindowAgent` 注入自定义 callable。
