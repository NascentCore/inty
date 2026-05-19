from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.tags import INTERNAL_API_TAG, WEB_APP_TAG, NOT_USED_TAG
from app.api.utils.logger_route import LoggerRoute
from app.models.notification import TEMPLATE_TYPE_MAP
from app.schemas.notification import (
    NotificationItem,
    NotificationList,
    NotificationQuery,
    NotificationSendRequest,
    NotificationTemplateCreate,
    NotificationTemplateItem,
)
from app.schemas.response import APIResponse, PaginationData
from app.services import notification_service

router = APIRouter(prefix="/notifications", route_class=LoggerRoute)


@router.post(
    "/",
    response_model=APIResponse,
    include_in_schema=False,
    tags=[INTERNAL_API_TAG, NOT_USED_TAG],
)
async def send_notification(
    request: NotificationSendRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user=Depends(deps.get_current_superuser),
) -> APIResponse[Dict[str, int]]:
    """
    发送通知
    - 支持指定用户发送或全员发送
    - 支持动态参数替换模板内容
    """
    try:
        await notification_service.send_notification(
            db, background_tasks, request
        )
        return APIResponse.success(message="Notification sent successfully")
    except ValueError as e:
        logger.error(f"发送通知参数错误: {str(e)}")
        return APIResponse.error(message=str(e))
    except Exception as e:
        logger.error(f"发送通知失败: {str(e)}")
        return APIResponse.error(
            message="Failed to send notification, please try again later"
        )


@router.get(
    "/",
    response_model=APIResponse[NotificationList],
    tags=[WEB_APP_TAG, NOT_USED_TAG],
)
async def list_notifications(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user=Depends(deps.get_current_active_user),
    page: int = 1,
    page_size: int = 20,
    is_read: Optional[bool] = Query(
        None, description="是否已读，不传则查询全部"
    ),
) -> APIResponse[NotificationList]:
    """
    分页查询用户的消息列表；返回用户收到的通知。
    """
    try:
        # 创建查询参数
        query = NotificationQuery(
            user_id=current_user.id,
            is_read=is_read,
            skip=(page - 1) * page_size,
            limit=page_size,
        )

        # 查询数据
        items, total = await notification_service.query_notifications(db, query)

        # 转换为响应格式
        items = [
            NotificationItem.model_validate(obj, from_attributes=True)
            for obj in items
        ]

        # 计算总页数
        total_pages = (total + page_size - 1) // page_size if page_size else 1

        # 构建分页响应
        pagination = NotificationList(
            list=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

        return APIResponse.success(data=pagination)
    except Exception as e:
        logger.error(f"查询通知列表失败: {str(e)}")
        return APIResponse.error(message=str(e))


@router.get(
    "/templates/types",
    response_model=APIResponse[Dict[str, int]],
    include_in_schema=False,
    tags=[INTERNAL_API_TAG, NOT_USED_TAG],
)
async def get_template_types(
    current_user=Depends(deps.get_current_superuser),
) -> APIResponse[Dict[str, int]]:
    """
    获取通知模板类型映射关系
    """
    try:
        return APIResponse.success(data=TEMPLATE_TYPE_MAP)
    except Exception as e:
        logger.error(f"获取通知模板类型映射失败: {str(e)}")
        return APIResponse.error(
            message="Failed to get notification template type mapping"
        )


@router.post(
    "/templates",
    response_model=APIResponse[NotificationTemplateItem],
    include_in_schema=False,
    tags=[INTERNAL_API_TAG, NOT_USED_TAG],
)
async def create_notification_template(
    template_data: NotificationTemplateCreate,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user=Depends(deps.get_current_superuser),
) -> APIResponse[NotificationTemplateItem]:
    """
    创建通知模板
    """
    try:

        template = await notification_service.create_notification_template(
            db, template_data
        )
        return APIResponse.success(
            data=NotificationTemplateItem.model_validate(
                template, from_attributes=True
            )
        )
    except ValueError as e:
        logger.error(f"创建通知模板参数错误: {str(e)}")
        return APIResponse.error(message=str(e))
    except Exception as e:
        logger.error(f"创建通知模板失败: {str(e)}")
        return APIResponse.error(
            message="Failed to create notification template, please try again later"
        )


@router.get(
    "/templates",
    response_model=APIResponse[PaginationData[NotificationTemplateItem]],
    include_in_schema=False,
    tags=[INTERNAL_API_TAG, NOT_USED_TAG],
)
async def list_templates(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user=Depends(deps.get_current_superuser),
    page: int = 1,
    page_size: int = 20,
    is_active: Optional[bool] = Query(
        None, description="是否激活，不传则查询全部"
    ),
) -> APIResponse[PaginationData[NotificationTemplateItem]]:
    """
    分页查询通知模板列表
    """
    try:
        # 查询数据
        items, total = await notification_service.query_templates(
            db,
            skip=(page - 1) * page_size,
            limit=page_size,
            is_active=is_active,
        )

        # 转换为响应格式
        items = [
            NotificationTemplateItem.model_validate(obj, from_attributes=True)
            for obj in items
        ]

        # 计算总页数
        total_pages = (total + page_size - 1) // page_size if page_size else 1

        # 构建分页响应
        pagination = PaginationData[NotificationTemplateItem](
            list=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

        return APIResponse.success(data=pagination)
    except Exception as e:
        logger.error(f"查询通知模板列表失败: {str(e)}")
        return APIResponse.error(
            message="Failed to query notification template list"
        )
