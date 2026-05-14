# Companion Memory Store

## 一句话

MemoryStore 是 Companion Harness 的「工作区状态层」：人设、对话与控制面文档；持久化到 Postgres `companion_memory_document_versions`；MemoryStore 不复用 legacy `memory` 表。

- 不在范围：分层 Markdown 记忆（episodic / gist / semantic）的策展机制 —— 见 [`MEMORY_PIPELINE.md`](/docs/companion_harness/MEMORY_PIPELINE.md)。
- 不在范围：跨 transport / turn / tool 的整体职责切分 —— 见 [`ARCH.md`](/docs/companion_harness/ARCH.md)。
- 不在范围：legacy 主站 `memory` 表与节日 / 日常抽取管线（避免混淆）。

---

## 当前 MemoryStore：四类状态

MemoryStore 把一次 companion 会话的状态切成四个角色。逻辑接口都是 POSIX 格式相对路径（对模型友好），权威存储在 Postgres `companion_memory_document_versions`，每条文档由 `document_kind` 标签分类。

### 1. 人设根稿（IDENTITY / SOUL / USER / MEMORY）

- companion 的身份、稳定边界、对用户的长期理解，以及跨日的语义记忆。
- 由记忆管线与少量工具策展更新；通常只读注入到 system prompt。
- 分层与触发机制详见 [`MEMORY_PIPELINE.md`](/docs/companion_harness/MEMORY_PIPELINE.md)，本文不重复。

### 2. 对话轨迹（transcript / inner_tick / ai_private）

- **`transcript.jsonl`**：用户可见对话主轨；每轮末追加 user / assistant，作为下一轮上下文与压实输入；体积大时带截窗读取。
- **`transcript_inner_tick.jsonl`**：仅承载**维护型**内在节拍；与主 transcript 按时间合并后供 inner_tick scene；proactive heartbeat 仍写主轨。
- **`ai_private.md`**：内在节拍等非用户主对话轮的正文，注入 `## 内在活动（ai_private）` system 块；`ai_private.jsonl` 同属 MemoryStore，读路径以代码为准。

> 设计要点：用户可见 vs 维护型轨迹**物理分文件**，否则上下文压实与 LangSmith trace 都会混入半相关的对白。

### 3. 控制面状态（context.json + `.companion_*` / `.inty_v2_*` JSON）

- **`context.json`**：会话元数据 —— experience profile、bootstrap 标志、跳过开关、session id。**禁止**用通用文档写工具直接覆盖；改用字段级 setter 工具（如 experience profile 工具）确保语义。
- **`.companion_*` / `.inty_v2_*` 状态文件**：管线节拍计数、压实状态、定时队列等快照；由各子系统覆盖式写入，间接影响管线触发与上下文规模。
- 这一层不属于人设 system 切片；它决定**这一轮怎么走**，不决定**这一轮说什么**。

### 4. 生图索引（`generated_images/`）

- 索引行（`index.jsonl`）随 MemoryStore 一致管理；二进制产物可走对象存储，索引行可记 `gcs_http_url` 等。
- `generate_image` / `modify_image` 成功后追加索引；后续改图工具按最新记录解析默认源。

## References

[Future ideas](/docs/companion_harness/todos/MEMORY_STORE.md)
