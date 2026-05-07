# 核心 AI 组件

应该重命名为 AI

## Companion REPL tools

- Optional env **`INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL`**: when set to `1` / `true` / `yes` / `on`, `build_openai_repl_tools` omits **`tool_update_agent_status_line`** (avoids Postgres for local harness scripts). When unset, behavior unchanged for production-style runs.

## Companion tool-call model

- WS production tool-call route (`/api/v1/chat/ws` background tool loop) uses YAML field **`app.agent.companion_tool_call_model`** (`AgentConfig`), default **`google/gemini-3-flash-preview`**, decoupled from the foreground envelope chat model (`select_chat_model`). Empty string falls back to the current chat model id.
- Injection path: `app/services/companion_chat_service.py:_companion_manager_for_resolved_model` -> `CompanionLLMConfig.tool_model` -> `CompanionLLMClient.resolve_model("tool")` -> `app/core/agentic_kernel/companion/turn.py` `start_tool_background_job(tool_model_name=...)`.
- harness / REPL may still override via **`INTY_V2_PROTO_TOOL_MODEL`** (`CompanionLLMConfig.from_openrouter_env`).
