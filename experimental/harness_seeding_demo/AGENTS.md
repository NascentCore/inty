# harness_seeding_demo

- 试验脚本默认设置 **`INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL=1`**（排除依赖 Postgres 的状态行工具），对应内核 `build_openai_repl_tools` 的可选开关；生产路径不设该变量则不变。
- 推理调用：`CompanionManager` / `run_turn`，详见 [README.md](README.md)。
- 新增产物优先：`seeds/`、`scorer/`、`scripts/`。
- 仓库根空包 `experimental/__init__.py` 便于 `PYTHONPATH=.`.
- `run_trial.py` / `run_matrix.py` 可选加载根目录 `.env`（`python-dotenv`），见 [experimental/AGENTS.md](../AGENTS.md)。
