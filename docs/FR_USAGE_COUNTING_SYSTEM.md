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

在线链路只读写 `Usage Counter`（O(1)），必要时写事件日志；报表/审计走事件表。

---

## 4. 数据模型

## 4.1 用户时区字段
- 在用户维度持久化 `registered_timezone`（IANA 时区名，如 `America/Los_Angeles`）。
- 若值为空或非法，判定时降级为 `UTC`。
- 推荐将该字段定义为“注册时区快照”，避免频繁修改导致配额边界可被利用。

> 建议：若业务必须支持时区修改，采用“下一个周期生效”，并保留 `timezone_effective_from`。

## 4.2 限额策略表 `usage_limit_policies`
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
- 用于对账、离线分析和问题排查。

---

## 5. 周期边界计算（重点）

## 5.1 时区解析规则
```text
timezone_for_weekly_monthly =
  user.registered_timezone if valid
  else "UTC"
```

## 5.2 边界定义
- `daily`: 可配置为“自然日”或“滚动 24h”。
  - 若与当前行为兼容优先，可先保留滚动 24h。
- `weekly`: 以本地周起点（建议周一 00:00）为边界。
- `monthly`: 以本地每月 1 日 00:00 为边界。

`weekly/monthly` 必须先在用户时区下求本地边界，再转换到 UTC 存库。

## 5.3 伪代码
```python
def resolve_tz(user) -> ZoneInfo:
    tz_name = user.registered_timezone
    if tz_name is valid IANA:
        return ZoneInfo(tz_name)
    return ZoneInfo("UTC")

def cycle_window(now_utc, cycle_type, user):
    tz = resolve_tz(user)
    now_local = now_utc.astimezone(tz)

    if cycle_type == "weekly":
        # Monday = 0
        start_local = (now_local - timedelta(days=now_local.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_local = start_local + timedelta(days=7)
    elif cycle_type == "monthly":
        start_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_local = (start_local + relativedelta(months=1))
    elif cycle_type == "daily":
        # 兼容模式：rolling 24h，或改为本地自然日
        ...

    return start_local.astimezone(UTC), end_local.astimezone(UTC), str(tz)
```

---

## 6. 在线判定与扣减流程（原子）

## 6.1 `check_and_consume` 流程
1. 解析用户当前 `tier`（guest/free/subscribed）。
2. 查策略表得到 `limit_value`。
3. 计算当前周期窗口（特别是 week/month 用注册时区）。
4. 在一个数据库事务内执行：
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
- 强制客户端传 `request_id`（或服务端生成并回传）。
- 幂等表唯一约束：`(user_id, resource_type, request_id)`。
- 重试命中幂等时返回首次执行结果，避免重复扣减。

## 7.3 异常策略
- 判定链路建议默认 **fail-closed**（防超用），但可按资源配置例外（如部分体验型功能 fail-open）。
- 所有降级需打结构化日志并报警。

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

## 9.1 统一配额检查接口（内部服务）
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
返回各周期：
- `used`
- `limit`
- `remaining`
- `reset_at_utc`
- `timezone_used`

---

## 10. 迁移与上线计划（从现有系统平滑迁移）

1. **Phase 0：准备**
   - 新增 `registered_timezone` 字段（或确认已有）。
   - 创建 `usage_limit_policies` / `usage_counters` / `usage_events` / `idempotency` 表。
2. **Phase 1：双写**
   - 继续写旧 `subscription_usage`，并同步写新事件与新计数器。
3. **Phase 2：影子校验**
   - 新旧结果并行比对，输出差异报表（按用户/资源/周期）。
4. **Phase 3：切流**
   - 读路径切到新计数系统；保留旧链路回滚开关。
5. **Phase 4：收敛**
   - 观察稳定后减少旧链路依赖，保留历史表用于审计。

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

