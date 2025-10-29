# core - 核心模块

## Cursor Summary

- 目录用途: 汇集后端核心能力与跨模块基础设施。
- 关键子目录/文件:
  - `config.py`: 应用配置集中管理（环境变量、常量）。
  - `logging.py`: 日志配置与封装。
  - `voice/`: 语音合成/播放相关核心模型。
  - `agent/`: 智能体/角色核心提示与封装。
  - `prompting/`: 角色、个性与表达等提示词素材库。
  - 其他: `chat.py` 等面向聊天的核心逻辑。

## 日志（Logging）

- 自 2025-10 起，后端日志时间统一为 UTC（通过 `TZ=UTC` 与 Loguru `timezone="UTC"` 设置）。
- Uvicorn/FastAPI 等标准 `logging` 日志会被拦截并转发到 Loguru，时间同样为 UTC。
