# DAILY_REPORT_MIGRATION_TO_GITHUB_ACTIONS

CREATED_BY_AGENT

## 背景

当前“用户数据分析日报/周报”由 `push_worker` 内的 APScheduler 定时生成，主链路稳定，但缺少一个独立于常驻进程的“外部兜底执行入口”。

目标是评估并落地迁移到 GitHub Actions 的可行方案，同时避免一次性替换生产主链路导致风险放大。

## 当前状态（As-Is）

- 主生产路径：
  - `app/services/push_scheduler_service.py` 每日/每周定时触发日报周报生成。
  - 启动时异步补算最近缺失日报/周报。
- 报表计算逻辑：
  - `app/services/user_analytics_report_service.py`
  - 对同一 `(report_type, report_date)` 已有记录时会跳过（幂等）。
- 手工补算入口：
  - `scripts/run_user_analytics_report.py`（支持 `--type`、`--date`、`--force`）。

## 迁移方案对比

### 方案 A（推荐）

保留 `push_worker` 作为主路径，新增 GitHub Actions 用于：

1. 定时兜底补算（比主路径晚触发）；
2. 手工触发（`workflow_dispatch`）重算指定日期。

优点：

- 风险低，不中断现有主链路；
- 即便主链路偶发失败，兜底任务可自动补齐；
- 保留人工重算入口，运维更灵活。

代价：

- 维护两条触发链路（主路径 + 兜底路径）；
- 需要谨慎设置 cron，避免与主任务同一时间争用资源。

### 方案 B（不在本次执行）

完全迁移：移除 `push_worker` 内日报/周报定时，仅保留 GitHub Actions 调度。

风险：

- 失去 push_worker 启动时自动补算能力；
- 若 GitHub Actions 调度延迟/异常，主业务无本地调度兜底；
- 对 runner 网络与环境依赖更强。

## 本次决策

执行 **方案 A**：

- 不改动现有 `push_worker` 主链路；
- 新增一个 GitHub Actions workflow 作为“兜底 + 手工补算”入口。

## 方案 A 设计

### 1) Runner 与网络

- 使用 **self-hosted runner（`inty-prod-server-gcp`）** 运行任务，以访问生产私网 DB。
- 不使用 GitHub 托管 `ubuntu-latest` 直接连生产私网。

### 2) 触发策略

- `schedule`：
  - 每日兜底：UTC 08:00（晚于主任务默认 06:00）
  - 每周兜底：周一 UTC 09:00（晚于主任务默认 06:00）
- `workflow_dispatch`：
  - 支持手工指定 `report_type`、`report_date`、`force`。

### 3) 幂等与覆盖策略

- 默认不覆盖：依赖 `compute_and_save_*` 的“已存在则跳过”行为。
- 仅在手工触发且 `force=true` 时删除既有记录后重算。

### 4) 失败处理

- 任务失败直接标红，便于在 Actions 与告警系统追踪。
- 使用 `concurrency` 避免同一报表任务并发执行。

### 5) 回滚策略

- 如兜底 workflow 引发资源争用或异常，直接禁用该 workflow 即可；
- 主路径 `push_worker` 不受影响，可继续独立产出日报/周报。

## 验收标准

1. 新 workflow 可在 `workflow_dispatch` 下成功执行 daily/weekly 补算命令；
2. 定时任务 cron 仅作为兜底，不替换主链路；
3. 未修改 `push_scheduler_service` 中现有日报/周报定时逻辑；
4. 文档与 workflow 配置一致。
