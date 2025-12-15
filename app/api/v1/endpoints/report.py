from typing import Optional

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.tags import NOT_USED_TAG, WEB_APP_TAG
from app.api.utils.logger_route import LoggerRoute
from app.db.session import get_async_db
from app.models.report import ReportStatus, ReportType
from app.models.user import User
from app.schemas.report import ReportCreate, ReportQuery, ReportsList, TargetType
from app.schemas.response import APIResponse
from app.services import report_service

router = APIRouter(prefix="/report", route_class=LoggerRoute)


@router.get("/", response_model=ReportsList, tags=[WEB_APP_TAG])
async def list_reports(
    target_type: Optional[TargetType] = None,
    status: Optional[ReportStatus] = None,
    report_type: Optional[ReportType] = None,
    order_by: Optional[str] = "created_at_desc",
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """查询 Report/Feedback 列表，支持按创建时间排序（order_by: created_at_desc 或 created_at_asc）"""
    query = ReportQuery(
        target_type=target_type,
        status=status,
        report_type=report_type,
        order_by=order_by,
        skip=skip,
        limit=limit,
    )
    items, total = await report_service.query_reports(db, query)
    return ReportsList(items=items, total=total)


@router.post("/", response_model=APIResponse, tags=[WEB_APP_TAG, NOT_USED_TAG])
async def create_report(
    report_in: ReportCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Submit report"""
    try:
        report = await report_service.create_report(db, report_in, current_user.id)
        return APIResponse.success()
    except Exception as e:
        logger.error(f"Failed to create report: {str(e)}")
        return APIResponse.error(message=str(e))
