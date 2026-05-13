#!/usr/bin/env python3
"""Read-only checks for user_analytics_report (daily). Run from inty repo root.

Loads database settings from ./config.yaml (never printed). See sibling SKILL.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "config.yaml").is_file() and (p / "app" / "models").is_dir():
            return p
    raise SystemExit(
        "Could not find repo root (need config.yaml and app/models/). "
        "Run this script from the inty checkout; use repo-root PYTHONPATH for imports."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify user_analytics_report daily row(s) against DB + Pydantic."
    )
    parser.add_argument(
        "--date",
        type=str,
        default="",
        help="Report date YYYY-MM-DD (UTC calendar day). If omitted, use latest daily.",
    )
    args = parser.parse_args()

    root = _repo_root()
    sys.path.insert(0, str(root))

    try:
        import yaml
    except ImportError as e:
        raise SystemExit(f"PyYAML required: {e}") from e
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError as e:
        raise SystemExit(f"psycopg2 required: {e}") from e

    cfg_path = root / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())["database"]
    conn = psycopg2.connect(
        host=cfg["host"],
        port=cfg.get("port", 5432),
        user=cfg["user"],
        password=cfg["password"],
        dbname=cfg["db"],
        connect_timeout=15,
    )
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if args.date:
        report_date = date.fromisoformat(args.date)
    else:
        cur.execute(
            """
            SELECT report_date
            FROM user_analytics_report
            WHERE report_type = 'daily'
            ORDER BY report_date DESC, created_at DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            print("No daily rows in user_analytics_report.")
            raise SystemExit(2)
        report_date = row["report_date"]

    print(f"=== report_date={report_date} ===")

    cur.execute(
        """
        SELECT id, report_type, report_date, created_at
        FROM user_analytics_report
        WHERE report_type = 'daily' AND report_date = %s
        ORDER BY created_at DESC
        """,
        (report_date,),
    )
    rows = cur.fetchall()
    if not rows:
        print("No daily row for that date.")
        raise SystemExit(2)
    for r in rows:
        print(dict(r))

    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM user_analytics_report
        WHERE report_type = 'daily' AND report_date = %s
        """,
        (report_date,),
    )
    print("=== daily_rows_for_date ===", dict(cur.fetchone()))

    cur.execute(
        """
        SELECT id,
               jsonb_typeof(stats) AS stats_type,
               jsonb_typeof(charts) AS charts_type,
               stats ? 'total_new_users' AS stats_has_total_new_users,
               charts ? 'popular_agents' AS charts_has_popular_agents
        FROM user_analytics_report
        WHERE report_type = 'daily' AND report_date = %s
        ORDER BY created_at DESC
        """,
        (report_date,),
    )
    print("=== jsonb / keys ===")
    for r in cur.fetchall():
        print(dict(r))

    cur.execute(
        """
        SELECT id,
               (stats->>'total_new_users')::int AS total_new_users,
               (stats->>'total_user_messages')::int AS total_user_messages,
               (stats->>'total_active_sessions')::int AS total_active_sessions,
               (stats->>'total_image_generation_requests')::int AS img_req
        FROM user_analytics_report
        WHERE report_type = 'daily' AND report_date = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (report_date,),
    )
    print("=== sample metrics (latest created_at) ===")
    m = cur.fetchone()
    print(dict(m))

    cur.execute(
        """
        SELECT stats
        FROM user_analytics_report
        WHERE report_type = 'daily' AND report_date = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (report_date,),
    )
    stats_row = cur.fetchone()
    raw = stats_row["stats"]
    if isinstance(raw, str):
        raw = json.loads(raw)
    from backend.ops.schemas.user_analytics import UserAnalyticsStatsResponse

    UserAnalyticsStatsResponse.model_validate(raw)
    print("=== Pydantic === stats OK")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
