# 用户数据分析日报/周报 MultipleResultsFound 完整验证报告

**文档类型**：问题验证与修复报告  
**涉及组件**：`backend/push_worker` 定时任务 → `user_analytics_report_service`  
**状态**：已修复并验证  
**日期**：2026-02-13  

---

## 1. 问题概述

生产环境（prod-intellimate）运行 `backend/push_worker/main.py` 时，用户数据分析日报定时任务（`_run_user_analytics_daily_report`）在执行过程中抛出 `sqlalchemy.exc.MultipleResultsFound`，导致该次调度失败。报错发生在检查「当日是否已有日报」的查询上：代码期望最多返回 0 或 1 行，实际返回了多行。

---

## 2. 报错现象

### 2.1 异常信息

```
sqlalchemy.exc.MultipleResultsFound: Multiple rows were found when one or none was required
```

### 2.2 调用栈摘要

| 层级 | 文件 | 位置 |
|------|------|------|
| 入口 | `backend/push_worker/main.py` | `loop.run_until_complete(main())` |
| 调度 | `app/services/push_scheduler_service.py` | `_run_user_analytics_daily_report` 约 495 行，调用 `user_analytics_compute_daily(db, report_date)` |
| 业务 | `app/services/user_analytics_report_service.py` | `compute_and_save_daily_report` 约 243 行：`if existing.scalar_one_or_none():` |
| SQLAlchemy | `sqlalchemy/engine/result.py` | `scalar_one_or_none()` → `_only_one_row()` → 抛出 `MultipleResultsFound` |

### 2.3 环境与数据

- **运行环境**：远程（如 ssh inty），`backend/push_worker` 进程。
- **数据库**：生产配置中 Database URL 指向 **inty-dev**（日志截图：`postgresql://...@10.41.177.3:5432/inty-dev`）。
- **报错日期**：`report_date = 2026-02-12`（从堆栈中 `datetime.date(2026, 2, 12)` 可知）。

---

## 3. 根因分析

### 3.1 数据库约束变化

- 表 `user_analytics_report` 在创建时（迁移 `c9d0e1f2a3b4`）曾包含唯一索引 `ix_user_analytics_report_type_date`，约束 `(report_type, report_date)` 唯一。
- 迁移 **a0b3e0778673**（20260211，更新数据库表）在 `upgrade()` 中执行了：
  ```python
  op.drop_index(op.f('ix_user_analytics_report_type_date'), table_name='user_analytics_report')
  ```
- 因此当前生产库中该表**不再**有 `(report_type, report_date)` 唯一约束，同一 (report_type, report_date) 可存在多行（例如并发写入或重复 backfill 导致）。

### 3.2 代码假设与冲突

- `compute_and_save_daily_report` 与 `compute_and_save_weekly_report` 在写入前会查询「是否已有同类型、同日/周的报告」：
  ```python
  existing = await db.execute(
      select(UserAnalyticsReport).where(
          UserAnalyticsReport.report_type == "daily",  # 或 "weekly"
          UserAnalyticsReport.report_date == report_date,
      )
  )
  if existing.scalar_one_or_none():  # 此处要求 0 或 1 行
      logger.info("日报/周报 已存在，跳过")
      return None
  ```
- `Result.scalar_one_or_none()` 的约定：恰好 0 行返回 `None`，恰好 1 行返回该行，**多行时抛出 `MultipleResultsFound`**。
- 一旦表中存在多行相同 (report_type, report_date)，该调用即抛错，与当前数据状态冲突。

### 3.3 结论

根因是**数据与代码假设不一致**：表在迁移后允许重复的 (report_type, report_date)，而代码仍按「至多一行」使用 `scalar_one_or_none()`，遇到多行即崩溃。

---

## 4. 验证过程

### 4.1 验证方式

在**本地**连接生产只读副本（replica），对与生产一致的数据库 **inty-dev** 执行重复检查，确认是否存在多行相同的 (report_type, report_date)。

### 4.2 使用脚本与配置

- **脚本**：`scripts/check_user_analytics_report_duplicates.py`
- **配置**：`devops/config.yaml.prod`（`replica_host: "34.87.163.31"`, `replica_port: 5432`, `replica_user` / `replica_password`）
- **数据库**：`inty-dev`（与生产日志中的 Database URL 一致；注意为带连字符的 `inty-dev`，非 `inty_dev`）

执行命令：

```bash
export PYTHONPATH=.
python scripts/check_user_analytics_report_duplicates.py --config devops/config.yaml.prod --db inty-dev
```

### 4.3 实际运行结果（原文）

```
连接副本 34.87.163.31:5432 数据库 inty-dev ...
发现 2 组重复的 (report_type, report_date):
  daily  2026-02-12  cnt=2
  daily  2026-02-11  cnt=2

示例：查看某日日报多行（将 2026-02-12 换成上面出现的日期）:
  SELECT id, report_type, report_date, created_at
  FROM user_analytics_report
  WHERE report_type = 'daily' AND report_date = '2026-02-12'
  ORDER BY created_at;
```

### 4.4 验证结论

- 副本 **inty-dev** 中确实存在**多行**相同 (report_type, report_date)：
  - **daily 2026-02-12**：2 条（与报错日期一致）
  - **daily 2026-02-11**：2 条
- 与堆栈中 `report_date=2026-02-12` 及 `MultipleResultsFound` 现象一致，**根因在本地通过 replica 数据得到确认**。

---

## 5. 修复方案与改动

### 5.1 修复思路

在不改变「已有报告则跳过」语义的前提下，使逻辑**容忍**「已存在多行」的既有数据：不再要求「至多一行」，改为「存在任意一行即跳过」。

### 5.2 代码改动

**文件**：`app/services/user_analytics_report_service.py`

**日报**（`compute_and_save_daily_report`）：

- 原：`if existing.scalar_one_or_none():` 后打日志「日报 xxx 已存在，跳过」并 `return None`。
- 现：`existing_rows = existing.scalars().all()`，若 `existing_rows` 非空则打日志「日报 xxx 已存在（共 N 条），跳过」并 `return None`。

**周报**（`compute_and_save_weekly_report`）：

- 同上，将「日报」改为「周报」，同样使用 `scalars().all()` 判断是否存在任意一行，若存在则记录「周报 xxx 已存在（共 N 条），跳过」并 `return None`。

### 5.3 行为说明

- 当表中该 (report_type, report_date) 有 0 行：行为不变，继续写入新报告。
- 当有 1 行：行为不变，跳过并打日志，且 N=1。
- 当有多行：**不再抛错**，跳过并打日志「共 N 条」，便于后续排查与清理；定时任务不再因 `MultipleResultsFound` 崩溃。

---

## 6. 单元测试验证

### 6.1 涉及用例

- `tests/app/services/test_user_analytics_report_service.py`：
  - `test_compute_and_save_daily_report_skips_existing`
  - `test_compute_and_save_daily_report_creates_new`
  - `test_compute_and_save_weekly_report_skips_existing`
  - `test_compute_and_save_weekly_report_creates_new`

### 6.2 修改说明

- 原先通过 mock `execute` 返回的 `Result`，并设置 `scalar_one_or_none.return_value` 来模拟「已存在」或「不存在」。
- 现改为对同一 Result mock 使用 `scalars.return_value.all.return_value`：
  - 已存在：`[MagicMock()]`（非空列表）
  - 不存在：`[]`（空列表）

### 6.3 运行结果

在仓库根目录执行：

```bash
python -m pytest tests/app/services/test_user_analytics_report_service.py -v
```

上述四个用例及同文件其余用例均通过，修复未改变「已存在则跳过、不存在则创建」的对外行为。

---

## 7. 文档与脚本

- **调试说明**：`tests/docs/DEBUG_USER_ANALYTICS_MULTIPLE_RESULTS.md`（现象、根因、远程/本地确认方式、修复要点、可选后续）。
- **本地验证脚本**：`scripts/check_user_analytics_report_duplicates.py`（默认连接 replica 的 `inty-dev`，执行重复检查 SQL 并打印结果）。

---

## 8. 结论与后续建议

### 8.1 结论

- **问题**：生产 inty-dev 上 `user_analytics_report` 表因唯一索引被迁移删除，存在同一 (report_type, report_date) 多行；代码使用 `scalar_one_or_none()` 导致多行时抛出 `MultipleResultsFound`，日报任务失败。
- **验证**：通过本地连接 replica 的 inty-dev 运行 `check_user_analytics_report_duplicates.py`，确认存在 2026-02-12、2026-02-11 两日 daily 各 2 条重复，与报错现象一致。
- **修复**：日报/周报均改为用 `scalars().all()` 判断「是否已有记录」，有任意一行即跳过并打日志（含条数），避免多行时抛错；单元测试已更新并通过。

### 8.2 后续建议（可选）

- **数据清理**：若希望恢复「每个 (report_type, report_date) 仅保留一条」，可在主库按业务规则去重（例如保留 `created_at` 最新的一条，删除其余）。
- **重新加唯一约束**：去重完成后，可通过新 Alembic 迁移重新创建 `(report_type, report_date)` 唯一索引，防止再次产生重复；加约束前必须先消除现有重复行。

---

## 9. 近期提交与结论：真实错误，非预期行为

### 9.1 相关提交时间线（近期）

| 日期 | 提交 | 说明 |
|------|------|------|
| 2026-02-10 | f784c79b (#2184) | **运行 alembic revision 生成新的 version 文件**：新增迁移 a0b3e0778673（`更新数据库表`），内容为 **autogenerate 自动生成**。 |
| 2026-02-11 | 15d07da2 (#2190) | Update user analytics report configuration and service to support batch… |
| 2026-02-11 | a7d38464 | add some log of user analytics job |
| 2026-02-11 | d12c9a06 | fix the high load of user analytics report |
| 2026-02-12 | 22bc5e20 (#2227) | **github workflow 更新生产环境 db schema（使用 alembic upgrade head）**：生产库开始通过 CI 执行 `alembic upgrade head`。 |
| 2026-02-12/13 | （生产） | 日报任务报错 `MultipleResultsFound`（report_date=2026-02-12 等）。 |

### 9.2 迁移 a0b3e0778673 的由来

- 该迁移文件内注明：`# ### commands auto generated by Alembic - please adjust! ###`，即由 **alembic revision --autogenerate** 生成，并非手写。
- 同一迁移中还包含对 `agents`、`chat_history`、`festival_memory_config`、`memory`、`subscription_usage`、`feedback_push_history` 的注释或索引变更；对 `user_analytics_report` 仅有 **drop** `ix_user_analytics_report_type_date`。
- ORM 模型 `app/models/user_analytics_report.py` 自创建起**未声明** `(report_type, report_date)` 的唯一约束（无 `UniqueConstraint` 或 `Index(..., unique=True)`），而建表迁移（20260202_120000）在数据库侧创建了该唯一索引。autogenerate 以**当前模型**为准对比数据库，认为库中多出的该索引应删除，故生成了 `drop_index`。

### 9.3 结论：属于真实错误（回归），非预期业务行为

- **删除唯一索引并非产品预期**：业务上仍为「每个 (report_type, report_date) 只应有一条报告」；允许重复多行并非需求，而是迁移 autogenerate 的**附带结果**（为与其他表注释/索引变更一起提交，未单独审查或调整）。
- **代码与 schema 不一致**：迁移在 2 月 12 日随 #2227 在生产执行后，表中已无唯一约束，可能出现多行；而 `user_analytics_report_service` 一直用 `scalar_one_or_none()` 假设「至多一行」，未做相应修改，属于 **schema 与代码假设不一致** 导致的回归。
- **表现**：迁移上线后，一旦出现重复（如并发或重复 backfill），定时任务即抛 `MultipleResultsFound`，属**真实错误**；本次修复（改为 `scalars().all()` 判断存在即跳过）是正确的防御性修复，并可与后续「数据去重 + 重新加唯一约束」配合恢复业务不变量。
