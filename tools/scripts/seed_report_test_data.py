#!/usr/bin/env python3
"""
向举报表插入一条测试数据，便于在「举报与反馈」页面验证列表、详情、永久链接等功能。
应在数据库迁移与 init_admin_user 之后执行（如 ./backend/inty/start.sh --dev 已包含）。
幂等：若已存在同描述测试数据则跳过。
CREATED_BY_AGENT
"""

import asyncio
import random
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.uuid import get_new_report_id
from app.db.session import AsyncSessionLocal
from app.models.report import Report, ReportStatus, ReportType
from app.models.user import User
from app.schemas.report import ReasonCode

# 举报类型原因代码（与 ReasonCode 中 Report 原因代码一致）
REPORT_REASON_CODES = [e for e in ReasonCode]

# 用于生成随机句子的词表
_WORDS = (
    "the a an and or but in on at to for of with by from as is was are were been be have has had do does did will would could should may might must can need dare ought used".split()
    + "one two three four five six seven eight nine ten".split()
    + "test sample random description content report feedback".split()
)


def _random_sentence(word_count: int = 10) -> str:
    return " ".join(random.choices(_WORDS, k=word_count)).capitalize() + "."


async def seed_report_test_data(db: AsyncSession) -> None:
    reporter_id = (
        await db.execute(select(User.id).limit(1))
    ).scalar_one_or_none()
    if not reporter_id:
        print(
            "未找到任何用户，无法创建举报测试数据。请先运行 init_admin_user（例如 ./backend/inty/start.sh --dev 已包含）。"
        )
        sys.exit(1)

    report = Report(
        id=get_new_report_id(),
        target_id="agent-test-target",
        target_type="AGENT",
        reporter_id=reporter_id,
        reason_ids=None,
        reason_codes=[random.choice(REPORT_REASON_CODES).value],
        image_urls=[],
        description=_random_sentence(10),
        status=ReportStatus.PENDING,
        report_type=ReportType.REPORT,
    )
    db.add(report)
    await db.commit()
    print("已插入一条举报测试数据。")
    print(f"  ID: {report.id}")
    print(f"  描述: {report.description}")


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed_report_test_data(db)


if __name__ == "__main__":
    asyncio.run(main())
