# 可扩展性问题修复 TODO

## P0 - 事件循环阻塞（最致命）

- [ ] **修复 chat_history_service 同步 DB 调用阻塞事件循环**
  - 文件：`app/services/chat_history_service.py`
  - 问题：51 处同步函数在 async 路径中被直接调用，阻塞事件循环
  - 方案：使用 `asyncio.to_thread()` 或 `run_in_executor()` 包装所有同步函数
  - 关键函数：
    - `get_chat_history_connection()` (line 60)
    - `get_messages_paginated()` (line 718)
    - `get_last_message_with_timestamp()` (line 155)
    - `has_user_messages_ever()` (line 208)
    - `add_user_message()` (line 243)
    - `add_ai_message_sync()` (line 254)
    - `get_history_messages()` (line 949)
    - `clear_session()` (line 1011)

- [ ] **修复 GCS 同步 SDK 调用阻塞事件循环**
  - 文件：`app/external_services/gcs.py`
  - 问题：`upload_to_gcs()`、`download_from_gcs()`、`check_gcs_file_exists()` 是同步网络 I/O
  - 方案：使用 `asyncio.to_thread()` 包装或迁移到异步 GCS SDK
  - 关键函数：
    - `upload_to_gcs()` (line 39)
    - `download_from_gcs()` (line 199)
    - `check_gcs_file_exists()` (line 188)

- [ ] **修复语音服务同步操作**
  - 文件：`app/services/voice_service.py`
  - 问题：`GCSService.upload_voice_file()` 名义 async 但内部调用同步函数
  - 方案：将同步 GCS 调用移到线程池执行

- [ ] **修复其他同步网络/CPU 密集操作**
  - 问题：`requests.get()`、`subprocess.run(ffmpeg)`、PIL/cv2 图像处理在请求链路中
  - 方案：所有 CPU 密集或同步 I/O 操作移到后台任务或线程池

## P1 - 数据库查询优化

- [ ] **修复 chat 列表 N+1 查询问题**
  - 文件：`app/services/chat_service.py`
  - 问题：`get_chats()` 循环调用 `get_last_message_with_timestamp()` 和 `has_user_messages_ever()` (line 87-91)
  - 方案：使用批量查询或 JOIN 优化，或使用 Redis 缓存最近消息

- [ ] **优化分页查询（OFFSET → cursor-based）**
  - 文件：`app/services/chat_history_service.py`
  - 问题：`get_messages_paginated()` 使用 OFFSET，深分页性能差 (line 718)
  - 方案：改为基于 `created_at` 或 `id` 的游标分页

- [ ] **添加同步连接池**
  - 文件：`app/services/chat_history_service.py`
  - 问题：全局 `_connection` 是单连接，无池化 (line 60)
  - 方案：使用连接池替代单连接，或迁移到异步 SQLAlchemy

- [ ] **优化 JSON 序列化开销**
  - 文件：`app/services/chat_history_service.py`
  - 问题：`get_messages_paginated()` 中每条消息都要解析 JSON (line 718-926)
  - 方案：考虑使用 PostgreSQL JSONB 索引或缓存解析结果

## P2 - 线程池与并发控制

- [ ] **重构 Agent 线程池设计**
  - 文件：`app/core/agent/agent.py`
  - 问题：每个 Agent 实例创建独立 `ThreadPoolExecutor`，最多 1600 线程 (line 239-246)
  - 方案：使用全局共享线程池，或使用 `asyncio.Semaphore` 控制并发数

- [ ] **添加外部 API 速率限制**
  - 文件：`app/core/agent/agent.py`
  - 问题：OpenAI 调用使用同步 client + `time.sleep()`，缺少全局并发控制 (line 611-758)
  - 方案：添加全局速率限制器，使用异步重试机制替代 `time.sleep()`

- [ ] **优化锁竞争**
  - 文件：`app/core/agent/agent.py`
  - 问题：AgentManager/Agent 级别锁在热门 agent 时形成热点竞争
  - 方案：减少锁粒度，使用读写锁或无锁数据结构

- [ ] **优化缓存锁竞争**
  - 文件：`app/services/cache_service.py`
  - 问题：`InMemoryCache` 使用 `RLock`，高并发下串行化
  - 方案：使用更细粒度的锁或考虑迁移到 Redis

## P3 - 基础设施优化

- [ ] **启用多 worker 模式**
  - 文件：`start.sh`
  - 问题：单 worker 启动，无法利用多核 (line 40-49)
  - 方案：使用 `uvicorn --workers N` 或 `gunicorn + uvicorn workers`

- [ ] **添加可观测性指标**
  - 问题：缺少连接池、线程池、事件循环延迟监控
  - 方案：添加以下指标：
    - 事件循环延迟（event loop lag）
    - 数据库连接池使用率
    - 线程池队列长度
    - 请求 P50/P95/P99 延迟

- [ ] **优化缓存实现**
  - 文件：`app/services/cache_service.py`
  - 问题：无容量上限/无淘汰策略，内存可能无限增长
  - 方案：添加 LRU 淘汰策略或容量限制

- [ ] **减少 debug 日志开销**
  - 文件：`app/services/cache_service.py`
  - 问题：高 QPS 下大量 `logger.debug()` 调用产生 I/O 压力
  - 方案：使用采样日志或提升日志级别

- [ ] **解耦后台任务与 API**
  - 文件：`app/main.py`
  - 问题：后台任务与 API 共用同一事件循环，资源竞争
  - 方案：将重任务移到独立进程或使用任务队列（Celery/RQ/Arq）
