# Memory Store for agentic companion

## 一句话

MemoryStore 是 Companion Harness 的「工作区状态层」：人设、对话与控制面文档；
持久化到 Postgres `companion_memory_document_versions`；
MemoryStore 不复用 legacy `memory` 表。

MemoryStore stores MemDoc.
MemDoc is human-redable with file-system-like semantic addressing.

## MemDoc 与 prompt slice

| 概念 | 职责 | 典型落点 |
|------|------|----------|
| **Memory doc** | **持久化**（Postgres `companion_memory_document_versions`）；人类可读，便于 REPL / SQL / LangSmith 检视；也是 LLM 经工具读写的正文 | `IDENTITY.md`、`COMPANIONSHIP.md`、`transcript.jsonl` 等 |
| **Prompt slice** | **运行时效果**：组装进当轮 `role: system` 的文本块；决定模型此刻「看见什么」 | `system_messages.py` / `prompt_stack` 注入的各块 |

约定：

- **Persistable prompt slice** 与 Memory doc **1:1**：`PromptSliceId` → `{STEM}.md`（见 `prompt_slices.slice_to_workspace_rel`）。注入前从 MemoryStore 读正文（`load_prompt_bundle`）。
- **Non-persistable slice** 无 Memory doc 对应体，或仅有包内种子、不以会话文档为真源：`BOOTSTRAP`、`TOOLS`、`SIGNIFICANCE_PERCEPTION`、`AXIOM` / `SAFETY` 等。
- **Slice 还可来自代码**：固定 doctrine、channel output-format、`user-time-context` 尾缀、inner-tick 合成句等——这些不是 Memory doc，但是 prompt slice。

## Memory projection

Prompt 是 versioned slice space（MemDoc + conversation turns，仅 TTL 不同）的 **budget-bounded、可 replay 重建** 的投影（非 function-determinism）；agent 通过 slice 内容/metadata 编辑与 offline slot-algebra morphs 塑形。

读侧管线：

```
MemoryStore → [RETRIEVAL/SELECTION] → [PROJECTION] → PromptPlan
```

- **Static backbone** — doctrine、capability、output contract；代码固定顺序，无 MemDoc metadata。
- **Dynamic MemDoc region** — persona / relationship / world / memory；按 score 投影排序。
- **Conversation region** — projected transcript（非字面 replay）；旧 turn 迁入 memory slice；ephemeral turn 用后丢弃。

Retrieval tiers：**resident**（恒为候选）/ **verbatim window**（近期原话，dreaming 周期锚定 [#3376](https://github.com/NascentCore/inty/issues/3376)）/ **associative**（按 relevance 按需取）。

Write ↔ read 闭环：dreaming consolidation 写入 MemDoc ↔ 本节 activation 读回 prompt；见 [DESIGN.md](./DESIGN.md) § 记忆模型。

Implementation spec：`memory/retrieval.py`、`prompting/projection/`、`prompt_builder.py`、`dreaming_consolidation.py`。Issues：#3521、#3523、#3522、#3453、#3713、#3714。Speculative 见 [BRAINSTORM.md](./BRAINSTORM.md) § Memory projection（待定）。

## 当前 MemDoc：四类状态

MemoryStore 把一次 companion 会话的状态切成四个角色。逻辑接口都是 POSIX 格式相对路径（对模型友好），权威存储在 Postgres `companion_memory_document_versions`，每条文档由 `document_kind` 标签分类。

### 1. 人设根稿（IDENTITY / SOUL / USER / STYLE / COMPANIONSHIP / MEMORY / LIFE_CURRENTS）

- companion 的身份、稳定边界、对用户的长期理解，以及跨日的语义记忆。
- **`LIFE_CURRENTS.md`**（AUTONOMY）：Inty 在 **虚拟空间/环境**中的自主活动状态（中期主题、当日兴致、进展）——**她在世界里做什么**，不是对用户的心理独白。与 `ai_private.jsonl` 分工见 [`AUTONOMY.md`](./AUTONOMY.md#ai_privatejsonl-vs-life_currentsmd核心区分)。
- 由记忆管线与少量工具策展更新；通常只读注入到 system prompt（`LIFE_CURRENTS` 另由 AUTONOMY 写、PROACTIVE_CHAT 只读 hint）。
- **DREAMING（sleeping）** 做 **当日汇总**：用户可见 `transcript.jsonl`（chat / proactive / scheduled）与沉默 awake 轨（autonomy / monolog 的 inner-tick transcript、`LIFE_CURRENTS.md`、`ai_private.jsonl` 等）一并策展进 gist 与 semantic MemoryDoc。实现与 `TODO(dreaming-day-rollup)`（[#3376](https://github.com/NascentCore/inty/issues/3376)）见 [`dreaming_consolidation`](/app/core/companion_harness/memory/dreaming_consolidation.py)、[`AUTONOMY.md`](./AUTONOMY.md)。

### 2. 对话轨迹（transcript / inner_tick / ai_private）

- **`transcript.jsonl`**：用户可见对话主轨；每轮末追加 user / assistant，作为下一轮上下文与压实输入；体积大时带截窗读取。Proactive chat 也写本轨；**proactive rhythm** 以本轨**最后一条 assistant 的 `ts`** 为锚（见 [DESIGN.md](./DESIGN.md) 与 `proactive_chat.py`）。**Manifest 行**（`source=ai_private_splice_manifest`）：仅索引本轮 tail-splice 的 `ai_private` thought UUIDs，**过滤**出 chat history / UI；后续轮 hydrate 为 assistant monolog 供 LLM 与 DREAMING。
- **`transcript_inner_tick.jsonl`**：沉默 inner-tick turn（`MONOLOG`、`AUTONOMY`）；与主 transcript 按时间合并后供 inner_tick scene；proactive / scheduled 仍写主轨。
- **`ai_private.md` / `ai_private.jsonl`**：**对用户的心理独白**（情绪、未说出口的念头、关系场景里的内在节拍），供 MONOLOG inner-tick 注入 `内在活动（ai_private）` system 块。不是虚拟环境里的「动手做事」——后者见 `LIFE_CURRENTS.md`（AUTONOMY）。
  - **结构化行**（`ai_private.jsonl`）：`{ uuid, ts, text, after_user_msg_uuid? }`；消费后 append-only **surfaced marker** `{ kind: surfaced, ref_uuid, ts }`。
  - **读**：MONOLOG 经 `get_ai_private_jsonl_text_for_prompt`；USER_CHAT / PROACTIVE_CHAT 经 `transcript_ai_private` tail-splice + manifest hydrate；DREAMING expand manifest + 未 surfaced 当日行。
  - **写**：MONOLOG 经伴侣工具 `ai_private_append`（append-only）；**不经** `memory_store_write_document` allowlist。

### LivingSphere 小家（`LIVING_SPHERE.md` + `living_sphere_updates.jsonl`）

- **`LIVING_SPHERE.md`**：可读快照，注入 system prompt；由 `living_sphere` curator 在 memory pipeline 写回，**不在** `MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST` 内。
- **`living_sphere_updates.jsonl`**：用户明确指令的快路径 append 日志（工具 `living_sphere_record_update`）；同样有 ORM 映射，**不在** allowlist，**不可**经 `memory_store_write_document` 整文件覆盖。
- 详见 [`LIVING_SPHERE.md`](./LIVING_SPHERE.md)。

> 设计要点：用户可见 vs 维护型轨迹**物理分文件**，否则上下文压实与 LangSmith trace 都会混入半相关的对白。

### 3. 控制面状态（context.json + `.companion_*` / `.inty_v2_*` JSON）

- **`context.json`**：会话元数据 —— experience profile、bootstrap 标志、跳过开关、session id。**禁止**用通用文档写工具直接覆盖；改用字段级 setter 工具（如 experience profile 工具）确保语义。
- **`.companion_*` / `.inty_v2_*` 状态文件**：管线节拍计数、压实状态、定时队列等快照；由各子系统覆盖式写入，间接影响管线触发与上下文规模。
- 这一层不属于人设 system 切片；它决定**这一轮怎么走**，不决定**这一轮说什么**。
