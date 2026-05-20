# 用户数据分析日报周报

CREATED_BY_AGENT

## 需求背景

生产环境用户每日分析页面在查询「全部用户数据」时会导致页面卡顿。将全部用户的聚合统计单独迁移到新页面，分为日报和周报；数据由定时任务预计算并落库，新页面只读预计算结果，不包含也不查询对话详情。

## 核心约束

1. **原页面逻辑不变**：`UserAnalyticsPage` 保持现有筛选与 API 调用，不做修改。
2. **日报/周报不包含对话详情**：不展示、不查询 `userSessionsDetail`、`conversationsDetail` 等细粒度数据，仅展示 `UserAnalyticsStatsResponse` 中的聚合指标。

## 表结构

### user_analytics_report

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR | 主键 |
| report_type | VARCHAR(16) | `daily` / `weekly` |
| report_date | DATE | 日报：统计日期；周报：该周周一日期 |
| stats | JSONB | `UserAnalyticsStatsResponse` 的完整 JSON |
| charts | JSONB | 图表数据：new_users, conversation_rounds, user_rounds_distribution, users_hitting_limit, popular_agents, generated_images（日报当天生图列表）, daily_top_agents_by_rounds（日报按聊天轮数 Top10 角色）, daily_most_discussed_agent（日报聊天轮数最高角色） |
| created_at | TIMESTAMPTZ | 创建时间 |

唯一约束：`(report_type, report_date)`

## 统计语义

- **日报**：`report_date` 为统计日，统计该日 UTC 00:00–24:00 的活跃数据。用户范围：`register_start=2020-01-01`，`register_end=report_date+1`；活跃范围：`activity_start=report_date`，`activity_end=report_date+1`。
- **周报**：`report_date` 为该周周一，统计该周周一至周日的活跃数据。用户范围同上；活跃范围：`activity_start=report_date`，`activity_end=report_date+7`。

## 预计算由谁执行（当前）

| 能力 | 生产默认 | 入口 |
|------|----------|------|
| **日报**（T-1 UTC） | GitHub Actions | [`.github/workflows/daily_intellimate_user_activity_report.yaml`](../.github/workflows/daily_intellimate_user_activity_report.yaml) → `tools/scripts/run_user_analytics_report.py --type daily` |
| **周报** | 无定时（需手动或脚本） | `run_user_analytics_report.py --type weekly` |
| **push worker 调度** | **默认全关** | `push_scheduler_service` 仅在 `config.yaml` 显式打开对应开关时注册 cron / 启动补算 |

push worker 上保留 `_run_user_analytics_*` 与补算实现，便于本地或历史环境按需打开；**勿与 GitHub Actions 日报同时开启**，避免主库/副本重复重算（见 [`docs/completed/FR_USER_ANALYTICS_DAILY_REPORT_STANDBY_CONFLICT.md`](completed/FR_USER_ANALYTICS_DAILY_REPORT_STANDBY_CONFLICT.md)）。

## push worker 配置（`user_analytics_report`）

默认值（[`app/utils/config.py`](../app/utils/config.py) 中 `UserAnalyticsReportConfig`）均为 **关闭**：

```yaml
user_analytics_report:
  enabled: false          # 总开关；false 时 push worker 不进入日报/周报/补算分支
  daily_enabled: false    # 日报 cron（生产由 GitHub Actions 承担）
  weekly_enabled: false   # 周报 cron
  backfill_enabled: false # 启动时缺失日报/周报补算（范围受 daily/weekly 开关约束）
  daily_cron_hour: 6      # UTC，仅 daily_enabled 时生效
  weekly_cron_hour: 6     # UTC 每周一，仅 weekly_enabled 时生效
  statement_timeout_sec: 600
  batch_size: 500
```

在 push worker 上恢复某一能力时，需同时设 `enabled: true` 与对应子开关（例如仅本地测周报：`weekly_enabled: true`）。

### 启动时自动补算（仅 `backfill_enabled: true`）

push worker 启动后异步补算；`compute_and_save_*` 已存在则跳过。

- **日报补算范围**（`daily_enabled` 为 true 时）：`today - 30` 至 `today - 1`
- **周报补算范围**（`weekly_enabled` 为 true 时）：过去 7 个周一（可跨年）

### 生产大数据量

数据库默认 `command_timeout=30` 秒，复杂统计查询易超时。日报/周报计算会在事务内执行 `SET LOCAL statement_timeout`，使用 `user_analytics_report.statement_timeout_sec`（默认 600 秒）。生产环境若仍超时，可在 `config.yaml` 中调大，例如 `statement_timeout_sec: 900` 或 `1200`。

### 只读副本（减轻主库压力）

日报/周报相关**读请求**可走只读副本，**写请求**仍走主库。在 `config.yaml` 的 `database` 下启用副本：

```yaml
database:
  host: "主库 host"
  port: 5432
  # ... 其他主库配置 ...
  # 只读副本（用于日报周报等读多写少场景）
  replica_host: "34.87.163.31"  # 副本 host，不填则全部走主库
  replica_port: 5432             # 可选，不填则用主库 port
```

启用后：

- **GET /api/v1/evaluation/user-analytics/reports**：从副本读 `user_analytics_report`。
- **预计算日报/周报**（定时任务、补算、脚本）：统计类查询从副本读，写入 `user_analytics_report` 仍走主库。

未配置 `replica_host` 时行为与之前一致，全部使用主库。若日报在副本上出现 conflict with recovery，参见 [FR_USER_ANALYTICS_DAILY_REPORT_STANDBY_CONFLICT.md](completed/FR_USER_ANALYTICS_DAILY_REPORT_STANDBY_CONFLICT.md)。

## 补算脚本

用于历史数据回填：

```bash
export PYTHONPATH=.
python tools/scripts/run_user_analytics_report.py --type daily --date 2026-02-01
python tools/scripts/run_user_analytics_report.py --type weekly --date 2026-01-27
# 强制覆盖已存在的报告（用于重新生成含图表数据的报告）
python tools/scripts/run_user_analytics_report.py --type daily --date 2026-02-01 --force
```

### 批量补算

**最近 30 天每日日报**（跨平台，推荐）：

```bash
export PYTHONPATH=.
python -c "
from datetime import date, timedelta
today = date.today()
for i in range(1, 31):
  d = (today - timedelta(days=i)).isoformat()
  print(d)
" | while read d; do
  echo "补算日报 $d"
  python tools/scripts/run_user_analytics_report.py --type daily --date "$d"
done
```

**最近 30 天每日日报**（macOS，`date -v` 语法）：

```bash
export PYTHONPATH=.
for i in $(seq 1 30); do
  d=$(date -v-${i}d +%Y-%m-%d)
  echo "补算日报 $d"
  python tools/scripts/run_user_analytics_report.py --type daily --date "$d"
done
```

**最近 30 天每日日报**（Linux，`date -d` 语法）：

```bash
export PYTHONPATH=.
for i in $(seq 1 30); do
  d=$(date -d "$i days ago" +%Y-%m-%d)
  echo "补算日报 $d"
  python tools/scripts/run_user_analytics_report.py --type daily --date "$d"
done
```

**当年上半年每周周报**（1 月第 1 个周一到 6 月最后一个周一）：

```bash
export PYTHONPATH=.
# 2026 年上半年各周周一日期，按需修改年份
for d in 2026-01-06 2026-01-13 2026-01-20 2026-01-27 \
        2026-02-03 2026-02-10 2026-02-17 2026-02-24 \
        2026-03-02 2026-03-09 2026-03-16 2026-03-23 2026-03-30 \
        2026-04-06 2026-04-13 2026-04-20 2026-04-27 \
        2026-05-04 2026-05-11 2026-05-18 2026-05-25 \
        2026-06-01 2026-06-08 2026-06-15 2026-06-22 2026-06-29; do
  echo "补算周报 $d"
  python tools/scripts/run_user_analytics_report.py --type weekly --date "$d"
done
```

或使用 Python 生成上半年周报日期（跨平台）：

```bash
export PYTHONPATH=.
python -c "
from datetime import date, timedelta
year = 2026  # 按需修改
# 1 月第一个周一
d = date(year, 1, 1)
while d.weekday() != 0:
  d += timedelta(days=1)
# 遍历到 6 月最后一个周一
while d.month <= 6:
  print(d.isoformat())
  d += timedelta(days=7)
" | while read d; do
  echo "补算周报 $d"
  python tools/scripts/run_user_analytics_report.py --type weekly --date "$d"
done
```

## API

### GET /api/v1/evaluation/user-analytics/reports

获取预计算报告列表。

| 参数 | 类型 | 说明 |
|------|------|------|
| report_type | string | `daily` \| `weekly`，不传则返回全部 |
| limit | int | 返回条数，默认 30，最大 100 |

响应：`UserAnalyticsReportsResponse`，包含 `reports: UserAnalyticsReportItem[]`。

## 前端

- 页面：`evaluation/pages/UserAnalyticsReportsPage.tsx`
- 路由 key：`user-analytics-reports`
- 菜单位置：用户数据分析 与 用户每日消息 之间
- 曲线面板：每日/每周用量曲线（消息数、生图请求数、语音通话次数、语音播报次数、发起聊天人数、语音播报次数/消息数比值）；每日/每周生图用量（生图请求数、生图成功数）
- 新增角色热度面板：在「每日生图用量」下展示「每日最受欢迎角色（Top 10，按聊天轮数）」；同一角色跨日期用连线展示排名变化
- 图表：用户注册结构、Top 20 热门角色、对话轮数分布（按 Session/用户）、达到聊天限制的用户趋势
- 日报详情：展示当日聊天轮数最高角色 + 当天生成图片缩略图（来源于 `chat_history.meta_data.generated_image`）
