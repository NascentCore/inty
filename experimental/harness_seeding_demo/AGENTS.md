# `harness_seeding_demo/`：伴侣内核种子试验场

**一句话**：围绕 **`CompanionManager` / `run_turn`** 做 **批量试验与评分矩阵**；默认通过环境变量 **关闭依赖 Postgres 的状态行工具**，以便在轻量环境跑通。

## 读者

- 调 prompt 种子、评分器或试验矩阵的研究员与编码智能体。

## 习惯

- **新产物**：优先落在 `seeds/`、`scorer/`、`scripts/` 等既有桶中。
- **环境**：可用仓库根 `.env`（dotenv）注入密钥；`PYTHONPATH=.` 由调用方在仓库根设置。

## 细节

- 具体 CLI 与矩阵参数：见 [`README.md`](README.md)。
