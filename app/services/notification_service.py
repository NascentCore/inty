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

# 反向映射字典
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
    db: AsyncSession, query: NotificationQuery
) -> Tuple[List[UserNotification], int]:
    """
    查询用户通知列表
    """
    # 构建基础查询
    stmt = select(UserNotification).filter(
        UserNotification.user_id == query.user_id, UserNotification.deleted_at.is_(None)
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
    request: NotificationSendRequest,
) -> None:
    try:
        # 1. Get template
        template = await db.get(NotificationTemplate, request.template_id)
        if not template:
            raise ValueError(
                f"Notification template does not exist: {request.template_id}"
            )
        if not template.is_active:
            raise ValueError(
                f"Notification template is disabled: {request.template_id}"
            )

        # 2. Get recipient user list
        if request.all_users:
            # Send to all users, need to query all users based on actual situation
            stmt = select(User.id).where(User.is_active == True)
            result = await db.execute(stmt)
            user_ids = [row[0] for row in result.all()]
        else:
            if not request.user_ids:
                raise ValueError("Recipient user list is empty")
            # Send to specified users
            user_ids = request.user_ids

        # 3. Render template content
        try:
            # Render title
            title_template = Template(template.title)
            rendered_title = title_template.render(**request.params)

            # Render content
            content_template = Template(template.content)
            rendered_content = content_template.render(**request.params)

            # Render image URLs
            rendered_image_urls = []
            if template.image_urls:
                for image_url in template.image_urls:
                    rendered_image_url = Template(image_url).render(**request.params)
                    rendered_image_urls.append(rendered_image_url)

            # Render link URLs
            rendered_link_urls = []
            if template.link_urls:
                for link_url in template.link_urls:
                    rendered_link_url = Template(link_url).render(**request.params)
                    rendered_link_urls.append(rendered_link_url)

        except Exception as e:
            logger.error(f"Template rendering failed: {str(e)}")
            raise ValueError(f"Template rendering failed: {str(e)}")

        # 4. Generate notifications
        notifications = []

        for user_id in user_ids:
            try:
                # Generate notification ID
                notification_id = uid("notify")

                # Create notification record
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

        # 5. Batch save notifications
        if notifications:
            db.add_all(notifications)
            await db.commit()

        # 6. Send FCM messages asynchronously (background task)
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
    dry_run: bool = False,
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
        dry_run: If True, validate message format without actually sending

    Returns:
        bool: Whether sending was successful
    """
    try:
        if dry_run:
            logger.info(f"[DRY RUN] FCM 测试模式：验证消息格式，不会实际发送")

        # 1. Get all device tokens for multiple users
        tokens = await user_service.get_users_device_tokens(db, user_ids)

        if not tokens:
            logger.warning(f"Users {user_ids} have no registered device tokens")
            return False

        # 2. Send messages
        success_count = 0
        fail_count = 0
        invalid_tokens = []
        send_results = []

        for token in tokens:
            try:
                single_message = messaging.Message(
                    token=token,
                    notification=messaging.Notification(
                        title=title, body=body, image=image_url
                    ),
                    data=data or {},
                )

                # 发送消息（支持 dry_run 模式）
                message_id = messaging.send(single_message, dry_run=dry_run)

                if dry_run:
                    logger.info(
                        f"[DRY RUN] 消息验证成功: token={token[:20]}..., message_id={message_id}"
                    )
                else:
                    logger.debug(
                        f"FCM 消息发送成功: token={token[:20]}..., message_id={message_id}"
                    )

                send_results.append(
                    {
                        "token": token[:20] + "...",
                        "message_id": message_id,
                        "status": "success",
                    }
                )
                success_count += 1

            except INVALID_EXCEPTIONS as e:
                invalid_tokens.append(token)
                fail_count += 1
                error_msg = str(e)
                logger.warning(
                    f"FCM 发送失败（无效 token）: token={token[:20]}..., error={error_msg}"
                )
                send_results.append(
                    {
                        "token": token[:20] + "...",
                        "status": "invalid_token",
                        "error": error_msg,
                    }
                )
            except Exception as e:
                fail_count += 1
                error_msg = str(e)
                error_type = type(e).__name__
                logger.error(
                    f"FCM 发送失败: token={token[:20]}..., error_type={error_type}, error={error_msg}"
                )
                send_results.append(
                    {
                        "token": token[:20] + "...",
                        "status": "error",
                        "error_type": error_type,
                        "error": error_msg,
                    }
                )

        # 3. Process results
        if dry_run:
            logger.info(
                f"[DRY RUN] 测试完成: 成功={success_count}, 失败={fail_count}, 总计={len(tokens)}"
            )
            logger.debug(f"[DRY RUN] 详细结果: {send_results}")
        else:
            if fail_count > 0:
                logger.error(
                    f"FCM 消息发送失败: {fail_count} 个设备失败, 成功={success_count}"
                )
                logger.debug(f"发送结果详情: {send_results}")

            # 4. Clean up invalid tokens (仅在非 dry_run 模式下)
            if invalid_tokens:
                try:
                    await db.execute(
                        delete(DeviceToken).where(DeviceToken.token.in_(invalid_tokens))
                    )
                    await db.commit()
                    logger.debug(f"已清理 {len(invalid_tokens)} 个无效 token")
                except Exception as e:
                    logger.error(f"清理无效 token 失败: {str(e)}")
                    logger.error(f"错误堆栈: {traceback.format_exc()}")

                return False

            logger.info(f"FCM 消息发送成功: {success_count} 个设备")
            logger.debug(f"发送结果详情: {send_results}")

        return success_count > 0

    except Exception as e:
        logger.error(f"Failed to send FCM message: {str(e)}")
        logger.error(f"Error stack: {traceback.format_exc()}")
        return False
