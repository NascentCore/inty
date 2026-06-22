# CREATED_BY_AGENT
"""
手动补算用户数据分析日报/周报，用于历史数据回填。

生产 IntelliMate 日报定时由 GitHub Actions（daily_intellimate_user_activity_report.yaml）
调用本脚本（见 docs/FR_USER_ANALYTICS_REPORTS.md）。

用法（在仓库根目录）:
    export PYTHONPATH=.
    python tools/scripts/run_user_analytics_report.py --type daily --date 2026-02-01
    python tools/scripts/run_user_analytics_report.py --type weekly --date 2026-01-27

--type: daily | weekly
--date: YYYY-MM-DD。日报：统计该日；周报：该周周一日期
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta

from loguru import logger

from app.core.logging import init_logger
from app.db.session import AsyncSessionLocal
from app.services.user_analytics_report_service import (
    compute_and_save_daily_report,
    compute_and_save_weekly_report,
)


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="手动补算用户数据分析日报/周报",
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["daily", "weekly"],
        help="报告类型：daily=日报，weekly=周报",
    )
    parser.add_argument(
        "--date",
        required=True,
        help="日期 YYYY-MM-DD。日报：统计该日；周报：该周周一日期",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制覆盖已存在的报告（用于重新生成含图表数据的报告）",
    )
    args = parser.parse_args()

    try:
        report_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        logger.error(f"无效日期格式: {args.date}，应为 YYYY-MM-DD")
        return 1

    if args.type == "weekly" and report_date.weekday() != 0:
        logger.warning(
            f"周报日期 {args.date} 不是周一（weekday=0），将按该周周一计算"
        )
        report_date = report_date - timedelta(days=report_date.weekday())

    init_logger()

    try:
        async with AsyncSessionLocal() as db:
            if args.force:
                from sqlalchemy import delete

                from app.models.user_analytics_report import UserAnalyticsReport

                await db.execute(
                    delete(UserAnalyticsReport).where(
                        UserAnalyticsReport.report_type == args.type,
                        UserAnalyticsReport.report_date == report_date,
                    )
                )
                await db.commit()
            if args.type == "daily":
                result = await compute_and_save_daily_report(db, report_date)
            else:
                result = await compute_and_save_weekly_report(db, report_date)

        if result:
            logger.info(f"{args.type} 报告 {args.date} 已保存，id={result.id}")
        else:
            logger.info(f"{args.type} 报告 {args.date} 已存在，跳过")
        return 0
    except KeyboardInterrupt:
        logger.info("用户中断")
        return 1
    except Exception as e:
        logger.error(f"补算失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
