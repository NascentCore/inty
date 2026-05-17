---
name: inspect-repl-message-metadata
description: >-
  Decode inty_v2_repl assistant **metadata section** lines (chat / inner-tick / toolcall, ms,
  user_msg_uuid, langsmith ids, optional langsmith_*_url=, tool_background_started). Modern server emits
  meta_data.inner_tick_activity, so the REPL distinguishes proactive_chat vs
  maintenance directly in the label; LangSmith fallback is for legacy frames
  only. Triggers: REPL pasted line, "is this proactive heartbeat",
  proactive vs maintenance inner-tick. For missing chat reply after user-input, see inty-backend-inspect
  (tool_background / turn_lock), not this skill alone.
---

# Inspect REPL message metadata

- **何时用**
  - 用户贴了助手 **metadata section** 行（`[墙钟] <label> <ms>ms …`），或问：来源、`inner-tick` 是否陪伴心跳、`proactive_chat` vs `maintenance`
  - **不要**用本技能单独解释「用户发了消息却没有 `chat` 行」——见 [`inty-backend-inspect`](../inty-backend-inspect/SKILL.md) 专项 **卡住的 tool_background**

- **Metadata section 长什么样**
  - `[墙钟] <label> <ms>ms` + 可选 `user_msg_uuid=` / `asst=` / `langsmith_trace_id=` / `langsmith_run_id=` + 可选 `langsmith_trace_url=` / `langsmith_run_url=` + 可选 `tool_background_started=true`
  - **label 取值与判定顺序**（实现：[`tools/inty_v2_repl/main.py`](../../../tools/inty_v2_repl/main.py) `_repl_assistant_banner_label`）
    - `meta_data.inner_tick_activity` 非空 → `inner-tick {activity}`，其中 `proactive_chat` 显示为 `proactive-chat`，`maintenance` 原样
      - **优先级最高**：即便同帧 `source=tool_bg`，只要 `inner_tick_activity` 在，label 仍是 `inner-tick …`
    - 否则按 `meta_data.source`：`tool_bg` → `toolcall`；`inner_tick` → `inner-tick`；`greeting` → `greeting`；`chat` → `chat`
    - 兜底用 transcript `assistant_source`（`inner_tick` / `greeting` / `chat`），最终默认 `chat`
  - **`tool_background_started=true`**
    - 实现：同文件 `_repl_metadata_section_flags_fragment`（metadata section 尾部 flags）
    - 语义：多帧下行里前台已返回且后台 tool 路径已起；见 [`tools/inty_v2_repl/AGENTS.md`](../../../tools/inty_v2_repl/AGENTS.md)
  - **`inner-tick …` 正文为 `[SILENT]`**
    - 表示 proactive / maintenance 心跳轮 **刻意不展示** 给用户；**不是**对用户刚发那条消息的 `chat` 回复
    - 用户已有 `user-input` 却长时间只有 `[SILENT]` inner-tick、仍无 **`chat`** 行 → 用 [`inty-backend-inspect`](../inty-backend-inspect/SKILL.md) 查 **`tool_bg_idle` / `turn_lock` 排队**

- **从 label 直接判定 inner-tick 模式（首选）**
  - `inner-tick proactive-chat` → `InnerTickMode.PROACTIVE_CHAT`（陪伴心跳）
  - `inner-tick maintenance` → `InnerTickMode.MAINTENANCE`（运维内 tick）
  - **裸** `inner-tick`（无尾随活动名）→ 旧服务端，未带 `inner_tick_activity`；此时按下条用 LangSmith 定案
  - **枚举真源**
    - [`app/core/companion_harness/companion/models.py`](../../../app/core/companion_harness/companion/models.py) `InnerTickMode`
  - **服务端注入点**
    - 前台帧：[`app/api/v1/endpoints/chat.py`](../../../app/api/v1/endpoints/chat.py) `meta_data.inner_tick_activity = companion_turn.inner_tick_activity`
    - `tool_bg` 帧：同文件，`ChatWsCompanionWireMetaData(... inner_tick_activity=ev.inner_tick_activity ...)`
    - 内核：[`turn.py`](../../../app/core/companion_harness/companion/turn.py) `inner_tick_activity = route_inner_mode.value if inner_tick_turn else None`

- **LangSmith 兜底（仅旧帧或交叉验证）**
  - 从 metadata section 取 `langsmith_run_id=…`
  - 仓库根执行：
    - `python tools/scripts/download_run.py --run-id <RUN_ID>`（或位置参数 `RUN_ID`；见 `python tools/scripts/download_run.py --help`）
  - 打开 JSON，看 **`extra.metadata`**
    - **`inner_tick_mode`**：`proactive_chat` | `maintenance`
    - **`inty_turn_lane`**：如 `inner_tick`
    - **不要**单靠 span 的 `name` 判断模式
  - **前置与排错**
    - 全步骤：[`langsmith-download-run`](../langsmith-download-run/SKILL.md)

- **和日志 / DB 一起查**
  - [`inty-backend-inspect`](../inty-backend-inspect/SKILL.md)
