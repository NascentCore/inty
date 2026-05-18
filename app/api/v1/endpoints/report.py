from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.tags import NOT_USED_TAG, WEB_APP_TAG
from app.api.utils.logger_route import LoggerRoute
from app.db.session import get_async_db
from app.models.report import ReportStatus, ReportType
from app.models.user import User
from app.schemas.report import (
    ReportCreate,
    ReportConversationGroups,
    ReportConversationMessages,
    ReportGithubIssueUpdate,
    ReportOut,
    ReportQuery,
    ReportsList,
    TargetType,
)
from app.schemas.response import APIResponse
from app.services import report_service

router = APIRouter(prefix="/report", route_class=LoggerRoute)


@router.get("/", response_model=ReportsList, tags=[WEB_APP_TAG])
async def list_reports(
    target_type: Optional[TargetType] = None,
    target_id: Optional[str] = None,
    status: Optional[ReportStatus] = None,
    report_type: Optional[ReportType] = None,
    order_by: Optional[str] = "created_at_desc",
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_superuser),
):
    """查询 Report/Feedback 列表，支持按创建时间排序（order_by: created_at_desc 或 created_at_asc）"""
    query = ReportQuery(
        target_type=target_type,
        target_id=target_id,
        status=status,
        report_type=report_type,
        order_by=order_by,
        skip=skip,
        limit=limit,
    )
    items, total = await report_service.query_reports(db, query)
    return ReportsList(items=items, total=total)


@router.get("/{report_id}", response_model=ReportOut, tags=[WEB_APP_TAG])
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_superuser),
):
    """按 id 获取单条举报详情（用于永久链接打开）。"""
    report = await report_service.get_report(db, report_id)
    return ReportOut.model_validate(report)


@router.get(
    "/{report_id}/conversation-groups",
    response_model=ReportConversationGroups,
    tags=[WEB_APP_TAG],
)
async def get_report_conversation_groups(
    report_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_superuser),
):
    """获取举报人全部聊天记录的 user_id:agent_id 分组列表。"""
    try:
        report = await report_service.get_report(db, report_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    items = await report_service.get_report_conversation_groups(
        db, report.reporter_id
    )
    return ReportConversationGroups(items=items, total=len(items))


@router.get(
    "/{report_id}/conversation-messages",
    response_model=ReportConversationMessages,
    tags=[WEB_APP_TAG],
)
async def get_report_conversation_messages(
    report_id: str,
    user_id: str = Query(..., description="User ID from group key"),
    agent_id: str = Query(..., description="Agent ID from group key"),
    page: int = Query(1, ge=1, description="Round-based page number"),
    size: int = Query(20, ge=1, le=100, description="Rounds per page"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_superuser),
):
    """按轮次分页加载某个 user_id:agent_id 分组的聊天消息（默认每页 20 轮）。"""
    try:
        report = await report_service.get_report(db, report_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if user_id != report.reporter_id:
        raise HTTPException(
            status_code=400,
            detail="user_id must match report reporter_id",
        )

    data = await report_service.get_report_conversation_messages(
        db,
        user_id=user_id,
        agent_id=agent_id,
        page=page,
        size=size,
    )
    return ReportConversationMessages.model_validate(data)


@router.put(
    "/{report_id}/github-issue", response_model=ReportOut, tags=[WEB_APP_TAG]
)
async def update_report_github_issue(
    report_id: str,
    payload: ReportGithubIssueUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_superuser),
):
    """更新举报记录关联的 GitHub issue URL。"""
    try:
        report = await report_service.update_report_github_issue(
            db, report_id, payload.github_issue
        )
    except ValueError as exc:
        error_message = str(exc)
        if error_message == "Report not found":
            raise HTTPException(status_code=404, detail=error_message) from exc
        raise HTTPException(status_code=400, detail=error_message) from exc
    return ReportOut.model_validate(report)


@router.post("/", response_model=APIResponse, tags=[WEB_APP_TAG, NOT_USED_TAG])
async def create_report(
    report_in: ReportCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """提交举报或反馈，任意已登录用户可调用"""
    try:
        report = await report_service.create_report(
            db, report_in, current_user.id
        )
        return APIResponse.success()
    except Exception as e:
        logger.error(f"Failed to create report: {str(e)}")
        return APIResponse.error(message=str(e))


@router.delete("/{report_id}", response_model=APIResponse, tags=[WEB_APP_TAG])
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_superuser),
):
    try:
        await report_service.delete_report(
            db,
            report_id,
            current_user_id=current_user.id,
            is_superuser=current_user.is_superuser,
        )
        return APIResponse.success()
    except PermissionError:
        return APIResponse.error(
            message="Not authorized to delete this record", code=403
        )
    except ValueError:
        return APIResponse.error(message="Record not found", code=404)
    except SQLAlchemyError as e:
        logger.error(f"Failed to delete report: {str(e)}")
        return APIResponse.error(message="Delete failed", code=500)
