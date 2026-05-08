# iMate companion 设计（kernel）

## 路由

- HTTP `chat/completions`：传统 `Agent.chat`。
- WebSocket `chat/ws`：`companion_chat_service` → `CompanionManager` → `companion.turn.run_turn`。权威：`MemoryStore`（ORM 持久化文档 + `transcript.jsonl`）；产品聊天行：`chat_history_service`。

## 回合

- 由 prompt 切片（`PromptBundle`）组装 system + transcript 窗口 + 可选 compaction。
- LLM：`CompanionLLMClient`（OpenAI 兼容）；tool 循环调用 `companion_tool_runtime.execute_tool_call`（schema 在 `tools.py`）。
- 回合后：按配置将记忆管线入队或同步。

## 双 LLM

- 启用时：chat 与 tool 分流不同模型路由；**生产 WebSocket** 在 `tools_for_turn` 非空时固定为「前台 chat（`chat_model`，JSON envelope）+ 后台线程完整 tool 循环（`tool_model`）」，后台 tool 模型 id 可由 YAML **`app.agent.companion_tool_call_model`** 与订阅 chat 模型解耦（见 `/app/core/AGENTS.md`）。`run_turn` 内不再有同步多轮 tool 调用路径。
- Chat 路可携带与并行路相同的工具定义镜像，并约定 `tool_choice=none`，以便对齐上下文而不在 chat 路实际调用工具。

**实现补充（与代码对齐）**：`CompanionLLMClient.chat_completion` 按「本轮请求是否带 tools」切换两套同步客户端并分别解析 `chat_model` / `tool_model`。上述「异步前台 chat + 后台 tool 循环」由 `companion/tool_background.py` 实现；**WebSocket companion** 经 `run_turn` 在工具启用时调用 `start_tool_background_job`。后台线程 `asyncio.run` 不可与安全共享全局 `AsyncSessionLocal` 混用；`start_tool_background_job(..., main_event_loop=...)` 时，`tool_update_agent_status_line` 的 PG 写入由 `app/services/agent_status_line.persist_agent_status_line` 经 `run_coroutine_threadsafe` 投递回主事件循环。提示词里关于「镜像工具 + chat 路禁调用」的分支主要在 **`prompts.build_system_messages`**（例如 `include_repl_image_generation_contract=False` 时的 chat 分支契约）；生产 WebSocket 默认路径见下文「回合」详细说明。

## 重要性感知

- **Significance 引导**：包内模板 `SIGNIFICANCE_PERCEPTION.md` 全文经 `bundle.significance_perception_md` 注入（不从 MemoryStore 读该路径）；当 **chat** 分支为非 tool 路时，可选用结构化信封（`response_format` JSON schema，定义见 `significance_perception.py` 中 `DUAL_LLM_CHAT_RESPONSE_FORMAT`）。
- 字段：`user_facing_reply`、`importance_round`、`importance_user_message`、`importance_assistant_message`（均为 1-10 的重要性整数）。
- Assistant 的 transcript 行可携带 `significance_perception`；WebSocket 路径可将该 dict 写入 AI 消息的 `chat_history.meta_data`，供下游任务消费。

**实现补充（与代码对齐）**：`companion/turn.py` 中 `use_dual_structured_chat = (not heartbeat_turn) and not tools_for_turn`。当前 **`build_companion_tools` → `build_openai_repl_tools` 在正常用户轮次下返回的工具列表非空**，故在该约定未改前，**上述 JSON envelope 与 transcript 上的 `significance_perception` 在默认 WebSocket 闲聊路径上通常不会生效**；`chat.py` 仍会在 dict 非空时写入 `meta_data["significance_perception"]`。

## 记忆抽取（可选）

- 配置 **`memory_extraction.use_significance_perception_in_extraction`**：为真时按 `importance_round` 排序回合、在 prompt 行上标注分数、向抽取 prompt 追加短英文提示块。默认关闭（见 `app/services/memory_extraction_service.py`）。

## 命名

- **`companion_tool_runtime.py`**：companion 工具 schema、派发与执行（不限于文件系统 I/O）。

## REPL

- **`tools/inty_v2_repl`**：仅 WebSocket 终端客户端（`python -m tools.inty_v2_repl.main repl` → `/api/v1/chat/ws`）；companion 推理在 `app/core/agentic_kernel/companion/`。说明见 [`tools/inty_v2_repl/README.md`](../../tools/inty_v2_repl/README.md)。

---

以下为与 **`app/core/agentic_kernel`** 及 **`companion_chat_service` / WebSocket** 实现对齐的扩展说明（路由表、入口、bootstrap、持久化等）。

## 两条对话路径（对照）

| 路由 | 核心栈 | `app/core/agentic_kernel` 作用 |
| --- | --- | --- |
| `POST /api/v1/chat/completions/{agent_id}` | 传统 `app.core.agent.agent.Agent` | 可选使用 `prompting/assembler`、`tools/runtime` 等（见 `Agent` 的 import）。**不**执行 `companion.turn.run_turn`。 |
| `WS /api/v1/chat/ws` | `companion_chat_service` + `CompanionManager` + `companion.turn.run_turn` | 主路径：`companion/*` 与共享的 `providers/facade`、`tools/registry`、`tools/dispatchers/*`。 |

WebSocket 处理函数在 `app/api/v1/endpoints/chat.py`（`router` 前缀为 `/chat`，在 `API_V1_PREFIX` 下全路径为 `/api/v1/chat/ws`）。

## WebSocket 入口与是否走 companion

1. `chat_completions_websocket` 接受连接、解析 `current_user`、可选 `assume_user_id`、读取头 `appVersionCode`。
2. 服务端不在 `accept` 后推送 connect-time kickoff；客户端用 `messageType: IMPLICIT_USER_SIGNED_ON` 聊天帧触发首轮问候（文案见 `/app/core/agentic_kernel/companion/implicit_signal_messages.py`）。Query `agent_id` 仍为 REPL 等场景的 URL 约定。
3. 主循环：解析 `ChatWebSocketRequest`、合并时间上下文、调用 `_agent_chat_completions_impl(..., chat_route="websocket")`。
4. 在 `_agent_chat_completions_impl` 中 `use_companion = (chat_route == "websocket")`。为真时，自然语言回复由 `companion_chat_service.run_companion_chat_turn_for_api` 产生，**不**走 `Agent.generate_message...`。

## 服务与 session 层

- **`app/services/companion_chat_service.py`**
  - 从 `global_config_loaded_from_config_yaml` 构建 `CompanionConfig` / `CompanionLLMConfig`（`app.features`、`agent.chat_llm_*`、`agent.api_key`、`agent.companion_tool_call_model`（写入 `tool_model`，可与解析后的 chat 模型 id 不同）、`database.url` 作为 MemoryStore 的 DSN 等）。
  - 按「解析后的 chat 模型 id + 运行时指纹」LRU 缓存 `CompanionManager`。
  - `run_companion_chat_turn_for_api`：`get_or_create_session`、可选 `_maybe_append_companion_ws_session_system`（仅 **`USER_INTERACTIVE`** bootstrap）、再 `manager.run_turn`。
- **`app/core/agentic_kernel/companion/manager.py`**
  - `get_or_create_session`：按合成 scope 路径注册 `MemoryStore`、写入最小种子文档、`ensure_minimal_documents_in_store`。
  - `run_turn`：薄封装，调用 `companion.turn.run_turn`。

## 核心一轮：`companion/turn.py` 中 `run_turn`

单轮用户文本（或 heartbeat 的合成文本）顺序大致为：

1. 从 `MemoryStore` 加载 `ContextMeta`、`PromptBundle`（`load_context_meta`、`load_prompt_bundle`）。
2. 加载 `transcript.jsonl`，可按配置做 transcript compaction（`transcript_compaction.py`）。
3. **`prompts.build_system_messages`**（若写「拼 system prompt」，以该函数为准；另存在 `build_system_prompt` 用于拼接字符串场景）。含 interactive bootstrap、`SIGNIFICANCE_PERCEPTION` slice 等分支。
4. **`tools.build_companion_tools`** → `companion_tool_runtime.build_openai_repl_tools`；interactive bootstrap 激活时工具集合会收窄。
5. LLM 与 tool：**若 `tools_for_turn` 为空**，单次 `CompanionLLMClient.chat_completion`（chat 路由、`chat_model`）。**若非空**，先 `start_tool_background_job`（后台线程内对 tool 路由连续 `chat_completion` + `execute_tool_call`），再在同一 `run_turn` 内前台 `chat_completion`（chat 路由、`tools=None`、JSON envelope）；详见 `tool_background.py`。
6. 工具执行：`companion_tool_runtime.execute_tool_call` → **`tools/registry.py`**、`tools/dispatchers/memory_store.py`、`tools/dispatchers/media.py` 等与 companion 共用的解析/派发；交互式 bootstrap 专有逻辑在 `companion/` 内（主要在后台 tool 循环中触发）。
7. 将 user/assistant（及 tool 轨迹）写入 transcript；`schedule_memory_update_after_turn` / `memory_pipeline.py` 做回合后记忆处理。

**`companion/turn_engine.py`**：拼 OpenAI messages 的辅助模块（例如测试或 REPL 风格组装）。生产 **`WS /api/v1/chat/ws`** 不 import 它，而是经 `companion_chat_service` 走 **`turn.run_turn`**。

## Bootstrap：`companion_memory_bootstrap_type`

| 取值 | Session 创建 | API 路径上首轮行为 |
| --- | --- | --- |
| `NONE`（默认） | 最小种子文档入 store | 每条用户消息均为 `run_turn` |
| `USER_INTERACTIVE` | 同上 + `context.json` 等交互阶段标记 | 仍为 `run_turn`；模型通过 `companion_update_prompt_slice` / `companion_bootstrap_user_interactive_complete`（见 `bootstrap_user_interactive.py`）；SOUL 锁定等与 `memory_pipeline`、`companion_tool_runtime` 协同 |

实现入口：`manager.py`（session）、`companion_chat_service.py`（分支与首轮 `run_turn`）。

## WebSocket companion 路径会用到的共享内核

- **`providers/facade.py`**（及 `openai_compatible.py`）：`CompanionLLMClient` 的 HTTP 客户端。
- **`tools/registry.py`**、**`tools/dispatchers/*`**：`companion_tool_runtime` 内注册表与 memory_store/media 派发辅助。

当前 **`build_openai_repl_tools`** 在向模型暴露的工具列表末尾仍包含 **`google_web_search`、`generate_image`、`modify_image`** 等（定义在同文件的 `build_openai_tools()` 拼装结果上）；执行路径在 **`companion_tool_runtime.execute_tool_call`**。

## 不在「WS companion 答复」主链上的模块

以下仍在 `app/core/agentic_kernel/` 下，但 **`companion/turn.py`** 与 **`companion_chat_service` → WebSocket** 链**不**依赖它们：

- **`contracts/*`**、`runtime/turn_orchestrator.py`、`runtime/persistence.py`、`bridges/experimental_bridge.py`：另一套基于 `TurnInput` / `TurnOutput` 的类型化回合管线，不等同于当前 companion REPL 循环。

推断 WebSocket companion 行为应以 **`companion/turn.py`** 与 **`companion_tool_runtime.py`** 为准，而非单独看 `contracts/`。

## 持久化（概念）

- **MemoryStore 权威（API companion）**：文档与 transcript 版本经 **`MemoryStore`**（配置好 DSN 时 ORM 落库，如表 **`companion_memory_document_versions`**），而非进程内以本地磁盘为唯一真相。
- **产品聊天记录**：用户/助手消息经 **`chat_history_service`** 在 companion 返回后写入；可选将 `significance_perception` 放入 AI 消息的 `meta_data`。

合成路径：`CompanionManager` 仍使用 `companion_chat_service.COMPANION_MEMORY_STORE_SCOPE_ROOT_PREFIX`（默认 `/var/lib/inty/companion_memory_scopes`）拼出逻辑 scope 根路径，供工具内路径解析与 store 注册键使用。

---

## 回合内行为（kernel 实现摘要）

- **System**：来自 `PromptBundle`、上下文模式、包内 **TOOLS** 模版全文（`bundle.tools_md`）、`IDENTITY` / `SOUL` / `USER`、亲密模式下可选 MEMORY 块、可选 interactive bootstrap 片段、输出契约等；**陪伴心跳**轮由 `_heartbeat_clause()` 与 `HEARTBEAT_SYNTHETIC_USER_TEXT`（system）驱动，不读工作区 `HEARTBEAT.md`；组装函数为 **`build_system_messages`**。
- **Transcript**：窗口由 `transcript_llm_window_max_messages` 与默认上限共同约束；可配置 compaction。
- **LLM**：OpenAI 兼容 **`CompanionLLMClient.chat_completion`**；无工具时为单次 chat 路由 + chat model。有工具时（生产 WS）：前台 chat 路由 + chat model；后台 tool 循环用 tool 路由 + `resolve_model("tool")`（YAML `app.agent.companion_tool_call_model` 经 `companion_chat_service` 注入）。
- **Tools**：`tools.py` 暴露 schema；执行在 **`companion_tool_runtime.execute_tool_call`**。
- **回合后**：`defer_memory_update=True`（API 默认）时异步调度记忆管线。
