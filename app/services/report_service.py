from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.report_reasons import (
    FEEDBACK_REASON_ID_TO_CODE,
    REPORT_REASON_ID_TO_CODE,
)
from app.core.uuid import get_new_report_id
from app.models.report import Report, ReportType
from app.schemas.report import ReportCreate, ReportQuery


def _normalized_reason_codes(
    reason_codes: Optional[List[str]],
    reason_ids: Optional[List[int]],
    report_type: Optional[ReportType],
    *,
    require: bool,
) -> List[str]:
    """将各种形式的举报原因转换为字符串代码列表。"""

    normalized: List[str] = []
    if reason_codes:
        seen = set()
        for raw in reason_codes:
            if raw is None:
                continue
            code = raw.strip().upper()
            if not code or code in seen:
                continue
            normalized.append(code)
            seen.add(code)
        if normalized:
            return normalized

    if reason_ids:
        mapping = (
            FEEDBACK_REASON_ID_TO_CODE
            if report_type == ReportType.FEEDBACK
            else REPORT_REASON_ID_TO_CODE
        )
        converted: List[str] = []
        missing_ids: List[str] = []
        seen = set()
        for rid in reason_ids:
            code = mapping.get(rid)
            if code is None:
                missing_ids.append(str(rid))
                continue
            if code in seen:
                continue
            seen.add(code)
            converted.append(code)

        if missing_ids:
            raise ValueError(f"未知的 reason_id: {', '.join(missing_ids)}")

        if converted:
            return converted

    if require:
        raise ValueError("reason_codes 至少需要包含一项")

    return []


async def create_report(
    db: AsyncSession, report_in: ReportCreate, reporter_id: str
) -> Report:
    report_id = get_new_report_id()
    resolved_reason_codes = _normalized_reason_codes(
        report_in.reason_codes, report_in.reason_ids, report_in.report_type, require=True
    )
    # 如果 report_type 为 None，则存储为 None（数据库为 NULL），业务逻辑中视为 REPORT
    report = Report(
        id=report_id,
        target_id=report_in.target_id,
        target_type=report_in.target_type,
        reporter_id=reporter_id,
        reason_codes=resolved_reason_codes,
        image_urls=report_in.image_urls or [],
        description=report_in.description,
        report_type=report_in.report_type,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def query_reports(db: AsyncSession, query: ReportQuery):
    filters = []
    normalized_reason_codes = _normalized_reason_codes(
        query.reason_codes, query.reason_ids, query.report_type, require=False
    )
    if normalized_reason_codes:
        filters.append(Report.reason_codes.overlap(normalized_reason_codes))
    if query.target_id:
        filters.append(Report.target_id == query.target_id)
    if query.target_type:
        filters.append(Report.target_type == query.target_type)
    if query.status:
        filters.append(Report.status == query.status)
    if query.reporter_id:
        filters.append(Report.reporter_id == query.reporter_id)
    if query.report_type:
        # 如果查询 REPORT，需要包含 report_type 为 NULL 的记录（NULL 视为 REPORT）
        if query.report_type == ReportType.REPORT:
            filters.append(
                (Report.report_type == ReportType.REPORT)
                | (Report.report_type.is_(None))
            )
        else:
            filters.append(Report.report_type == query.report_type)

    # 查询总数
    count_stmt = select(func.count()).select_from(Report).where(and_(*filters))
    total = (await db.execute(count_stmt)).scalar_one()

    # 查询分页数据
    stmt = select(Report).where(and_(*filters)).offset(query.skip).limit(query.limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    for item in items:
        # 如果 report_type 为 None，在序列化时视为 "REPORT"
        if item.report_type is None:
            item.report_type = ReportType.REPORT

    return items, total
