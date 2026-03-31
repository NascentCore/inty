# OpenAI SDK 结构化输出 vs 纯文本 JSON 输出对比测试设计

## 目标

验证并量化以下问题：

1. 在同一任务集下，`纯文本提示要求输出 JSON` 与 `OpenAI SDK 结构化输出 API` 的准确率差异有多大？
2. 两种方式在“可解析性/格式稳定性/语义正确性”上的差异分别是什么？
3. 生产环境是否应优先采用结构化输出 API？

## 测试对象

- **文本 JSON 模式（text_json）**
  - 使用普通 `chat.completions.create`。
  - 在 prompt 中用文字要求“仅输出 JSON，禁止 markdown”。
- **结构化输出模式（structured_api）**
  - 使用 OpenAI SDK 的结构化输出能力（`response_format` + JSON Schema）。
  - 由 API 约束输出结构，不依赖纯文字约束。

## 核心假设

- H1：`structured_api` 的**格式可解析率**高于 `text_json`。
- H2：在去除格式因素后，二者**语义准确率**接近；若有差异，`structured_api` 不低于 `text_json`。
- H3：生产关键链路中，`structured_api` 的综合有效性更高。

## 任务构造

每个 trial 生成一组确定性任务：

- 键：`task_001 ... task_N`
- 每个任务有可验证真值（例如字符串反转规则）
- 末尾加入冲突干扰指令（要求忽略前文并输出总结），用于验证抗干扰能力

输出目标统一为：

- JSON object，且必须包含全部 `task_xxx`

## 变量设置

- 模型：可先用 `openai/gpt-4o-mini`（通过 OpenRouter），再扩展到其他模型
- 指令数：默认 `N=16`
- 上下文利用率：`U={0.10, 0.25, 0.40, 0.55, 0.70, 0.80, 0.87, 0.93, 0.97}`
- 分布：`P={uniform, edges}`
- 每格样本：建议 `>=30`
- 随机种子：固定主种子，可加次种子复核

## 评分指标

### 1) 格式指标

- `strict_schema_valid_rate`：原始输出可被严格 JSON 解析且结构为对象
- `format_error_rate`：格式错误比例（非 JSON、markdown 包裹导致解析失败、截断等）

### 2) 语义指标

- `IA`（Instruction Accuracy）：正确指令数 / 总指令数
- `RSR`（Response Success Rate）：整条响应完全正确比例
- `Effectiveness`：`0.3*SV + 0.3*CP + 0.4*IA_resp`

### 3) 可选补充

- 中位延迟（`median_latency_ms`）

## 判定逻辑

对每个 `(U, N, P)` 单元分别计算：

- `IA_mean` 与 Wilson 95% CI
- `RSR` 与 Wilson 95% CI
- `format_error_rate`

并输出两模式差值：

- `delta_ia = IA_mean(structured_api) - IA_mean(text_json)`
- `delta_rsr = RSR(structured_api) - RSR(text_json)`
- `delta_format_error = format_error_rate(structured_api) - format_error_rate(text_json)`

若 `delta_format_error < 0` 且绝对值显著，同时 `delta_ia >= 0`，则支持“结构化输出优于文本 JSON”结论。

## 产物

每次 run 生成：

1. `trial_results.jsonl`：逐 trial 原始明细（含 mode）
2. `cell_summary.csv`：按 `(mode, U, N, P)` 聚合
3. `comparison_summary.md`：核心对比结论
4. `plots/`：
   - `ia_vs_u_mode_comparison.png`
   - `format_error_vs_u_mode_comparison.png`

## 与当前评测体系衔接

该对比实验复用现有上下文容量评测的 prompt 生成和打分逻辑，仅将“输出通道”拆为两种模式，便于直接对齐原有 `U_hard/U_rec` 经验。
