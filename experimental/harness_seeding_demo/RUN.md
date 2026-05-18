# How to run the harness seeding experiment

目标：在同一套 `CompanionManager` / `run_turn` 链路上，只替换 `seeds/` 下的 workspace 初值，对比「第几轮用户话之后助理回复首次通过情感理解打分」。

---

## 1. 前置条件

- 已克隆本仓库，当前目录为仓库根（下文记为 `$REPO_ROOT`）。
- Python 3.12 + 仓库根目录 `.venv`（或其它已安装 `requirements.txt` 的环境）。
- 网络可达 OpenAI 兼容 API（默认 OpenRouter）。
- **推荐本地**：将密钥写在 **`devops/config.yaml.local`** 的 **`agent.api_key`**（与后端一致）。`run_trial.py` / `run_matrix.py` 默认读取该文件：若 **`OPENROUTER_API_KEY`** 与 **`OPENAI_API_KEY`** 均未设置，会把 `agent.api_key` 写入进程环境变量 **`OPENAI_API_KEY`**（不打印密钥）。文件不存在则跳过并沿用环境变量。
- 或直接导出 **`OPENROUTER_API_KEY`** 或 **`OPENAI_API_KEY`**（优先级高于 YAML）。
- 可选：安装 **`python-dotenv`**，仓库根 **`.env`** 会在读取 YAML 之前加载。

- `run_trial` / `run_matrix` 默认设置 **`INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL=1`**，从而在无本地 Postgres 时避免 `tool_update_agent_status_line` 失败导致空可见回复。若需与默认 REPL 工具表完全一致：`export INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL=0`（通常需 Postgres 可用）。

---

## 2. 每次运行前

```bash
cd $REPO_ROOT
source .venv/bin/activate
export PYTHONPATH=.
```

确认密钥来源其一可用：

```bash
# 已导出 env
test -n "${OPENROUTER_API_KEY:-${OPENAI_API_KEY:-}}" && echo "API key set"

# 或依赖 config.yaml.local（默认路径）
test -f devops/config.yaml.local && echo "config.yaml.local present"
```

强制不用 YAML、只用环境变量：`--no-config-yaml`。指定其它配置文件：`--config-yaml /path/to/config.yaml`。

---

## 3. 单次试验（一种子）

对某一个种子目录跑固定用户台本，写出 `summary.json` 与 `turns.jsonl`。

```bash
python experimental/harness_seeding_demo/scripts/run_trial.py \
  --seed-dir experimental/harness_seeding_demo/seeds/empathic \
  --script experimental/harness_seeding_demo/fixtures/work_stress_script_12.json \
  --output-dir experimental/harness_seeding_demo/results/run01
```

**常用参数**

| 参数 | 含义 |
|------|------|
| `--seed-dir` | 种子目录（内含 `IDENTITY.md`、`SOUL.md`、`USER.md`、`MEMORY.md`、`context.json` 等） |
| `--script` | 用户台本：默认推荐 **12 句** `fixtures/work_stress_script_12.json`；另有 3 句 `work_stress_script.json` |
| `--output-dir` | 结果目录；省略则用系统临时目录 |
| `--threshold` | **仅** rubric `default` 的阈值，默认 `0.85` |
| `--rubrics` | 逗号分隔：`default,strict_emotional,premature_solution,boundary_tone` |
| `--rubric-threshold` | 覆盖某一 rubric，如 `strict_emotional=1.0`（可重复） |
| `--max-turns` | 最多执行用户句数，默认 `50` |
| `--defer-memory-ms` | 每轮后等待毫秒数，默认 `800`；设为 `0` 取消等待 |
| `--config-yaml` | 默认 `devops/config.yaml.local`；缺失则跳过 |
| `--no-config-yaml` | 不从 YAML 注入密钥 |

**产出**

- `summary.json`：`first_pass_turn_by_rubric`（每种 rubric 首次达标轮次）、`thresholds_by_rubric`、`first_pass_turn`（= default rubric 兼容字段）、`llm` 元数据等。
- `turns.jsonl`：每轮 `rubrics` -> `{ id: { score, passed, checks } }`。

**Rubric 含义（启发式）**

- **default**：承接词 + 痛点复述 + 非空 + 非轻视（阈值默认 0.85）。
- **strict_emotional**：在 default 基础上要求 **正文长度 >= 120** 且痛苦轮至少 **两类** 痛点词出现在回复中（默认阈值 **1.0**）。
- **premature_solution**：痛苦轮下禁止 **首行编号清单**，且编号式「怎么做」须出现在 **简短承接** 之后（默认阈值 **1.0**）。
- **boundary_tone**：禁止指责词、开头强硬命令；需 **邀请/许可式** 措辞；若用户提到边界则禁止开头「你应该…」（默认阈值 **1.0**）。

---

## 4. 矩阵试验（多种子）

对 `seeds/` 下每个子目录各跑一次，汇总 `matrix_summary.json`。

```bash
python experimental/harness_seeding_demo/scripts/run_matrix.py \
  --output-dir experimental/harness_seeding_demo/results/matrix01 \
  --repetitions 3
```

**可选参数**：`--seeds-root`、`--script`（默认 **12 句**）、`--threshold`、`--rubrics`、`--rubric-threshold`、`--max-turns`、`--defer-memory-ms`、`--repetitions`（默认 **3**）。

**产出**

- 每次重复：`results/matrix01/rep_<n>/<seed>/summary.json` 与 `turns.jsonl`
- 全量明细：`results/matrix01/matrix_all_repetitions.json`
- 按种子聚合：`results/matrix01/matrix_summary.json`（各 rubric 的 **`median_first_pass_<id>`** 与 **`all_passed_turn1_<id>`**）
- 失败：`matrix_errors.json`；任意子任务失败则退出码 **1**

内置种子名：`baseline`、`empathic`、`functional`、`teammate_on`、`teammate_off`。

---

## 5. 读懂结果

- **按 rubric**：查看 `first_pass_turn_by_rubric` / `median_first_pass_*`。严 rubric（默认阈值 1.0）更容易在较晚轮次才首次达标。
- **启发式**：所有 rubric 均为规则打分，**不等于**人工情感理解质量。

---

## 6. 离线自检（不调 LLM）

仅验证打分器与 workspace 种子写入逻辑：

```bash
pytest tests/experimental/test_harness_seeding_demo_scorer.py \
  tests/experimental/test_harness_seeding_demo_workspace_setup.py -v
```

---

## 7. 故障排查

- **`401` / API key**：检查环境变量或 `.env`。
- **超时**：可调 `INTY_V2_PROTO_ASYNC_CHAT_FRONT_TIMEOUT_SEC`（见 companion LLM 配置）或检查网络。
- **磁盘**：工作区在 `--output-dir/_ws_base/...`（默认）；矩阵多次运行会占用若干 workspace 状态；结果目录默认在 `experimental/harness_seeding_demo/results/`（若存在 `.gitignore` 忽略规则，勿提交密钥或大日志）。

更完整的设计背景见同目录 [README.md](README.md) 与 [PLAN.md](PLAN.md)。
