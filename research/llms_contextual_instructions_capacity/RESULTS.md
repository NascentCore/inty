# 结果汇总

## 运行元数据（实时）

- 运行 ID：`20260330T150952Z`
- 生成时间：`2026-03-30T15:11:39.145268+00:00`
- 模型 ID：`google/gemini-2.5-flash-lite`
- 模式：`live`（真实模型 API）
- 每个单元试验次数：`3`（快速实时扫面）
- 矩阵规模：`4 个利用率 * 3 个指令数 * 2 个分布 = 24 个单元`
- 总试验数：`72`

结果产物：

- `research/llms_contextual_instructions_capacity/results/20260330T150952Z/trial_results.jsonl`
- `research/llms_contextual_instructions_capacity/results/20260330T150952Z/cell_summary.csv`
- `research/llms_contextual_instructions_capacity/results/20260330T150952Z/failure_taxonomy.md`
- `research/llms_contextual_instructions_capacity/results/20260330T150952Z/limit_recommendation.json`
- `research/llms_contextual_instructions_capacity/results/20260330T150952Z/summary.json`
- `research/llms_contextual_instructions_capacity/results/20260330T150952Z/summary.md`

## 使用的阈值

- IA >= `0.95`
- RSR >= `0.85`
- 有效性 >= `0.92`
- 格式错误率 <= `0.02`

## 定量结果摘要（实时）

来自实时 `limit_recommendation.json`：

- `<=8` 指令桶：`U_rec = None`，`U_hard = 0.55`
- `<=16` 指令桶：`U_rec = None`，`U_hard = 0.55`
- `<=32` 指令桶：`U_rec = None`，`U_hard = None`
- `<=64` 指令桶：`U_rec = None`，`U_hard = None`

本次实时快扫解读：

- 在严格的 CI 门控阈值下，且每个 cell 只有 3 次试验，没有任何利用率点进入推荐安全区（`U_rec=None`）。
- 对 `<=8` 与 `<=16` 指令桶，硬上限检测首次在 `U=0.55` 触发。
- `<=32` 与 `<=64` 在本次快扫中不适用（未包含大于 16 的指令数），因此硬上限为 `None`。

## 定性失败摘要（实时）

来自实时 `failure_taxonomy.md`：

- 值错误：`0`
- 遗漏/不完整：`0`
- 全局覆盖或非 JSON：`4`
- 未分类：`0`

观察到的失败模式：

1. 主要失败模式是格式包装（` ```json ... ``` `），不是 key-value 映射错误。
2. 当前解析器要求纯 JSON；带 markdown 代码块的输出会被计入格式错误。
3. 本次实时快扫未出现“值错误/漏项”，说明在采样范围内核心指令抽取能力较强。

## 结论

1. 使用 `google/gemini-2.5-flash-lite` 的真实模型运行已成功，评测链路在实时模式下可端到端运行。
2. 这轮快扫中，模型主要问题是严格输出格式（代码块包裹 JSON），不是指令语义正确性本身。
3. 由于每个 cell 试验数较低（`3`）且矩阵为缩减版，当前 `U_hard=0.55` 应视为临时结果。

本实验使用的 `U_hard` 定义：

- `U_hard` 是在同一指令桶中，`uniform` 与 `edges` 两种分布检查下，阈值失败连续出现在 2 个利用率点时对应的第一个利用率。
- 业务含义：超过 `U_hard` 后，质量下降不再是偶发噪声，而是趋势性风险区间。

## 生产级指导的下一步建议

建议用完整矩阵并将每个 cell 试验数提升到至少 `30`：

`python3 research/llms_contextual_instructions_capacity/run_benchmark.py --model google/gemini-2.5-flash-lite --trials-per-cell 30 --output-dir research/llms_contextual_instructions_capacity/results`

然后用最终运行结果更新本文件中的各指令桶 `U_rec` 与 `U_hard`。

## 之前的基线（dry-run 合成）

- 运行 ID：`20260330T110255Z`
- 该基线保留在 `results/20260330T110255Z`，用于评测框架校准对比。

## 额外实时模型对比（同一矩阵）

三模型可比的快扫矩阵：

- `U={0.10, 0.55, 0.80, 0.93}`
- `N={1, 8, 16}`
- `P={uniform, edges}`
- `trials_per_cell=3`

实时运行 ID：

- `google/gemini-2.5-flash-lite`: `20260330T150952Z`
- `deepseek/deepseek-v3.2`: `20260330T161158Z`
- `openai/gpt-4o-mini`: `20260330T162012Z`

### `U_hard` 对比

`<=8` 指令桶：

- `google/gemini-2.5-flash-lite`: `U_hard=0.55`
- `deepseek/deepseek-v3.2`: `U_hard=0.55`
- `openai/gpt-4o-mini`: `U_hard=0.55`

`<=16` 指令桶：

- `google/gemini-2.5-flash-lite`: `U_hard=0.55`
- `deepseek/deepseek-v3.2`: `U_hard=0.55`
- `openai/gpt-4o-mini`: `U_hard=0.55`

说明：

1. 在这套快扫矩阵里，三模型在已覆盖的桶上都得到了相同的临时 `U_hard`。
2. `<=32` 与 `<=64` 仍为 `None`，因为本矩阵未覆盖大于 `16` 的指令数。
3. 失败模式存在差异：
   - `deepseek/deepseek-v3.2` 的格式包装失败更多（较多 markdown 代码块 JSON 输出）。
   - `openai/gpt-4o-mini` 在本次快扫中无失败，但由于试验次数低、CI 规则严格，最终临时硬上限边界仍与其他模型一致。

## Gemini 上下文占用率-成功率专项实验（20260331T012644Z）

### 实验设置

- 模型：`google/gemini-2.5-flash-lite`
- 目标：评估“不同上下文占用率 U 下，指令遵循成功率（完成指令占比）”
- 固定条件：
  - 指令数 `N=16`
  - 分布 `P=uniform`
  - 每个利用率点 `5` 次试验
- 利用率扫描：
  - `U={0.10, 0.25, 0.40, 0.55, 0.70, 0.80, 0.87, 0.93, 0.97}`
- 成功率定义：
  - 成功率 = 完成指令数 / 总指令数
  - 在产物中对应 `cell_summary.csv` 的 `ia_mean`

结果产物目录：

- `research/llms_contextual_instructions_capacity/results/20260331T012644Z/`
- 曲线图：`research/llms_contextual_instructions_capacity/results/20260331T012644Z/plots/gemini_success_rate_vs_u.png`

### 实验结果（逐利用率）

- U=0.10：成功率 `0.80`
- U=0.25：成功率 `1.00`
- U=0.40：成功率 `1.00`
- U=0.55：成功率 `0.80`
- U=0.70：成功率 `1.00`
- U=0.80：成功率 `1.00`
- U=0.87：成功率 `1.00`
- U=0.93：成功率 `0.80`
- U=0.97：成功率 `1.00`

失败类型统计（本次 run）：

- 遗漏或不完整：`0`
- 键正确但值错误：`0`
- 全局覆盖或非 JSON：`3`
- 未分类：`0`

### 分析与结论

1. 在本次条件（`N=16, uniform, trials=5`）下，成功率总体较高，多数利用率点达到 `1.00`。
2. 成功率下降点（`U=0.10, 0.55, 0.93`）均对应“全局覆盖或非 JSON”类型失败，说明主要瓶颈仍是输出格式稳定性，而非指令语义理解错误。
3. 该曲线未显示随 `U` 单调下降，提示当前样本规模下噪声较大，单次快扫更适合“发现风险点”，不适合直接给生产硬阈值。
4. 由于本次只覆盖 `uniform`，且每点仅 `5` 次，结论应视为专项观察结果；用于生产上限时仍需补齐 `edges` 并提高每点样本数（建议 >=30）。

### 对应建议

1. 若要将本曲线转为可执行阈值，建议在相同 `U` 网格下新增 `P=edges` 并将 `trials_per_cell` 提升到 `30`。
2. 若业务强依赖 JSON 严格解析，建议在后处理阶段增加代码块剥离（```json ... ``` -> 纯 JSON）再复算成功率，以区分“格式问题”与“语义问题”。
