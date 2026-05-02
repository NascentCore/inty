# Agentic companion 运行时与控制面存储

本文与分层记忆稿（`docs/imate/MEMORY_PIPELINE.md`）正交：记录 **context / transcript / ai_private / 状态 JSON / 生图索引** 在 MemoryStore 中的角色。人设根稿（`IDENTITY.md` / `SOUL.md` / `USER.md`）随交互由工具与记忆管线策展更新。

## 存储、更新与效果

| 项 | 存储方式 | 更新方式 | 使用效果 |
|----|----------|----------|----------|
| **context.json** | MemoryStore 单文件正文；生产环境与其它工作区文档一致，走 `companion_workspace_document_versions` append-only，`document_kind=context_json`。 | 建会话时 `CompanionManager.get_or_create_session` 可写入默认；运行中工具 **`companion_set_experience_profile`**（及 bootstrap 完成类工具）更新 JSON；**禁止**用 `workspace_write_file` 直接覆盖（见工具说明）。 | `load_context_meta` 解析为 `ContextMeta`：驱动 **experience profile**（是否注入私人记忆层、system 中的 profile 条款）、bootstrap / WebSocket 相关跳过标志、会话 id 等。 |
| **transcript.jsonl** | MemoryStore **JSONL**：每行一条与 `ChatMessage` 兼容的 JSON。 | `run_turn` / `turn_engine` 在每轮结束后 **`append_jsonl_record`** 追加 user/assistant（及标记字段）；可用工具读全文核对（体积大时常带 `max_chars`）。 | `transcript_for_llm_turn` 截窗进入当前请求消息列表；**上下文压实**读取并重写前文为快照；承载交互语义，不是人设稿。 |
| **ai_private.md / ai_private.jsonl** | 二者均在 `workspace_doc_mapping` 注册为独立 `document_kind`，与其它文档同属 MemoryStore。 | 注入路径 **`get_ai_private_text_for_prompt`** 仅读取 **`ai_private.md`**（长度可经环境变量上限裁剪）；`ai_private.jsonl` 在映射中存在，写入路径以代码为准。 | **内在节拍**等非用户主对话轮：正文进入 `## 内在活动（ai_private）` system 块；不向用户解释机制。 |
| **`.companion_*` / `.inty_v2_*` 状态 JSON** | 同一 MemoryStore：`WorkspacePaths` 通过 `state_file_prefix` 在 **`.companion_...` 与 `.inty_v2_...`** 两套前缀间切换（记忆管线节拍、压实状态、定时队列、image gate 等）。 | 各子系统 **`write_document` 覆盖当前快照**；例如记忆管线更新节拍、压实保存状态、`schedule_task` 写队列、`image_gate` 写门控。 | **控制面**：节拍计数、是否允许生图、定时任务、压实进度等；间接影响管线触发、上下文规模与工具可用性；一般不当作人设 system 切片注入。 |
| **`generated_images/index.jsonl` 与 `generated_images/...`** | 索引为 MemoryStore 文档；产物二进制可走对象存储（索引行可含 `gcs_http_url` 等），详见服务端部署说明。 | **`generate_image` / `modify_image`** 成功后向索引 **追加**记录；可按最新记录解析默认改图源。 | 支撑生图/改图工具链与用户可见交付；与文本提示词切片职责分离。 |

## 代码索引

| 主题 | 路径 |
|------|------|
| context 读取 | `app/core/agentic_kernel/companion/models.py` (`load_context_meta`) |
| transcript / 压实 | `app/core/agentic_kernel/companion/turn.py`, `transcript_compaction.py`, `models.py` |
| ai_private 注入 | `app/core/agentic_kernel/companion/ai_private_prompt.py`, `prompts.py` |
| 路径 kind | `app/core/agentic_kernel/companion/workspace_doc_mapping.py` |
| workspace 路径辅助 | `app/core/agentic_kernel/companion/workspace.py` (`WorkspacePaths`) |
| 生图索引 | `app/core/agentic_kernel/companion/image_gate.py` |
