# 核心 AI 组件

应该重命名为 AI

## Companion REPL tools

- Optional env **`INTY_COMPANION_DISABLE_AGENT_STATUS_LINE_TOOL`**: when set to `1` / `true` / `yes` / `on`, `build_openai_repl_tools` omits **`tool_update_agent_status_line`** (avoids Postgres for local harness scripts). When unset, behavior unchanged for production-style runs.
- OpenAI Chat Completions **`tools`** payloads: `build_openai_repl_tools` returns lists normalized by **`prepare_openai_tools_for_chat_completions`** in [`app/core/agentic_kernel/companion/openai_tools_prepare.py`](app/core/agentic_kernel/companion/openai_tools_prepare.py), which sets each function tool's **`strict`** (default **True**) so SDK structured parsing / vendor strict-schema paths stay consistent. Optional env **`INTY_OPENAI_TOOLS_STRICT`**: unset or `1`/`true`/`yes`/`on` keeps strict on; `0`/`false`/`no`/`off`/`none` sets **`strict`: false** on every function tool (for gateways that reject strict tool schemas).

## Companion tool-call model

- WS production tool-call route (`/api/v1/chat/ws` background tool loop) uses YAML field **`app.agent.companion_tool_call_model`** (`AgentConfig`), default **`google/gemini-3-flash-preview`**, decoupled from the foreground envelope chat model (`select_chat_model`). Empty string falls back to the current chat model id.
- Injection path: `app/services/companion_chat_service.py:_companion_manager_for_resolved_model` -> `CompanionLLMConfig.tool_model` -> `CompanionLLMClient.resolve_model("tool")` -> `app/core/agentic_kernel/companion/turn.py` `start_tool_background_job(tool_model_name=...)`.
- harness / REPL may still override via **`INTY_V2_PROTO_TOOL_MODEL`** (`CompanionLLMConfig.from_openrouter_env`).
