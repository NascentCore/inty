# 核心 AI 组件

应该重命名为 AI

## Companion REPL tools

- Optional env **`INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL`**: when set to `1` / `true` / `yes` / `on`, `build_openai_repl_tools` omits **`tool_update_agent_status_line`** (avoids Postgres for local harness scripts). When unset, behavior unchanged for production-style runs.
