# `user_analytics_report` 日报验证

替换占位：`YOUR_REPORT_DATE`（统计日）、`YOUR_ROW_ID`（可选，日志里的 `id`）。

```sql
SELECT id, report_type, report_date, created_at
FROM user_analytics_report
WHERE id = 'YOUR_ROW_ID';

SELECT id, report_type, report_date, created_at
FROM user_analytics_report
WHERE report_type = 'daily'
  AND report_date = DATE 'YOUR_REPORT_DATE'
ORDER BY created_at DESC;
```

```sql
SELECT COUNT(*) AS daily_rows_for_date
FROM user_analytics_report
WHERE report_type = 'daily'
  AND report_date = DATE 'YOUR_REPORT_DATE';
```

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

```sql
SELECT
  id,
  (stats->>'total_new_users')::int AS total_new_users,
  (stats->>'total_user_messages')::int AS total_user_messages,
  (stats->>'total_active_sessions')::int AS total_active_sessions,
  (stats->>'total_image_generation_requests')::int AS img_req
FROM user_analytics_report
WHERE report_type = 'daily'
  AND report_date = DATE 'YOUR_REPORT_DATE';
```

`psql` 导出 `stats`：

```sql
\copy (
  SELECT stats
  FROM user_analytics_report
  WHERE report_type = 'daily'
    AND report_date = DATE 'YOUR_REPORT_DATE'
  LIMIT 1
) TO '/tmp/uar_stats.json';
```

仓库根目录：

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

GitHub Actions Job 日志搜索：`已保存，id=`，与上表 `WHERE id = ...` 对照。
