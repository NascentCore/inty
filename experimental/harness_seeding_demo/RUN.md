# How to run the harness seeding experiment

目标：在同一套 `CompanionManager` / `run_turn` 链路上，只替换 `seeds/` 下的 workspace 初值，对比「第几轮用户话之后助理回复首次通过情感理解打分」。

---

## 1. 前置条件

- 已克隆本仓库，当前目录为仓库根（下文记为 `$REPO_ROOT`）。
- Python 3.12 + 仓库根目录 `.venv`（或其它已安装 `requirements.txt` 的环境）。
- 网络可达 OpenAI 兼容 API（默认 OpenRouter）：设置 **`OPENROUTER_API_KEY`** 或 **`OPENAI_API_KEY`**。
- 可选：安装 **`python-dotenv`**，并在仓库根放置 **`.env`**；`run_trial.py` / `run_matrix.py` 会自动加载。

其它可选环境变量见 `CompanionLLMConfig.from_openrouter_env()`（例如 `OPENROUTER_BASE_URL`）。

---

## 2. 每次运行前

```bash
cd $REPO_ROOT
source .venv/bin/activate
export PYTHONPATH=.
```

确认密钥已生效（示例）：

```bash
test -n "${OPENROUTER_API_KEY:-${OPENAI_API_KEY:-}}" && echo "API key set"
```

---

## 3. 单次试验（一种子）

对某一个种子目录跑固定用户台本，写出 `summary.json` 与 `turns.jsonl`。

```bash
python experimental/harness_seeding_demo/scripts/run_trial.py \
  --seed-dir experimental/harness_seeding_demo/seeds/empathic \
  --script experimental/harness_seeding_demo/fixtures/work_stress_script.json \
  --output-dir experimental/harness_seeding_demo/results/run01
```

**常用参数**

| 参数 | 含义 |
|------|------|
| `--seed-dir` | 种子目录（内含 `IDENTITY.md`、`SOUL.md`、`USER.md`、`MEMORY.md`、`context.json` 等） |
| `--script` | 用户台本：`fixtures/work_stress_script.json`（JSON 数组）或 `.txt`（每行一句，`#` 开头为注释） |
| `--output-dir` | 结果目录；省略则用系统临时目录 |
| `--threshold` | 打分阈值，默认 `0.85`，须在 `[0, 1]` |
| `--max-turns` | 最多执行用户句数，默认 `50` |
| `--defer-memory-ms` | 每轮后等待毫秒数，默认 `800`；异步记忆队列场景可用；设为 `0` 取消等待 |

**产出**

- `summary.json`：`first_pass_turn`（首次达标的用户轮序号，未达标为 `null`）、`turns_executed`、`workspace_path` 等。
- `turns.jsonl`：每轮 `user_text`、`assistant_text`、`score`、`passed`、`checks`。

---

## 4. 矩阵试验（多种子）

对 `seeds/` 下每个子目录各跑一次，汇总 `matrix_summary.json`。

```bash
python experimental/harness_seeding_demo/scripts/run_matrix.py \
  --output-dir experimental/harness_seeding_demo/results/matrix01
```

**可选参数**：`--seeds-root`、`--script`、`--threshold`、`--max-turns`、`--defer-memory-ms`（与单次试验含义相同）。

**产出**

- 每个种子：`results/matrix01/<seed_name>/summary.json` 与 `turns.jsonl`
- 汇总：`results/matrix01/matrix_summary.json`

内置种子名：`baseline`、`empathic`、`functional`、`teammate_on`、`teammate_off`。

---

## 5. 读懂结果

- **主指标**：`first_pass_turn` 越小，表示在相同台本与阈值下越快达到「情感理解」规则门槛（见 `scorer/emotional_rubric.py`，演示用启发式，非产品质检标准）。
- **对照**：`teammate_on` 与 `teammate_off` 共用相近 `SOUL.md`，差别在是否预填 `USER.md`，用于观察「团队预注」是否减少达标所需轮次（在模型与台本固定时再看）。

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
