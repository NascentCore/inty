# `harness_seeding_demo/`：伴侣内核种子试验场

**一句话**：围绕 **`CompanionManager` / `run_turn`** 做 **批量试验与评分矩阵**；`workspace_setup` / `run_trial` 与生产一致，要求仓库根 `config.yaml` 的 **`database.url` 非空**（MemoryStore 注册表与 `CompanionManager` 会话写 Postgres）。仍可单独用环境变量关闭**仅状态行类**工具等轻量依赖，但不再支持「无 DSN 跑完整内核会话」。

## 读者

- 调 prompt 种子、评分器或试验矩阵的研究员与编码智能体。

## 习惯

- **新产物**：优先落在 `seeds/`、`scorer/`、`scripts/` 等既有桶中。
- **环境**：可用仓库根 `.env`（dotenv）注入密钥；`PYTHONPATH=.` 由调用方在仓库根设置。

## 细节

- 具体 CLI 与矩阵参数：见 [`README.md`](README.md)。
