# Companion Harness · `companion` 子包

单轮编排：MemoryStore 文档、多段 system、前台 chat、异步 `tool_background`、significance envelope、transcript / 运行时事件；**人设与状态以 `companion_memory_document_versions` 正文为准**，harness **不读** `Agent` ORM。范式与表细节见 [/docs/companion_harness/MEMORY_STORE.md](/docs/companion_harness/MEMORY_STORE.md)。

## 该改哪些文件

- **回合与路由**：`turn.py`、`turn_routes.resolve_turn_route_mode`、`prompt_stack.py`
- **LLM**：`llm_client.py`；同步单轮契约与注入：`llm/ports.ChatCompletionsSyncPort` → `llm/chat_completions.create_chat_completion_sync`（`CompanionLLMClient.chat_completions_sync`；`start_tool_background_job` 可注入）。**新增同步 completion 须走此端口或** `companion_llm_runtime_event_bind_ctx`（`llm_runtime_events.py`）
- **工具后台**：`tools/tool_background.py`

## 记忆路径（注入标题见 `memory_taxonomy.py`）

| 逻辑路径 | 称呼 |
|----------|------|
| `memory/daily/{date}.md` | 情景 / episodic |
| `memory/{date}.md` | 单日摘要 / gist |
| `MEMORY.md` | 语义 / semantic |

**System 顺序**：越全局的约束越靠前（首条常为包内 [AXIOM.md](/app/core/companion_harness/companion/prompts/AXIOM.md)）。Workspace 模板见 [templates](/app/core/companion_harness/memory/templates/)，更新频率大致：SOUL → IDENTITY/USER → MEMORY。

## 持久化（提要）

- DSN 启用时正文入 **`companion_memory_document_versions`**；registry 键 **`CompanionScope.registry_key()`**（`user_id:companion_id:chat_id`），入口 **`get_memory_store`**；append-only，取 **`sequence_id` 最大**。路径 ↔ `document_kind`：**`memory_store_document_mapping.py`**
- API 里 **`agent_id` = `companion_id`**。网关仍可 `get_agent_for_chat` 查 **`agents`** 做存在性等；**推理用文档只来自版本表**（按 `user_id` + `companion_id` + `chat_id` 排查）
- `CHAT_LOGS.md` 默认不进 LLM；`transcript.jsonl`、`.companion_runtime_events.jsonl`、`context.json` 等同表持久化逻辑见 MEMORY_STORE 文档

## `context.json`（`ContextMeta`，`models.py`）

- **`context_mode`**：Experience Profile id（小写），真源 **`experience_profile.py`**
- **USER_INTERACTIVE**：`bootstrap` / `post_bootstrap_context_mode` 语义与 **`companion_bootstrap_user_interactive_complete`**、**`companion_set_experience_profile`**（须 `user_confirmed`）见代码与 `CompanionManager.get_or_create_session`
- 缺文件时 `load_context_meta` 回退默认；**勿**用 `memory_store_write_document` 写 `context.json`（模型改体验用工具；Ops 可直接写 `context_json` 版本行）

## 种子与 system

- **`templates/`**：工作区缺省种子；**`prompts/`**：`AXIOM.md` / `BOOTSTRAP.md` / `TOOLS.md` / `SIGNIFICANCE_PERCEPTION.md` 固定文案（`memory_store_scope.load_template_seed_text` 仅对上述四文件名走 `prompts/`，其余走 `templates/`）
- **`prompts.build_system_messages`** 多段 system；心跳句 `_heartbeat_clause()`；可写切片仅限 IDENTITY/SOUL/USER/MEMORY 根稿（`companion_update_prompt_slice`）

## Significance

envelope 与解析：**`significance_perception.py`**；注入时机：**`prompt_stack`**；落库 transcript / 可选 **`meta_data.significance_perception`**；抽取侧默认关。

## Async tool 与 transcript

- `tools_enabled` → **`ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL`**：用户轮 **先** 前台 envelope（无 tools），**再** 线程里 `start_tool_background_job`，**返回不等**后台；**维护性 inner tick** 跳过前台 envelope、工具首轮可强制
- 下一轮前 **`tool_bg_idle`** wait（**`INTY_TOOL_BG_IDLE_WAIT_TIMEOUT_SEC`**）；`tool_bg` assistant 行 + **`--- Tool results ---`**
- 双轨契约、前台为何关部分 repl 条款：**`prompts/system_messages.py`** + **`prompt_stack.companion_turn_tools_and_system_messages`**
