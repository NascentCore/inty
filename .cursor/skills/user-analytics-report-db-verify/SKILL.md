---
name: user-analytics-report-db-verify
description: >-
  Verifies `user_analytics_report` daily rows in Postgres (row presence, count,
  JSONB shape, sample metrics, Pydantic contract). Use when validating daily
  user analytics after GitHub Actions or `scripts/run_user_analytics_report.py`,
  or when the user asks to check / audit / confirm user analytics report DB data.
disable-model-invocation: true
---

# User analytics report — DB verification

## Before you start

- **Production daily rollups** come from GitHub Actions (`daily_intellimate_user_activity_report.yaml`), not push worker (`user_analytics_report` defaults all off). See `docs/FR_USER_ANALYTICS_REPORTS.md`.
- Needs **network access** to the DB host in repo-root `config.yaml` (`database` section). Do **not** paste passwords, DSNs, or full `config.yaml` into chat.
- Prefer a **read-only** DB role for queries.
- Repo doc with SQL templates: [tests/docs/TEST_USER_ANALYTICS_REPORT_DB_VERIFICATION.md](../../../tests/docs/TEST_USER_ANALYTICS_REPORT_DB_VERIFICATION.md).

## Interpretation trap

In **daily** reports, `stats.total_new_users` is **not** “signups that calendar day”. It is the count of users with `created_at` in `[2020-01-01 UTC, report_date+1 00:00 UTC)` — i.e. **cumulative registered users through the end of `report_date` (UTC)**. Day-scoped activity metrics (`total_user_messages`, `total_active_sessions`, etc.) use the activity window for `report_date` only. See `compute_and_save_daily_report` in `app/services/user_analytics_report_service.py`.

## Preferred execution

From the **inty repo root** (where `config.yaml` exists), with venv active and deps installed (`psycopg2`, `pyyaml`, project tree on `PYTHONPATH` for Pydantic):

```bash
source .venv/bin/activate
export PYTHONPATH=.
python .cursor/skills/user-analytics-report-db-verify/scripts/verify_user_analytics_report_db.py
python .cursor/skills/user-analytics-report-db-verify/scripts/verify_user_analytics_report_db.py --date 2026-05-12
```

Script prints a short evidence block (ids, counts, types, sample ints, `stats OK` or traceback). It never prints the DB password.

## If you cannot run the script

Run the SQL blocks from [tests/docs/TEST_USER_ANALYTICS_REPORT_DB_VERIFICATION.md](../../../tests/docs/TEST_USER_ANALYTICS_REPORT_DB_VERIFICATION.md), then validate exported `stats` with:

```bash
cd /path/to/inty
export PYTHONPATH=.
python3 -c "import json; from pathlib import Path; from backend.ops.schemas.user_analytics import UserAnalyticsStatsResponse; UserAnalyticsStatsResponse.model_validate(json.loads(Path('/tmp/uar_stats.json').read_text().strip())); print('stats OK')"
```

## GitHub Actions cross-check

In the workflow job log, search for **`已保存，id=`** and confirm that `id` matches `user_analytics_report.id` from SQL. Workflow in repo: `.github/workflows/user_analytics_report_fallback.yaml`.

## Report back

Summarize: chosen `report_date`, row `id`, `daily_rows_for_date`, `stats`/`charts` `jsonb_typeof`, key presence (`total_new_users`, `popular_agents`), optional sample metrics, Pydantic outcome, and whether log `id` aligns (if logs were available).
