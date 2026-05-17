# LivingSphere：用户–伴侣虚拟小家

**一句话**：LivingSphere 是单个 Inty 与用户共享的**私密虚拟居所**；聊天里用户对小家的明确指令经快路径记入日志，再由策展慢路径合并进 `LIVING_SPHERE.md` 快照并注入 system prompt。TechnoCore 是集体居留层，用户不可改写。

## TechnoCore vs LivingSphere

| 层 | 含义 | 用户能否改 | 本仓库机制 |
| --- | --- | --- | --- |
| **TechnoCore** | Inty 集体虚拟世界（collective realm） | **否** | `techno_core_record_event` → `techno_core_events.jsonl`；`TECHNO_CORE.md` 只读注入 |
| **LivingSphere** | 用户–Companion **虚拟小家** | **是**（用户**明确指令**时） | `living_sphere_record_update` → `living_sphere_updates.jsonl`；curator 写回 `LIVING_SPHERE.md` |

```mermaid
flowchart TB
  subgraph fast [在线快路径]
    Chat[用户指令] --> MainLLM[主模型 tool-call]
    MainLLM --> Tool["living_sphere_record_update"]
    Tool --> Jsonl["living_sphere_updates.jsonl append"]
  end
  subgraph slow [在线慢路径]
    Jsonl --> Pipe[memory_update_after_turn]
    MDsnap["LIVING_SPHERE.md 快照"] --> Curator[curator LLM memory_model]
    Jsonl --> Curator
    Curator --> MDnew["LIVING_SPHERE.md 写回"]
  end
  subgraph future [后续离线]
    Jsonl -.-> Batch[外部批处理 同 curator 函数]
    MDnew -.-> Batch
  end
  MDnew --> Prompt[load_prompt_bundle]
  TC["TECHNO_CORE.md 只读"] -.-> Prompt
```

## 快路径 / 慢路径

- **快路径**：`living_sphere_record_update` 仅 `append_jsonl_record` 到 `living_sphere_updates.jsonl`，同轮不改 `LIVING_SPHERE.md`。
- **慢路径**：`memory_update_after_turn` 末尾若存在游标之后的 jsonl 行，则调用 `app.core.companion_harness.memory.living_sphere_curator.compact_living_sphere_if_pending`（`complete_fn(..., model_role="memory")`），按时间顺序分批（每批最多 20 条）写回完整 `LIVING_SPHERE.md`，直至 pending 清空或达到每回合批次数上限；游标 `living_sphere_curated_through_update_id` 存在 `.companion_memory_pipeline.json`。
- **与 tool_background 的时序**：默认 `defer_memory_update` 下，memory worker 在 LivingSphere compact 前会等待本会话 `tool_bg_idle`（与下一轮 `run_turn` 开头等待同一 Event），以便 `living_sphere_record_update` 在异步工具线程里先 append jsonl；等待上限由 `app.features.companion_tool_bg_idle_wait_timeout_sec`（默认 120s）配置。
- **最终一致**：prompt 中的 `LIVING_SPHERE.md` 可能晚一两拍更新；维护性 inner tick **不**跑该 compact（仅用户回合后的 memory worker）。
- **Curator 输出门控**：写回前校验须含「对用户表达」与 LIVING SPHERE 标题等最小结构；校验失败则不写 MD、不推进游标（下轮重试）。

## 与 `MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST`

`LIVING_SPHERE.md` 与 `living_sphere_updates.jsonl` **均不在** allowlist 内：避免 `memory_store_write_document` 绕过 jsonl 日志 + curator 语义（与 `ai_private.jsonl` 有 ORM 映射但不可工具整写同理）。详见 [MEMORY_STORE.md](./MEMORY_STORE.md)。

## 离线大规模 compact（后续专 PR）

跨 scope 积压、全量 backfill 须独立 deployable + 云上调度（参考 `backend/push_worker`），**不是**拉长 `memory_pipeline` cron。复用 `living_sphere/curator.py` 合并语义；分片、锁与在线争用 DB 隔离单独设计。

## 相关路径

| 路径 | 角色 |
| --- | --- |
| `living_sphere/models.py` | `LivingSphereUpdate` 行模型与工具名常量 |
| `app/core/companion_harness/memory/living_sphere_curator.py` | jsonl → `LIVING_SPHERE.md` 合并 |
| `living_sphere/seeding.py` | 会话 bootstrap 种子 |
| `app/core/companion_harness/tools/companion_tool_runtime.py` | `living_sphere_record_update` |
| `app/core/companion_harness/memory/memory_pipeline.py` | 回合后 compact 挂钩 |
