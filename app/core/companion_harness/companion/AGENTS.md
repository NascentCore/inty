# Companion Harness · `companion` 子包

## 总览

- **是什么**：单轮对话编排层——把 **MemoryStore 工作区文档**、**多段 system 提示词**、**前台 chat 与异步 tool_background**、**结构化 envelope（significance）** 与 **transcript / 运行时事件** 串成一次对用户可见的回合；人设与长期状态以版本表中的正文为准，不读 `Agent` ORM 的人设列。
- **和谁相关**：改一轮里「谁先 LLM、谁带 tools、system 顺序、inner tick 分支」时读本包 **`turn.py`** / **`turn_routes.py`** / **`prompt_stack.py`**；改 OpenRouter 调用与可注入同步完成面时读 **`llm_client.py`** 与 harness **`llm/ports.py`**、**`llm/chat_completions.py`**；改工具后台线程契约时读 **`tools/tool_background.py`**（由 `turn` 启动）。
- **边界**：持久化范式、表结构与 registry 细节仍以 [/docs/companion_harness/MEMORY_STORE.md](/docs/companion_harness/MEMORY_STORE.md) 与下文「持久化与数据表」为准；本文件不重复 `memory/` 包内实现细节。

## 关键入口与 LLM 同步端口

- **路由**：`turn_routes.resolve_turn_route_mode` 根据 `inner_tick_turn` / `InnerTickMode` / `tools_enabled` 等决定前台是否 envelope、是否走异步工具轨；与 `turn.run_turn` 内分支一致，改路由时两处语义需对齐。
- **同步 chat 完成面**：`llm.ports.ChatCompletionsSyncPort` 描述「单轮 OpenAI-compatible `chat.completions` + harness 约定 kwargs」的可注入形状；规范实现为 `llm.chat_completions.create_chat_completion_sync`。`CompanionLLMClient.chat_completions_sync` 默认绑定该实现；`start_tool_background_job` 可注入同一端口，使前台与后台工具环共享管线（LangSmith enrich、失败记入 `llm_inference_failure` 等）。**新增 companion 侧同步 completion 调用应走此端口或等价绑定**，否则与 `companion_llm_runtime_event_bind_ctx`（`llm_runtime_events.py`）及运行时可观测性脱节。

## 分层记忆（路径与心理学术语）

| 逻辑路径 | 命名（中 / EN） | 说明 |
|----------|-----------------|------|
| `memory/daily/{date}.md` | 情景记忆 / episodic memory | 按轮追加的当日流水，`memory_pipeline._append_diary` |
| `memory/{date}.md` | 单日摘要 / gist memory | 当日结构化纪要，`memory_pipeline._rewrite_day_summary_md` |
| `MEMORY.md` | 语义记忆 / semantic memory | 跨日整合定稿，`memory_pipeline._rewrite_memory_md` |

注入 LLM 的 section 标题常量：`memory_taxonomy.py`（与 `prompts.build_system_messages` 一致）。

系统层级约束以 System Role 注入到各层提示词；每个文件承载该层约束的语义。越底层、越全局的约束应出现在越靠前的 system 段（模型对靠前指令通常更服从）。这些段落刻画的是「用户–智能体」交互对与模式的整体理解，不等同于智能体静态人设全文——因此称为 system-hierarchy，而非「角色设定单」之类命名。

1. **AXIOM.md**：[prompts/AXIOM.md](/app/core/companion_harness/companion/prompts/AXIOM.md)（非 Workspace 根目录稿）
2. 下列为 [templates](/app/core/companion_harness/memory/templates/) 下 Workspace 初始模板，随交互更新；越靠前更新越慢：
   1. SOUL.md
   2. IDENTITY.md / USER.md
   3. MEMORY.md

## 持久化与数据表

- **目标架构（范式）**：MemoryStore 与 ARCH 命名对齐后的合并说明（SessionBinding / SessionCorpus、现状与目标态、Harness LTM 边界）见 [/docs/companion_harness/MEMORY_STORE.md](/docs/companion_harness/MEMORY_STORE.md)。
- **权威存储**：工作区正文（含 `IDENTITY.md` / `SOUL.md` / `USER.md` / `MEMORY.md` / `CHAT_LOGS.md`（WebSocket `user_signed_out` 等运维追加流水，`document_kind=chat_logs_md`，默认不参与 LLM prompt；后续是否接入产品/分析管线另行设计）/ `transcript.jsonl` / `.companion_runtime_events.jsonl`（运行时异常事件 JSONL，`runtime_events.py` 仅经 MemoryStore 读写）/ `context.json` 等逻辑路径）在启用 PostgreSQL DSN 时写入表 **`companion_memory_document_versions`**（ORM：`app.models.companion_memory_documents.CompanionMemoryDocumentVersion`）。
- **进程内 registry**：带 repository 的 `MemoryStore` 在 [`memory_registry.py`](/app/core/companion_harness/memory/memory_registry.py) 中仅以 **`CompanionScope.registry_key()`**（`user_id:companion_id:chat_id`）注册与复用；`get_memory_store(scope, dsn=...)` 为唯一入口，工具与 `run_turn` 边界通过 **`MemoryStore` 实例**（及线程局部的 runtime inspect overlay）对齐同一 ORM 写入面。
- **作用域**：`(user_id, companion_id, chat_id, document_kind[, calendar_date])`；同一键下 **append-only**，当前正文取 **`sequence_id` 最大** 的一行。`document_kind` 与相对路径的对应关系见 **`memory_store_document_mapping.py`**（例如 `IDENTITY.md` -> `identity`，`context.json` -> `context_json`）。
- **`companion_id` 与 API**：`app.services.companion_chat_service.run_companion_chat_turn_for_api` 把 HTTP/API 里的 **`agent_id` 原样作为 `companion_id`** 传入 `CompanionManager.get_or_create_session`，因此查库时用 **`companion_id = <agent 的 id>`** 即可对齐一次 companion 会话。
- **与旧聊天路径的区别**：旧路径主要消费 **`agents`** 表里的 `main_prompt` / `mode_prompt` / `personality` 等字段做 system 拼装；**companion harness 代码路径（`app/core/companion_harness`）不读 `Agent` ORM**。人设与对话状态以 **版本表里的 `content`**（及模板种子）为准，而不是 `agents` 上的人设列。
- **路由层补充**：WebSocket 聊天入口在调用 companion 之前仍会 **`get_agent_for_chat` 查 `agents`**（例如校验角色存在、会话侧仍构造 `Agent` 实例）；**真正一轮 companion 推理用的工作区文档**仍来自 **`companion_memory_document_versions`**。排查「这段对话对应的设定」时，应优先按 **`user_id` + `companion_id`(=agent_id) + `chat_id`** 查各 `document_kind` 的最新 `content`。

## context.json

### 内容

- JSON，对应 Pydantic 模型 `ContextMeta`（见 `models.py`）。字段名仍为 **`context_mode`**，语义为 **Experience Profile id**（规范化小写），与 `app/core/companion_harness/experience_profile.py` 单一真源一致；另有 `user_id`、`companion_id`、`chat_id`。
- **`bootstrap`**：`ExperienceContextMode.BOOTSTRAP`，仅在 **`companion_memory_bootstrap_type=USER_INTERACTIVE`** 且 **`workspace_bootstrap_user_interactive_completed`** 为 false 时由内核写入 `context_mode`；用于 system「当前体验配置」与 Trace 对齐交互式引导阶段，**不可**作为 `app.features.companion_default_context_mode` 或 **`companion_set_experience_profile`** 的用户自选目标。
- **`post_bootstrap_context_mode`**（可选）：USER_INTERACTIVE 种子写入，表示引导结束后应恢复的常规体验 profile（规范化小写，**不得**为 `bootstrap`）。模型调用 **`companion_bootstrap_user_interactive_complete`** 后：若当前仍为 `bootstrap`，将 `context_mode` 恢复为该字段（缺省回退 `intimate`），并删除此键；若引导期内已通过 **`companion_set_experience_profile`** 切换为非 `bootstrap`，则保留当前 `context_mode`。
- 建 session 时由 `CompanionManager.get_or_create_session` 写入默认体验配置（非 USER_INTERACTIVE 时为 `app.features.companion_default_context_mode`；USER_INTERACTIVE 新种子为 `context_mode=bootstrap` + `post_bootstrap_context_mode=<默认>`）及当前 `user_id` / `companion_id` / `chat_id`。

### 是否必需

- **跑通 `run_turn` 不是硬性必需**：`load_context_meta` 在 store 中无文件或内容为空时返回默认 `ContextMeta()`（`context_mode` 默认为 `intimate`，三个 id 为空字符串）。
- **仍建议保留并写入**：持久化非默认的体验配置 id；在同一张版本表里留下 `(user_id, companion_id, chat_id)` 便于排查与扩展（`load_prompt_bundle` 与 `prompts.build_system_messages` 通过 `experience_profile` 解析是否注入私人记忆层及 system 条款）。
- **运行时修改**：模型侧使用工具 **`companion_set_experience_profile`**（须 `user_confirmed: true`，禁止静默推断）。不要用 `memory_store_write_document` 写 `context.json`。Ops / 网关可对表 **`companion_memory_document_versions`** 中 `document_kind=context_json` 写入新版本，等价于外部更新。

## 包内种子稿：`templates/` 与 `prompts/`

- **`templates/`**：工作区缺省时由 `memory_store_scope.load_template_seed_text` 写入的持久化约定稿种子（如 `IDENTITY.md` / `SOUL.md` / `USER.md` / `MEMORY.md`）。
- **`prompts/`**：不作为 MemoryStore 根目录同名文件的默认种子；内含 **`AXIOM.md`**、**`BOOTSTRAP.md`**、**`TOOLS.md`**、**`SIGNIFICANCE_PERCEPTION.md`**（固定注入文案）。`BOOTSTRAP.md` 由交互式 bootstrap 读入。`load_template_seed_text` 对上述四字文件名走 `prompts/`，其余仍走 `templates/`。
- **`AXIOM.md`**：产品层「根本法则」，由 `memory_store_scope.get_imate_axiom_system_text()` 从包内 `prompts/AXIOM.md` 读取（`lru_cache`），在 `prompts.build_system_messages` 中作为**首条** `system` 注入。

## System 与提示词切片

- **多段 system**：`prompts.build_system_messages` 返回若干条 `{"role":"system","content":...}`（**首条**为 AXIOM（若非空），其次为安全基线，余下为包内 TOOLS 模版正文 / IDENTITY / SOUL 等；内在节拍「陪伴心跳」轮次另注入 `_heartbeat_clause()`，不读工作区 `HEARTBEAT.md`），由 `turn.run_turn` 与 `turn_engine.build_repl_turn_base_messages` 置于对话列表前缀；`build_system_prompt` 用 `prompt_slices.SYSTEM_PROMPT_SLICE_SEPARATOR` 将各段 `content` 拼成单字符串，供仅需单串的调用方使用（与交互式 bootstrap 块拼接同一常量）。
- **切片枚举**：`companion_update_prompt_slice` 仅允许 `PROMPT_SLICE_TO_REL` 中的四字根目录稿（IDENTITY / SOUL / USER / MEMORY）；SIGNIFICANCE / TOOLS 引导为包内固定模版注入。

### 持久化

- **可以且在生产 API 路径下默认已入库**：`context.json` 映射为 `CompanionMemoryDocumentKind.CONTEXT_JSON`（`memory_store_document_mapping.py`），经 `MemoryStore.write_document` 走与 `IDENTITY.md` 等相同的 append-only 版本表 `companion_memory_document_versions`（`document_kind = context_json`），读最新一条即当前正文。
- 在 `repository_only_store_text` 为 true 时，通过 `store.write_document("context.json", ...)` 写入，不落盘为工作区权威来源。

### 相关代码入口

- 读取：`models.load_context_meta(..., store=store)`；`turn.run_turn` 在组装 prompt 前加载。
- 写入：`manager.CompanionManager.get_or_create_session`（`context.json` 缺失时）。

## Importance scoring（significance perception）

- **含义**：前台 chat 与异步 tool 收尾共用同一 envelope：`user_facing_reply`、三条 `importance_*`（1-10）、`output_to_user`（前台须为 true；工具收尾可为 false 表示静默）。解析与 schema 真源：[`significance_perception.py`](/app/core/companion_harness/companion/significance_perception.py)（模块顶部 docstring 汇总全链路消费点）。
- **提示词**：包内 [`prompts/SIGNIFICANCE_PERCEPTION.md`](/app/core/companion_harness/companion/prompts/SIGNIFICANCE_PERCEPTION.md) 经 `PromptBundle.significance_perception_md` 注入；与 JSON 输出契约一同由 `prompts/system_messages.py` 在 `include_significance_perception_slice` 为真时挂上。
- **路由**：`prompt_stack.py` 决定何时注入 significance slice（与 `turn.run_turn` 中何时使用结构化 envelope 对齐）；详见该文件内注释。
- **落库**：`turn.run_turn` 将解析后的 dict 写入 transcript assistant 行；API 层 `chat.py` 可将同一 dict 写入 `chat_history` AI 消息的 `meta_data.significance_perception`。
- **下游**：`memory_extraction.use_significance_perception_in_extraction` 为真时，[`memory_extraction_service.py`](/app/services/memory_extraction_service.py) 按 `importance_round` 排序并在抽取 prompt 中标注分数（默认关闭）。

## Async tool_background 与 transcript

- **用户轮返回正文 vs 工具 LLM**：`tools_enabled` 时路由恒为 `ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL`。对**普通用户轮**（非「维护性 inner tick」），`run_turn` **先** `await` 前台 `chat_completion`（`tools=None`、双 LLM envelope），`CompanionTurnResult.assistant_text` 仅来自该前台解析的可见文案；**随后** `start_tool_background_job` 在**独立线程**里跑 tool 模型多轮（tool call → execute → 再 chat…），**`run_turn` 返回不等待**该后台链路结束。因此：**有 tool 时，对用户定稿的主回复不依赖「工具路径上那次 LLM」跑完**；工具侧产出经 `ToolOutputEvent` / transcript 的 `tool_bg` 行进入后续轮次与观测。
- **维护性 inner tick 例外**：`inner_tick_turn` 且非 proactive 时内核**跳过**前台 envelope（`assistant_text` 置空），工具路径 `force_tools_first_round=True`，可见 NL 若存在由 `tool_background` 收尾 envelope 等机制产生，语义上不同于「用户轮先聊后工具」的快路径。
- **双 LLM**：前台 envelope 返回后，工具链在后台线程跑完；落盘 `transcript.jsonl` 的 `assistant` 行带 `source=tool_bg`，`content` 为对用户可见 NL（若有）并在其后追加固定 **`--- Tool results ---`** 段，内含本轮工具返回文本摘要（供下一轮 **chat** 与 **tool** 共用同一 transcript 窗口）。
- **顺序**：`CompanionSession.tool_bg_idle`（`threading.Event`）在 `run_turn` 加载 transcript **之前** wait，确保上一轮后台线程已 `set()`（超时则告警并降级继续，环境变量 **`INTY_TOOL_BG_IDLE_WAIT_TIMEOUT_SEC`** 可覆盖秒数，默认与前台 HTTP 超时一致）。
- **快轨 / 慢轨（提示词）**：前台 chat completion **不带 tools**（低延迟「系统 1」）；可核验事实（含运行时自省）由并行 **tool_background**（「系统 2」）自愿调用工具完成。内核**不用代码**改写 `tool_choice` 来强逼首轮工具；契约见 `prompts/system_messages.py`（mirrored chat 合约 + 工具侧紧凑指令 + 工具路首轮说明）。
- **前台 system 组装**：当路由为 `ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL` 且构建非 compact 的前台 stack 时，`prompt_stack.companion_turn_tools_and_system_messages` 设 `include_repl_image_generation_contract=False`，使前台走「快思考路径与并行工具路径须一致」块并挂上 dual-LLM envelope 说明，而**不**注入含「（6）须先调用 companion_runtime_inspect」的完整工具输出条款（该条款对无工具的 API 会造成矛盾）。
- **自省调试**：`run_turn` 写入 `runtime_inspect_set_correlation`（`trace_id`、`user_msg_uuid`）；`tool_background` 线程 overlay 同步写入同一 `correlation`。工具 `companion_runtime_inspect` 在 JSON 顶层输出 `correlation`（若可得），与 `runtime_events`（含 `llm_inference_failure`、`tool_background_failure` 等）一并便于对齐日志与 LangSmith；同步 completion 须经上文 **LLM 同步端口** 或调用前绑定 `companion_llm_runtime_event_bind_ctx`。队列记忆管线在 worker 内绑定；`defer_memory_update=False` 时在 `run_turn` 调用同步 `memory_update_after_turn` 前会临时重新绑定同一 correlation。
