<!-- CREATED_BY_AGENT -->
# Usage Counting System 设计（guest/free/subscribed × daily/weekly/monthly）

## 1. 目标与范围

### 1.1 目标

- 为三类用户（`guest`、`free`、`subscribed`）提供统一的用量计数与限额判定系统。
- 支持多周期限额：`daily`、`weekly`、`monthly`。
- 满足关键约束：**`weekly` 和 `monthly` 的刷新边界按用户注册时区计算；若没有注册时区则使用 `UTC`**。
- 在高并发下保证“计数 + 判定 + 扣减”的原子性，避免超扣/少扣。

### 1.2 非目标（本期不做）

- 不讨论前端 UI/埋点展示细节。
- 不引入复杂计费（例如按美元成本实时计费）。
- 不替换全部历史统计表，仅在限额判定链路内引入新计数核心。

---

## 2. 现状与痛点（基于当前实现）

- 当前后端主要依赖 `subscription_usage` 做事件记录，再按 `24h` 或 UTC 日界进行聚合查询。
- 痛点：
  1. 周/月周期能力缺失。
  2. 时区语义不统一（以 UTC 为主），无法满足“按用户注册时区刷新”的规则。
  3. 每次判定都 `sum` 历史事件，热点用户会带来查询压力。
  4. 缺乏标准化幂等防重，客户端重试可能重复记数。

---

## 3. 核心设计概览

采用 **“事件日志 + 周期聚合计数器”** 双层设计：

1. **Usage Event Log（审计层）**  
   追加写入每次消费事件，保证可追溯、可回放、可对账。
2. **Usage Counter（判定层）**  
   按 `(user_id, resource_type, cycle_type, cycle_start_utc)` 聚合，承载在线限额判断。

在线链路只读写 `Usage Counter`（O(1)），必要时写事件日志；报表/审计走事件表。**报表、审计、对账、离线分析等只读查询统一走只读副本**，降低主库压力（见 7.4）。

---

## 4. 数据模型

## 4.1 用户时区字段

- 在 **`app/models/user.py`** 的 users 表新增字段 `registered_timezone`（IANA 时区名，如 `America/Los_Angeles`）。
- 若值为空或非法，判定时降级为 `UTC`。
- 推荐将该字段定义为“注册时区快照”，避免频繁修改导致配额边界可被利用。

> 建议：若业务必须支持时区修改，采用“下一个周期生效”，并保留 `timezone_effective_from`。

## 4.2 限额配置：app/utils/config.py → app/core global config

- 限额策略定义在 **`app/utils/config.py`**（如 `usage_limit_policies`），通过 **app/core 的 global config** 暴露给判定链路（如 `limit_value`）；读路径统一查 core 的 global config。
- 维度：
  - `user_tier`: `guest | free | subscribed`
  - `resource_type`: 如 `chat`, `voice_generation`, `image_generation`, `agent_creation`
  - `cycle_type`: `daily | weekly | monthly`
- 字段：
  - `limit_value`（-1 表示无限）
  - `is_enabled`
  - `priority`（支持策略覆盖）
  - `updated_at`

## 4.3 周期计数器表 `usage_counters`

- 主键建议：`(user_id, resource_type, cycle_type, cycle_start_utc)`
- 核心字段：
  - `cycle_end_utc`
  - `timezone_used`（本周期使用的时区，审计用）
  - `used_count`
  - `updated_at`

## 4.4 事件表 `usage_events`（可选强烈建议）

- 字段：
  - `event_id`, `request_id`（幂等键）
  - `user_id`, `resource_type`, `delta`
  - `occurred_at_utc`
  - `cycle_type`, `cycle_start_utc`
  - `metadata`（模型名、业务来源等）
- **唯一约束**：`(user_id, resource_type, request_id)`，用于幂等。
- **写入语义**：首次请求时写入本条 `usage_events` 并更新 `usage_counters`；重试时先按 `(user_id, resource_type, request_id)` 查是否已有记录，若命中则只返回首次执行结果，**不再次写入事件、不再次更新计数器**。
- 用于对账、离线分析和问题排查。

## 4.5 Device Registration API：app 上报系统时区

- 调用 device registration api 时，app 上报当前系统时区（如注册、登录或设置接口）；后端对 `users.registered_timezone` 做 **新增或修改**（有则更新，无则写入）。
- 数据库表中的使用事件均为 UTC 计时。

---

## 5. 周期边界计算（重点）

## 5.1 时区解析规则

```text
timezone_for_weekly_monthly =
  user.registered_timezone if valid
  else "UTC"
```

## 5.2 边界定义

- `daily`: 配置为“自然日”。
  - 若与当前行为兼容优先，可先保留滚动 24h。
- `weekly`: 以本地周起点（建议周一 00:00）为边界。
- `monthly`: 以本地每月 1 日 00:00 为边界。

`weekly/monthly` 必须先在用户时区下求本地边界，再转换到 UTC 存库。

---

## 6. 在线判定与扣减流程（原子）

## 6.1 `check_and_consume` 流程

1. 解析用户当前 `tier`（guest/free/subscribed）。
2. 查 app/core 的 global config 中的 `limit_value`（数据来源为 app/utils/config.py 的限额策略）。
3. 计算当前周期窗口（特别是 week/month 用注册时区）。
4. 在一个数据库事务内执行（**本流程必须全程使用主库**，不可走只读副本，否则复制延迟会导致幂等误判或重复扣减）：
   - 幂等校验（`request_id` 已处理则直接返回上次结果）。
   - `upsert usage_counters` 并尝试 `used_count += delta`。
   - 若超限则回滚并返回 `LIMIT_EXCEEDED`。
   - 成功则写入 `usage_events`。
5. 返回 `allowed`, `used`, `remaining`, `reset_at_utc`。

## 6.2 原子 SQL 思路（PostgreSQL）

```sql
INSERT INTO usage_counters (...)
VALUES (...)
ON CONFLICT (user_id, resource_type, cycle_type, cycle_start_utc)
DO UPDATE
SET used_count = usage_counters.used_count + :delta,
    updated_at = NOW()
WHERE usage_counters.used_count + :delta <= :limit_value
RETURNING used_count;
```

- `RETURNING` 无结果即表示超限。
- 无限额度（`limit_value = -1`）可走快速路径：仅计数不判定或直接放行。

---

## 7. 并发、幂等、异常策略

## 7.1 并发

- 利用数据库唯一键 + `ON CONFLICT ... DO UPDATE` 保证并发安全。
- 对热点资源可加分片键或按资源拆表（后续扩展）。

## 7.2 幂等

- 强制客户端传 `request_id`。
- 幂等通过 `usage_events` 表唯一约束 `(user_id, resource_type, request_id)` 实现：首次请求写入事件并更新计数器；重试时若该唯一键已存在则只查并返回首次执行结果，不写事件、不更新计数器。

## 7.3 异常策略

- 判定链路建议默认 **fail-closed**（防超用），但可按资源配置例外（如部分体验型功能 fail-open）。
- 所有降级需打结构化日志并报警。

## 7.4 只读副本（Read Replica）

为降低主库压力，以下读路径**优先使用只读副本**，与现有 `get_async_replica_db` / `prefer_replica_read` 模式一致；副本不可用时回退主库。

- **必须走主库**（不可用副本）：
  - **`check_and_consume` 全流程**：幂等校验、读计数器、写计数器、写事件在同一事务内，若读走副本会因复制延迟导致重试误判或重复扣减。
  - **Device Registration API 写 `users.registered_timezone`**：写操作仅主库。
- **优先走只读副本**：
  - **查询剩余额度接口（9.2）**：纯读 `usage_counters`、必要时 `users.registered_timezone`；可接受数秒复制延迟。若业务要求“查额度必须包含刚发生的扣减”，可改为走主库。
  - **报表、审计、对账、离线分析**：对 `usage_events`、`usage_counters` 的只读聚合与扫描，可接受分钟级延迟，统一走只读副本。

**实现**：配置沿用 `config.database.replica_host` / `async_replica_url`；读路径通过 `get_async_replica_db` 或 service 层 `prefer_replica_read=True` 使用副本，副本不可用时回退主库（与 `memory_extraction_service`、`user_analytics_report_service` 一致）。

---

## 8. 时区与边界特殊场景

1. **DST 夏令时切换**  
   因为边界在“本地时间”计算后再转 UTC，天然可处理 23/25 小时日的情况。
2. **用户无注册时区**  
   固定使用 `UTC`，满足需求中的 fallback。
3. **时区非法值**  
   记录告警并回落 `UTC`。
4. **用户改时区**  
   建议“下个周期生效”，防止通过频繁切换时区绕过限额。

---

## 9. 对外接口（建议）

## 9.1 统一配额检查接口（app/services API）

```text
check_and_consume(
  user_id,
  resource_type,
  delta,
  cycle_types=[daily, weekly, monthly],
  request_id,
  metadata
) -> {
  allowed: bool,
  violations: [{cycle_type, used, limit, reset_at_utc}],
  counters: [...]
}
```

## 9.2 查询剩余额度接口

- 纯读接口，**优先使用只读副本**（见 7.4）；副本不可用时回退主库。
- 返回各周期：`used`、`limit`、`remaining`、`reset_at_utc`、`timezone_used`。

---

## 10. 迁移与上线计划（从现有系统平滑迁移）

1. **Phase 0：准备**
   - 在 **`app/models/user.py`** / users 表新增 `registered_timezone` 字段。
   - 在 app/utils/config.py 与 app/core 中接入限额策略；创建 `usage_counters`、`usage_events` 表（无需单独 idempotency 表，幂等由 usage_events 唯一约束承担）。
2. **Phase 1：实现新系统**
   - 仅实现并写入新系统：**只写 `usage_events` + `usage_counters`**；**旧系统 `subscription_usage` 完全不动**（不双写、不修改旧表）。
3. **Phase 2：切流**
   - 新系统稳定后，读路径一次性切到新计数系统；保留旧链路回滚开关。
4. **Phase 3：收敛**
   - 观察稳定后减少对旧链路的依赖；保留 `subscription_usage` 历史表用于审计与既有报表。

---

## 11. 监控与运维

- 指标：
  - `quota_check_total{resource,tier,cycle,allowed}`
  - `quota_over_limit_total{resource,tier,cycle}`
  - `quota_check_latency_ms`
  - `timezone_fallback_utc_total`
  - `idempotency_hit_total`
- 日志：
  - 输出 `user_id`, `resource_type`, `cycle_type`, `limit`, `used`, `timezone_used`, `request_id`。
- 数据治理：
  - `usage_events` 按时间分区，设置冷热分层与归档 TTL。

---

## 12. 验收标准（与本需求直接相关）

1. 对同一用户在 `weekly/monthly` 周期的判断，边界必须由 `registered_timezone` 决定。  
2. 当 `registered_timezone` 缺失或非法时，系统使用 `UTC`，且行为可观测（有监控指标）。  
3. 在并发请求下，计数不出现超扣（原子性）。  
4. 客户端重试不会导致重复计数（幂等）。  
5. 能同时返回 `daily/weekly/monthly` 剩余额度与下次刷新时间。
