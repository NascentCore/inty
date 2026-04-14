# core - 核心模块

## Cursor Summary

- 目录用途: 汇集后端核心能力与跨模块基础设施。
- 关键子目录/文件:
  - `config.py`: 应用配置集中管理（环境变量、常量）。
  - `logging.py`: 日志配置与封装。
  - `voice/`: 语音合成/播放相关核心模型。
  - `agent/`: 智能体/角色核心提示与封装。
  - `repl_input/`: REPL 类 CLI 的跨线程 stdin 行队列与定时等待切片（与长耗时 turn 解耦）。
  - `prompting/`: 角色、个性与表达等提示词素材库。
  - 其他: `chat.py` 等面向聊天的核心逻辑。

## 日志（Logging）

- 日志时间为进程本地时区的墙钟时间，格式含与 UTC 的数值偏移（`ZZ`，如 `+0800`），与本地 REPL 横幅一致。
- Uvicorn/FastAPI 等标准 `logging` 日志会被拦截并转发到 Loguru，时间戳规则相同。
