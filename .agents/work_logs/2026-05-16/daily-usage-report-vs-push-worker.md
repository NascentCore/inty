# 日报兜底 workflow 与机上 push worker 双写

**一句话**：生产库上若 push worker 仍在跑用户数据分析日报，会先写入 `user_analytics_report`，导致 GitHub「Daily primary DB usage report」定时任务日志里出现「已存在，跳过」、Actions 仍成功但无新行。

## 行动要点

- 现象：`compute_and_save_daily_report` 见当日 `daily` 行已存在即 `return None`，脚本仍 `exit 0`，易误判「workflow 没产出数据」。
- 根因：与 push worker 内 `_run_user_analytics_daily_report`（同 UTC 窗口、同 T-1 日期）争用同一幂等键。
- 已做（运维）：在生产机通过 `docker stop inty-push-worker-prod` 与 `docker stop inty-push-worker-dev` 暂停机上 push worker（本地习惯用 `ssh inty` 登录）；**恢复运行前需明确「谁负责写日报」**，避免双写或长期停推送侧任务。

## 后续待办

- 产品/运维：要么只保留一侧写日报（改配置停 `user_analytics_report` 或只保留 Actions 兜底），要么错开 cron / 接受「先写者为准」并用 workflow_dispatch + force 强制重算。
- 若重启 push worker：确认 `config.yaml` 中 `user_analytics_report.enabled` 与定时策略是否与 Actions 一致。
