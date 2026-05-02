# Harness 种子对照试验：设置与结论（总结）

本文档用中文概括试验设置与结论。原始数据表、英文对照与跨 Run 细节见 [MATRIX_RUN_REPORT.md](MATRIX_RUN_REPORT.md)。

---

## 1. 试验目的（一句话）

在**同一 harness**（`CompanionManager` + `run_turn`）下，仅更换 `seeds/*` 工作区初值，观察「达到若干启发式情感质量门槛」所需的**首轮达标轮次**（及重复试验下的中位数）是否因种子不同而分化。

---

## 2. 共同设置（所有 Run）

- **智能体本体**：`app/core/agentic_kernel/companion/`，试验代码不 fork 推理核；工作区种子通过 `workspace_setup.py` 在 session 创建前写入 `MemoryStore`。
- **Harness**：`scripts/run_trial.py` 逐句用户台本、`scripts/run_matrix.py` 多种子 x 多重复。
- **自演化管线**：试验中 largely 关闭重量级 USER/SOUL 记忆策展，避免与「种子初值」混淆；详见 [RUN.md](../RUN.md)。
- **无 Postgres 时的工具噪声**：默认 `INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL=1`，避免 `tool_update_agent_status_line` 在无 DB 时干扰回复体与评分（内核侧为可选环境变量开关）。

---

## 3. 三次试验 regime 的设置差异

| 项目 | Run A（历史，嘈杂） | Run B（短脚本，harness 已修） | Run C（本次主结论） |
|------|---------------------|-------------------------------|---------------------|
| 日期 | 2026-05-01 | 2026-05-01 | 2026-05-02 |
| 用户台本 | 3 句 `work_stress_script.json` | 同左 | 12 句 `work_stress_script_12.json` |
| Rubric | 约等同 `default` @ 0.85，单指标 | 同左 | `default` 0.85；`strict_emotional`、`premature_solution`、`boundary_tone` 均为 1.0 |
| 每种子重复次数 | 1 | 1 | 3 |
| 状态行工具 | 未默认关闭，易受 DB 影响 | 默认关闭 | 默认关闭 |
| 输出目录（示例） | `results/matrix_20260501_*`（已清理） | `results/matrix_rerun_20260501_162708/` | `results/matrix_exp_20260502/`（原始 JSON gitignored） |

Run C 的模型与密钥：**OpenRouter** `deepseek/deepseek-v3.2`，密钥来自 `devops/config.yaml.local`（注入为 `OPENAI_API_KEY`，与 [RUN.md](../RUN.md) 一致）。`matrix_errors.json` 为空表示矩阵子进程无报错。

---

## 4. Run C 结论（主结果）

1. **基础设施先于「种子叙事」**：Run A 与 B 对比说明，在短脚本、单 rubric 下，**DB 工具失败与空 `assistant_text`** 可使不同种子看起来差异很大；修 harness 后 Run B **五种子的 first_pass 均为 1**，差异主要来自噪声消除而非 SOUL 文本本身。
2. **短脚本 + 宽松单指标易饱和**：仅 3 句 + `default` 时，种子难以区分；需要更长压力弧（12 句）和/或更严指标（Run C）。
3. **Run C 下多指标才拉开种子**（中位数与 `all_passed_turn1_*` 见 [MATRIX_RUN_REPORT.md](MATRIX_RUN_REPORT.md) 表）：
   - **`strict_emotional`**：`functional` 唯一在 3 次重复上均首轮达标；`teammate_on` 中位数最差（5），且重复间首轮达标轮次为 1 / 5 / 7，**方差大**。
   - **`boundary_tone`**：多种子未做到三次重复均首轮达标；与脚本是否显式谈边界、以及 rubric 是否要求「邀请式」措辞有关。
   - **`premature_solution`**：本脚本与模型下**全体种子 median 均为 1**，判别力不足（编号建议很少出现在「反思」之前的前 320 字内）。
4. **不应过度外推**：上述 rubric 为**关键词启发式**，不是人工标注的共情 ground truth。`teammate_on` 在 `strict_emotional` 上表现弱，**不能**直接推出「团队预填伤害用户」；可能原因包括更长工具/前言、风格未在首轮满足「两条压力词」、采样随机性等。

---

## 5. 后续建议（与报告一致）

- 提高重复次数 **N** 或固定采样参数，降低种子比较的方差。
- 改进或替换 `premature_solution`，使其在常见回复形态下更常触发。
- 对 `teammate_on` 晚达标 repetition 做**人工抽查** transcript，区分「真共情差」与「评分器与风格不匹配」。

---

## 6. 相关文件

- 运行参数与故障排除：[RUN.md](../RUN.md)
- 英文数据表与 Run A/B/C 对照：[MATRIX_RUN_REPORT.md](MATRIX_RUN_REPORT.md)
- 矩阵快照索引：[MATRIX_RUN_20260501.md](MATRIX_RUN_20260501.md)
