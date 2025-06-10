from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.notification import UserNotification, NotificationTemplateType, TEMPLATE_TYPE_MAP
from app.schemas.notification import (
    NotificationItem, 
    NotificationQuery,
    NotificationSendResponse,
    NotificationTemplateCreate,
    NotificationTemplateItem,
    NotificationSendRequest
)
from app.schemas.response import APIResponse, PaginationData
from app.services import notification_service
from loguru import logger

router = APIRouter()

@router.post("/", response_model=APIResponse[NotificationSendResponse])
async def send_notification(
    request: NotificationSendRequest,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user = Depends(deps.get_current_active_user),
) -> APIResponse[Dict[str, int]]:
    """
    发送通知
    - 支持指定用户发送或全员发送
    - 支持动态参数替换模板内容
    """
    try:
        if not current_user.is_superuser:
            logger.error("非超级管理员不能发送通知")
            return APIResponse.error(message="非超级管理员不能发送通知")
            
        success_count, fail_count = await notification_service.send_notification(db, request)
        return APIResponse.success(data={
            "success_count": success_count,
            "fail_count": fail_count
        })
    except ValueError as e:
        logger.error(f"发送通知参数错误: {str(e)}")
        return APIResponse.error(message=str(e))
    except Exception as e:
        logger.error(f"发送通知失败: {str(e)}")
        return APIResponse.error(message="发送通知失败，请稍后重试")


@router.get("/", response_model=APIResponse[PaginationData[NotificationItem]])
async def list_notifications(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user = Depends(deps.get_current_active_user),
    page: int = 1,
    page_size: int = 20,
    is_read: Optional[bool] = Query(None, description="是否已读，不传则查询全部"),
) -> APIResponse[PaginationData[NotificationItem]]:
    """
    分页查询用户的消息列表
    """
    try:
        # 创建查询参数
        query = NotificationQuery(
            user_id=current_user.id,
            is_read=is_read,
            skip=(page - 1) * page_size,
            limit=page_size
        )
        
        # 查询数据
        items, total = await notification_service.query_notifications(db, query)
        
        # 转换为响应格式
        items = [NotificationItem.model_validate(obj, from_attributes=True) for obj in items]
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size if page_size else 1
        
        # 构建分页响应
        pagination = PaginationData[NotificationItem](
            list=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
        return APIResponse.success(data=pagination)
    except Exception as e:
        logger.error(f"查询通知列表失败: {str(e)}")
        return APIResponse.error(message=str(e))


@router.get("/templates/types", response_model=APIResponse[Dict[str, int]])
async def get_template_types() -> APIResponse[Dict[str, int]]:
    """
    获取通知模板类型映射关系
    """
    try:
        return APIResponse.success(data=TEMPLATE_TYPE_MAP)
    except Exception as e:
        logger.error(f"获取通知模板类型映射失败: {str(e)}")
        return APIResponse.error(message="获取通知模板类型映射失败")


@router.post("/templates", response_model=APIResponse[NotificationTemplateItem])
async def create_notification_template(
    template_data: NotificationTemplateCreate,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user = Depends(deps.get_current_active_user),
) -> APIResponse[NotificationTemplateItem]:
    """
    创建通知模板
    """
    try:
        if not current_user.is_superuser:
            logger.error("非超级管理员不能创建通知模板")
            return APIResponse.error(message="非超级管理员不能创建通知模板")
            
        template = await notification_service.create_notification_template(db, template_data)
        return APIResponse.success(data=NotificationTemplateItem.model_validate(template, from_attributes=True))
    except ValueError as e:
        logger.error(f"创建通知模板参数错误: {str(e)}")
        return APIResponse.error(message=str(e))
    except Exception as e:
        logger.error(f"创建通知模板失败: {str(e)}")
        return APIResponse.error(message="创建通知模板失败，请稍后重试")


@router.get("/templates", response_model=APIResponse[PaginationData[NotificationTemplateItem]])
async def list_templates(
    db: AsyncSession = Depends(deps.get_async_db),
    current_user = Depends(deps.get_current_active_user),
    page: int = 1,
    page_size: int = 20,
    is_active: Optional[bool] = Query(None, description="是否激活，不传则查询全部"),
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
            is_active=is_active
        )
        
        # 转换为响应格式
        items = [NotificationTemplateItem.model_validate(obj, from_attributes=True) for obj in items]
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size if page_size else 1
        
        # 构建分页响应
        pagination = PaginationData[NotificationTemplateItem](
            list=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
        return APIResponse.success(data=pagination)
    except Exception as e:
        logger.error(f"查询通知模板列表失败: {str(e)}")
        return APIResponse.error(message="查询通知模板列表失败")


