# Push Worker

推送服务器，做循环的周期性任务，读取数据库，处理数据等等。

入口为 `main.py`，运行：`python -m backend.push_worker.main`。

从仓库根目录启动推送服务：`./backend/push_worker/start.sh`。

## 用户分析日报/周报（默认不跑）

`push_scheduler_service` 可通过 `config.yaml` 的 `user_analytics_report` 调度预计算；**默认 `enabled` / `daily_enabled` / `weekly_enabled` / `backfill_enabled` 均为 false**，push worker 不注册相关 cron、不启动补算。生产 **IntelliMate 日报** 由 GitHub Actions workflow `daily_intellimate_user_activity_report.yaml` 执行。细节见 [`docs/FR_USER_ANALYTICS_REPORTS.md`](../../docs/FR_USER_ANALYTICS_REPORTS.md)。
