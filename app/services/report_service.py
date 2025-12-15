from typing import List

from sqlalchemy import and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.uuid import get_new_report_id
from app.models.report import (
    FEEDBACK_REASON_ID_TO_CODE,
    REASON_ID_TO_CODE,
    Report,
    ReportType,
)
from app.schemas.report import ReportCreate, ReportQuery, ReportReason


def list_report_reasons() -> List[ReportReason]:
    """返回硬编码的举报原因列表（不再从数据库查询）"""
    return [
        ReportReason(
            id=id,
            code=code,
            description=None,
            is_active=True,
        )
        for id, code in REASON_ID_TO_CODE.items()
    ]


async def create_report(
    db: AsyncSession, report_in: ReportCreate, reporter_id: str
) -> Report:
    report_id = get_new_report_id()

    # 处理 reason_codes 和向后兼容的 reason_ids
    reason_codes = report_in.reason_codes
    reason_ids = []

    # 如果提供了 reason_ids（向后兼容），转换为 reason_codes
    if report_in.reason_ids:
        # 根据 report_type 选择使用哪个映射
        # 如果 report_type 为 None，默认为 REPORT
        is_feedback = report_in.report_type == ReportType.FEEDBACK
        id_to_code_map = (
            FEEDBACK_REASON_ID_TO_CODE if is_feedback else REASON_ID_TO_CODE
        )

        # 使用硬编码的映射关系转换
        if not reason_codes:
            # 验证所有 reason_ids 都存在，如果不存在则抛出错误
            missing_ids = [
                rid for rid in report_in.reason_ids if rid not in id_to_code_map
            ]
            if missing_ids:
                raise ValueError(
                    f"Invalid reason_ids: {missing_ids}. These reason IDs do not exist."
                )
            # id_to_code_map 返回的是字符串，需要转换为枚举
            from app.schemas.report import ReasonCode

            reason_codes = [
                ReasonCode(id_to_code_map[rid]) for rid in report_in.reason_ids
            ]
        # 为了向后兼容，仍然保存 reason_ids
        reason_ids = report_in.reason_ids

    # 验证至少提供了 reason_codes 或 reason_ids，且 reason_codes 包含至少一个非空值
    if not reason_codes or not any(reason_codes):
        raise ValueError(
            "Either reason_codes or reason_ids must be provided, and reason_codes must contain at least one non-empty value"
        )

    # 将枚举值转换为字符串（如果 reason_codes 是枚举列表）
    # 用于存储到数据库（数据库字段是 ARRAY(String)）
    if reason_codes:
        reason_codes_str = [
            code.value if hasattr(code, "value") else str(code) for code in reason_codes
        ]
    else:
        reason_codes_str = []

    # 如果 report_type 为 None，则存储为 None（数据库为 NULL），业务逻辑中视为 REPORT
    report = Report(
        id=report_id,
        target_id=report_in.target_id,
        target_type=report_in.target_type,
        reporter_id=reporter_id,
        reason_ids=reason_ids or [],  # 向后兼容，如果只有 reason_codes 则为空列表
        reason_codes=reason_codes_str,
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
    # DEPRECATED: 支持通过 reason_ids 查询（向后兼容）
    if query.reason_ids:
        filters.append(Report.reason_ids.overlap(query.reason_ids))
    # 支持通过 reason_codes 查询
    if query.reason_codes:
        # 将枚举值转换为字符串（如果 reason_codes 是枚举列表）
        reason_codes_str = [
            code.value if hasattr(code, "value") else code
            for code in query.reason_codes
        ]
        filters.append(Report.reason_codes.overlap(reason_codes_str))
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

    # 构建排序
    order_clause = Report.created_at.desc()  # 默认按创建时间降序
    if query.order_by == "created_at_asc":
        order_clause = Report.created_at.asc()

    # 查询分页数据
    stmt = (
        select(Report)
        .where(and_(*filters))
        .order_by(order_clause)
        .offset(query.skip)
        .limit(query.limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    # 确保 reason_codes 存在（向后兼容：如果只有 reason_ids，转换为 reason_codes）
    for item in items:
        # 如果 reason_codes 为空但 reason_ids 存在，从 reason_ids 转换
        if not item.reason_codes and item.reason_ids:
            # 根据 report_type 选择使用哪个映射
            # 如果 report_type 为 None，默认为 REPORT
            is_feedback = item.report_type == ReportType.FEEDBACK
            id_to_code_map = (
                FEEDBACK_REASON_ID_TO_CODE if is_feedback else REASON_ID_TO_CODE
            )
            # 使用硬编码的映射关系转换，只转换存在的 ID
            converted_codes = [
                id_to_code_map[rid] for rid in item.reason_ids if rid in id_to_code_map
            ]
            item.reason_codes = converted_codes if converted_codes else []

    # 确保所有字段在序列化前都是正确的类型（处理 None 值）
    for item in items:
        # 确保 reason_ids 是列表（不能是 None）
        if item.reason_ids is None:
            item.reason_ids = []
        # 确保 reason_codes 是列表（不能是 None）
        if item.reason_codes is None:
            item.reason_codes = []
        # 如果 report_type 为 None，在序列化时视为 "REPORT"
        if item.report_type is None:
            item.report_type = ReportType.REPORT

    return items, total
