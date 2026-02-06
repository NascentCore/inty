# Push Worker 内存泄漏分析与修复

<!-- CREATED_BY_AGENT -->

本文档记录生产环境中 `push_worker` 进程 RSS 持续增长问题的原因、分析流程与修复方案。

## 1. 现象

- **监控**：GCE 实例上 `python -m app.services.push_worker` 进程 RSS 在约 12 小时内从约 2 GiB 升至近 6 GiB，呈近似线性上升；同一实例上 uvicorn 主应用进程内存相对稳定。
- **时间**：约 2026 年 2 月初，与近期推送/记忆/报表等功能的发布时间接近。

## 2. 根因

**push_worker 从未启动 `cache_service.start_cleanup_task()`，导致内存缓存无限增长。**

- **主应用**（`app/main.py`）在 lifespan 中会调用 `cache_service.start_cleanup_task()`，每 2 分钟清理一次过期条目（user_cache、session_cache、agent_cache）。
- **push_worker** 是独立入口（`app/services/push_worker.py`），不经过 main 的 lifespan，因此从未启动上述清理任务。
- 推送流程会调用：
  - `agent_manager.get_agent()` → Agent 内 `_get_user_profile_sync()` → `cache_service.set_user_info(user_id, ...)`（每个被生成推送的用户写入一条）；
  - `agent_service.get_agent_for_chat()` → `cache_service.set_agent_config(agent_id, ...)`（每个用到的 Agent 写入一条，含完整 prompt 等）。
- 过期条目仅在下次 `get()` 时顺带删除；若 key 不再被访问，则一直常驻内存。随推送量增加，`user_cache` / `agent_cache`（及可能的 `session_cache`）的 `total_entries` 单调上升，导致 RSS 持续增长。

## 3. 分析流程

### 3.1 假设与埋点

围绕“内存为何持续增长”建立多条可验证假设，并在调度与推送路径中写入 NDJSON 调试日志（hypothesisId A–E），用于区分不同原因：

| 假设 | 含义 | 埋点位置 |
|------|------|----------|
| A | cache 条目数随时间只增不减（无定期清理） | 各 job 入口写 `cache_service.get_cache_stats()` |
| B | AgentManager 中 Agent 实例数或占用持续上升 | 各 job 入口写 `agent_manager.get_agent_count()` |
| C | 近期任务（记忆抽取、节日记忆、用户报表）单次加载数据过大 | 记忆/节日任务中写 `len(user_ids)`、`len(due_configs)` 等 |
| D | asyncio 任务数或调度相关引用持续增长 | 各 job 入口写 `len(asyncio.all_tasks(loop))` |
| E | 推送批次列表等大对象被长期引用 | `process_push_batch` 中写 `user_count`、`stage`、`batch_size` |

埋点写入 `.cursor/debug.log`（NDJSON，每行一条），便于按时间与 hypothesisId 分析。

### 3.2 验证结论

- **A**：修复前无埋点运行时，从代码可确认 push_worker 未调用 `start_cleanup_task()`；修复后埋点显示 `cleanup_running: true`，且 `user_cache` / `session_cache` / `agent_cache` 的 `total_entries` 在验证运行中保持为 0（有清理且无泄漏式增长）。
- **B**：AgentManager 有 `max_agents` 与定期 `_cleanup_idle_agents()`，埋点显示 `agent_count` 稳定（如 10），非主因。
- **C/D/E**：作为辅助观察，未发现明显异常；主因归结为 A。

## 4. 修复方案

### 4.1 内存泄漏修复

- 在 **push_worker** 的 `run()` 中，在 `start()` 成功且未 return 之后，增加：
  - `await cache_service.start_cleanup_task()`
- 在 **push_worker** 的 `_stop_async()` 与同步 `stop()` 中，在停调度器之前增加：
  - `cache_service.stop_cleanup_task()`

这样 push_worker 与主应用一致，每 2 分钟执行一次过期缓存清理，cache 条目数有上界，RSS 不再因缓存无限增长而单调上升。

### 4.2 相关改动（Ctrl+C 退出卡住）

在排查过程中顺带修复了 Ctrl+C 后进程无法退出的问题：

- **原因 1**：`push_scheduler_service.stop()` 使用 `scheduler.shutdown(wait=True)`，在主线程（同事件循环）中阻塞等待 job 结束，而 job 依赖事件循环推进，形成死锁。
- **修复**：改为 `shutdown(wait=False)`，不再在 stop 中等待 job。
- **原因 2**：`asyncio.run(main())` 在 main 返回后会 `_cancel_all_tasks` 并 `gather` 等待所有被取消任务；若 job 卡在 `asyncio.to_thread()` 或 async I/O（如 `db.execute`），取消要等 I/O 返回才生效，进程一直不退出。
- **修复**：改为自建事件循环、`run_until_complete(main())`，在 `main()` 返回后仅 `loop.close()`，不再执行 `shutdown_asyncgens()` 的 `run_until_complete`，避免再次驱动循环去执行卡住的已取消任务。

## 5. 验证建议

- **本地/验证环境**：运行 push_worker 至少 20 分钟，观察 debug 日志中 hypothesisId "A" 的 `cache_stats`，确认 `cleanup_running: true` 且 `total_entries` 不单调上升。
- **生产**：部署后通过 GCP Monitoring 观察 push_worker 进程 RSS 1–2 天，确认曲线不再长期单调上升。

## 6. 涉及文件

- `app/services/push_worker.py`：增加 cache 清理任务的启动与停止；调整退出流程（自建 loop、`_stop_async` 取消任务并限时等待、finally 仅 `loop.close()`）。
- `app/services/push_scheduler_service.py`：`stop()` 中 `shutdown(wait=False)`。
- `app/services/cache_service.py`：被 push_worker 调用 `start_cleanup_task` / `stop_cleanup_task`；后续增加 `InMemoryCache.max_entries` 兜底（见第 7 节）。

## 7. 后续：生产仍涨与兜底上限

- **现象**：修复部署后，部分环境反馈 push_worker RSS 仍随运行时间缓慢上升（例如 5.5 小时内 0.4 GiB → 近 2 GiB）。
- **本地复现**：在无推送流量（0 用户需推送）的本地运行中，埋点显示 cache `total_entries` 始终为 0、`cleanup_running: true`、`agent_count` 稳定、`task_count` 波动正常，**未能复现增长**；说明在生产有真实推送流量时，cache 或其它结构才可能被大量写入。
- **兜底**：在 `InMemoryCache` 中增加可选参数 `max_entries`；`CacheService` 为 user_cache / session_cache / agent_cache 分别设置上限（50_000 / 10_000 / 2_000）。在 `set()` 时若已达上限且 key 不在缓存中，先清理过期条目，再按 `created_at` 淘汰最旧条目，保证条目数不超过上限，即使清理任务偶发延迟或写入速率很高也能限制内存。
- **建议**：生产保留或临时加入 cache_stats / agent_count 等埋点，在 RSS 上升时抓取日志对比 `total_entries` 与 `agent_count`，便于区分是 cache 逼近上限还是其它对象（如 Agent 实例、调度器）导致；若仍涨可考虑进一步限制 Agent 数量或单 Agent 体积。
