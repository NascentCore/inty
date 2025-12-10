from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.tags import NOT_USED_TAG, WEB_APP_TAG
from app.api.utils.logger_route import LoggerRoute
from app.db.session import get_async_db
from app.models.user import User
from app.schemas.report import ReportCreate
from app.schemas.response import APIResponse
from app.services import report_service

router = APIRouter(prefix="/report", route_class=LoggerRoute)


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
