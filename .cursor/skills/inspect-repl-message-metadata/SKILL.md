---
name: inspect-repl-message-metadata
description: >-
  Decode inty_v2_repl assistant banner lines (chat / inner-tick / toolcall, ms,
  user_msg_uuid, langsmith ids, tool_background_started). inner-tick label does
  not distinguish proactive_chat vs maintenance; use langsmith_run_id with
  download_run.py and extra.metadata.inner_tick_mode. Triggers: REPL pasted
  line, "is this proactive heartbeat", proactive vs maintenance inner-tick.
---

# Inspect REPL message metadata

- **何时用**
  - 用户贴了 `[墙钟] <label> <ms>ms …` 助手行，或问：来源、`inner-tick` 是否陪伴心跳、`proactive_chat` vs `maintenance`

- **横幅长什么样**
  - `[墙钟] <label> <ms>ms` + 可选 `user_msg_uuid=` / `asst=` / `langsmith_trace_id=` / `langsmith_run_id=` + 可选 `tool_background_started=true`
  - **label 从哪来**
    - 下行 `meta_data.source`（或 transcript 的 `assistant_source`）
    - 实现：[`tools/inty_v2_repl/main.py`](../../../tools/inty_v2_repl/main.py) `_repl_assistant_banner_label`
      - `tool_bg` → `toolcall`
      - `inner_tick` → `inner-tick`
      - 否则 → `chat`
  - **`tool_background_started=true`**
    - 实现：同文件 `_repl_meta_banner_fragment`
    - 语义：多帧下行里前台已返回且后台 tool 路径已起；见 [`tools/inty_v2_repl/AGENTS.md`](../../../tools/inty_v2_repl/AGENTS.md)

- **歧义（必须记住）**
  - **`inner-tick` ≠ 一定是陪伴心跳（`proactive_chat`）**
    - `proactive_chat` 与 `maintenance` 的助手帧 `source` 都是 `inner_tick`，REPL 打同一标签
  - **枚举真源**
    - [`app/core/agentic_kernel/companion/models.py`](../../../app/core/agentic_kernel/companion/models.py) `InnerTickMode`

- **用 LangSmith 定案**
  - 从横幅取 `langsmith_run_id=…`
  - 仓库根执行（key / project 与后端一致见下链）：
    - `python tools/scripts/download_run.py <RUN_ID> -o tmp/langsmith_runs/<RUN_ID>.json`
  - 打开 JSON，看 **`extra.metadata`**
    - **`inner_tick_mode`**：`proactive_chat` | `maintenance`
    - **`inty_turn_lane`**：如 `inner_tick`
    - **不要**单靠 span 的 `name` 判断模式
  - **前置与排错**
    - 全步骤：[`langsmith-download-run`](../langsmith-download-run/SKILL.md)

- **和日志 / DB 一起查**
  - [`inty-backend-inspect`](../inty-backend-inspect/SKILL.md)
