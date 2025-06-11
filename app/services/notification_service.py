from typing import Optional, List, Tuple
from app.models.user import User
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import UserNotification, NotificationTemplate, NotificationTemplateType
from app.schemas.notification import NotificationQuery, NotificationTemplateCreate, NotificationSendRequest
from loguru import logger
from datetime import datetime, UTC
from app.core.uuid import uid
from jinja2 import Template
from jinja2.exceptions import TemplateError
from firebase_admin import messaging
from app.services import user_service
from app.models.user import DeviceToken
import traceback
from fastapi import BackgroundTasks
from firebase_admin.exceptions import InvalidArgumentError

# 类型映射字典
TEMPLATE_TYPE_MAP = {
    NotificationTemplateType.TEXT_WITH_LINK: 1,
    NotificationTemplateType.IMAGE_WITH_LINK: 2,
    NotificationTemplateType.TEXT_ONLY: 3,
    NotificationTemplateType.IMAGE_ONLY: 4,
    NotificationTemplateType.IMAGE_TEXT_LINK: 5,
}

# 反向映射字典
TEMPLATE_TYPE_REVERSE_MAP = {v: k for k, v in TEMPLATE_TYPE_MAP.items()}

async def create_notification_template(
    db: AsyncSession,
    template_data: NotificationTemplateCreate
) -> NotificationTemplate:
    """
    创建通知模板
    """
    template = NotificationTemplate(
        type=template_data.type,
        title=template_data.title,
        content=template_data.content,
        image_urls=template_data.image_urls,
        link_urls=template_data.link_urls,
        is_active=template_data.is_active
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template

async def query_templates(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    is_active: Optional[bool] = None
) -> Tuple[List[NotificationTemplate], int]:
    """
    分页查询通知模板列表
    """
    # 构建基础查询
    stmt = select(NotificationTemplate)
    
    # 添加过滤条件
    if is_active is not None:
        stmt = stmt.where(NotificationTemplate.is_active == is_active)
    
    # 按创建时间倒序排序
    stmt = stmt.order_by(NotificationTemplate.created_at.desc())
    
    # 获取总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)
    
    # 添加分页
    stmt = stmt.offset(skip).limit(limit)
    
    # 执行查询
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return items, total

async def query_notifications(
    db: AsyncSession,
    query: NotificationQuery
) -> Tuple[List[UserNotification], int]:
    """
    查询用户通知列表
    """
    # 构建基础查询
    stmt = select(UserNotification).filter(
        UserNotification.user_id == query.user_id,
        UserNotification.deleted_at.is_(None)
    )
    
    # 添加过滤条件
    if query.is_read is not None:
        stmt = stmt.where(UserNotification.is_read == query.is_read)
    
    # 按创建时间倒序排序
    stmt = stmt.order_by(UserNotification.created_at.desc())
    
    # 获取总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)
    
    # 添加分页
    stmt = stmt.offset(query.skip).limit(query.limit)
    
    # 执行查询
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return items, total

async def send_notification(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    request: NotificationSendRequest
) -> None:
    """
    发送通知
    """
    try:
        # 1. 获取模板
        template = await db.get(NotificationTemplate, request.template_id)
        if not template:
            raise ValueError(f"通知模板不存在: {request.template_id}")
        if not template.is_active:
            raise ValueError(f"通知模板已禁用: {request.template_id}")

        # 2. 获取接收用户列表
        if request.all_users:
            # 全员发送，这里需要根据实际情况查询所有用户
            stmt = select(User.id).where(User.is_active == True)
            result = await db.execute(stmt)
            user_ids = [row[0] for row in result.all()]
        else:
            if not request.user_ids:
                raise ValueError("接收用户列表为空")
            # 指定用户发送
            user_ids = request.user_ids

        # 3. 渲染模板内容
        try:
            # 渲染标题
            title_template = Template(template.title)
            rendered_title = title_template.render(**request.params)
            
            # 渲染内容
            content_template = Template(template.content)
            rendered_content = content_template.render(**request.params)
            
            # 渲染图片URL
            rendered_image_urls = []
            if template.image_urls:
                for image_url in template.image_urls:
                    rendered_image_url = Template(image_url).render(**request.params)
                    rendered_image_urls.append(rendered_image_url)
            
            # 渲染链接URL
            rendered_link_urls = []
            if template.link_urls:
                for link_url in template.link_urls:
                    rendered_link_url = Template(link_url).render(**request.params)
                    rendered_link_urls.append(rendered_link_url)
                    
        except Exception as e:
            logger.error(f"模板渲染失败: {str(e)}")
            raise ValueError(f"模板渲染失败: {str(e)}")

        # 4. 生成通知
        notifications = []

        for user_id in user_ids:
            try:
                # 生成通知ID
                notification_id = uid("notify")
                
                # 创建通知记录
                notification = UserNotification(
                    id=notification_id,
                    user_id=user_id,
                    template_id=template.id,
                    type=int(template.type),  # 确保 type 是整数类型
                    dynamic_params=request.params,
                    title=rendered_title,
                    content=rendered_content,
                    image_urls=rendered_image_urls,
                    link_urls=rendered_link_urls,
                    is_read=True, # 默认已读
                    read_at=datetime.now()
                )
                notifications.append(notification)
            except Exception as e:
                logger.error(f"为用户 {user_id} 创建通知失败: {str(e)}")

        # 5. 批量保存通知
        if notifications:
            db.add_all(notifications)
            await db.commit()

        # 6. 异步发送FCM消息（后台任务）
        background_tasks.add_task(
            send_fcm_multicast,
            db,
            user_ids,
            rendered_title,
            rendered_content,
            request.params,
            rendered_image_urls[0] if rendered_image_urls else None
        )

    except Exception as e:
        logger.error(f"发送通知失败: {str(e)}")
        raise 

INVALID_EXCEPTIONS = (
    messaging.UnregisteredError,
    InvalidArgumentError,
    messaging.SenderIdMismatchError,
)

async def send_fcm_multicast(
    db: AsyncSession,
    user_ids: List[str],
    title: str,
    body: str,
    data: Optional[dict] = None,
    image_url: Optional[str] = None
) -> bool:
    """发送FCM多播消息推送
    
    适用于多用户同一条通知
    
    Args:
        db: 数据库会话
        user_ids: 用户ID列表
        title: 通知标题
        body: 通知内容
        data: 额外数据（可选）
        image_url: 图片URL（可选）
        
    Returns:
        bool: 是否发送成功
    """
    try:
        # 1. 获取多个用户的所有设备token
        tokens = await user_service.get_users_device_tokens(db, user_ids)
        
        if not tokens:
            logger.warning(f"用户 {user_ids} 没有注册任何设备token")
            return False
        
        # 2. 发送消息
        success_count = 0
        fail_count = 0
        invalid_tokens = []
        
        for token in tokens:
            try:
                single_message = messaging.Message(
                    token=token,
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                        image=image_url
                    ),
                    data=data or {}
                )
                messaging.send(single_message)
                success_count += 1
            except INVALID_EXCEPTIONS:
                invalid_tokens.append(token)
                fail_count += 1
            except Exception as e:
                logger.error(f"发送到设备 {token} 失败: {str(e)}")
                fail_count += 1
                
        # 3. 处理结果
        if fail_count > 0:
            logger.error(f"FCM消息发送失败: {fail_count} 个设备失败")
            

        # 4. 清理失效的token
        if invalid_tokens:
            try:
                await db.execute(
                    delete(DeviceToken).where(DeviceToken.token.in_(invalid_tokens))
                )
                await db.commit()
                logger.info(f"已清理 {len(invalid_tokens)} 个失效的token")
            except Exception as e:
                logger.error(f"清理失效token失败: {str(e)}")
                logger.error(f"错误堆栈: {traceback.format_exc()}")
            
            return False
            
        logger.info(f"FCM消息发送成功: {success_count} 个设备")
        return True
        
    except Exception as e:
        logger.error(f"发送FCM消息失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False 

