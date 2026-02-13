# 用户数据分析日报/周报：MultipleResultsFound 远程调试

## 现象

- **报错**：`sqlalchemy.exc.MultipleResultsFound: Multiple rows were found when one or none was required`
- **发生位置**：`push_scheduler_service._run_user_analytics_daily_report` → `user_analytics_compute_daily` → `compute_and_save_daily_report`（或周报对应路径），在检查「当日/当周报告是否已存在」时对 `existing.scalar_one_or_none()` 调用处。
- **环境**：通常出现在远程（如 ssh inty）运行的 `backend/push_worker/main.py`，生产日志中的 Database URL 指向的即出错的库（如生产 inty-dev）。

## 根因简述

- 表 `user_analytics_report` 上原本有唯一索引 `(report_type, report_date)`，迁移 `a0b3e0778673`（20260211）已将该唯一索引**删除**，因此同一 `(report_type, report_date)` 可以存在多行。
- 代码用 `select(...).where(...); existing.scalar_one_or_none()` 判断「是否已有报告」；当存在多行时，`scalar_one_or_none()` 会抛出 `MultipleResultsFound`。

## 在远程环境确认（不重跑 push_worker）

在 **ssh inty**（或对应环境）上对**主库**执行查询，确认是否存在重复行：

```sql
-- 查看 (report_type, report_date) 的重复情况
SELECT report_type, report_date, COUNT(*) AS cnt
FROM user_analytics_report
GROUP BY report_type, report_date
HAVING COUNT(*) > 1
ORDER BY report_date DESC;
```

若报错日期为 2026-02-12，可单独查看该日日报行数：

```sql
SELECT id, report_type, report_date, created_at
FROM user_analytics_report
WHERE report_type = 'daily' AND report_date = '2026-02-12'
ORDER BY created_at;
```

确认存在多行即说明根因成立。

## 在本地通过 replica 的 inty_dev 验证

生产错误来自生产服务器的 **inty-dev** 数据库；可在本地连接生产只读副本的 **inty-dev** 数据库做同样检查（副本与主库数据一致或略滞后）。

使用仓库脚本（需能访问 replica 公网或同 VPC/VPN）：

```bash
export PYTHONPATH=.
python scripts/check_user_analytics_report_duplicates.py --config devops/config.yaml.prod --db inty-dev
```

脚本会从 `devops/config.yaml.prod` 读取 `replica_host` / `replica_port` / `replica_user` / `replica_password`，连接数据库 **inty-dev**，执行上述重复检查 SQL 并打印结果。未传 `--db` 时默认即为 `inty-dev`。环境变量 `DB_NAME`、`DB_REPLICA_HOST` 等可覆盖配置。

## 代码层面的修复

- **防御性处理**：在 `compute_and_save_daily_report` 与 `compute_and_save_weekly_report` 中，不再使用 `existing.scalar_one_or_none()`，改为「取结果集后若存在任意一行则跳过」：
  - 使用 `existing.scalars().all()`，若 `len(rows) > 0` 则打日志并 `return None`，避免多行时抛错。
- 这样在远程即使已有重复数据，定时任务也不会再因 `MultipleResultsFound` 崩溃；若有多条会打日志便于后续清理或加回唯一约束。

## 可选后续

- **数据清理**：若需恢复「每个 (report_type, report_date) 仅保留一条」，可在主库上按业务规则去重（例如每对保留 `created_at` 最新的一条，删除其余）。
- **重新加唯一约束**：去重后可通过新迁移重新创建 `(report_type, report_date)` 唯一索引，防止再次产生重复；加约束前必须先消除现有重复行。
