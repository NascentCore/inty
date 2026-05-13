# 用户数据分析日报（`user_analytics_report`）落库验证说明

面向：已在 GitHub Actions 上跑过「Daily primary DB usage report」或等价脚本（`run_user_analytics_report.py --type daily`），需要在**能访问生产主库**的环境自行核对数据库记录的人员。

---

## 前置条件

- **网络**：可访问生产 Postgres 主库（与 `devops/config.yaml.prod` 中 `database` 段一致；未配置副本时即主库）。
- **凭证**：使用该文件中的 `user` / `password` / `db` / `host` / `port`（勿将密码贴到公开渠道或聊天）。
- **工具**：`psql` 或任意 SQL 客户端；若需校验 JSON 与后端契约一致，可选本仓库 + Python 3.12 及项目依赖。

---

## 1. 确认存在目标行（主键或业务键）

将 `YOUR_REPORT_DATE` 换成统计日（例如 `2026-05-12`）；若要对齐某次 Action 日志中的主键，将 `YOUR_ROW_ID` 换成日志里的 `id`。

```sql
-- 按主键（与 Action 日志里 id=… 对齐）
SELECT id, report_type, report_date, created_at
FROM user_analytics_report
WHERE id = 'YOUR_ROW_ID';

-- 按业务键：日报 + 统计日
SELECT id, report_type, report_date, created_at
FROM user_analytics_report
WHERE report_type = 'daily'
  AND report_date = DATE 'YOUR_REPORT_DATE'
ORDER BY created_at DESC;
```

**期望**：存在 `report_type = 'daily'` 且 `report_date` 为目标日期的行；若曾使用 `--force` 重算，通常仅保留**最新一条**该日期的 daily（以 `created_at` 为准取最新）。

---

## 2. 确认该日期的 daily 行数（幂等 / 强制重算后）

```sql
SELECT COUNT(*) AS daily_rows_for_date
FROM user_analytics_report
WHERE report_type = 'daily'
  AND report_date = DATE 'YOUR_REPORT_DATE';
```

**期望**：一般为 `1`。若大于 `1`，说明历史上存在重复插入，需按你们数据治理策略决定是否清理。

---

## 3. 确认 `stats` / `charts` 类型与关键键

```sql
SELECT
  id,
  jsonb_typeof(stats)  AS stats_type,
  jsonb_typeof(charts) AS charts_type,
  stats ? 'total_new_users' AS stats_has_total_new_users,
  charts ? 'popular_agents' AS charts_has_popular_agents
FROM user_analytics_report
WHERE report_type = 'daily'
  AND report_date = DATE 'YOUR_REPORT_DATE';
```

**期望**：

- `stats_type` 为 `object`。
- `charts_type` 一般为 `object`（若你们某版本允许 `charts` 为空，与当时写入逻辑一致即可）。
- `stats_has_total_new_users` 为 `true`。
- `charts_has_popular_agents` 为 `true`（图表块含热门角色等维度）。

---

## 4. （可选）抽样核对聚合量级

```sql
SELECT
  id,
  (stats->>'total_new_users')::int           AS total_new_users,
  (stats->>'total_user_messages')::int        AS total_user_messages,
  (stats->>'total_active_sessions')::int     AS total_active_sessions,
  (stats->>'total_image_generation_requests')::int AS img_req
FROM user_analytics_report
WHERE report_type = 'daily'
  AND report_date = DATE 'YOUR_REPORT_DATE';
```

**期望**：字段为非负整数，量级与 Ops 看板或内部口径无明显矛盾（不要求与某次日志逐字一致）。

---

## 5. （可选）用 Pydantic 校验 `stats` 与当前后端契约一致

在已 clone 本仓库、且已安装与后端一致依赖的机器上操作。

### 5.1 导出 `stats` 为 JSON 文件

使用可连库的 `psql`（连接方式略）：

```sql
\copy (
  SELECT stats
  FROM user_analytics_report
  WHERE report_type = 'daily'
    AND report_date = DATE 'YOUR_REPORT_DATE'
  LIMIT 1
) TO '/tmp/uar_stats.json';
```

### 5.2 在仓库根目录执行校验脚本

```bash
cd /path/to/inty
export PYTHONPATH=.
python3 - <<'PY'
import json
from pathlib import Path
from backend.ops.schemas.user_analytics import UserAnalyticsStatsResponse

raw = json.loads(Path("/tmp/uar_stats.json").read_text())
UserAnalyticsStatsResponse.model_validate(raw)
print("stats OK")
PY
```

**期望**：打印 `stats OK` 且无异常；若校验失败，说明库中 `stats` 与当前代码中的统计响应模型不一致，需单独排查版本或历史数据。

---

## 6. （可选）与 GitHub Actions 日志对齐

在对应 Workflow **Run** 的 Job 日志中搜索 `已保存，id=`，将日志中的 `id` 与「步骤 1」中按主键查询的结果对照，应一致。

---

## 安全提示

- 查询尽量使用**只读账号**；避免在生产库上执行无必要的 `UPDATE`/`DELETE`。
- 导出 `stats`/`charts` 可能含运营敏感信息，注意存储与传输范围。
