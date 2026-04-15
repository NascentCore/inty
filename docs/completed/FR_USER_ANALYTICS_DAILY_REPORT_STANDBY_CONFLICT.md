# 用户数据分析日报：Standby Conflict with Recovery

## 问题现象

- **报错**：`asyncpg.exceptions.SerializationError: canceling statement due to conflict with recovery`  
  DETAIL：`User query might have needed to see row versions that must be removed.`
- **发生位置**：`push_scheduler_service._run_user_analytics_daily_report` → `user_analytics_compute_daily` → `compute_and_save_daily_report`（读分支使用 `AsyncSessionLocalReplica`）。
- **触发 SQL**：`user_analytics_service._query_session_message_counts` 中对 `chat_history` 的批量聚合：`session_id IN ($1..$1000)` + 日期范围 + GROUP BY。

## 概念简述

- **Standby**：PostgreSQL 只读副本，持续从主库接收并重放 WAL，保持与主库一致，并可对外提供只读查询，用于读写分离或高可用。
- **Conflict with recovery**：副本上长查询占用的旧行版本与 WAL 重放需要回收/覆盖的行版本冲突；为不拖住复制，副本会取消该查询。

## 根因分析

- 日报读请求在配置了 `async_replica_url` 时走只读副本（`user_analytics_report_service.compute_and_save_daily_report` 中 `AsyncSessionLocalReplica()`）。
- `get_conversation_rounds` 会为约 19.8 万 chat 生成 session_id，再在 `_query_session_message_counts` 中按**每批 1000 个** session_id 查询 `chat_history`，单批扫描量大、多批串行，总时长易超过副本允许的「不阻塞恢复」时间，触发 conflict with recovery。

## 可选方案对比

| 方案 | 说明 |
|------|------|
| 日报读改走主库 | 根除冲突，但主库读压力增大。 |
| **减少单次负载、缩短单次查询时间** | 减小每批 session 数量，使单条 SQL 在副本上更快结束（**采用**）。 |
| 调大副本 `max_standby_streaming_delay` 或开 `hot_standby_feedback` | 缓解冲突，但拉长主从延迟或主库膨胀。 |
| 对 conflict with recovery 做有限重试 | 可作为辅助手段。 |

## 采用方案与实施要点

采用「**减小批次 + 可选重试**」：

1. **减小批次大小**  
   - 在 `user_analytics_service` 中通过配置 `user_analytics_report.batch_size`（默认 500）控制每批 session 数量，替代原常量 1000。  
   - 单条 SQL 涉及的 session_id 减少，在副本上占用快照时间缩短，降低与 WAL 恢复冲突的概率。

2. **可选：有限重试**  
   - 在 `compute_and_save_daily_report` 使用副本的分支内，捕获 `asyncpg.exceptions.SerializationError`（或 message 含 "conflict with recovery" 的等价异常），最多重试 1～2 次，重试前短 sleep（如 3 秒）。  
   - 仅捕获可处理的特定异常，不捕获笼统 `Exception`。

3. **不改动（基线）**  
   - 不改为「始终走主库」；仅在副本连续冲突后降级主库读取；不修改 `statement_timeout_sec` 默认值。

## 实施记录

- **batch_size**：在 `config.yaml` 的 `user_analytics_report` 下可配置 `batch_size`（默认 500），由 `UserAnalyticsService` 读取并用于 `_batch_list`。
- **重试**：副本读分支对 SerializationError / conflict with recovery 做最多 2 次重试，间隔 3 秒。
- **降级主库**：当副本重试后仍持续 `conflict with recovery`，自动回退主库读取并继续落库，避免日报/周报缺失。
- **方案一：按当日有活动的 session 缩小范围**  
  日报计算时先查询「当日有消息的 session_id」集合（`get_active_session_ids_on_date`，单次 `SELECT DISTINCT session_id` 扫 `chat_history` 当日），再与注册范围内的 chat 取交集；仅对这些 session 做后续的 `get_conversation_rounds`、`get_user_rounds_distribution`、`get_user_sessions_detail`、`get_popular_agents` 批量聚合。若当日活跃 session 远小于全量（如 1～2 万 vs 19.8 万），批次数与副本负载显著下降。

相关文档：[FR_USER_ANALYTICS_REPORTS.md](../FR_USER_ANALYTICS_REPORTS.md)。
