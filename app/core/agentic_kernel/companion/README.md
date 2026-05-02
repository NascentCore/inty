# Companion kernel 说明

## 分层记忆（路径与心理学术语）

| 逻辑路径 | 命名（中 / EN） | 说明 |
|----------|-----------------|------|
| `memory/daily/{date}.md` | 情景记忆 / episodic memory | 按轮追加的当日流水，`memory_pipeline._append_diary` |
| `memory/{date}.md` | 单日摘要 / gist memory | 当日结构化纪要，`memory_pipeline._rewrite_day_summary_md` |
| `MEMORY.md` | 语义记忆 / semantic memory | 跨日整合定稿，`memory_pipeline._rewrite_memory_md` |

注入 LLM 的 section 标题常量：`memory_taxonomy.py`（与 `prompts.build_system_messages` 一致）。

## 持久化与数据表

- **权威存储**：工作区正文（含 `IDENTITY.md` / `SOUL.md` / `USER.md` / `MEMORY.md` / `transcript.jsonl` / `context.json` 等逻辑路径）在启用 PostgreSQL DSN 时写入表 **`companion_workspace_document_versions`**（ORM：`app.models.companion_workspace.CompanionWorkspaceDocumentVersion`）。
- **作用域**：`(user_id, companion_id, chat_id, document_kind[, calendar_date])`；同一键下 **append-only**，当前正文取 **`sequence_id` 最大** 的一行。`document_kind` 与相对路径的对应关系见 **`workspace_doc_mapping.py`**（例如 `IDENTITY.md` -> `identity`，`context.json` -> `context_json`）。
- **`companion_id` 与 API**：`app.services.companion_chat_service.run_companion_chat_turn_for_api` 把 HTTP/API 里的 **`agent_id` 原样作为 `companion_id`** 传入 `CompanionManager.get_or_create_session`，因此查库时用 **`companion_id = <agent 的 id>`** 即可对齐一次 companion 会话。
- **与旧聊天路径的区别**：旧路径主要消费 **`agents`** 表里的 `main_prompt` / `mode_prompt` / `personality` 等字段做 system 拼装；**agentic companion 内核代码路径（`app/core/agentic_kernel`）不读 `Agent` ORM**。人设与对话状态以 **版本表里的 `content`**（及模板种子）为准，而不是 `agents` 上的人设列。
- **路由层补充**：WebSocket 聊天入口在调用 companion 之前仍会 **`get_agent_for_chat` 查 `agents`**（例如校验角色存在、会话侧仍构造 `Agent` 实例）；**真正一轮 companion 推理用的工作区文档**仍来自 **`companion_workspace_document_versions`**。排查「这段对话对应的设定」时，应优先按 **`user_id` + `companion_id`(=agent_id) + `chat_id`** 查各 `document_kind` 的最新 `content`。

## context.json

### 内容

- JSON，对应 Pydantic 模型 `ContextMeta`（见 `models.py`）。字段名仍为 **`context_mode`**，语义为 **Experience Profile id**（规范化小写），与 `app/core/agentic_kernel/experience_profile.py` 单一真源一致；另有 `user_id`、`companion_id`、`chat_id`。
- 建 session 时由 `CompanionManager.get_or_create_session` 写入默认体验配置（`app.features.companion_default_context_mode`）及当前 `user_id` / `companion_id` / `chat_id`。

### 是否必需

- **跑通 `run_turn` 不是硬性必需**：`load_context_meta` 在 store 中无文件或内容为空时返回默认 `ContextMeta()`（`context_mode` 默认为 `intimate`，三个 id 为空字符串）。
- **仍建议保留并写入**：持久化非默认的体验配置 id；在同一张版本表里留下 `(user_id, companion_id, chat_id)` 便于排查与扩展（`load_prompt_bundle` 与 `prompts.build_system_messages` 通过 `experience_profile` 解析是否注入私人记忆层及 system 条款）。
- **运行时修改**：模型侧使用工具 **`companion_set_experience_profile`**（须 `user_confirmed: true`，禁止静默推断）。不要用 `workspace_write_file` 写 `context.json`。Ops / 网关可对表 **`companion_workspace_document_versions`** 中 `document_kind=context_json` 写入新版本，等价于外部更新。

## 模板目录 `templates/`

- 多数 `.md` 由 `workspace.load_workspace_seed_text` 等在缺省时写入工作区；`BOOTSTRAP.md` 由交互式 bootstrap 读入，不对应持久化切片名。
- **`AXIOM.md`**：产品层「根本法则」文案，**不**作为工作区持久化切片；正文由 `workspace.get_imate_axiom_system_text()` 从包内 `templates/AXIOM.md` 读取（`lru_cache`），并在 `prompts.build_system_messages` 中作为**首条** `system` 注入（先于安全基线与 `IDENTITY` / `SOUL` 等）。

## System 与提示词切片

- **多段 system**：`prompts.build_system_messages` 返回若干条 `{"role":"system","content":...}`（**首条**为 AXIOM（若非空），其次为安全基线，余下为 TOOLS / IDENTITY / SOUL 等；内在节拍「陪伴心跳」轮次另注入 `_heartbeat_clause()`，不读工作区 `HEARTBEAT.md`），由 `turn.run_turn` 与 `turn_engine.build_repl_turn_base_messages` 置于对话列表前缀；`build_system_prompt` 用 `prompt_slices.SYSTEM_PROMPT_SLICE_SEPARATOR` 将各段 `content` 拼成单字符串，供仅需单串的调用方使用（与交互式 bootstrap 块拼接同一常量）。
- **切片枚举**：`prompt_slices.PromptSliceId` 与 `companion_update_prompt_slice` 可写映射 `PROMPT_SLICE_TO_REL` 同源。

### 持久化

- **可以且在生产 API 路径下默认已入库**：`context.json` 映射为 `CompanionWorkspaceDocKind.CONTEXT_JSON`（`workspace_doc_mapping.py`），经 `MemoryStore.write_document` 走与 `IDENTITY.md` 等相同的 append-only 版本表 `companion_workspace_document_versions`（`document_kind = context_json`），读最新一条即当前正文。
- 在 `repository_only_workspace_text` 为 true 时，通过 `store.write_document("context.json", ...)` 写入，不落盘为工作区权威来源。

### 相关代码入口

- 读取：`models.load_context_meta(..., store=store)`；`turn.run_turn` 在组装 prompt 前加载。
- 写入：`manager.CompanionManager.get_or_create_session`（`context.json` 缺失时）。
