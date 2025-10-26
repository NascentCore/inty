from typing import List

from sqlalchemy import and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.uuid import get_new_report_id
from app.models.report import Report, ReportReason
from app.schemas.report import ReportCreate, ReportQuery


async def list_report_reasons(db: AsyncSession) -> List[ReportReason]:
    stmt = select(ReportReason).where(ReportReason.is_active == True)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_report(
    db: AsyncSession, report_in: ReportCreate, reporter_id: str
) -> Report:
    report_id = get_new_report_id()
    report = Report(
        id=report_id,
        target_id=report_in.target_id,
        target_type=report_in.target_type,
        reporter_id=reporter_id,
        reason_ids=report_in.reason_ids,
        image_urls=report_in.image_urls or [],
        description=report_in.description,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def query_reports(db: AsyncSession, query: ReportQuery):
    filters = []
    if query.reason_ids:
        filters.append(Report.reason_ids.overlap(query.reason_ids))
    if query.target_id:
        filters.append(Report.target_id == query.target_id)
    if query.target_type:
        filters.append(Report.target_type == query.target_type)
    if query.status:
        filters.append(Report.status == query.status)
    if query.reporter_id:
        filters.append(Report.reporter_id == query.reporter_id)
# 查询总数
    count_stmt = select(func.count()).select_from(Report).where(and_(*filters))
    total = (await db.execute(count_stmt)).scalar_one()
# 查询分页数据
    stmt = select(Report).where(and_(*filters)).offset(query.skip).limit(query.limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
# Reason_ids 转 Reason_codes
    all_reason_ids = set()
    for item in items:
        all_reason_ids.update(item.reason_ids)
    reason_map = {}
    if all_reason_ids:
        reason_stmt = select(ReportReason).where(ReportReason.id.in_(all_reason_ids))
        reason_result = await db.execute(reason_stmt)
        reason_map = {r.id: r.code for r in reason_result.scalars().all()}
    for item in items:
        item.reason_codes = [reason_map.get(rid, "") for rid in item.reason_ids]

    return items, total
