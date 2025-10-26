import traceback
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import BackgroundTasks
from firebase_admin import messaging
from firebase_admin.exceptions import InvalidArgumentError
from jinja2 import Template
from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.uuid import uid
from app.models.notification import (
    NotificationTemplate,
    NotificationTemplateType,
    UserNotification,
)
from app.models.user import DeviceToken, User
from app.schemas.notification import (
    NotificationQuery,
    NotificationSendRequest,
    NotificationTemplateCreate,
)
from app.services import user_service
# 类型映射字典
TEMPLATE_TYPE_MAP = {
    NotificationTemplateType.TEXT_WITH_LINK: 1,
    NotificationTemplateType.IMAGE_WITH_LINK: 2,
    NotificationTemplateType.TEXT_ONLY: 3,
    NotificationTemplateType.IMAGE_ONLY: 4,
    NotificationTemplateType.IMAGE_TEXT_LINK: 5,
}
#逆向地图字典
TEMPLATE_TYPE_REVERSE_MAP = {v: k for k, v in TEMPLATE_TYPE_MAP.items()}


async def create_notification_template(
    db: AsyncSession, template_data: NotificationTemplateCreate
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
        is_active=template_data.is_active,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def query_templates(
    db: AsyncSession, skip: int = 0, limit: int = 20, is_active: Optional[bool] = None
) -> Tuple[List[NotificationTemplate], int]:
    """
    分页查询通知模板列表
    """
# 构建基础查询
    stmt = select(NotificationTemplate)
#添加过滤条件
    if is_active is not None:
        stmt = stmt.where(NotificationTemplate.is_active == is_active)
# 按创建时间倒序排序
    stmt = stmt.order_by(NotificationTemplate.created_at.desc())
# 获取总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)
#添加分页
    stmt = stmt.offset(skip).limit(limit)
# 执行查询
    result = await db.execute(stmt)
    items = result.scalars().all()

    return items, total


async def query_notifications(
    db: AsyncSession, query: NotificationQuery
) -> Tuple[List[UserNotification], int]:
    """
    查询用户通知列表
    """
# 构建基础查询
    stmt = select(UserNotification).filter(
        UserNotification.user_id == query.user_id, UserNotification.deleted_at.is_(None)
    )
#添加过滤条件
    if query.is_read is not None:
        stmt = stmt.where(UserNotification.is_read == query.is_read)
# 按创建时间倒序排序
    stmt = stmt.order_by(UserNotification.created_at.desc())
# 获取总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)
#添加分页
    stmt = stmt.offset(query.skip).limit(query.limit)
# 执行查询
    result = await db.execute(stmt)
    items = result.scalars().all()

    return items, total


async def send_notification(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    request: NotificationSendRequest,
) -> None:
    try:
＃1。获取模板
        template = await db.get(NotificationTemplate, request.template_id)
        if not template:
            raise ValueError(
                f"Notification template does not exist: {request.template_id}"
            )
        if not template.is_active:
            raise ValueError(
                f"Notification template is disabled: {request.template_id}"
            )
#2.获取美味用户列表
        if request.all_users:
# 发送给所有用户，需要根据实际情况查询所有用户
            stmt = select(User.id).where(User.is_active == True)
            result = await db.execute(stmt)
            user_ids = [row[0] for row in result.all()]
        else:
            if not request.user_ids:
                raise ValueError("Recipient user list is empty")
# 发送给用户指定
            user_ids = request.user_ids
＃3。渲染模板内容
        try:
# 渲染标题
            title_template = Template(template.title)
            rendered_title = title_template.render(**request.params)
# 渲染内容
            content_template = Template(template.content)
            rendered_content = content_template.render(**request.params)
# 渲染图像 URL
            rendered_image_urls = []
            if template.image_urls:
                for image_url in template.image_urls:
                    rendered_image_url = Template(image_url).render(**request.params)
                    rendered_image_urls.append(rendered_image_url)
# 渲染链接 URL
            rendered_link_urls = []
            if template.link_urls:
                for link_url in template.link_urls:
                    rendered_link_url = Template(link_url).render(**request.params)
                    rendered_link_urls.append(rendered_link_url)

        except Exception as e:
            logger.error(f"Template rendering failed: {str(e)}")
            raise ValueError(f"Template rendering failed: {str(e)}")
＃4。生成通知
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
                    type=int(template.type),  # Ensure type is integer
                    dynamic_params=request.params,
                    title=rendered_title,
                    content=rendered_content,
                    image_urls=rendered_image_urls,
                    link_urls=rendered_link_urls,
                    is_read=True,  # Default read
                    read_at=datetime.now(),
                )
                notifications.append(notification)
            except Exception as e:
                logger.error(
                    f"Failed to create notification for user {user_id}: {str(e)}"
                )
＃5。批量保存通知
        if notifications:
            db.add_all(notifications)
            await db.commit()
＃6。异步发送 FCM 消息（后台任务）
        background_tasks.add_task(
            send_fcm_multicast,
            db,
            user_ids,
            rendered_title,
            rendered_content,
            request.params,
            rendered_image_urls[0] if rendered_image_urls else None,
        )

    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")
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
    image_url: Optional[str] = None,
) -> bool:
    """Send FCM multicast message push

    Suitable for same notification to multiple users

    Args:
        db: Database session
        user_ids: List of user IDs
        title: Notification title
        body: Notification content
        data: Additional data (optional)
        image_url: Image URL (optional)

    Returns:
        bool: Whether sending was successful
    """
    try:
＃1。获取多个用户的所有设备令牌
        tokens = await user_service.get_users_device_tokens(db, user_ids)

        if not tokens:
            logger.warning(f"Users {user_ids} have no registered device tokens")
            return False
#2.发送消息
        success_count = 0
        fail_count = 0
        invalid_tokens = []

        for token in tokens:
            try:
                single_message = messaging.Message(
                    token=token,
                    notification=messaging.Notification(
                        title=title, body=body, image=image_url
                    ),
                    data=data or {},
                )
                messaging.send(single_message)
                success_count += 1
            except INVALID_EXCEPTIONS:
                invalid_tokens.append(token)
                fail_count += 1
            except Exception as e:
                logger.error(f"Failed to send to device {token}: {str(e)}")
                fail_count += 1
＃3。Pr获得结果
        if fail_count > 0:
            logger.error(f"FCM message sending failed: {fail_count} devices failed")
＃4。清理无效令牌
        if invalid_tokens:
            try:
                await db.execute(
                    delete(DeviceToken).where(DeviceToken.token.in_(invalid_tokens))
                )
                await db.commit()
                logger.debug(f"Cleaned up {len(invalid_tokens)} invalid tokens")
            except Exception as e:
                logger.error(f"Failed to clean up invalid tokens: {str(e)}")
                logger.error(f"Error stack: {traceback.format_exc()}")

            return False

        logger.info(f"FCM message sent successfully: {success_count} devices")
        return True

    except Exception as e:
        logger.error(f"Failed to send FCM message: {str(e)}")
        logger.error(f"Error stack: {traceback.format_exc()}")
        return False
