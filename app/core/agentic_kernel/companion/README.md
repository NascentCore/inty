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
- **仍建议保留并写入**：持久化非默认的 `context_mode`；在同一张版本表里留下 `(user_id, companion_id, chat_id)` 便于排查与扩展（当前 system 主要消费 `context_mode`，见 `load_prompt_bundle` 与 `prompts.build_system_messages` / `build_system_prompt` 中的 `_context_mode_clause`）。

## 模板目录 `templates/`

- 多数 `.md` 由 `workspace.load_workspace_seed_text` 等在缺省时写入工作区；`BOOTSTRAP.md` 由交互式 bootstrap 读入，不对应持久化切片名。
- **`AXIOM.md`**：产品层「根本法则」文案，**不**作为工作区持久化切片；正文由 `workspace.get_imate_axiom_system_text()` 从包内 `templates/AXIOM.md` 读取（`lru_cache`），并在 `prompts.build_system_messages` 中作为**首条** `system` 注入（先于安全基线与 `IDENTITY` / `SOUL` 等）。

## System 与提示词切片

- **多段 system**：`prompts.build_system_messages` 返回若干条 `{"role":"system","content":...}`（**首条**为 AXIOM（若非空），其次为安全基线，余下为 TOOLS / HEARTBEAT / IDENTITY / SOUL 等），由 `turn.run_turn` 与 `turn_engine.build_repl_turn_base_messages` 置于对话列表前缀；`build_system_prompt` 用 `prompt_slices.SYSTEM_PROMPT_SLICE_SEPARATOR` 将各段 `content` 拼成单字符串，供仅需单串的调用方使用（与交互式 bootstrap 块拼接同一常量）。
- **切片枚举**：`prompt_slices.PromptSliceId`（无 `AGENTS`）与 `companion_update_prompt_slice` 可写映射 `PROMPT_SLICE_TO_REL` 同源。
- **AGENTS.md**：不再注入模型、不由 `load_prompt_bundle` 读取、`PromptBundle.agents_md` 恒为默认空；版本表仍可能保留历史 `AGENTS` 文档 kind，仅作遗留数据。

### 持久化

- **可以且在生产 API 路径下默认已入库**：`context.json` 映射为 `CompanionWorkspaceDocKind.CONTEXT_JSON`（`workspace_doc_mapping.py`），经 `MemoryStore.write_document` 走与 `IDENTITY.md` 等相同的 append-only 版本表 `companion_workspace_document_versions`（`document_kind = context_json`），读最新一条即当前正文。
- 在 `repository_only_workspace_text` 为 true 时，通过 `store.write_document("context.json", ...)` 写入，不落盘为工作区权威来源。

### 相关代码入口

- 读取：`models.load_context_meta(..., store=store)`；`turn.run_turn` 在组装 prompt 前加载。
- 写入：`manager.CompanionManager.get_or_create_session`（`context.json` 缺失时）。
