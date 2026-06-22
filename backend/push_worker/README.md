# Push Worker

推送服务器，做循环的周期性任务，读取数据库，处理数据等等。

入口为 `main.py`，运行：`python -m backend.push_worker.main`。

从仓库根目录启动推送服务：`./backend/push_worker/start.sh`。

## 调度范围

push worker 仅保留 IntelliMate Android 仍依赖的任务：

- re-engagement FCM（`agent_message`，10min / 30min / 2h / 24h / 48h）
- 节日记忆抽取与 FCM 通知（`festival_memory`）
- 推送管线维护（初始化、新用户发现、token 更新扫描）

用户分析日报/周报由 GitHub Actions `daily_intellimate_user_activity_report.yaml` 与 `tools/scripts/run_user_analytics_report.py` 承担。日常记忆抽取由 `tools/scripts/run_memory_extraction.py` 手动运行。
