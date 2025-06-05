from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.report import ReportStatus
from app.schemas.report import ReportReason, ReportCreate, ReportQuery, ReportOut, TargetType
from app.services import report_service
from app.db.session import get_async_db
from app.models.user import User
from app.schemas.response import APIResponse, PaginationData
from loguru import logger

router = APIRouter()

@router.get("/reasons", response_model=APIResponse[List[ReportReason]])
async def get_report_reasons(
    db: AsyncSession = Depends(get_async_db)
):
    """举报原因列表"""
    try:
        reasons = await report_service.list_report_reasons(db)
        return APIResponse.success(data=reasons)
    except Exception as e:
        logger.error(f"获取举报原因失败: {str(e)}")
        return APIResponse.error(message=str(e))

@router.post("/", response_model=APIResponse)
async def create_report(
    report_in: ReportCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """提交举报"""
    try:
        report = await report_service.create_report(db, report_in, current_user.id)
        return APIResponse.success()
    except Exception as e:
        logger.error(f"创建举报失败: {str(e)}")
        return APIResponse.error(message=str(e))

@router.get("/", response_model=APIResponse[PaginationData[ReportOut]])
async def list_reports(
    reason_ids: Optional[List[int]] = Query(None),
    target_id: Optional[str] = None,
    target_type: Optional[TargetType] = None,
    status: Optional[ReportStatus] = None,
    reporter_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """举报记录查询（需管理员权限）"""
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")
    try:
        skip = (page - 1) * page_size
        query = ReportQuery(
            reason_ids=reason_ids,
            target_id=target_id,
            target_type=target_type,
            status=status,
            reporter_id=reporter_id,
            skip=skip,
            limit=page_size
        )
        items, total = await report_service.query_reports(db, query)
        items = [ReportOut.model_validate(obj, from_attributes=True) for obj in items]
        total_pages = (total + page_size - 1) // page_size if page_size else 1
        pagination = PaginationData[ReportOut](
            list=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        return APIResponse.success(data=pagination)
    except Exception as e:
        logger.error(f"举报查询失败: {str(e)}")
        return APIResponse.error(message=str(e)) 