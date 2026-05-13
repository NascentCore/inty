# 后端架构分层边界规则

## 目标

- 为 `app/` 提供可执行的分层依赖边界。
- 在 CI 阶段阻断新增违规跨层依赖。

## 分层职责

- `api`
  - HTTP 路由、请求解析、鉴权入口、响应组装。
  - 允许依赖：`services`、`schemas`、`core`、`db`、`utils`、`models`、`external_services`。
  - 禁止依赖：`middleware`。
- `services`
  - 业务编排、事务边界、对模型与外部能力的组合。
  - 禁止依赖：`middleware`。
- `models`
  - SQLAlchemy 持久化模型定义。
  - 禁止依赖：`services`、`schemas`、`external_services`、`middleware`。
- `schemas`
  - Pydantic 契约模型。
  - 禁止依赖：`external_services`、`middleware`。
- `utils`
  - 通用工具函数和小型基础能力。
  - 禁止依赖：`models`、`middleware`。
- `external_services`
  - 第三方服务适配层（GCS、Google Play、Firebase 等）。
  - 禁止依赖：`api`、`services`、`models`、`middleware`。
- `middleware`
  - FastAPI 中间件，仅由 `app/main.py` 和 API 装配阶段使用。

## 执行方式

- 检查脚本：`tools/scripts/check_layer_dependencies.py`
- 本地运行：
  - `source .venv/bin/activate && python tools/scripts/check_layer_dependencies.py`
  - 可选输出 JSON：`source .venv/bin/activate && python tools/scripts/check_layer_dependencies.py --json-output /tmp/layer_violations.json`
- CI 集成：
  - `.github/workflows/ci_backend.yaml` 中新增 `Check architecture layer boundaries` 步骤。
  - 任何违规 import 将导致 CI 失败。

## 当前规则范围说明

- 本轮为 P0 第一步，先落地高信号禁止清单，避免一次性大规模重构。
- 后续可在不破坏现有业务的前提下逐步收紧：
  - `api -> models/external_services`
  - `services -> api`
  - `schemas -> services`
