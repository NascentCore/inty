# Companion Memory Store

## 一句话

MemoryStore 是 Companion Harness 的「工作区状态层」：人设、对话与控制面文档；持久化到 Postgres `companion_memory_document_versions`；MemoryStore 不复用 legacy `memory` 表。

- **进程内注册表**：`memory_registry.get_memory_store(scope, dsn=...)` 始终挂上 `SqlAlchemyMemoryRepository`，**必须**传入非空 `dsn`（与 `CompanionConfig.memory_pg_dsn`、仓库根 `config.yaml` 的 `database.url` 同源）；不存在「注册表里仅内存、不写库」的路径。纯逻辑测试应直接构造 `MemoryStore(scope, repository=None)` 并绕过注册表；需要走注册表 + ORM 的测试与 `experimental/harness_seeding_demo` 的播种脚本假定 **`database.url` 已配置且库可达**（与 `tests/app/core/companion_harness/companion_memory_registry_dsn.py` 的约定一致）。
- 不在范围：分层 Markdown 记忆（episodic / gist / semantic）的策展机制 —— 见 [`dreaming_consolidation`](/app/core/companion_harness/memory/dreaming_consolidation.py)。
- 不在范围：跨 transport / turn / tool 的整体职责切分 —— 见 [`DESIGN.md`](/docs/companion_harness/DESIGN.md)。
- 不在范围：legacy 主站 `memory` 表与节日 / 日常抽取管线（避免混淆）。

---

## 当前 MemoryStore：四类状态

MemoryStore 把一次 companion 会话的状态切成四个角色。逻辑接口都是 POSIX 格式相对路径（对模型友好），权威存储在 Postgres `companion_memory_document_versions`，每条文档由 `document_kind` 标签分类。

### 1. 人设根稿（IDENTITY / SOUL / USER / MEMORY / LIFE_CURRENTS）

- companion 的身份、稳定边界、对用户的长期理解，以及跨日的语义记忆。
- **`LIFE_CURRENTS.md`**（AUTONOMY）：Inty 在 **虚拟空间/环境**中的自主活动状态（中期主题、当日兴致、进展）——**她在世界里做什么**，不是对用户的心理独白。与 `ai_private.jsonl` 分工见 [`AUTONOMY.md`](./AUTONOMY.md#ai_privatejsonl-vs-life_currentsmd核心区分)。
- 由记忆管线与少量工具策展更新；通常只读注入到 system prompt（`LIFE_CURRENTS` 另由 AUTONOMY 写、PROACTIVE_CHAT 只读 hint）。
- **DREAMING（sleeping）** 做 **当日汇总**：用户可见 `transcript.jsonl`（chat / proactive / scheduled）与沉默 awake 轨（autonomy / maintenance 的 inner-tick transcript、`LIFE_CURRENTS.md`、`ai_private.jsonl` 等）一并策展进 gist 与 semantic MemoryDoc。实现与 `TODO(dreaming-day-rollup)` 见 [`dreaming_consolidation`](/app/core/companion_harness/memory/dreaming_consolidation.py)、[`AUTONOMY.md`](./AUTONOMY.md)。

### 2. 对话轨迹（transcript / inner_tick / ai_private）

- **`transcript.jsonl`**：用户可见对话主轨；每轮末追加 user / assistant，作为下一轮上下文与压实输入；体积大时带截窗读取。Proactive chat 也写本轨；**proactive rhythm** 以本轨**最后一条 assistant 的 `ts`** 为锚（见 [DESIGN.md](./DESIGN.md) 与 `proactive_chat.py`）。
- **`transcript_inner_tick.jsonl`**：沉默 inner-tick turn（`MAINTENANCE`、`AUTONOMY`）；与主 transcript 按时间合并后供 inner_tick scene；proactive / scheduled 仍写主轨。
- **`ai_private.md` / `ai_private.jsonl`**：**对用户的心理独白**（情绪、未说出口的念头、关系场景里的内在节拍），供 MAINTENANCE inner-tick 注入 `内在活动（ai_private）` system 块。不是虚拟环境里的「动手做事」——后者见 `LIFE_CURRENTS.md`（AUTONOMY）。
  - **读**：由 `get_ai_private_jsonl_text_for_prompt` / `get_ai_private_text_for_prompt` 等从 MemoryStore 读取（实现见 `app/core/companion_harness/companion/ai_private_prompt.py`）。
  - **写（当前事实）**：`ai_private.jsonl` 已映射到 ORM（`memory_store_document_mapping.py`），但伴侣工具链里 **`memory_store_write_document` 受 `MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST` 约束**（仅 allowlist 内 `.md`），**不含** `ai_private.jsonl`，故 **模型经工具默认不可写**该文件；运维/测试或代码内直接 `MemoryStore.write_document` / `append_jsonl_record` 仍可写入。TODO(`ai-private-jsonl-write`)：为 MAINTENANCE 接通 append（专用 append 工具优先，或 allowlist + runtime 仅 append）。

### LivingSphere 小家（`LIVING_SPHERE.md` + `living_sphere_updates.jsonl`）

- **`LIVING_SPHERE.md`**：可读快照，注入 system prompt；由 `living_sphere` curator 在 memory pipeline 写回，**不在** `MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST` 内。
- **`living_sphere_updates.jsonl`**：用户明确指令的快路径 append 日志（工具 `living_sphere_record_update`）；同样有 ORM 映射，**不在** allowlist，**不可**经 `memory_store_write_document` 整文件覆盖。
- 详见 [`LIVING_SPHERE.md`](./LIVING_SPHERE.md)。

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
