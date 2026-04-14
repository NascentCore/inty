# Companion kernel 说明

## 持久化与数据表

- **权威存储**：工作区正文（含 `IDENTITY.md` / `SOUL.md` / `USER.md` / `MEMORY.md` / `transcript.jsonl` / `context.json` 等逻辑路径）在启用 PostgreSQL DSN 时写入表 **`companion_workspace_document_versions`**（ORM：`app.models.companion_workspace.CompanionWorkspaceDocumentVersion`）。
- **作用域**：`(user_id, companion_id, chat_id, document_kind[, calendar_date])`；同一键下 **append-only**，当前正文取 **`sequence_id` 最大** 的一行。`document_kind` 与相对路径的对应关系见 **`workspace_doc_mapping.py`**（例如 `IDENTITY.md` -> `identity`，`context.json` -> `context_json`）。
- **`companion_id` 与 API**：`app.services.companion_chat_service.run_companion_chat_turn_for_api` 把 HTTP/API 里的 **`agent_id` 原样作为 `companion_id`** 传入 `CompanionManager.get_or_create_session`，因此查库时用 **`companion_id = <agent 的 id>`** 即可对齐一次 companion 会话。
- **与旧聊天路径的区别**：旧路径主要消费 **`agents`** 表里的 `main_prompt` / `mode_prompt` / `personality` 等字段做 system 拼装；**agentic companion 内核代码路径（`app/core/agentic_kernel`）不读 `Agent` ORM**。人设与对话状态以 **版本表里的 `content`**（及模板种子）为准，而不是 `agents` 上的人设列。
- **路由层补充**：WebSocket 聊天入口在调用 companion 之前仍会 **`get_agent_for_chat` 查 `agents`**（例如校验角色存在、会话侧仍构造 `Agent` 实例）；**真正一轮 companion 推理用的工作区文档**仍来自 **`companion_workspace_document_versions`**。排查「这段对话对应的设定」时，应优先按 **`user_id` + `companion_id`(=agent_id) + `chat_id`** 查各 `document_kind` 的最新 `content`。

## context.json

### 内容

- JSON，对应 Pydantic 模型 `ContextMeta`（见 `models.py`）：`context_mode`、`user_id`、`companion_id`、`chat_id`。
- 建 session 时由 `CompanionManager.get_or_create_session` 写入默认 `context_mode`（来自配置）及当前 `user_id` / `companion_id` / `chat_id`。

### 是否必需

- **跑通 `run_turn` 不是硬性必需**：`load_context_meta` 在 store 中无文件或内容为空时返回默认 `ContextMeta()`（`context_mode` 默认为 `intimate`，三个 id 为空字符串）。
- **仍建议保留并写入**：持久化非默认的 `context_mode`；在同一张版本表里留下 `(user_id, companion_id, chat_id)` 便于排查与扩展（当前 system prompt 主要消费 `context_mode`，见 `load_prompt_bundle` 与 `prompts.build_system_prompt` 中的 `_context_mode_clause`）。

### 持久化

- **可以且在生产 API 路径下默认已入库**：`context.json` 映射为 `CompanionWorkspaceDocKind.CONTEXT_JSON`（`workspace_doc_mapping.py`），经 `MemoryStore.write_document` 走与 `IDENTITY.md` 等相同的 append-only 版本表 `companion_workspace_document_versions`（`document_kind = context_json`），读最新一条即当前正文。
- 在 `repository_only_workspace_text` 为 true 时，通过 `store.write_document("context.json", ...)` 写入，不落盘为工作区权威来源。

### 相关代码入口

- 读取：`models.load_context_meta(..., store=store)`；`turn.run_turn` 在组装 prompt 前加载。
- 写入：`manager.CompanionManager.get_or_create_session`（`context.json` 缺失时）。
