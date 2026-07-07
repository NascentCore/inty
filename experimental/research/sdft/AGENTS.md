# `research/sdft/`：SDFT 论文复现（研究沙盒）

**一句话**：薄封装 [idanshen/Self-Distillation](https://github.com/idanshen/Self-Distillation)，不复制 `DistilTrainer`；仅 pin、配置、CLI 与验收记录。

## 边界

- 不接入 `companion_harness` 或线上训练管线。
- **配置层**可用 Pydantic 默认值；`runner` / `main` 入口对 yaml 必填字段 `assert`。
- 不写 pytest；验收见 `results/validation_log.md` 与 `main.py validate`。
- **当前环境常无 GPU**：GPU/CUDA/vLLM 失败记入 validation_log 且 `expected: true`。

## 习惯

- 入口：`main.py`（Cyclopts：`train` | `eval` | `validate`）。
- `tooluse` / `science` 数据加载 **仅** 调用 upstream `main.load_*_dataset`（cwd=`upstream/`）。
- 完整训练依赖：`pip install -r upstream/requirements.txt`（含 vLLM）；smoke 用 `requirements-smoke.txt`。
