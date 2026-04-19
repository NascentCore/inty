# iMate companion 设计（与 `app/core/agentic_kernel` 实现一致）

## 两条对话路径

| 路由 | 核心栈 | `app/core/agentic_kernel` 作用 |
| --- | --- | --- |
| `POST /api/v1/chat/completions/{agent_id}` | 传统 `app.core.agent.agent.Agent` | 可选使用 `prompting/assembler`、`tools/runtime` 等（见 `Agent` 的 import）。**不**执行 `companion.turn.run_turn`。 |
| `WS /api/v1/chat/ws` | `companion_chat_service` + `CompanionManager` + `companion.turn.run_turn` | 主路径：`companion/*` 与共享的 `providers/facade`、`tools/registry`、`tools/dispatchers/*`。 |

WebSocket 处理函数在 `app/api/v1/endpoints/chat.py`（`router` 前缀为 `/chat`，在 `API_V1_PREFIX` 下全路径为 `/api/v1/chat/ws`）。

## WebSocket 入口与是否走 companion

1. `chat_completions_websocket` 接受连接、解析 `current_user`、可选 `assume_user_id`、读取头 `appVersionCode`。
2. 若 query 带 `agent_id`，可调用 `_try_send_ws_user_interactive_bootstrap_kickoff` 发**最多一条**主动 assistant JSON（仅用于 interactive bootstrap 开屏；受 `app.features.companion_workspace_bootstrap_type` 等配置约束）。
3. 主循环：解析 `ChatWebSocketRequest`、合并时间上下文、调用 `_agent_chat_completions_impl(..., chat_route="websocket")`。
4. 在 `_agent_chat_completions_impl` 中 `use_companion = (chat_route == "websocket")`。为真时，自然语言回复由 `companion_chat_service.run_companion_chat_turn_for_api` 产生，**不**走 `Agent.generate_message...`。

## 服务与 session 层

- **`app/services/companion_chat_service.py`**
  - 从 `global_config_loaded_from_config_yaml` 构建 `CompanionConfig` / `CompanionLLMConfig`（`app.features`、`agent.chat_llm_*`、`agent.api_key`、`database.url` 作为 MemoryStore 的 DSN 等）。
  - 按「解析后的 chat 模型 id + 运行时指纹」LRU 缓存 `CompanionManager`。
  - `run_companion_chat_turn_for_api`：`get_or_create_session`、可选 `_maybe_append_companion_ws_session_system`（仅 **`USER_INTERACTIVE`** bootstrap）、再 `manager.run_turn`。
  - `run_companion_interactive_bootstrap_kickoff_for_ws`：连接阶段 kickoff，内部用户句来自 `bootstrap_user_interactive.py` 的常量。

- **`app/core/agentic_kernel/companion/manager.py`**
  - `get_or_create_session`：按 workspace 路径注册 `MemoryStore`、写入最小种子文档、`ensure_minimal_workspace_documents_in_store`。
  - `run_turn`：薄封装，调用 `companion.turn.run_turn`。

## 核心一轮：`companion/turn.py` 中 `run_turn`

单轮用户文本（或 heartbeat 的合成文本）顺序大致为：

1. 从 `MemoryStore` 加载 `ContextMeta`、`PromptBundle`（`load_context_meta`、`load_prompt_bundle`）。
2. 加载 `transcript.jsonl`，可按配置做 transcript compaction（`transcript_compaction.py`）。
3. **`prompts.build_system_messages`**（若写「拼 system prompt」，以该函数为准；另存在 `build_system_prompt` 用于拼接字符串场景）。含 interactive bootstrap、`SIGNIFICANCE_PERCEPTION` slice 等分支。
4. **`tools.build_companion_tools`** → `companion_tool_runtime.build_openai_repl_tools`；interactive bootstrap 激活时工具集合会收窄。
5. Tool 循环：`CompanionLLMClient.chat_completion`，HTTP 经 **`providers/facade.py`**（见 `llm_client.py`）。有无 tools 时分流 **chat / tool** 两套同步客户端与 `_resolve_model("chat"|"tool")`。
6. 工具执行：`companion_tool_runtime.execute_tool_call` → **`tools/registry.py`**、`tools/dispatchers/workspace.py`、`tools/dispatchers/media.py` 等与 companion 共用的解析/派发；交互式 bootstrap 专有逻辑在 `companion/` 内。
7. 将 user/assistant（及 tool 轨迹）写入 transcript；`schedule_memory_update_after_turn` / `memory_pipeline.py` 做回合后记忆处理。

**`companion/turn_engine.py`**：面向本地 REPL（`tools/inty_v2_repl`）拼 OpenAI messages。生产 **`WS /api/v1/chat/ws`** 不 import 它，而是经 `companion_chat_service` 走 **`turn.run_turn`**。

## Bootstrap：`companion_workspace_bootstrap_type`

| 取值 | Session 创建 | API 路径上首轮行为 |
| --- | --- | --- |
| `NONE`（默认） | 最小种子文档入 store | 每条用户消息均为 `run_turn` |
| `USER_INTERACTIVE` | 同上 + `context.json` 等交互阶段标记 | 仍为 `run_turn`；模型通过 `companion_update_prompt_slice` / `companion_bootstrap_user_interactive_complete`（见 `bootstrap_user_interactive.py`）；SOUL 锁定等与 `memory_pipeline`、`companion_tool_runtime` 协同 |

实现入口：`manager.py`（session）、`companion_chat_service.py`（分支与 WS kickoff）。

## WebSocket companion 路径会用到的共享内核

- **`providers/facade.py`**（及 `openai_compatible.py`）：`CompanionLLMClient` 的 HTTP 客户端。
- **`tools/registry.py`**、**`tools/dispatchers/*`**：`companion_tool_runtime` 内注册表与 workspace/media 派发辅助。

当前 **`build_openai_repl_tools`** 在向模型暴露的工具列表末尾仍包含 **`google_web_search`、`generate_image`、`modify_image`** 等（定义在同文件的 `build_openai_tools()` 拼装结果上）；执行路径在 **`companion_tool_runtime.execute_tool_call`**。

## 不在「WS companion 答复」主链上的模块

以下仍在 `app/core/agentic_kernel/` 下，但 **`companion/turn.py`** 与 **`companion_chat_service` → WebSocket** 链**不**依赖它们：

- **`contracts/*`**、`runtime/turn_orchestrator.py`、`runtime/persistence.py`、`bridges/experimental_bridge.py`：另一套基于 `TurnInput` / `TurnOutput` 的类型化回合管线，不等同于当前 companion REPL 循环。

推断 WebSocket companion 行为应以 **`companion/turn.py`** 与 **`companion_tool_runtime.py`** 为准，而非单独看 `contracts/`。

## 持久化（概念）

- **Workspace 权威（API companion）**：文档与 transcript 版本经 **`MemoryStore`**（配置好 DSN 时 ORM 落库，如表 **`companion_workspace_document_versions`**），而非进程内以本地磁盘为唯一真相。
- **产品聊天记录**：用户/助手消息经 **`chat_history_service`** 在 companion 返回后写入；可选将 `significance_perception` 放入 AI 消息的 `meta_data`。

合成路径：`CompanionManager` 仍使用 `companion_chat_service.COMPANION_API_WORKSPACE_ROOT_PREFIX`（默认 `/var/lib/inty/companion_workspaces`）拼出逻辑 workspace 根路径，供工具内路径解析与 store 注册键使用。

---

## 回合内行为（kernel 摘要）

- **System**：来自 `PromptBundle`、上下文模式、`TOOLS.md` / `HEARTBEAT.md`（若有）、`IDENTITY` / `SOUL` / `USER`、亲密模式下可选 MEMORY 块、可选 interactive bootstrap 片段、输出契约等；组装函数为 **`build_system_messages`**。
- **Transcript**：窗口由 `transcript_llm_window_max_messages` 与默认上限共同约束；可配置 compaction。
- **LLM**：OpenAI 兼容 **`CompanionLLMClient.chat_completion`**；无 tools 时用 chat 路由客户端与 chat model，有 tools 时用 tool 路由客户端与 tool model（见 `_resolve_model`）。
- **Tools**：`tools.py` 暴露 schema；执行在 **`companion_tool_runtime.execute_tool_call`**。
- **回合后**：`defer_memory_update=True`（API 默认）时异步调度记忆管线。

## 双客户端（chat / tool）与「双路 LLM」文档表述

代码中 **`CompanionLLMClient.chat_completion`** 按「本轮请求是否携带 tools」在两套同步 OpenAI 兼容客户端之间切换，并分别解析 **`chat_model` / `tool_model`**（未配置则回退 `default_model`）。这与「并行前台 chat + 后台 tool 队列」不是同一机制：**后者**在 **`companion/tool_background.py`** 与 **`tools/inty_v2_repl/orchestrator.py`**，**当前 HTTP API 与 `run_companion_chat_turn_for_api` 未挂载** `start_tool_background_job`。

## 重要性感知（significance）

- Prompt slice：**`SIGNIFICANCE_PERCEPTION.md`**（经 `bundle.significance_perception_md`）。
- **`run_turn`** 中 `use_dual_structured_chat = (not heartbeat_turn) and not tools_for_turn`。实现上：**`heartbeat_turn=True` 时强制 `tools_for_turn=[]`**；**非 heartbeat 时 `tools_for_turn = build_companion_tools(...)` 且当前返回的工具列表恒非空**。因此 **`use_dual_structured_chat` 在本文件编写时的 `turn.py` 逻辑下恒为假**：**`response_format`（`significance_perception.py` 中 `DUAL_LLM_CHAT_RESPONSE_FORMAT`）与 transcript 行的 `significance_perception` 在此路径上不会被填充**，除非日后修改「无工具用户轮」或 `build_companion_tools` 的约定。
- WebSocket 已将 **非空** `significance_perception` dict 写入 **`chat_history`** AI 消息的 **`meta_data["significance_perception"]`**（见 `chat.py`）；在当前约束下该字段通常为 absent。

## 记忆抽取（可选，产品侧）

- 配置 **`memory_extraction.use_significance_perception_in_extraction`**（默认 `False`）：为真时可在抽取流程中利用重要性字段排序与标注（见 `app/services/memory_extraction_service.py`）。

## 命名与本地 REPL

- **`companion_tool_runtime.py`**：工具 schema、派发与 **`execute_tool_call`**，不限于文件系统 I/O。
- **`tools/inty_v2_repl`**：本地 harness；测试里可通过 `sys.path` 挂载（如 `tests/conftest.py`）。
