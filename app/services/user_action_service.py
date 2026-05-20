# CREATED_BY_AGENT
"""
用户 Action 服务

处理用户相关的 Action 判断逻辑，如索取 feedback 等。
"""

import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.uuid import uid
from app.models.feedback_push import FeedbackPushHistory
from app.models.report import Report, ReportType
from app.models.subscription import SubscriptionUsage
from app.models.user import User
from app.schemas.user import ActionType, UserAction

# Feedback action 的聊天轮数阈值
FEEDBACK_ACTION_THRESHOLDS = [20, 30, 40, 50, 60]

# 新用户定义：注册时间小于此时长
NEW_USER_THRESHOLD_HOURS = 24

# 两个阈值之间的最小间隔
THRESHOLD_INTERVAL_HOURS = 24


async def get_user_total_chat_count(db: AsyncSession, user_id: str) -> int:
    """查询用户总聊天轮数（含 keep talking）"""
    try:
        result = await db.execute(
            select(func.sum(SubscriptionUsage.usage_count)).where(
                and_(
                    SubscriptionUsage.user_id == user_id,
                    SubscriptionUsage.usage_type == "chat",
                )
            )
        )
        total_count = result.scalar() or 0
        return int(total_count)
    except Exception as e:
        logger.error(
            f"查询用户总聊天轮数失败: user_id={user_id}, error={str(e)}"
        )
        return 0


async def has_user_submitted_feedback(db: AsyncSession, user_id: str) -> bool:
    """检查用户是否已填写 feedback"""
    try:
        result = await db.execute(
            select(func.count(Report.id)).where(
                and_(
                    Report.reporter_id == user_id,
                    Report.report_type == ReportType.FEEDBACK,
                )
            )
        )
        count = result.scalar() or 0
        return count > 0
    except Exception as e:
        logger.error(
            f"检查用户是否已填写 feedback 失败: user_id={user_id}, error={str(e)}"
        )
        return False


async def _is_new_user(db: AsyncSession, user_id: str) -> bool:
    """检查用户是否为新用户（注册时间未满24小时）"""
    try:
        result = await db.execute(
            select(User.created_at).where(User.id == user_id)
        )
        created_at = result.scalar_one_or_none()

        if created_at is None:
            return True

        now = datetime.datetime.now(datetime.timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=datetime.timezone.utc)

        return (now - created_at) < datetime.timedelta(
            hours=NEW_USER_THRESHOLD_HOURS
        )
    except Exception as e:
        logger.error(f"检查新用户失败: user_id={user_id}, error={str(e)}")
        return True


async def _get_last_feedback_record(
    db: AsyncSession, user_id: str
) -> Optional[FeedbackPushHistory]:
    """获取用户最后一条 feedback 记录"""
    result = await db.execute(
        select(FeedbackPushHistory)
        .where(FeedbackPushHistory.user_id == user_id)
        .order_by(FeedbackPushHistory.sent_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _find_next_threshold(last_threshold: int) -> Optional[int]:
    """找到下一个阈值"""
    for threshold in FEEDBACK_ACTION_THRESHOLDS:
        if threshold > last_threshold:
            return threshold
    return None


async def _should_request_feedback(
    db: AsyncSession, user_id: str, total_chat_count: int
) -> tuple[bool, Optional[int]]:
    """
    判断是否应该索取 feedback

    策略：
    1. 已填写 feedback → 返回 false
    2. 按阈值顺序递进，每个阈值只返回一次 true
    3. 距离上一次返回 true 需间隔24小时

    Returns:
        (should_request, threshold): 是否应该索取及对应的阈值
    """
    if await has_user_submitted_feedback(db, user_id):
        return False, None

    last_record = await _get_last_feedback_record(db, user_id)

    if last_record is None:
        next_threshold = FEEDBACK_ACTION_THRESHOLDS[0]
    else:
        now = datetime.datetime.now(datetime.timezone.utc)
        sent_at = last_record.sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=datetime.timezone.utc)

        if (now - sent_at) < datetime.timedelta(hours=THRESHOLD_INTERVAL_HOURS):
            return False, None

        next_threshold = _find_next_threshold(last_record.chat_count_threshold)
        if next_threshold is None:
            return False, None

    if total_chat_count < next_threshold:
        return False, None

    return True, next_threshold


async def _record_feedback_action(
    db: AsyncSession, user_id: str, threshold: int
) -> None:
    """记录 feedback action 已被返回"""
    try:
        sent_at = datetime.datetime.now(datetime.timezone.utc)
        history = FeedbackPushHistory(
            id=uid("fpush"),
            user_id=user_id,
            chat_count_threshold=threshold,
            sent_at=sent_at,
        )
        db.add(history)
        await db.commit()
        logger.info(
            f"Feedback action 已记录: user_id={user_id}, threshold={threshold}"
        )
    except Exception as e:
        logger.error(
            f"记录 feedback action 失败: user_id={user_id}, threshold={threshold}, "
            f"error={str(e)}"
        )
        await db.rollback()


async def get_user_actions(db: AsyncSession, user_id: str) -> list[UserAction]:
    """
    获取用户的 actions 列表

    目前支持的 action：
    - request_feedback: 索取用户反馈

    策略：
    1. 新用户（注册时间未满24小时）→ enabled=false
    2. 已填写 feedback → enabled=false
    3. 按阈值顺序递进（20, 30, 40, 50, 60），每个阈值只返回一次 enabled=true
    4. 两个阈值之间需间隔24小时

    始终返回包含所有 action type 的列表，enabled 值表示是否满足条件。
    """
    request_feedback_enabled = False

    try:
        if not await _is_new_user(db, user_id):
            total_chat_count = await get_user_total_chat_count(db, user_id)
            should_request, threshold = await _should_request_feedback(
                db, user_id, total_chat_count
            )

            if should_request and threshold is not None:
                await _record_feedback_action(db, user_id, threshold)
                request_feedback_enabled = True

    except Exception as e:
        logger.error(
            f"获取用户 actions 失败: user_id={user_id}, error={str(e)}"
        )

    return [
        UserAction(
            type=ActionType.REQUEST_FEEDBACK, enabled=request_feedback_enabled
        )
    ]
