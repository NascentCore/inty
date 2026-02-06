# Push Worker 内存问题分析与修复

<!-- CREATED_BY_AGENT -->

本文档记录生产环境中 `push_worker` 进程 RSS 持续增长问题的**排查过程、尝试的方法、观察到的现象**，以及**内存问题原因的详细说明**与修复方案。

---

## 1. 现象

- **监控**：GCE 实例上 `python -m app.services.push_worker` 进程 RSS 在约 12 小时内从约 2 GiB 升至近 6 GiB，呈近似线性上升；同一实例上 uvicorn 主应用进程内存相对稳定。
- **时间**：约 2026 年 2 月初。
- **其他**：进程曾出现“莫名退出”；标准输出中可见 `Killed`（通常为 OOM killer）；多次重启后内存曲线呈多条“阶梯式上升后终止”的线段。

---

## 2. 排查过程（时间线）

1. **第一阶段**：假设内存持续增长由“缓存未清理”导致。经代码审查确认 push_worker 未调用 `cache_service.start_cleanup_task()`，主应用则会在 lifespan 中调用。在 push_worker 中增加清理任务的启动与停止后，cache 的 total_entries 在运行中保持为 0，**该根因已修复**。
2. **第二阶段**：修复 cache 后，在**未执行记忆抽取**时机器内存仍缓慢上升；进程曾因内存问题宕机。说明除 cache 外仍有其他因素，遂继续定位。
3. **第三阶段**：在调度与记忆抽取路径增加 NDJSON 埋点（job 入口/出口、LOCATE 等），观察到记忆抽取的「获取待处理用户」步骤中，`get_users_to_extract_before_to_thread`、`memory_extraction_sync_entered` 出现，但**从未**出现 `get_users_to_extract_after_to_thread` 及本周期内的 memory_extraction job_exit，**卡点定位到** `asyncio.to_thread(_compute_users_to_extract_sync, ...)` 内部。
4. **第四阶段**：使用**独立脚本**仅执行 to_thread 内逻辑（不启动 push_worker），并周期性采样 RSS。约 25 分钟内 RSS 从 284 MB 单调上升至 496 MB（约 +8.5 MB/分钟），**确认 to_thread 内逻辑单独即可导致内存持续增加**。
5. **收尾**：移除排查时加入的 debug 埋点，保留独立测试脚本与本文档。

---

## 3. 尝试的方法

| 方法 | 说明 |
|------|------|
| 假设 A–E | 针对 cache 条目数、Agent 数、任务数、推送批次等建立可验证假设，通过埋点写 cache_stats、agent_count、task_count 等，排除 cache 外其他候选。 |
| job_entry / job_exit | 在各定时任务入口与 finally 出口写快照（含 pool、agent_locks 等细指标），用于对比单次执行前后及多任务时间线。 |
| LOCATE 埋点 | 在记忆抽取 `get_users_to_extract` 中：DB 查完后写 before_to_thread；to_thread 内同步函数入口写 sync_entered；to_thread 返回后写 after_to_thread。用于精确定位卡点是否在 to_thread 内。 |
| tracemalloc | 可选开启，在 cache 清理循环中周期性写 current_mb、peak_mb、top_allocations，辅助观察分配来源（排查阶段使用，已移除）。 |
| 独立脚本 | `scripts/run_memory_extraction_to_thread_standalone.py`：仅加载与 get_users_to_extract 相同的输入并调用 `_compute_users_to_extract_sync`，主线程每 N 秒采样 RSS 写入 NDJSON，用于验证 to_thread 内逻辑是否单独导致内存上升。 |

上述埋点曾写入 `.cursor/debug.log`（NDJSON）；排查结束后**已从代码中移除**，仅保留独立脚本。

---

## 4. 观察到的现象

- **Cache**：修复清理任务后，运行中 cache 的 total_entries 均为 0，cleanup 正常；**可排除 cache 导致泄漏**。
- **记忆抽取 to_thread**：在多次运行中，debug 日志有 before_to_thread、sync_entered，**从未**出现 after_to_thread 或本周期 memory_extraction job_exit；进程被 Kill 或“莫名退出”时，to_thread 仍未返回。
- **数据规模**（典型）：users_with_chats ≈ 1 万，total_chats/sids_list_len ≈ 20 万，distinct_lasts_count ≈ 4558，**约 18.7 万次** SQL（对每个 last、每个 sids chunk 各一次查询）。
- **进程退出**：标准输出出现 `Killed`（SIGKILL），与 OOM killer 行为一致；时间线上记忆抽取与推送/节日任务同时触发，随后 2h/30min 推送结束，进程被 Kill。
- **独立脚本**：仅运行 to_thread 逻辑时，RSS 在 sync 运行期间**随 elapsed_sec 单调上升**（例如 284 → 496 MB / 25 分钟），增速约 8.5 MB/分钟；**无** push_worker 其他任务时结论一致。

---

## 5. 内存问题原因详解

### 5.1 已修复：cache 未清理（第一阶段根因）

- **原因**：push_worker 未启动 `cache_service.start_cleanup_task()`，user_cache / agent_cache 等过期条目仅在被访问时顺带删除，未访问则常驻，随推送量增加 total_entries 单调上升。
- **修复**：在 push_worker 的 `run()` 中调用 `cache_service.start_cleanup_task()`，在 `_stop_async()` 与 `stop()` 中调用 `cache_service.stop_cleanup_task()`。

### 5.2 已解决：记忆抽取「获取待处理用户」长时间占用且持续分配

- **责任任务**：**记忆抽取 (memory_extraction)** 中的 **获取待处理用户** 步骤。  
- **代码路径**：`push_scheduler_service._run_memory_extraction()` → `memory_get_users_to_extract()` → `asyncio.to_thread(_compute_users_to_extract_sync, ...)`。  
- **文件与函数**：`app/services/memory_extraction_service.py` 中的 `_compute_users_to_extract_sync`（在 to_thread 内执行）。  
- **现状**：已通过「筛选用 subscription_usage、单用户处理仍用 chat_history」方案修复，见 6.1。

**为何曾导致内存持续增加：**

1. **单次运行时间极长**：当前实现对每个 `last`（约 4558 个）、每个 sids chunk（约 41 个）各执行一次针对 `chat_history` 的 SQL，共约 **18.7 万次** 查询，在单一线程内顺序执行，耗时可长达数小时。
2. **运行过程中持续分配**：工作线程内构建并持有 `session_to_total`（约 20 万 key）、`last_to_session_incr`（每个 last 对应若干 session 的计数），以及大量查询结果；主进程在 `get_users_to_extract()` 返回前一直持有传入的 `user_to_chats`、`user_to_last`。随着循环推进，这些结构不断增长，RSS 随执行时间**单调上升**。
3. **不返回则一直不释放**：to_thread 在观测/进程存活期内**从未返回**（或返回极晚），因此该次分配的生命周期覆盖整段运行直至进程被 Kill；**不是**“每 5/10 分钟又多占一块不释放”，而是**同一次任务**内随执行时间持续分配。

**与「严格意义的内存泄漏」的区分**：  
若 to_thread **最终返回**，上述大对象理论上会被回收。当前现象是 to_thread 在进程被 Kill 前未返回，导致“等效”长期占用；**没有证据**表明存在“无限增长、永不释放”的经典泄漏。其他任务（10min/30min/2h 推送、节日记忆）均有 job_exit，无证据表明它们在结束后仍长期持有内存。

### 5.3 进程被 Kill 与多实例曲线

- 当 RSS 升至系统可承受上限时，Linux OOM killer 会向进程发 SIGKILL（表现为 `Killed`）。  
- 若 push_worker 由脚本或进程管理器在退出后再次拉起，则新进程新 PID，监控上呈现多条“上升后终止”的线段，每条对应一次运行。

---

## 6. 修复与优化

### 6.1 已做

- **cache 清理**：push_worker 启动/停止时与主应用一致地启停 cache 清理任务。  
- **Ctrl+C 退出**：`push_scheduler_service.stop()` 改为 `shutdown(wait=False)`；push_worker 改为自建事件循环、在 main 返回后仅 `loop.close()`，避免卡在 to_thread 或 I/O 时无法退出。
- **优化 `_compute_users_to_extract_sync`（最终方案）**：  
  **筛选阶段**改为基于 `subscription_usage` 表，不再查询 `chat_history`。  
  - 新用户：对「在 chats 有会话且未在 memory_extraction_log 出现过」的用户，用一条（或按 `_MAX_IN_PARAMS` 分块）聚合 SQL：`SELECT user_id, SUM(usage_count) FROM subscription_usage WHERE usage_type = 'chat' AND user_id = ANY(...) GROUP BY user_id`，总聊天次数 ≥ `trigger_new_user_messages` 的进入待抽取列表。  
  - 老用户：对「已有抽取记录」的用户，用一条（或分块）批量 SQL：`subscription_usage` JOIN `(VALUES (user_id, last_at), ...)`，条件 `usage_date > last_at`，按 user 聚合 `SUM(usage_count)`，增量 ≥ `trigger_incremental_messages` 的进入待抽取列表。  
  - 查询量从原先约 18.7 万次 chat_history 查询降为少量（通常 2～4 条）subscription_usage 聚合查询，不再构建 `session_to_total`、逐用户 session 块 COUNT 等大结构，耗时与峰值内存显著下降。  
  **单用户处理阶段**不变：仍由 `get_all_messages_for_user` 从 `chat_history` 拉取消息，`extract_and_save` 做 LLM 抽取与写入 memory / memory_extraction_log。  
  **配置**：`MemoryExtractionConfig` 的 `trigger_new_user_messages`、`trigger_incremental_messages` 语义改为「按 subscription_usage 统计的聊天次数」；见 `app/core/config.py` 注释与 `get_users_to_extract` 的 docstring。  
  **索引（可选）**：为加速筛选查询，可为 `subscription_usage` 增加复合索引 `(user_id, usage_type, usage_date)`，通过单独 alembic version 应用（见 `alembic/versions/20260206_120000_subscription_usage_index_for_memory_extraction.py`）；不执行迁移仅影响查询性能，不影响正确性。

### 6.2 待做（建议）

- **限流或超时**：对记忆抽取任务做并发控制（如同一时间只允许一轮），或对 to_thread 设置超时，避免长时间占用叠加 OOM。

---

## 7. 保留的脚本：单独验证 to_thread 内存

**脚本**：`scripts/run_memory_extraction_to_thread_standalone.py`

**作用**：仅加载与 `get_users_to_extract` 相同的输入（user_to_chats、user_to_last），然后**仅**调用 `_compute_users_to_extract_sync(...)`（在子线程执行），主线程按 `--interval` 秒周期采样 RSS 并写入 NDJSON 日志，用于验证 to_thread 内逻辑是否单独导致内存持续增加。

**用法**（仓库根，建议使用项目 venv）：

```bash
export PYTHONPATH=.
.venv/bin/python scripts/run_memory_extraction_to_thread_standalone.py
.venv/bin/python scripts/run_memory_extraction_to_thread_standalone.py --interval 5 --log-file .cursor/standalone_to_thread.log
.venv/bin/python scripts/run_memory_extraction_to_thread_standalone.py --dry-run   # 仅加载输入后退出，不执行 sync
```

**日志**（默认 `.cursor/standalone_to_thread.log`）：  
`standalone_start`、`after_load_inputs`、`sync_running_sample`（每 interval 秒）、`standalone_finished`（sync 返回后）。  

**解读**：若仅运行该脚本时，`sync_running_sample` 的 rss_mb 随 elapsed_sec **单调上升**，且 `standalone_finished` 的 rss_mb 显著高于 `after_load_inputs`，则可认定 to_thread 内逻辑**单独**即可导致内存持续增加。一次实际运行中，约 25 分钟内 RSS 从 284 MB 升至 496 MB（约 +8.5 MB/分钟），已据此确认原因。

---

## 8. 涉及文件

- `app/services/push_worker.py`：cache 清理任务启停；退出流程（自建 loop、`shutdown(wait=False)` 等）。  
- `app/services/push_scheduler_service.py`：`stop()` 中 `shutdown(wait=False)`。  
- `app/services/cache_service.py`：逻辑未改，被 push_worker 调用 `start_cleanup_task` / `stop_cleanup_task`。  
- `app/services/memory_extraction_service.py`：包含 `_compute_users_to_extract_sync`（已改为用 subscription_usage 筛选）、`get_all_messages_for_user`（仍从 chat_history 读消息）。  
- `scripts/run_memory_extraction_to_thread_standalone.py`：独立测试 to_thread 内存的脚本（保留）。
