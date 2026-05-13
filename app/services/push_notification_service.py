"""
推送通知服务

实现主动推送功能：查询需要推送的聊天会话，生成 Agent 消息，发送 FCM 推送。
"""

import asyncio
import datetime
from types import SimpleNamespace
from typing import List, Optional, Tuple

from langchain_core.messages import HumanMessage
from loguru import logger
from sqlalchemy import Integer, and_, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.api.utils.feature_gating import is_festival_memory_enabled
from app.core.agent.agent import agent_manager
from app.core.config import global_config_loaded_from_config_yaml
from app.core.model_selection import select_chat_model
from app.core.prompting.push_message_prompt import (
    build_simple_push_message_prompt,
    build_welcome_message_prompt,
)
from app.core.uuid import uid
from app.db.session import AsyncSessionLocal
from app.models.chat import Chat
from app.models.push_notification import PushNotificationHistory
from app.models.agent import Agent, AgentVisibility
from app.models.chat_history import ChatHistory
from app.models.user import DeviceToken, User
from app.services import (
    agent_service,
    chat_history_service,
    chat_service,
    notification_service,
)
from app.services.chat_history_service import (
    add_ai_message,
    get_chat_history_connection,
)
from app.services.chat_service import generate_session_id
from app.services.global_services import subscription_service
from app.services.image_transform_service import image_transform_service
from app.services.memory_service import (
    get_pairs_with_undelivered_festival_memories,
    mark_system_notification_sent_for_user_agent,
)

# ============================================================================
# 常量配置
# ============================================================================


# TODO: 添加推送消息定义，python 代码内用此数据结构操作；发送给 firebase/app 时转换为 JSON 等。
# class PushMessage(BaseModel):
#     ....


def get_push_stage_config() -> dict:
    """
    获取推送阶段配置（从配置文件中读取）

    Returns:
        推送阶段配置字典：阶段名称 -> {未读记录数, 时间阈值}
    """
    config = global_config_loaded_from_config_yaml.push_notification
    if config.stages:
        return config.stages
    # 默认配置
    return {
        "10min": {"count": 0, "minutes": 10},
        "30min": {"count": 1, "minutes": 30},
        "2h": {"count": 2, "minutes": 120},
        "24h": {"count": 3, "hours": 24},
        "48h": {"count": 4, "hours": 48},
    }


# 推送阶段配置：阶段名称 -> {未读记录数, 时间阈值}
PUSH_STAGE_CONFIG = get_push_stage_config()


# 无聊天推送阶段到未读记录数的映射（统一使用相同的 stage 名称）
def get_no_chat_stage_to_count() -> dict:
    """
    获取无聊天推送阶段到未读记录数的映射（从配置中读取）

    Returns:
        无聊天推送阶段到未读记录数的映射字典
    """
    stage_config = get_push_stage_config()
    # 只返回 24h 和 48h 的映射
    return {
        "24h": stage_config.get("24h", {}).get("count", 3),
        "48h": stage_config.get("48h", {}).get("count", 4),
    }


NO_CHAT_STAGE_TO_COUNT = get_no_chat_stage_to_count()

# 最近聊天推送阶段到未读记录数的映射
RECENT_CHAT_STAGE_TO_COUNT = {
    "10min": 0,
    "30min": 1,
    "2h": 2,
}

# 推送类型常量
PUSH_TYPE_RECENT_CHAT = "recent_chat"
PUSH_TYPE_NO_CHAT = "no_chat"
PUSH_TYPE_FESTIVAL_MEMORY = "festival_memory"

# 未读推送记录数上限
MAX_UNREAD_PUSH_COUNT = 5

# 已读推送重新召回的时间窗口（小时）
READ_PUSH_RECALL_TIME_WINDOW_HOURS = 24

# 推送阶段顺序（从早到晚）
STAGE_ORDER = ["10min", "30min", "2h", "24h", "48h"]

# 推送阶段间隔配置：每个阶段相对于前一个阶段的间隔（分钟）
# 例如：30min 阶段应该在 10min 阶段推送后 20 分钟触发（30 - 10 = 20）
STAGE_INTERVALS = {
    "10min": None,  # 第一个阶段，无前一个阶段
    "30min": 20,  # 30 - 10 = 20 分钟
    "2h": 90,  # 120 - 30 = 90 分钟
    "24h": 1320,  # (24 * 60) - 120 = 1320 分钟 = 22 小时
    "48h": 1440,  # (48 * 60) - (24 * 60) = 1440 分钟 = 24 小时
}

# ============================================================================
# 内部辅助函数
# ============================================================================


async def _update_push_history_message_content(
    db: AsyncSession,
    user_id: str,
    message_content: str,
    stage: str,
    push_type: str,
    chat_id: Optional[str] = None,
) -> None:
    """
    更新推送历史记录的消息内容

    Args:
        db: 数据库会话
        user_id: 用户ID
        message_content: 消息内容
        stage: 推送阶段
        push_type: 推送类型
        chat_id: 聊天ID（可选）
    """
    try:
        conditions = [
            PushNotificationHistory.user_id == user_id,
            PushNotificationHistory.stage == stage,
            PushNotificationHistory.push_type == push_type,
        ]
        if chat_id:
            conditions.append(PushNotificationHistory.chat_id == chat_id)
        else:
            conditions.append(PushNotificationHistory.chat_id.is_(None))

        stmt = (
            select(PushNotificationHistory)
            .where(and_(*conditions))
            .order_by(PushNotificationHistory.sent_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        history = result.scalar_one_or_none()
        if history:
            history.message_content = message_content
            await db.commit()
        else:
            logger.warning(
                f"更新推送历史消息内容失败：未找到对应的推送历史记录: "
                f"user_id={user_id}, stage={stage}, push_type={push_type}, chat_id={chat_id}"
            )
    except Exception as e:
        logger.warning(
            f"更新推送历史消息内容失败: user_id={user_id}, stage={stage}, error={str(e)}"
        )


async def _delete_push_history_record(
    db: AsyncSession,
    user_id: str,
    stage: str,
    push_type: str,
    chat_id: Optional[str] = None,
) -> bool:
    """
    删除推送历史记录（用于生成消息失败时清理）

    Args:
        db: 数据库会话
        user_id: 用户ID
        stage: 推送阶段
        push_type: 推送类型
        chat_id: 聊天ID（可选）

    Returns:
        是否成功删除
    """
    try:
        conditions = [
            PushNotificationHistory.user_id == user_id,
            PushNotificationHistory.stage == stage,
            PushNotificationHistory.push_type == push_type,
        ]
        if chat_id:
            conditions.append(PushNotificationHistory.chat_id == chat_id)
        else:
            conditions.append(PushNotificationHistory.chat_id.is_(None))

        stmt = (
            select(PushNotificationHistory)
            .where(and_(*conditions))
            .order_by(PushNotificationHistory.sent_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        history = result.scalar_one_or_none()
        if history:
            await db.delete(history)
            await db.commit()
            logger.debug(
                f"已删除推送历史记录: user_id={user_id}, stage={stage}, push_type={push_type}, chat_id={chat_id}"
            )
            return True
        else:
            logger.debug(
                f"未找到要删除的推送历史记录: user_id={user_id}, stage={stage}, push_type={push_type}, chat_id={chat_id}"
            )
            return False
    except Exception as e:
        logger.warning(
            f"删除推送历史记录失败: user_id={user_id}, stage={stage}, error={str(e)}"
        )
        await db.rollback()
        return False


async def _check_user_has_device_token(
    db: AsyncSession,
    user_id: str,
) -> bool:
    """
    检查用户是否有有效的 device_token

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        是否有有效的 device_token（如果用户被标记为无效 token，返回 False）
    """
    try:
        # 检查用户是否被标记为无效 token
        user_stmt = select(User.fcm_token_invalid_at).where(User.id == user_id)
        user_result = await db.execute(user_stmt)
        fcm_token_invalid_at = user_result.scalar_one_or_none()

        # 如果用户被标记为无效 token，返回 False
        if fcm_token_invalid_at is not None:
            logger.debug(
                f"用户被标记为无效 FCM token: user_id={user_id}, invalid_at={fcm_token_invalid_at.isoformat()}"
            )
            return False

        # 检查用户是否有 device_token
        device_token_stmt = (
            select(DeviceToken.id)
            .where(DeviceToken.user_id == user_id)
            .order_by(DeviceToken.updated_at.desc())
            .limit(1)
        )
        device_token_result = await db.execute(device_token_stmt)
        return device_token_result.first() is not None
    except Exception as e:
        logger.error(f"检查用户 device_token 失败: user_id={user_id}, error={str(e)}")
        return False


async def _user_satisfies_festival_memory_version_gate(
    db: AsyncSession,
    user_id: str,
) -> bool:
    """
    检查用户的 last_android_app_version_code 是否满足节日记忆推送的版本门控。
    用于 push worker 发送节日记忆 FCM 时与 in-app 行为一致（仅向版本 >= min 的用户发送）。
    """
    stmt = select(User.last_android_app_version_code).where(User.id == user_id)
    result = await db.execute(stmt)
    version_code = result.scalar_one_or_none()
    return is_festival_memory_enabled(version_code)


async def _query_users_by_unread_count(
    db: AsyncSession,
    expected_unread_count: int,
    batch_size: int,
) -> List[SimpleNamespace]:
    """
    查询指定未读推送记录数的用户

    Args:
        db: 数据库会话
        expected_unread_count: 期望的未读推送记录数
        batch_size: 批次大小

    Returns:
        用户ID列表（SimpleNamespace对象，包含user_id属性）
    """
    if expected_unread_count == 0:
        # 对于未读记录数为0的情况，查询没有推送记录的用户（新用户）
        if not await is_push_system_initialized(db):
            logger.info("系统未初始化，跳过查询未读数为0的用户")
            return []

        stmt = (
            select(User.id.label("user_id"))
            .join(DeviceToken, User.id == DeviceToken.user_id)
            .outerjoin(
                PushNotificationHistory,
                User.id == PushNotificationHistory.user_id,
            )
            .where(
                and_(
                    User.deleted_at.is_(None),
                    PushNotificationHistory.id.is_(None),  # 没有推送记录
                )
            )
            .distinct()
            .limit(batch_size * 3)
        )
        result = await db.execute(stmt)
        return [SimpleNamespace(user_id=row[0]) for row in result.all()]
    else:
        # 对于未读记录数 > 0 的情况，查询推送记录表中未读推送记录数等于期望值的用户
        stmt = (
            select(
                PushNotificationHistory.user_id,
                func.count(PushNotificationHistory.id).label("unread_count"),
            )
            .where(PushNotificationHistory.read_at.is_(None))
            .group_by(PushNotificationHistory.user_id)
            .having(func.count(PushNotificationHistory.id) == expected_unread_count)
        )
        result = await db.execute(stmt)
        return result.all()


async def _check_read_push_users_for_recall(
    db: AsyncSession,
    read_push_user_ids: List[str],
    stage: str,
    expected_unread_count: int,
    threshold_time: datetime.datetime,
) -> List[SimpleNamespace]:
    """
    检查已读推送用户是否需要重新召回

    Args:
        db: 数据库会话
        read_push_user_ids: 已读推送用户ID列表
        stage: 推送阶段
        expected_unread_count: 期望的未读推送记录数
        threshold_time: 时间阈值

    Returns:
        需要重新召回的用户列表
    """
    recalled_users = []
    for read_user_id in read_push_user_ids:
        try:
            # 获取用户最近聊天
            recent_chat_data = await get_user_recent_chat(db, read_user_id, stage=stage)
            if recent_chat_data:
                chat, last_user_message_time = recent_chat_data
                # 如果最后消息时间超过阈值，说明用户不聊了，检查推送状态
                if last_user_message_time <= threshold_time:
                    reset_count = await reset_user_read_push_notifications(
                        db, read_user_id
                    )
                    if reset_count > 0:
                        logger.debug(
                            f"用户不聊了，检查推送状态: user_id={read_user_id}, stage={stage}, 已读推送记录数={reset_count}"
                        )
                        unread_count = await get_user_unread_push_count(
                            db, read_user_id
                        )
                        if unread_count == expected_unread_count:
                            recalled_users.append(SimpleNamespace(user_id=read_user_id))
            else:
                # 用户没有最近聊天，检查用户注册时间（仅对24h/48h阶段）
                if stage in ("24h", "48h"):
                    user_stmt = (
                        select(User)
                        .options(load_only(User.id, User.created_at, User.deleted_at))
                        .where(and_(User.id == read_user_id, User.deleted_at.is_(None)))
                    )
                    user_result = await db.execute(user_stmt)
                    user = user_result.scalar_one_or_none()
                    if user and user.created_at and user.created_at <= threshold_time:
                        reset_count = await reset_user_read_push_notifications(
                            db, read_user_id
                        )
                        if reset_count > 0:
                            logger.debug(
                                f"用户没有聊天且达到阈值，检查推送状态: user_id={read_user_id}, stage={stage}, 已读推送记录数={reset_count}"
                            )
                            unread_count = await get_user_unread_push_count(
                                db, read_user_id
                            )
                            if unread_count == expected_unread_count:
                                recalled_users.append(
                                    SimpleNamespace(user_id=read_user_id)
                                )
        except Exception as e:
            logger.error(
                f"检查已读推送用户时出错: user_id={read_user_id}, stage={stage}, error={str(e)}"
            )
            continue
    return recalled_users


async def _filter_users_by_push_conditions(
    db: AsyncSession,
    user_ids: List[str],
    stage: str,
    expected_unread_count: int,
    threshold_time: datetime.datetime,
    popular_agent: Optional[Agent],
    batch_size: int,
) -> List[Tuple[User, Optional[Chat], Optional[datetime.datetime], Optional[Agent]]]:
    """
    按推送条件过滤用户

    时间判断逻辑：
    - 10min 阶段：基于最后用户消息时间，检查是否在 10 分钟前
    - 30min 阶段：基于 10min 阶段的推送时间，检查是否已过去 20 分钟（30 - 10）
    - 2h 阶段：基于 30min 阶段的推送时间，检查是否已过去 90 分钟（120 - 30）
    - 24h 阶段：基于 2h 阶段的推送时间，检查是否已过去 22 小时（24 - 2）
    - 48h 阶段：基于 24h 阶段的推送时间，检查是否已过去 24 小时（48 - 24）

    如果前一个阶段的推送不存在或已被标记为已读，则跳过该用户（因为用户已经回来了）。

    Args:
        db: 数据库会话
        user_ids: 用户ID列表
        stage: 推送阶段
        expected_unread_count: 期望的未读推送记录数
        threshold_time: 时间阈值（仅用于 10min 阶段和 24h/48h 阶段的后备逻辑）
        popular_agent: 热门角色（用于无聊天推送）
        batch_size: 批次大小

    Returns:
        (用户, 聊天对象或None, 最后消息时间或用户注册时间, 热门角色或None) 的元组列表
    """
    users_needing_push = []
    skipped_no_user = 0
    skipped_no_device_token = 0
    skipped_no_chat = 0
    skipped_time_not_met = 0
    skipped_no_popular_agent = 0

    for user_id in user_ids:
        try:
            # 获取用户信息
            user_stmt = (
                select(User)
                .options(load_only(User.id, User.created_at, User.deleted_at))
                .where(and_(User.id == user_id, User.deleted_at.is_(None)))
            )
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            if not user:
                skipped_no_user += 1
                continue

            # 检查用户是否有 device_token
            if not await _check_user_has_device_token(db, user_id):
                skipped_no_device_token += 1
                continue

            # 获取用户最近聊天
            recent_chat_data = await get_user_recent_chat(db, user_id, stage=stage)
            if recent_chat_data:
                # 用户有活跃聊天
                chat, last_user_message_time = recent_chat_data

                # 判断时间条件
                time_condition_met = False

                if stage == "10min":
                    # 10min 阶段：基于最后用户消息时间
                    time_condition_met = last_user_message_time <= threshold_time
                else:
                    # 后续阶段（30min, 2h, 24h, 48h）：基于前一个阶段的推送时间
                    previous_push_time = await get_previous_stage_push_time(
                        db, user_id, stage, PUSH_TYPE_RECENT_CHAT, chat.id
                    )

                    if previous_push_time is None:
                        # 不存在前一个阶段的未读推送，跳过该用户
                        skipped_time_not_met += 1
                        logger.debug(
                            f"用户不存在前一个阶段的未读推送: user_id={user_id}, chat_id={chat.id}, stage={stage}"
                        )
                        continue

                    # 检查前一个阶段推送时间是否满足间隔要求
                    interval_minutes = STAGE_INTERVALS.get(stage)
                    if interval_minutes is None:
                        logger.error(f"未找到阶段间隔配置: stage={stage}")
                        skipped_time_not_met += 1
                        continue

                    now = datetime.datetime.now(datetime.timezone.utc)
                    time_since_previous_push = (
                        now - previous_push_time
                    ).total_seconds() / 60
                    time_condition_met = time_since_previous_push >= interval_minutes

                    logger.debug(
                        f"检查前一个阶段推送时间: user_id={user_id}, chat_id={chat.id}, stage={stage}, "
                        f"previous_push_time={previous_push_time.isoformat()}, "
                        f"time_since_previous_push={time_since_previous_push:.1f}分钟, "
                        f"required_interval={interval_minutes}分钟, "
                        f"condition_met={time_condition_met}"
                    )

                if time_condition_met:
                    users_needing_push.append(
                        (user, chat, last_user_message_time, None)
                    )
                    logger.debug(
                        f"用户满足推送条件（有聊天）: user_id={user_id}, chat_id={chat.id}, stage={stage}, "
                        f"unread_count={expected_unread_count}, last_message_time={last_user_message_time.isoformat()}"
                    )
                else:
                    skipped_time_not_met += 1
                    logger.debug(
                        f"用户时间不满足条件: user_id={user_id}, stage={stage}, "
                        f"last_message_time={last_user_message_time.isoformat()}"
                    )
            else:
                # 用户没有活跃聊天，检查用户注册时间（仅对24h/48h阶段）
                if stage in ("24h", "48h"):
                    # 对于 24h/48h 阶段，也需要基于前一个阶段的推送时间
                    previous_push_time = await get_previous_stage_push_time(
                        db, user_id, stage, PUSH_TYPE_NO_CHAT, None
                    )

                    if previous_push_time is None:
                        # 不存在前一个阶段的未读推送，检查用户注册时间（作为后备逻辑）
                        if user.created_at and user.created_at <= threshold_time:
                            if not popular_agent:
                                skipped_no_popular_agent += 1
                                continue
                            users_needing_push.append(
                                (user, None, user.created_at, popular_agent)
                            )
                            logger.debug(
                                f"用户满足推送条件（无聊天，基于注册时间）: user_id={user_id}, stage={stage}, "
                                f"unread_count={expected_unread_count}, created_at={user.created_at.isoformat()}"
                            )
                        else:
                            skipped_time_not_met += 1
                            logger.debug(
                                f"用户注册时间不满足条件: user_id={user_id}, stage={stage}, "
                                f"created_at={user.created_at.isoformat() if user.created_at else None}, threshold={threshold_time.isoformat()}"
                            )
                    else:
                        # 存在前一个阶段的未读推送，检查间隔
                        interval_minutes = STAGE_INTERVALS.get(stage)
                        if interval_minutes is None:
                            logger.error(f"未找到阶段间隔配置: stage={stage}")
                            skipped_time_not_met += 1
                            continue

                        now = datetime.datetime.now(datetime.timezone.utc)
                        time_since_previous_push = (
                            now - previous_push_time
                        ).total_seconds() / 60
                        time_condition_met = (
                            time_since_previous_push >= interval_minutes
                        )

                        logger.debug(
                            f"检查前一个阶段推送时间（无聊天）: user_id={user_id}, stage={stage}, "
                            f"previous_push_time={previous_push_time.isoformat()}, "
                            f"time_since_previous_push={time_since_previous_push:.1f}分钟, "
                            f"required_interval={interval_minutes}分钟, "
                            f"condition_met={time_condition_met}"
                        )

                        if time_condition_met:
                            if not popular_agent:
                                skipped_no_popular_agent += 1
                                continue
                            users_needing_push.append(
                                (user, None, user.created_at, popular_agent)
                            )
                            logger.debug(
                                f"用户满足推送条件（无聊天，基于前一个阶段推送时间）: user_id={user_id}, stage={stage}, "
                                f"unread_count={expected_unread_count}, previous_push_time={previous_push_time.isoformat()}"
                            )
                        else:
                            skipped_time_not_met += 1
                            logger.debug(
                                f"用户时间不满足条件（无聊天）: user_id={user_id}, stage={stage}, "
                                f"previous_push_time={previous_push_time.isoformat()}"
                            )
                else:
                    # 对于 10min/30min/2h 阶段，用户没有活跃聊天时不推送
                    skipped_no_chat += 1
                    logger.debug(
                        f"用户没有活跃聊天（不推送无聊天用户）: user_id={user_id}, stage={stage}"
                    )

            if len(users_needing_push) >= batch_size:
                break

        except Exception as e:
            logger.error(
                f"处理用户时出错: user_id={user_id}, stage={stage}, error={str(e)}"
            )
            continue

    logger.debug(
        f"用户过滤统计 (stage={stage}): "
        f"总计={len(user_ids)}, 满足条件={len(users_needing_push)}, "
        f"跳过(无用户)={skipped_no_user}, 跳过(无device_token)={skipped_no_device_token}, "
        f"跳过(无聊天)={skipped_no_chat}, 跳过(时间不满足)={skipped_time_not_met}, "
        f"跳过(无热门角色)={skipped_no_popular_agent}"
    )

    return users_needing_push


async def _get_user_by_id(
    db: AsyncSession,
    user_id: str,
) -> Optional[User]:
    """
    根据用户ID获取用户对象

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        用户对象，如果不存在则返回 None
    """
    try:
        user_stmt = (
            select(User)
            .options(load_only(User.id, User.created_at, User.deleted_at))
            .where(and_(User.id == user_id, User.deleted_at.is_(None)))
        )
        user_result = await db.execute(user_stmt)
        return user_result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"获取用户信息失败: user_id={user_id}, error={str(e)}")
        return None


async def _check_user_has_active_chat(
    db: AsyncSession,
    user_id: str,
) -> bool:
    """
    检查用户是否有活跃聊天

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        是否有活跃聊天
    """
    try:
        chat_stmt = (
            select(Chat)
            .where(
                and_(
                    Chat.user_id == user_id,
                    Chat.is_active == True,
                )
            )
            .limit(1)
        )
        chat_result = await db.execute(chat_stmt)
        return chat_result.scalar_one_or_none() is not None
    except Exception as e:
        logger.error(f"检查用户活跃聊天失败: user_id={user_id}, error={str(e)}")
        return False


async def _extract_agent_info(agent_data: dict) -> Tuple[str, Optional[str]]:
    """
    从 Agent 数据中提取名称和头像URL

    Args:
        agent_data: Agent 数据字典

    Returns:
        (agent_name, agent_avatar_url) 元组
    """
    agent_name = agent_data.get("name") or "角色"
    agent_avatar_url = None
    try:
        agent_avatar_url = await get_agent_avatar_url(agent_data)
    except Exception as e:
        logger.warning(f"获取 Agent 头像失败: {str(e)}")
    return agent_name, agent_avatar_url


# ============================================================================
# 查询函数
# ============================================================================


async def get_last_user_message_time(
    session_id: str,
) -> Optional[datetime.datetime]:
    """
    获取聊天会话最后一条用户消息的时间

    Args:
        session_id: 会话ID

    Returns:
        最后一条用户消息的时间，如果没有用户消息则返回 None
    """
    try:
        conn = get_chat_history_connection()

        # 查询最后一条用户消息
        query = """
            SELECT message, created_at
            FROM chat_history 
            WHERE session_id = %s 
            AND (message->>'type' = 'human' OR message->'data'->>'type' = 'human')
            ORDER BY created_at DESC 
            LIMIT 1
        """

        with conn.cursor() as cur:
            cur.execute(query, (session_id,))
            row = cur.fetchone()

            if row:
                return row[1]

        return None

    except Exception as e:
        logger.error(f"获取最后用户消息时间失败 {session_id}: {str(e)}")
        return None


# 初始化标志（使用简单的内存标志，重启后需要重新初始化）
_push_system_initialized = False


async def is_push_system_initialized(db: AsyncSession) -> bool:
    """
    检查推送系统是否已初始化

    通过检查是否有用户有推送记录来判断系统是否已初始化。
    如果至少有一个用户有推送记录，则认为系统已初始化。

    Args:
        db: 数据库会话

    Returns:
        是否已初始化
    """
    global _push_system_initialized

    if _push_system_initialized:
        return True

    try:
        # 检查是否有推送记录
        stmt = select(func.count(PushNotificationHistory.id)).limit(1)
        result = await db.execute(stmt)
        count = result.scalar() or 0

        if count > 0:
            _push_system_initialized = True
            return True

        return False

    except Exception as e:
        logger.error(f"检查推送系统初始化状态失败: {str(e)}")
        return False


def mark_push_system_initialized() -> None:
    """标记推送系统已初始化"""
    global _push_system_initialized
    _push_system_initialized = True
    logger.info("推送系统已标记为已初始化")


async def initialize_push_system(db: AsyncSession, batch_size: int = 1000) -> int:
    """
    初始化推送系统：第一次全量查询所有符合条件的用户

    查询所有有 device_token 的用户，确保这些用户都能被推送系统发现。
    不需要创建占位记录，因为未读推送记录数为0时会被查询函数自动发现。

    Args:
        db: 数据库会话
        batch_size: 每次处理的用户数量

    Returns:
        初始化的用户数量
    """
    try:
        logger.info("[初始化] 开始初始化推送系统...")

        # 检查是否已初始化
        if await is_push_system_initialized(db):
            logger.info("[初始化] 推送系统已初始化，跳过")
            return 0

        # 预加载 chat_history 连接（避免后续异步操作中的同步阻塞）
        try:
            get_chat_history_connection()
            logger.info("[初始化] chat_history 连接预加载完成")
        except Exception as e:
            logger.warning(f"[初始化] chat_history 连接预加载失败（可忽略）: {str(e)}")

        # 查询所有有 device_token 的用户
        stmt = (
            select(User.id)
            .join(DeviceToken, User.id == DeviceToken.user_id)
            .where(User.deleted_at.is_(None))
            .distinct()
        )

        result = await db.execute(stmt)
        all_user_ids = [row[0] for row in result.all()]

        total_users = len(all_user_ids)
        logger.info(f"[初始化] 找到 {total_users} 个有 device_token 的用户")

        # 发现新用户（没有推送记录的用户）
        new_users_count = await discover_new_users_for_push(db, batch_size=batch_size)
        logger.info(f"[初始化] 发现 {new_users_count} 个新用户（没有推送记录）")

        # 标记为已初始化
        mark_push_system_initialized()

        logger.info(
            f"[初始化] 推送系统初始化完成，共 {total_users} 个用户，其中 {new_users_count} 个新用户"
        )
        return total_users

    except Exception as e:
        logger.error(f"[初始化] 初始化推送系统失败: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return 0


async def discover_new_users_for_push(
    db: AsyncSession,
    batch_size: int = 1000,
) -> int:
    """
    发现新用户（没有推送记录的用户），为后续推送做准备

    这个函数主要用于定期扫描，确保新用户能够被推送系统发现。
    由于新用户没有推送记录，未读推送记录数为0，会被查询函数自动发现。

    Args:
        db: 数据库会话
        batch_size: 每次处理的用户数量

    Returns:
        发现的新用户数量
    """
    try:
        # 查询有 device_token 但没有推送记录的用户
        stmt = (
            select(User.id)
            .join(DeviceToken, User.id == DeviceToken.user_id)
            .outerjoin(
                PushNotificationHistory,
                User.id == PushNotificationHistory.user_id,
            )
            .where(
                and_(
                    User.deleted_at.is_(None),
                    PushNotificationHistory.id.is_(None),  # 没有推送记录
                )
            )
            .distinct()
            .limit(batch_size)
        )

        result = await db.execute(stmt)
        new_user_ids = [row[0] for row in result.all()]

        logger.info(f"[用户维度] 发现 {len(new_user_ids)} 个新用户（没有推送记录）")

        # 新用户不需要创建初始推送记录，因为未读推送记录数为0时会被查询函数自动发现
        # 这里只是记录日志，方便监控

        return len(new_user_ids)

    except Exception as e:
        logger.error(f"发现新用户失败: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return 0


async def discover_users_with_updated_tokens(
    db: AsyncSession,
    batch_size: int = 1000,
) -> int:
    """
    发现已更新 token 的用户（之前被标记为无效 token，但现在有新的 token）

    这个函数主要用于定期扫描，检查被标记为无效 token 的用户是否更新了 token。
    如果用户有新的 device_token（updated_at > fcm_token_invalid_at），则清除标记。

    使用循环处理机制，确保所有被标记的用户都能被处理。

    Args:
        db: 数据库会话
        batch_size: 每次处理的用户数量

    Returns:
        清除标记的用户数量
    """
    try:
        total_cleared_count = 0
        total_processed_count = 0
        max_iterations = 100  # 最大循环次数，防止无限循环
        iteration = 0

        logger.info(
            f"[token 更新扫描] 开始扫描已更新 token 的用户，批次大小: {batch_size}"
        )

        while iteration < max_iterations:
            iteration += 1

            # 查询被标记为无效 token 的用户（每次查询 batch_size 个）
            stmt = (
                select(User.id, User.fcm_token_invalid_at)
                .where(
                    and_(
                        User.deleted_at.is_(None),
                        User.fcm_token_invalid_at.isnot(None),
                    )
                )
                .order_by(
                    User.fcm_token_invalid_at.asc()
                )  # 按标记时间排序，优先处理较早标记的用户
                .limit(batch_size)
            )

            result = await db.execute(stmt)
            users_with_invalid_tokens = result.all()

            if not users_with_invalid_tokens:
                # 没有更多用户需要处理，退出循环
                if iteration == 1:
                    logger.debug("[token 更新扫描] 没有发现被标记为无效 token 的用户")
                else:
                    logger.info(
                        f"[token 更新扫描] 所有用户已处理完成，共处理 {total_processed_count} 个用户，清除 {total_cleared_count} 个标记"
                    )
                break

            batch_cleared_count = 0
            batch_processed_count = len(users_with_invalid_tokens)
            total_processed_count += batch_processed_count

            logger.debug(
                f"[token 更新扫描] 第 {iteration} 批: 处理 {batch_processed_count} 个用户"
            )

            for user_id, fcm_token_invalid_at in users_with_invalid_tokens:
                try:
                    # 检查用户是否有新的 device_token（updated_at > fcm_token_invalid_at）
                    device_token_stmt = (
                        select(DeviceToken.id)
                        .where(DeviceToken.user_id == user_id)
                        .where(DeviceToken.updated_at > fcm_token_invalid_at)
                        .limit(1)
                    )
                    device_token_result = await db.execute(device_token_stmt)
                    has_new_token = device_token_result.first() is not None

                    if has_new_token:
                        # 清除标记
                        update_stmt = (
                            update(User)
                            .where(User.id == user_id)
                            .values(fcm_token_invalid_at=None)
                        )
                        await db.execute(update_stmt)
                        batch_cleared_count += 1
                        logger.debug(
                            f"[token 更新扫描] 用户已更新 token，清除无效标记: user_id={user_id}, "
                            f"invalid_at={fcm_token_invalid_at.isoformat()}"
                        )

                except Exception as e:
                    logger.error(
                        f"[token 更新扫描] 处理用户失败: user_id={user_id}, error={str(e)}"
                    )
                    continue

            # 每批处理完后立即提交事务，确保已处理的用户标记被清除
            if batch_cleared_count > 0:
                try:
                    await db.commit()
                    total_cleared_count += batch_cleared_count
                    logger.debug(
                        f"[token 更新扫描] 第 {iteration} 批完成: 清除 {batch_cleared_count} 个用户的无效 token 标记"
                    )
                except Exception as e:
                    logger.error(f"[token 更新扫描] 提交事务失败: error={str(e)}")
                    await db.rollback()
                    # 继续处理下一批，不中断整个流程

            # 如果本批处理的用户数量少于 batch_size，说明已经处理完所有用户
            if batch_processed_count < batch_size:
                logger.info(
                    f"[token 更新扫描] 所有用户已处理完成，共处理 {total_processed_count} 个用户，清除 {total_cleared_count} 个标记"
                )
                break

        if iteration >= max_iterations:
            logger.warning(
                f"[token 更新扫描] 达到最大循环次数限制 ({max_iterations})，停止处理。"
                f"已处理 {total_processed_count} 个用户，清除 {total_cleared_count} 个标记"
            )

        if total_cleared_count > 0:
            logger.info(
                f"[token 更新扫描] 扫描完成: 共处理 {total_processed_count} 个用户，清除 {total_cleared_count} 个用户的无效 token 标记"
            )

        return total_cleared_count

    except Exception as e:
        logger.error(f"[token 更新扫描] 扫描失败: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        await db.rollback()
        return 0


async def get_user_unread_push_count(
    db: AsyncSession,
    user_id: str,
) -> int:
    """
    统计用户的未读推送记录数

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        未读推送记录数
    """
    try:
        stmt = select(func.count(PushNotificationHistory.id)).where(
            and_(
                PushNotificationHistory.user_id == user_id,
                PushNotificationHistory.read_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0
        return count
    except Exception as e:
        logger.error(f"统计用户未读推送记录数失败: user_id={user_id}, error={str(e)}")
        return 0


async def has_sent_push_for_stage(
    db: AsyncSession,
    chat_id: str,
    stage: str,
    push_type: str = PUSH_TYPE_RECENT_CHAT,
    last_message_time: Optional[datetime.datetime] = None,
) -> bool:
    """
    检查是否已发送过对应阶段的推送（未读且推送时间在最后消息时间之后）

    Args:
        db: 数据库会话
        chat_id: 聊天ID
        stage: 推送阶段 (10min, 30min, 2h)
        push_type: 推送类型
        last_message_time: 最后消息时间（如果提供，只检查推送时间在最后消息时间之后的记录）

    Returns:
        是否已发送过未读推送
    """
    try:
        conditions = [
            PushNotificationHistory.chat_id == chat_id,
            PushNotificationHistory.stage == stage,
            PushNotificationHistory.push_type == push_type,
            PushNotificationHistory.read_at.is_(None),  # 只查询未读推送
        ]

        # 如果提供了最后消息时间，只检查推送时间在最后消息时间之后的记录
        if last_message_time is not None:
            conditions.append(PushNotificationHistory.sent_at > last_message_time)

        stmt = select(PushNotificationHistory).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None
    except Exception as e:
        logger.error(f"检查推送历史失败: {str(e)}")
        return True  # 出错时返回 True，避免重复发送


async def get_previous_stage_push_time(
    db: AsyncSession,
    user_id: str,
    stage: str,
    push_type: str,
    chat_id: Optional[str] = None,
) -> Optional[datetime.datetime]:
    """
    获取前一个阶段的推送时间

    查询指定用户/聊天在前一个阶段的未读推送记录，返回该推送的 sent_at 时间。
    如果前一个阶段的推送已被标记为已读，则返回 None（因为用户已经回来了）。

    Args:
        db: 数据库会话
        user_id: 用户ID
        stage: 当前推送阶段
        push_type: 推送类型（recent_chat 或 no_chat）
        chat_id: 聊天ID（可选，用于有聊天推送）

    Returns:
        前一个阶段的推送时间（sent_at），如果不存在或已读则返回 None
    """
    try:
        # 获取前一个阶段
        if stage not in STAGE_ORDER:
            logger.error(f"无效的推送阶段: {stage}")
            return None

        stage_index = STAGE_ORDER.index(stage)
        if stage_index == 0:
            # 第一个阶段（10min），没有前一个阶段
            return None

        previous_stage = STAGE_ORDER[stage_index - 1]

        # 构建查询条件
        conditions = [
            PushNotificationHistory.user_id == user_id,
            PushNotificationHistory.stage == previous_stage,
            PushNotificationHistory.push_type == push_type,
            PushNotificationHistory.read_at.is_(None),  # 只查询未读推送
        ]

        # 根据推送类型添加 chat_id 条件
        if push_type == PUSH_TYPE_RECENT_CHAT:
            if chat_id:
                conditions.append(PushNotificationHistory.chat_id == chat_id)
            else:
                # 有聊天推送必须提供 chat_id
                logger.warning(
                    f"有聊天推送未提供 chat_id: user_id={user_id}, stage={stage}"
                )
                return None
        else:
            # 无聊天推送，chat_id 应该为 None
            conditions.append(PushNotificationHistory.chat_id.is_(None))

        # 查询前一个阶段的未读推送记录，按发送时间降序排列，取最新的一条
        stmt = (
            select(PushNotificationHistory)
            .where(and_(*conditions))
            .order_by(PushNotificationHistory.sent_at.desc())
            .limit(1)
        )

        result = await db.execute(stmt)
        previous_push = result.scalar_one_or_none()

        if previous_push:
            return previous_push.sent_at

        return None

    except Exception as e:
        logger.error(
            f"获取前一个阶段推送时间失败: user_id={user_id}, stage={stage}, error={str(e)}"
        )
        return None


async def get_previous_push_messages(
    db: AsyncSession,
    user_id: str,
    stage: str,
    push_type: str,
    chat_id: Optional[str] = None,
) -> List[str]:
    """
    获取之前阶段的推送消息内容列表（用于避免重复生成）

    查询指定用户/聊天在所有之前阶段的未读推送消息内容，用于在生成新推送消息时
    告知 Agent 避免重复。

    Args:
        db: 数据库会话
        user_id: 用户ID
        stage: 当前推送阶段
        push_type: 推送类型（recent_chat 或 no_chat）
        chat_id: 聊天ID（可选，用于有聊天推送）

    Returns:
        之前推送消息内容列表（按时间顺序，从早到晚）
    """
    try:
        # 获取当前阶段在 STAGE_ORDER 中的索引
        if stage not in STAGE_ORDER:
            logger.error(f"无效的推送阶段: {stage}")
            return []

        stage_index = STAGE_ORDER.index(stage)
        if stage_index == 0:
            # 第一个阶段（10min），没有之前的推送消息
            return []

        # 获取所有之前阶段的名称
        previous_stages = STAGE_ORDER[:stage_index]

        # 构建查询条件
        conditions = [
            PushNotificationHistory.user_id == user_id,
            PushNotificationHistory.stage.in_(previous_stages),
            PushNotificationHistory.push_type == push_type,
            PushNotificationHistory.read_at.is_(None),  # 只查询未读推送
            PushNotificationHistory.message_content.isnot(None),  # 确保有消息内容
        ]

        # 根据推送类型添加 chat_id 条件
        if push_type == PUSH_TYPE_RECENT_CHAT:
            if chat_id:
                conditions.append(PushNotificationHistory.chat_id == chat_id)
            else:
                # 有聊天推送必须提供 chat_id
                logger.warning(
                    f"有聊天推送未提供 chat_id: user_id={user_id}, stage={stage}"
                )
                return []
        else:
            # 无聊天推送，chat_id 应该为 None
            conditions.append(PushNotificationHistory.chat_id.is_(None))

        # 查询之前阶段的未读推送记录，按发送时间升序排列（从早到晚）
        stmt = (
            select(PushNotificationHistory.message_content)
            .where(and_(*conditions))
            .order_by(PushNotificationHistory.sent_at.asc())
        )

        result = await db.execute(stmt)
        messages = result.scalars().all()

        # 过滤掉空消息
        return [msg for msg in messages if msg and msg.strip()]

    except Exception as e:
        logger.error(
            f"获取之前推送消息内容失败: user_id={user_id}, stage={stage}, error={str(e)}"
        )
        return []


# ============================================================================
# 工具函数
# ============================================================================


def format_push_message(content: str, max_length: int = 100) -> str:
    """
    格式化推送消息（截取长度、添加省略号）

    Args:
        content: 原始消息内容
        max_length: 最大长度

    Returns:
        格式化后的消息
    """
    if not content:
        return ""

    if len(content) <= max_length:
        return content

    return content[: max_length - 3] + "..."


async def get_chats_needing_push(
    db: AsyncSession,
    stage: str,
    time_delta_minutes: int,
    batch_size: int = 50,
) -> List[Chat]:
    """
    查询需要推送的聊天会话

    Args:
        db: 数据库会话
        stage: 推送阶段 (10min, 30min, 2h)
        time_delta_minutes: 距离最后消息的时间（分钟）
        batch_size: 批次大小

    Returns:
        需要推送的聊天列表
    """
    try:
        # 计算时间阈值
        threshold_time = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(minutes=time_delta_minutes)

        # 查询所有活跃的聊天会话
        stmt = (
            select(Chat)
            .join(Agent, Chat.agent_id == Agent.id)
            .join(User, Chat.user_id == User.id)
            .where(
                and_(
                    Chat.is_active == True,
                    Agent.deleted_at.is_(None),
                    User.deleted_at.is_(None),
                )
            )
            .limit(batch_size)
        )

        result = await db.execute(stmt)
        all_chats = result.scalars().all()

        # 过滤出需要推送的聊天
        chats_needing_push = []
        for chat in all_chats:
            try:
                # 检查是否已发送过该阶段的推送
                if await has_sent_push_for_stage(db, chat.id, stage):
                    continue

                # 获取会话ID
                session_id = generate_session_id(chat.id)

                # 获取最后一条用户消息时间
                last_user_message_time = await get_last_user_message_time(session_id)

                if not last_user_message_time:
                    # 没有用户消息，跳过
                    continue

                # 检查时间是否匹配
                if last_user_message_time <= threshold_time:
                    chats_needing_push.append(chat)

            except Exception as e:
                logger.error(f"处理聊天 {chat.id} 时出错: {str(e)}")
                continue

        return chats_needing_push

    except Exception as e:
        logger.error(f"查询需要推送的聊天失败: {str(e)}")
        return []


async def get_agent_avatar_url(
    agent_data: dict,
) -> Optional[str]:
    """
    获取 Agent 头像 URL

    优先使用裁切头像（如果存在 extensions.avatar_crop），
    否则使用独立的 avatar 字段。

    Args:
        agent_data: Agent 数据字典

    Returns:
        Agent 头像 URL，如果不存在则返回 None
    """
    try:
        # 优先检查是否存在裁切数据
        if (
            agent_data.get("background")
            and agent_data.get("extensions")
            and isinstance(agent_data["extensions"], dict)
            and "avatar_crop" in agent_data["extensions"]
        ):
            avatar_crop_data = agent_data["extensions"]["avatar_crop"]

            # 验证裁切数据的完整性
            if (
                isinstance(avatar_crop_data, dict)
                and all(
                    key in avatar_crop_data
                    for key in [
                        "x",
                        "y",
                        "width",
                        "height",
                        "imageWidth",
                        "imageHeight",
                    ]
                )
                and all(
                    isinstance(avatar_crop_data[key], (int, float))
                    for key in [
                        "x",
                        "y",
                        "width",
                        "height",
                        "imageWidth",
                        "imageHeight",
                    ]
                )
                and avatar_crop_data["width"] > 0
                and avatar_crop_data["height"] > 0
            ):
                # 创建 CroppedArea 对象
                cropped_area = image_transform_service.CroppedArea(
                    x=int(avatar_crop_data["x"]),
                    y=int(avatar_crop_data["y"]),
                    width=int(avatar_crop_data["width"]),
                    height=int(avatar_crop_data["height"]),
                    image_width=int(avatar_crop_data["imageWidth"]),
                    image_height=int(avatar_crop_data["imageHeight"]),
                )

                # 使用裁切功能生成头像 URL
                return image_transform_service.transform_cropped_avatar_url(
                    agent_data["background"], cropped_area
                )

        # 如果没有裁切数据但有独立的 avatar，使用常规转换
        avatar = agent_data.get("avatar")
        if avatar:
            return image_transform_service.transform_mobile(avatar)

        return None

    except Exception as e:
        logger.warning(f"获取 Agent 头像 URL 失败: {str(e)}")
        # 如果裁切失败，尝试使用独立的 avatar
        avatar = agent_data.get("avatar")
        if avatar:
            try:
                return image_transform_service.transform_mobile(avatar)
            except Exception:
                return avatar
        return None


# ============================================================================
# 消息生成与推送
# ============================================================================


async def _save_push_message_to_history(
    db: AsyncSession,
    user_id: str,
    agent_id: str,
    stage: str,
    push_type: str,
    message_content: str,
    chat_id: Optional[str] = None,
) -> bool:
    """
    保存推送消息到聊天历史

    Args:
        db: 数据库会话
        user_id: 用户ID
        agent_id: Agent ID
        stage: 推送阶段
        push_type: 推送类型
        message_content: 消息内容
        chat_id: 聊天ID（可选）

    Returns:
        是否保存成功
    """
    try:
        # 生成会话ID
        if chat_id:
            session_id = generate_session_id(chat_id)
        else:
            session_id = str(agent_id)

        # 构建推送元数据
        push_meta_data = {
            "isPushMessage": True,
            "pushStage": stage,
            "pushType": push_type,
        }

        # 保存AI消息
        await add_ai_message(
            db=db,
            session_id=session_id,
            message=message_content,
            agent_id=agent_id,
            meta_data=push_meta_data,
        )
        logger.debug(
            f"推送消息已保存到聊天历史: user_id={user_id}, agent_id={agent_id}, "
            f"session_id={session_id}, stage={stage}, push_type={push_type}"
        )
        return True
    except Exception as e:
        logger.warning(
            f"保存推送消息到聊天历史失败: user_id={user_id}, agent_id={agent_id}, "
            f"error={str(e)}"
        )
        return False


async def generate_agent_message(
    db: AsyncSession,
    user_id: str,
    agent_id: str,
    stage: str,
    push_type: str = PUSH_TYPE_RECENT_CHAT,
    agent_data: Optional[dict] = None,
    chat_id: Optional[str] = None,
    save_to_history: bool = False,
) -> Optional[str]:
    """
    使用 Agent 生成主动消息

    Args:
        db: 数据库会话
        user_id: 用户ID
        agent_id: Agent ID
        stage: 推送阶段 (10min, 30min, 2h, 24h, 48h)
        push_type: 推送类型 (PUSH_TYPE_RECENT_CHAT 或 PUSH_TYPE_NO_CHAT)
        agent_data: Agent 数据字典（可选，如果未提供则从数据库获取）
        chat_id: 聊天ID（可选，用于 recent_chat 类型）
        save_to_history: 是否保存消息到聊天历史，默认为 False

    Returns:
        生成的消息内容，失败时返回 None
    """
    try:
        # 获取 Agent 数据（如果未提供）
        if agent_data is None:
            agent_data = await agent_service.get_agent_for_chat(db, agent_id=agent_id)
            if not agent_data:
                logger.error(f"Agent数据未找到: {agent_id}")
                return None

        # 获取 Agent 实例
        agent = await agent_manager.get_agent(agent_data)
        if not agent:
            logger.error(f"Agent实例获取失败: {agent_id}")
            return None

        # 获取用户信息（昵称 + 订阅/超级用户状态判定）
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            logger.warning(f"用户不存在，无法生成推送消息: user_id={user_id}")
            return None
        user_nickname = user.nickname or "You"
        subscription = await subscription_service.get_user_current_subscription(
            db, user_id
        )
        model_override = select_chat_model(user=user, is_subscribed=bool(subscription))

        # 查询之前的推送消息内容（用于避免重复生成）
        previous_push_messages = await get_previous_push_messages(
            db=db,
            user_id=user_id,
            stage=stage,
            push_type=push_type,
            chat_id=chat_id,
        )

        # 根据推送类型构建不同的提示词
        if push_type == PUSH_TYPE_NO_CHAT:
            # 欢迎消息
            prompt = build_welcome_message_prompt(
                agent_name=agent_data.get("name", "角色"),
                user_name=user_nickname,
            )
            # 对于无聊天推送，使用 agent_id 作为 session_id（临时会话）
            session_id = str(agent_id)
        else:
            # 主动消息
            prompt = build_simple_push_message_prompt(
                agent_name=agent_data.get("name", "角色"),
                user_name=user_nickname,
                time_since_last_message=stage,
                previous_push_messages=previous_push_messages,
            )
            # 生成会话ID
            if chat_id:
                session_id = generate_session_id(chat_id)
            else:
                session_id = str(agent_id)

        # 调用 Agent 生成消息（不保存用户消息）
        messages = [HumanMessage(content=prompt)]

        # 获取聊天设置（如果有 chat_id）
        chat_settings = None
        if chat_id:
            chat_settings = await chat_service.get_or_create_chat_settings(
                db, chat_id, user_id, agent_id
            )

        # 使用新方法生成消息（不保存用户消息）
        # user_profile 为 None 时，方法内部会自动获取
        gen_result = await agent.generate_message_without_user_save(
            user_id=user_id,
            session_id=session_id,
            messages=messages,
            user_profile=None,
            chat_settings=chat_settings,
            model_override=model_override,
            is_subscribed=bool(subscription),
        )

        if not gen_result:
            logger.warning(f"Agent未生成消息: user_id={user_id}, agent_id={agent_id}")
            return None

        response_content, trace_id = (
            gen_result if isinstance(gen_result, tuple) else (gen_result, None)
        )
        response_content = response_content.strip() if response_content else ""

        if not response_content:
            return None

        # 根据参数决定是否保存AI消息到聊天历史
        if save_to_history:
            try:
                # 构建推送元数据
                push_meta_data: dict = {
                    "isPushMessage": True,
                    "pushStage": stage,
                    "pushType": push_type,
                }
                if trace_id:
                    push_meta_data["langsmith_trace_id"] = trace_id

                # 保存AI消息
                await add_ai_message(
                    db=db,
                    session_id=session_id,
                    message=response_content,
                    agent_id=agent_id,
                    meta_data=push_meta_data,
                )
                logger.debug(
                    f"推送消息已保存到聊天历史: user_id={user_id}, agent_id={agent_id}, "
                    f"session_id={session_id}, stage={stage}, push_type={push_type}"
                )
            except Exception as e:
                logger.warning(
                    f"保存推送消息到聊天历史失败: user_id={user_id}, agent_id={agent_id}, "
                    f"error={str(e)}"
                )
                # 即使保存失败，也返回生成的消息内容

        return response_content

    except Exception as e:
        logger.error(
            f"生成Agent消息失败: user_id={user_id}, agent_id={agent_id}, error={str(e)}"
        )
        return None


async def send_push_notification(
    db: AsyncSession,
    user_id: str,
    agent_id: str,
    agent_name: str,
    message_content: str,
    stage: str,
    agent_avatar_url: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> bool:
    """
    发送 FCM 推送通知

    Args:
        db: 数据库会话
        user_id: 用户ID
        agent_id: Agent ID
        agent_name: 角色名称
        message_content: 消息内容
        stage: 推送阶段
        agent_avatar_url: Agent 头像 URL（可选）
        chat_id: 聊天ID（可选）

    Returns:
        是否发送成功
    """
    try:
        # 格式化消息内容
        formatted_body = format_push_message(message_content, max_length=100)

        # 构建推送数据
        push_data = {
            "agent_id": agent_id,
            "type": "agent_message",
            "stage": stage,
        }
        if chat_id:
            push_data["chat_id"] = chat_id

        # 转换头像 URL 为 CDN URL（如果提供）
        image_url = None
        if agent_avatar_url:
            try:
                image_url = image_transform_service.transform_mobile(agent_avatar_url)
            except Exception as e:
                logger.warning(
                    f"头像 URL 转换失败: {agent_avatar_url}, error={str(e)}, 使用原始 URL"
                )
                image_url = agent_avatar_url

        # 发送推送
        success = await notification_service.send_fcm_multicast(
            db=db,
            user_ids=[user_id],
            title=agent_name,
            body=formatted_body,
            data=push_data,
            image_url=image_url,
        )

        return success

    except Exception as e:
        logger.error(
            f"发送推送失败: user_id={user_id}, agent_id={agent_id}, error={str(e)}"
        )
        return False


async def send_festival_memory_push(
    db: AsyncSession,
    user_id: str,
    agent_id: str,
    agent_name: str,
    agent_avatar_url: Optional[str] = None,
    festival_memory_id: Optional[int] = None,
) -> bool:
    """
    发送节日记忆 FCM 推送（Love Journal 通知）。
    data 含 type=festival_memory、agent_id、festival_memory_id（字符串，与 App 键名一致）。
    """
    try:
        title = f"{agent_name} wrote you a secret Heartbeat Journal."
        body = "Take a quiet look."
        push_data = {
            "agent_id": agent_id,
            "type": "festival_memory",
        }
        if festival_memory_id is not None:
            push_data["festival_memory_id"] = str(festival_memory_id)

        image_url = None
        if agent_avatar_url:
            try:
                image_url = image_transform_service.transform_mobile(agent_avatar_url)
            except Exception as e:
                logger.warning(
                    f"头像 URL 转换失败: {agent_avatar_url}, error={str(e)}, 使用原始 URL"
                )
                image_url = agent_avatar_url

        success = await notification_service.send_fcm_multicast(
            db=db,
            user_ids=[user_id],
            title=title,
            body=body,
            data=push_data,
            image_url=image_url,
        )
        return success
    except Exception as e:
        logger.error(
            f"发送节日记忆推送失败: user_id={user_id}, agent_id={agent_id}, error={str(e)}"
        )
        return False


async def record_push_history(
    db: AsyncSession,
    user_id: str,
    agent_id: str,
    stage: str,
    push_type: str,
    message_content: Optional[str],
    sent_at: datetime.datetime,
    chat_id: Optional[str] = None,
) -> bool:
    """
    记录推送历史（使用 INSERT ... ON CONFLICT DO NOTHING 防止重复）

    Args:
        db: 数据库会话
        user_id: 用户ID
        agent_id: Agent ID
        stage: 推送阶段
        push_type: 推送类型
        message_content: 消息内容
        sent_at: 发送时间
        chat_id: 聊天ID（可选）

    Returns:
        是否成功记录（如果已存在则返回 False）
    """
    try:
        # 先尝试插入，如果唯一约束冲突则说明已存在
        push_history = PushNotificationHistory(
            id=uid("push"),
            chat_id=chat_id,
            user_id=user_id,
            agent_id=agent_id,
            stage=stage,
            push_type=push_type,
            message_content=message_content,
            sent_at=sent_at,
        )

        db.add(push_history)
        await db.commit()
        return True

    except Exception as e:
        # 检查是否是唯一约束冲突
        error_str = str(e).lower()
        if "unique" in error_str or "duplicate" in error_str:
            logger.debug(
                f"推送历史已存在: user_id={user_id}, chat_id={chat_id}, stage={stage}, push_type={push_type}"
            )
            await db.rollback()
            return False
        else:
            logger.error(f"记录推送历史失败: user_id={user_id}, error={str(e)}")
            await db.rollback()
            return False


async def reset_user_read_push_notifications(
    db: AsyncSession,
    user_id: str,
) -> int:
    """
    统计用户的已读推送记录数（用于重置推送状态判断）

    当用户不聊了时，统计已读推送记录数。由于未读计数只统计 read_at IS NULL 的记录，
    已读记录不影响未读计数，所以不需要删除记录，保留历史数据用于统计和分析。

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        已读推送记录数
    """
    try:
        # 统计所有已读推送记录数
        stmt = select(func.count(PushNotificationHistory.id)).where(
            and_(
                PushNotificationHistory.user_id == user_id,
                PushNotificationHistory.read_at.isnot(None),  # 只统计已读推送
            )
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0

        if count > 0:
            logger.debug(f"[用户维度] 用户有 {count} 条已读推送记录: user_id={user_id}")

        return count

    except Exception as e:
        logger.error(f"统计用户已读推送记录数失败: user_id={user_id}, error={str(e)}")
        return 0


async def mark_user_push_notifications_as_read(
    db: AsyncSession,
    user_id: str,
) -> int:
    """
    将指定用户的所有未读推送标记为已读（用户发送新消息时调用）

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        标记为已读的推送数量
    """
    try:
        read_at = datetime.datetime.now(datetime.timezone.utc)
        stmt = select(PushNotificationHistory).where(
            and_(
                PushNotificationHistory.user_id == user_id,
                PushNotificationHistory.read_at.is_(None),  # 只更新未读推送
            )
        )
        result = await db.execute(stmt)
        unread_notifications = result.scalars().all()

        if not unread_notifications:
            return 0

        # 批量更新为已读
        count = 0
        for notification in unread_notifications:
            notification.read_at = read_at
            count += 1

        await db.commit()
        logger.info(f"[用户维度] 标记用户推送为已读: user_id={user_id}, count={count}")
        return count

    except Exception as e:
        logger.error(f"标记用户推送为已读失败: user_id={user_id}, error={str(e)}")
        await db.rollback()
        return 0


# ============================================================================
# 推送处理函数
# ============================================================================


async def process_single_user_recent_chat_push(
    db: AsyncSession,
    user_id: str,
    chat_id: str,
    agent_id: str,
    stage: str,
    last_message_time: datetime.datetime,
) -> Tuple[bool, Optional[str]]:
    """
    处理单个用户的最近聊天推送（使用独立的数据库会话）

    Args:
        db: 数据库会话（独立会话）
        user_id: 用户ID
        chat_id: 聊天ID
        agent_id: Agent ID
        stage: 推送阶段
        last_message_time: 最后消息时间

    Returns:
        (success: bool, error: Optional[str])
    """
    try:
        logger.debug(
            f"[用户维度] 处理单个用户推送: user_id={user_id}, chat_id={chat_id}, agent_id={agent_id}, stage={stage}"
        )

        # 检查用户的未读推送记录数
        unread_count = await get_user_unread_push_count(db, user_id)
        if unread_count >= MAX_UNREAD_PUSH_COUNT:
            logger.debug(
                f"[用户维度] 用户未读推送记录数已达到上限 (>=5)，跳过: user_id={user_id}, unread_count={unread_count}"
            )
            return False, "推送次数已达上限"

        # 检查是否已发送过未读推送（推送时间在最后消息时间之后）
        if await has_sent_push_for_stage(
            db, chat_id, stage, PUSH_TYPE_RECENT_CHAT, last_message_time
        ):
            logger.debug(
                f"[用户维度] 推送已发送过（未读且推送时间在最后消息时间之后），跳过: "
                f"user_id={user_id}, chat_id={chat_id}, stage={stage}, last_message_time={last_message_time.isoformat()}"
            )
            return False, "已发送过推送"

        # 检查是否已存在推送历史（防止重复推送）
        if await has_sent_push_for_stage(
            db, chat_id, stage, PUSH_TYPE_RECENT_CHAT, None
        ):
            logger.debug(
                f"[用户维度] 推送历史已存在，跳过: user_id={user_id}, chat_id={chat_id}, stage={stage}"
            )
            return False, "推送历史已存在"

        # 获取 Agent 数据（用于生成消息和获取头像）
        agent_data = await agent_service.get_agent_for_chat(db, agent_id=agent_id)
        if not agent_data:
            error_msg = f"Agent数据未找到: {agent_id}"
            logger.error(f"[用户维度] {error_msg}")
            return False, error_msg

        # 生成 Agent 消息（不保存到聊天历史）
        message_content = await generate_agent_message(
            db,
            user_id=user_id,
            agent_id=agent_id,
            stage=stage,
            push_type=PUSH_TYPE_RECENT_CHAT,
            agent_data=agent_data,
            chat_id=chat_id,
            save_to_history=False,
        )

        if not message_content:
            error_msg = f"生成消息失败: chat_id={chat_id}"
            logger.warning(f"[用户维度] {error_msg}")
            return False, error_msg

        # 获取 Agent 名称和头像
        agent_name, agent_avatar_url = await _extract_agent_info(agent_data)

        # 发送 FCM 推送
        success = await send_push_notification(
            db,
            user_id=user_id,
            agent_id=agent_id,
            agent_name=agent_name,
            message_content=message_content,
            stage=stage,
            agent_avatar_url=agent_avatar_url,
            chat_id=chat_id,
        )

        if success:
            # FCM 发送成功，保存消息到聊天历史和记录推送历史
            sent_at = datetime.datetime.now(datetime.timezone.utc)

            # 保存消息到聊天历史
            history_saved = await _save_push_message_to_history(
                db=db,
                user_id=user_id,
                agent_id=agent_id,
                stage=stage,
                push_type=PUSH_TYPE_RECENT_CHAT,
                message_content=message_content,
                chat_id=chat_id,
            )

            if not history_saved:
                logger.warning(
                    f"[用户维度] 保存消息到聊天历史失败，但推送已发送: user_id={user_id}, chat_id={chat_id}"
                )

            # 记录推送历史
            await record_push_history(
                db=db,
                user_id=user_id,
                agent_id=agent_id,
                stage=stage,
                push_type=PUSH_TYPE_RECENT_CHAT,
                message_content=message_content,
                sent_at=sent_at,
                chat_id=chat_id,
            )

            logger.info(
                f"[用户维度] 推送成功: user_id={user_id}, chat_id={chat_id}, agent_id={agent_id}, "
                f"agent_name={agent_name}, stage={stage}, message_preview={message_content[:50]}..."
            )
            return True, None
        else:
            # FCM 发送失败，不保存消息，不记录推送历史
            error_msg = f"推送发送失败: user_id={user_id}, chat_id={chat_id}"
            logger.warning(f"[用户维度] {error_msg}")
            return False, error_msg

    except Exception as e:
        error_msg = (
            f"处理推送任务失败: user_id={user_id}, chat_id={chat_id}, error={str(e)}"
        )
        logger.error(f"[用户维度] {error_msg}")
        import traceback

        logger.error(traceback.format_exc())
        return False, error_msg


async def process_single_user_no_chat_push(
    db: AsyncSession,
    user_id: str,
    agent_id: str,
    stage: str,
) -> Tuple[bool, Optional[str]]:
    """
    处理单个用户的无聊天推送（使用独立的数据库会话）

    Args:
        db: 数据库会话（独立会话）
        user_id: 用户ID
        agent_id: Agent ID
        stage: 推送阶段

    Returns:
        (success: bool, error: Optional[str])
    """
    try:
        logger.debug(
            f"[用户维度] 处理单个无聊天用户推送: user_id={user_id}, agent_id={agent_id}, stage={stage}"
        )

        # 检查用户的未读推送记录数
        unread_count = await get_user_unread_push_count(db, user_id)
        if unread_count >= MAX_UNREAD_PUSH_COUNT:
            logger.debug(
                f"[用户维度] 用户未读推送记录数已达到上限 (>=5)，跳过: user_id={user_id}, unread_count={unread_count}"
            )
            return False, "推送次数已达上限"

        # 检查是否已发送过推送
        if await has_sent_push_for_user_stage(db, user_id, stage, PUSH_TYPE_NO_CHAT):
            logger.debug(
                f"[用户维度] 推送已发送过，跳过: user_id={user_id}, stage={stage}"
            )
            return False, "已发送过推送"

        # 获取 Agent 数据
        agent_data = await agent_service.get_agent_for_chat(db, agent_id=agent_id)
        if not agent_data:
            error_msg = f"Agent数据未找到: {agent_id}"
            logger.error(f"[用户维度] {error_msg}")
            return False, error_msg

        # 生成 Agent 消息（不保存到聊天历史）
        message_content = await generate_agent_message(
            db,
            user_id=user_id,
            agent_id=agent_id,
            stage=stage,
            push_type=PUSH_TYPE_NO_CHAT,
            agent_data=agent_data,
            chat_id=None,
            save_to_history=False,
        )

        if not message_content:
            error_msg = f"生成消息失败: user_id={user_id}, agent_id={agent_id}"
            logger.warning(f"[用户维度] {error_msg}")
            return False, error_msg

        # 获取 Agent 名称和头像
        agent_name, agent_avatar_url = await _extract_agent_info(agent_data)

        # 发送 FCM 推送
        success = await send_push_notification(
            db,
            user_id=user_id,
            agent_id=agent_id,
            agent_name=agent_name,
            message_content=message_content,
            stage=stage,
            agent_avatar_url=agent_avatar_url,
            chat_id=None,
        )

        if success:
            # FCM 发送成功，保存消息到聊天历史和记录推送历史
            sent_at = datetime.datetime.now(datetime.timezone.utc)

            # 保存消息到聊天历史
            history_saved = await _save_push_message_to_history(
                db=db,
                user_id=user_id,
                agent_id=agent_id,
                stage=stage,
                push_type=PUSH_TYPE_NO_CHAT,
                message_content=message_content,
                chat_id=None,
            )

            if not history_saved:
                logger.warning(
                    f"[用户维度] 保存消息到聊天历史失败，但推送已发送: user_id={user_id}, agent_id={agent_id}"
                )

            # 记录推送历史
            await record_push_history(
                db=db,
                user_id=user_id,
                agent_id=agent_id,
                stage=stage,
                push_type=PUSH_TYPE_NO_CHAT,
                message_content=message_content,
                sent_at=sent_at,
                chat_id=None,
            )

            logger.info(
                f"[用户维度] 无聊天推送成功: user_id={user_id}, agent_id={agent_id}, agent_name={agent_name}, "
                f"stage={stage}, message_preview={message_content[:50]}..."
            )
            return True, None
        else:
            # FCM 发送失败，不保存消息，不记录推送历史
            error_msg = f"推送发送失败: user_id={user_id}, agent_id={agent_id}"
            logger.warning(f"[用户维度] {error_msg}")
            return False, error_msg

    except Exception as e:
        error_msg = (
            f"处理推送任务失败: user_id={user_id}, agent_id={agent_id}, error={str(e)}"
        )
        logger.error(f"[用户维度] {error_msg}")
        import traceback

        logger.error(traceback.format_exc())
        return False, error_msg


async def process_single_user_push(
    db: AsyncSession,
    user_id: str,
    stage: str,
    chat: Optional[Chat] = None,
    agent: Optional[Agent] = None,
    last_message_time: Optional[datetime.datetime] = None,
) -> Tuple[bool, Optional[str]]:
    """
    统一处理单个用户的推送（有聊天和无聊天统一处理）

    Args:
        db: 数据库会话（独立会话）
        user_id: 用户ID
        stage: 推送阶段 (10min, 30min, 2h, 24h, 48h)
        chat: 聊天对象（如果有活跃聊天）
        agent: Agent对象（用于无聊天推送，如果有活跃聊天则从chat中获取）
        last_message_time: 最后消息时间（如果有活跃聊天）

    Returns:
        (success: bool, error: Optional[str])
    """
    try:
        # 确定推送类型和agent_id
        if chat:
            # 有活跃聊天
            push_type = PUSH_TYPE_RECENT_CHAT
            agent_id = chat.agent_id
            chat_id = chat.id
        else:
            # 没有活跃聊天
            push_type = PUSH_TYPE_NO_CHAT
            if not agent:
                error_msg = "无聊天推送需要提供agent对象"
                logger.error(f"{error_msg} (stage={stage})")
                return False, error_msg
            agent_id = agent.id
            chat_id = None

            logger.debug(
                f"处理单个用户推送: user_id={user_id}, stage={stage}, push_type={push_type}, "
                f"chat_id={chat_id}, agent_id={agent_id}"
            )

        # 检查用户的未读推送记录数
        unread_count = await get_user_unread_push_count(db, user_id)
        if unread_count >= MAX_UNREAD_PUSH_COUNT:
            logger.debug(
                f"用户未读推送记录数已达到上限 (>=5)，跳过: user_id={user_id}, stage={stage}, unread_count={unread_count}"
            )
            return False, "推送次数已达上限"

        # 检查是否已发送过推送
        if chat_id:
            # 有聊天：检查是否已发送过未读推送（推送时间在最后消息时间之后）
            if last_message_time and await has_sent_push_for_stage(
                db, chat_id, stage, push_type, last_message_time
            ):
                logger.debug(
                    f"推送已发送过（未读且推送时间在最后消息时间之后），跳过: "
                    f"user_id={user_id}, chat_id={chat_id}, stage={stage}"
                )
                return False, "已发送过推送"
            # 检查是否已存在推送历史（防止重复推送）
            if await has_sent_push_for_stage(db, chat_id, stage, push_type, None):
                logger.debug(
                    f"推送历史已存在，跳过: user_id={user_id}, chat_id={chat_id}, stage={stage}"
                )
                return False, "推送历史已存在"
        else:
            # 无聊天：检查是否已发送过推送
            if await has_sent_push_for_user_stage(db, user_id, stage, push_type):
                logger.debug(f"推送已发送过，跳过: user_id={user_id}, stage={stage}")
                return False, "已发送过推送"

        # 获取 Agent 数据（用于生成消息和获取头像）
        agent_data = await agent_service.get_agent_for_chat(db, agent_id=agent_id)
        if not agent_data:
            error_msg = f"Agent数据未找到: {agent_id}"
            logger.error(f"{error_msg} (stage={stage})")
            return False, error_msg

        # 生成 Agent 消息（不保存到聊天历史）
        message_content = await generate_agent_message(
            db,
            user_id=user_id,
            agent_id=agent_id,
            stage=stage,
            push_type=push_type,
            agent_data=agent_data,
            chat_id=chat_id,
            save_to_history=False,
        )

        if not message_content:
            error_msg = f"生成消息失败: user_id={user_id}, agent_id={agent_id}, chat_id={chat_id}"
            logger.warning(f"{error_msg} (stage={stage})")
            return False, error_msg

        # 获取 Agent 名称和头像
        agent_name, agent_avatar_url = await _extract_agent_info(agent_data)

        # 发送 FCM 推送
        success = await send_push_notification(
            db,
            user_id=user_id,
            agent_id=agent_id,
            agent_name=agent_name,
            message_content=message_content,
            stage=stage,
            agent_avatar_url=agent_avatar_url,
            chat_id=chat_id,
        )

        if success:
            # FCM 发送成功，保存消息到聊天历史和记录推送历史
            sent_at = datetime.datetime.now(datetime.timezone.utc)

            # 保存消息到聊天历史
            history_saved = await _save_push_message_to_history(
                db=db,
                user_id=user_id,
                agent_id=agent_id,
                stage=stage,
                push_type=push_type,
                message_content=message_content,
                chat_id=chat_id,
            )

            if not history_saved:
                logger.warning(
                    f"保存消息到聊天历史失败，但推送已发送: user_id={user_id}, chat_id={chat_id}, agent_id={agent_id}"
                )

            # 记录推送历史
            await record_push_history(
                db=db,
                user_id=user_id,
                agent_id=agent_id,
                stage=stage,
                push_type=push_type,
                message_content=message_content,
                sent_at=sent_at,
                chat_id=chat_id,
            )

            logger.info(
                f"推送成功: user_id={user_id}, chat_id={chat_id}, agent_id={agent_id}, "
                f"agent_name={agent_name}, stage={stage}, push_type={push_type}, message_preview={message_content[:50]}..."
            )
            return True, None
        else:
            # FCM 发送失败，不保存消息，不记录推送历史
            error_msg = f"推送发送失败: user_id={user_id}, chat_id={chat_id}, agent_id={agent_id}"
            logger.warning(f"{error_msg} (stage={stage})")
            return False, error_msg

    except Exception as e:
        error_msg = (
            f"处理推送任务失败: user_id={user_id}, stage={stage}, error={str(e)}"
        )
        logger.error(f"{error_msg} (stage={stage})")
        import traceback

        logger.error(traceback.format_exc())
        return False, error_msg


async def process_push_batch(
    db: AsyncSession,
    stage: str,
    batch_size: int = 50,
) -> Tuple[int, int]:
    """
    统一处理一批推送任务（所有阶段统一处理，使用并发处理）

    Args:
        db: 数据库会话（用于查询）
        stage: 推送阶段 (10min, 30min, 2h, 24h, 48h)
        batch_size: 批次大小

    Returns:
        (成功数量, 失败数量)
    """
    try:
        logger.info(f"开始处理推送批次: stage={stage}, batch_size={batch_size}")

        # 使用统一的查询函数
        users_needing_push = await get_users_needing_push(db, stage, batch_size)

        user_count = len(users_needing_push)
        logger.info(f"找到 {user_count} 个需要推送的用户 (stage={stage})")

        if user_count == 0:
            logger.info(f"没有需要推送的用户 (stage={stage})")
            return 0, 0

        # 计算并发数
        config = global_config_loaded_from_config_yaml.push_notification
        concurrent_workers = min(
            max(1, user_count // config.workers_per_user_ratio),
            config.max_concurrent_workers,
            user_count,
        )

        logger.info(
            f"用户数量: {user_count}, 并发 worker 数: {concurrent_workers} (stage={stage})"
        )

        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(concurrent_workers)

        # Worker 函数：处理单个用户（使用独立的数据库会话）
        async def process_user_worker(
            user, chat, time_ref, agent
        ) -> Tuple[bool, Optional[str]]:
            async with semaphore:
                async with AsyncSessionLocal() as worker_db:
                    try:
                        return await process_single_user_push(
                            db=worker_db,
                            user_id=user.id,
                            stage=stage,
                            chat=chat,
                            agent=agent,
                            last_message_time=time_ref if chat else None,
                        )
                    except Exception as e:
                        error_msg = f"Worker处理失败: user_id={user.id}, stage={stage}, error={str(e)}"
                        logger.error(error_msg)
                        return False, error_msg

        # 并发处理所有用户
        results = await asyncio.gather(
            *[
                process_user_worker(user, chat, time_ref, agent)
                for user, chat, time_ref, agent in users_needing_push
            ],
            return_exceptions=True,
        )

        # 统计结果
        success_count = 0
        fail_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                fail_count += 1
                user, chat, _, agent = users_needing_push[i]
                logger.error(
                    f"处理用户异常: user_id={user.id}, stage={stage}, chat_id={chat.id if chat else None}, error={str(result)}"
                )
            else:
                success, error = result
                if success:
                    success_count += 1
                else:
                    fail_count += 1

        logger.info(
            f"推送批次处理完成: stage={stage}, 成功={success_count}, 失败={fail_count}, 总计={user_count}"
        )
        return success_count, fail_count

    except Exception as e:
        logger.error(f"处理推送批次失败: stage={stage}, error={str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return 0, 0


async def process_festival_memory_push_batch(
    db: AsyncSession,
    batch_size: int = 50,
) -> Tuple[int, int]:
    """
    处理一批节日记忆推送：查询未投递且未发过 system notification 的 (user_id, agent_id)，
    发送 FCM 后记录推送历史并更新 memory.system_notification_sent_at。
    """
    try:
        pairs = await get_pairs_with_undelivered_festival_memories(db, limit=batch_size)
        if not pairs:
            logger.debug("[节日记忆推送] 无待推送的对")
            return 0, 0

        success_count = 0
        fail_count = 0
        for item in pairs:
            user_id = item["user_id"]
            agent_id = item["agent_id"]
            festival_memory_id = item.get("festival_memory_id")
            try:
                if not await _check_user_has_device_token(db, user_id):
                    logger.debug(
                        f"[节日记忆推送] 用户无 device_token，跳过: user_id={user_id}"
                    )
                    fail_count += 1
                    continue
                if not await _user_satisfies_festival_memory_version_gate(db, user_id):
                    logger.debug(
                        "[节日记忆推送] 用户版本不满足门控（未上报或低于 min_app_version_code_for_festival_memory），跳过: user_id=%s",
                        user_id,
                    )
                    fail_count += 1
                    continue
                if await has_sent_festival_push_for_user_agent(db, user_id, agent_id):
                    logger.debug(
                        f"[节日记忆推送] 已发过，跳过: user_id={user_id}, agent_id={agent_id}"
                    )
                    continue

                agent_data = await agent_service.get_agent_for_chat(
                    db, agent_id=agent_id
                )
                if not agent_data:
                    logger.warning(
                        f"[节日记忆推送] Agent 未找到: agent_id={agent_id}, 跳过"
                    )
                    fail_count += 1
                    continue
                agent_name, agent_avatar_url = await _extract_agent_info(agent_data)

                sent = await send_festival_memory_push(
                    db,
                    user_id=user_id,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    agent_avatar_url=agent_avatar_url,
                    festival_memory_id=festival_memory_id,
                )
                if not sent:
                    fail_count += 1
                    continue

                sent_at = datetime.datetime.now(datetime.timezone.utc)
                await record_push_history(
                    db,
                    user_id=user_id,
                    agent_id=agent_id,
                    stage="festival",
                    push_type=PUSH_TYPE_FESTIVAL_MEMORY,
                    message_content=None,
                    sent_at=sent_at,
                    chat_id=None,
                )
                await mark_system_notification_sent_for_user_agent(
                    db, user_id, agent_id
                )
                success_count += 1
                logger.info(
                    f"[节日记忆推送] 成功: user_id={user_id}, agent_id={agent_id}, festival_memory_id={festival_memory_id}"
                )
            except Exception as e:
                fail_count += 1
                logger.error(
                    f"[节日记忆推送] 处理失败: user_id={user_id}, agent_id={agent_id}, error={str(e)}"
                )

        logger.info(
            f"[节日记忆推送] 批次完成: 成功={success_count}, 失败={fail_count}, 总计={len(pairs)}"
        )
        return success_count, fail_count
    except Exception as e:
        logger.error(f"[节日记忆推送] 批次失败: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return 0, 0


async def process_no_chat_push_batch(
    db: AsyncSession,
    stage: str,
    time_delta_hours: int,
    batch_size: int = 50,
) -> Tuple[int, int]:
    """
    处理一批无聊天推送任务（使用并发处理）

    Args:
        db: 数据库会话（用于查询）
        stage: 推送阶段 (如 "24h", "48h")
        time_delta_hours: 距离用户注册的时间（小时）
        batch_size: 批次大小

    Returns:
        (成功数量, 失败数量)
    """
    try:
        logger.info(
            f"[用户维度] 开始处理无聊天推送批次: stage={stage}, time_delta_hours={time_delta_hours}, batch_size={batch_size}"
        )

        # 查询需要推送的用户（以用户为维度）
        users_with_agents = await get_users_needing_no_chat_push(
            db, stage, time_delta_hours, batch_size
        )

        user_count = len(users_with_agents)
        logger.info(
            f"[用户维度] 找到 {user_count} 个需要推送的用户 (stage={stage}, push_type=no_chat)"
        )

        if user_count == 0:
            logger.info(f"[用户维度] 没有需要推送的用户 (stage={stage})")
            return 0, 0

        # 计算并发数
        config = global_config_loaded_from_config_yaml.push_notification
        concurrent_workers = min(
            max(1, user_count // config.workers_per_user_ratio),
            config.max_concurrent_workers,
            user_count,
        )

        logger.info(
            f"[用户维度] 用户数量: {user_count}, 并发 worker 数: {concurrent_workers} (stage={stage})"
        )

        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(concurrent_workers)

        # Worker 函数：处理单个用户（使用独立的数据库会话）
        async def process_user_worker(user, agent) -> Tuple[bool, Optional[str]]:
            async with semaphore:
                async with AsyncSessionLocal() as worker_db:
                    try:
                        return await process_single_user_no_chat_push(
                            db=worker_db,
                            user_id=user.id,
                            agent_id=agent.id,
                            stage=stage,
                        )
                    except Exception as e:
                        error_msg = f"Worker处理失败: user_id={user.id}, error={str(e)}"
                        logger.error(f"[用户维度] {error_msg}")
                        return False, error_msg

        # 并发处理所有用户
        results = await asyncio.gather(
            *[process_user_worker(user, agent) for user, agent in users_with_agents],
            return_exceptions=True,
        )

        # 统计结果
        success_count = 0
        fail_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                fail_count += 1
                user, agent = users_with_agents[i]
                logger.error(
                    f"[用户维度] 处理用户异常: user_id={user.id}, agent_id={agent.id}, error={str(result)}"
                )
            else:
                success, error = result
                if success:
                    success_count += 1
                else:
                    fail_count += 1

        logger.info(
            f"[用户维度] 无聊天推送批次处理完成: stage={stage}, 成功={success_count}, 失败={fail_count}, 总计={user_count}"
        )
        return success_count, fail_count

    except Exception as e:
        logger.error(
            f"[用户维度] 处理无聊天推送批次失败: stage={stage}, error={str(e)}"
        )
        import traceback

        logger.error(traceback.format_exc())
        return 0, 0


async def get_users_without_chats(
    db: AsyncSession,
    limit: int = 100,
) -> List[User]:
    """
    查询没有活跃聊天的用户（有 device_token）

    Args:
        db: 数据库会话
        limit: 返回数量限制

    Returns:
        没有活跃聊天的用户列表
    """
    try:
        # 查询有 device_token 但没有活跃聊天的用户
        stmt = (
            select(User)
            .options(load_only(User.id, User.created_at, User.deleted_at))
            .join(DeviceToken, User.id == DeviceToken.user_id)
            .outerjoin(
                Chat,
                and_(
                    Chat.user_id == User.id,
                    Chat.is_active == True,
                ),
            )
            .where(
                and_(
                    User.deleted_at.is_(None),
                    Chat.id.is_(None),  # 没有活跃聊天
                )
            )
            .group_by(User.id)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return result.scalars().all()

    except Exception as e:
        logger.error(f"查询没有聊天的用户失败: {str(e)}")
        return []


async def get_user_recent_chat(
    db: AsyncSession,
    user_id: str,
    stage: Optional[str] = None,
) -> Optional[Tuple[Chat, datetime.datetime]]:
    """
    获取用户最近聊天的角色和最后消息时间（以用户为维度）

    Args:
        db: 数据库会话
        user_id: 用户ID
        stage: 推送阶段（可选，用于日志）

    Returns:
        (聊天对象, 最后用户消息时间) 的元组，如果没有聊天则返回 None
    """
    try:
        stage_info = f", stage={stage}" if stage else ""
        logger.debug(f"[用户维度] 获取用户最近聊天: user_id={user_id}{stage_info}")

        # 查询用户的所有活跃聊天
        stmt = (
            select(Chat)
            .join(Agent, Chat.agent_id == Agent.id)
            .where(
                and_(
                    Chat.user_id == user_id,
                    Chat.is_active == True,
                    Agent.deleted_at.is_(None),
                )
            )
        )

        result = await db.execute(stmt)
        chats = result.scalars().all()

        if not chats:
            stage_info = f", stage={stage}" if stage else ""
            logger.debug(f"[用户维度] 用户没有活跃聊天: user_id={user_id}{stage_info}")
            return None

        stage_info = f", stage={stage}" if stage else ""
        logger.debug(
            f"[用户维度] 用户有 {len(chats)} 个活跃聊天: user_id={user_id}{stage_info}"
        )

        # 获取每个聊天的最后用户消息时间
        chat_with_times = []
        for chat in chats:
            session_id = generate_session_id(chat.id)
            last_user_message_time = await get_last_user_message_time(session_id)

            if last_user_message_time:
                chat_with_times.append((chat, last_user_message_time))
                stage_info = f", stage={stage}" if stage else ""
                logger.debug(
                    f"[用户维度] 聊天有用户消息: user_id={user_id}, chat_id={chat.id}, "
                    f"agent_id={chat.agent_id}, last_message_time={last_user_message_time.isoformat()}{stage_info}"
                )

        if not chat_with_times:
            stage_info = f", stage={stage}" if stage else ""
            logger.debug(
                f"[用户维度] 用户所有聊天都没有用户消息: user_id={user_id}{stage_info}"
            )
            return None

        # 按最后消息时间排序，返回最近的
        chat_with_times.sort(key=lambda x: x[1], reverse=True)
        recent_chat, last_message_time = chat_with_times[0]

        stage_info = f", stage={stage}" if stage else ""
        logger.debug(
            f"[用户维度] 找到用户最近聊天: user_id={user_id}, chat_id={recent_chat.id}, "
            f"agent_id={recent_chat.agent_id}, last_message_time={last_message_time.isoformat()}{stage_info}"
        )
        return recent_chat, last_message_time

    except Exception as e:
        stage_info = f", stage={stage}" if stage else ""
        logger.error(
            f"[用户维度] 获取用户最近聊天失败: user_id={user_id}{stage_info}, error={str(e)}"
        )
        import traceback

        logger.error(traceback.format_exc())
        return None


async def get_popular_agent(
    db: AsyncSession,
    limit: int = 1,
) -> Optional[Agent]:
    """
    获取热门角色（基于 score）

    Args:
        db: 数据库会话
        limit: 返回数量限制

    Returns:
        热门角色，如果没有则返回 None
    """
    try:
        # 基于 score 排序，从 meta_data->>'score' 读取
        stmt = (
            select(Agent)
            .where(
                and_(
                    Agent.visibility == AgentVisibility.PUBLIC,
                    Agent.deleted_at.is_(None),
                )
            )
            .order_by(
                func.coalesce(
                    Agent.meta_data.op("->>")(text("'score'")).cast(Integer), 0
                ).desc(),
                Agent.created_at.desc(),  # 作为第二排序字段
            )
            .limit(limit)
        )

        result = await db.execute(stmt)
        agents = result.scalars().all()

        if agents:
            agent = agents[0]
            logger.debug(
                f"[用户维度] 找到热门角色: agent_id={agent.id}, name={agent.name}, "
                f"score={agent.meta_data.get('score') if agent.meta_data else 'None'}"
            )
            return agent
        else:
            logger.warning("[用户维度] 没有找到热门角色")
            return None

    except Exception as e:
        logger.error(f"[用户维度] 获取热门角色失败: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return None


async def has_sent_push_for_user_stage(
    db: AsyncSession,
    user_id: str,
    stage: str,
    push_type: str,
) -> bool:
    """
    检查用户是否已发送过对应阶段的推送（用于无聊天推送，只查询未读推送）

    Args:
        db: 数据库会话
        user_id: 用户ID
        stage: 推送阶段
        push_type: 推送类型

    Returns:
        是否已发送过未读推送
    """
    try:
        stmt = select(PushNotificationHistory).where(
            and_(
                PushNotificationHistory.user_id == user_id,
                PushNotificationHistory.stage == stage,
                PushNotificationHistory.push_type == push_type,
                PushNotificationHistory.chat_id.is_(None),
                PushNotificationHistory.read_at.is_(None),  # 只查询未读推送
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None
    except Exception as e:
        logger.error(f"检查推送历史失败: {str(e)}")
        return True  # 出错时返回 True，避免重复发送


async def has_sent_festival_push_for_user_agent(
    db: AsyncSession,
    user_id: str,
    agent_id: str,
) -> bool:
    """
    检查是否已对该 (user_id, agent_id) 发送过节日记忆推送。

    Returns:
        是否已发送过（存在 PushNotificationHistory 且 push_type == PUSH_TYPE_FESTIVAL_MEMORY）
    """
    try:
        stmt = (
            select(PushNotificationHistory.id)
            .where(
                and_(
                    PushNotificationHistory.user_id == user_id,
                    PushNotificationHistory.agent_id == agent_id,
                    PushNotificationHistory.push_type == PUSH_TYPE_FESTIVAL_MEMORY,
                )
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None
    except Exception as e:
        logger.error(f"检查节日记忆推送历史失败: {str(e)}")
        return True  # 出错时返回 True，避免重复发送


async def get_users_needing_push(
    db: AsyncSession,
    stage: str,
    batch_size: int = 50,
) -> List[Tuple[User, Optional[Chat], Optional[datetime.datetime], Optional[Agent]]]:
    """
    统一查询需要推送的用户（所有阶段统一处理）

    推送阶段映射：
    - 10min: 未读记录数=0，基于最后用户消息时间（10分钟前）
    - 30min: 未读记录数=1，基于 10min 阶段推送时间（间隔 20 分钟）
    - 2h: 未读记录数=2，基于 30min 阶段推送时间（间隔 90 分钟）
    - 24h: 未读记录数=3，基于 2h 阶段推送时间（间隔 22 小时）
    - 48h: 未读记录数=4，基于 24h 阶段推送时间（间隔 24 小时）

    注意：后续阶段（30min, 2h, 24h, 48h）基于前一个阶段的推送时间进行判断，
    而不是基于最后用户消息时间，确保阶段之间的时间间隔正确。

    Args:
        db: 数据库会话
        stage: 推送阶段 (10min, 30min, 2h, 24h, 48h)
        batch_size: 批次大小

    Returns:
        (用户, 聊天对象或None, 最后消息时间或用户注册时间, 热门角色或None) 的元组列表
    """
    try:
        stage_config = get_push_stage_config()
        config = stage_config.get(stage)
        if not config:
            logger.error(f"无效的推送阶段: {stage}")
            return []

        expected_unread_count = config["count"]

        # 计算时间阈值
        if "minutes" in config:
            threshold_time = datetime.datetime.now(
                datetime.timezone.utc
            ) - datetime.timedelta(minutes=config["minutes"])
        else:
            threshold_time = datetime.datetime.now(
                datetime.timezone.utc
            ) - datetime.timedelta(hours=config["hours"])

        logger.debug(
            f"开始查询需要推送的用户: stage={stage}, expected_unread_count={expected_unread_count}, threshold_time={threshold_time.isoformat()}"
        )

        # 获取热门角色（用于无聊天推送）
        popular_agent = await get_popular_agent(db, limit=1)

        # 查询推送记录表中未读推送的用户
        users_with_unread_count = await _query_users_by_unread_count(
            db, expected_unread_count, batch_size
        )

        if not users_with_unread_count:
            logger.debug(
                f"未找到未读推送记录数为 {expected_unread_count} 的用户 (stage={stage})"
            )
            return []

        logger.debug(
            f"找到 {len(users_with_unread_count)} 个未读推送记录数为 {expected_unread_count} 的用户 (stage={stage})"
        )

        # 处理已读推送的重新召回：使用时间窗口查询（最近24小时内被标记为已读的用户）
        read_push_time_window = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(hours=READ_PUSH_RECALL_TIME_WINDOW_HOURS)

        read_push_stmt = (
            select(PushNotificationHistory.user_id)
            .where(
                and_(
                    PushNotificationHistory.read_at.isnot(None),
                    PushNotificationHistory.read_at >= read_push_time_window,
                )
            )
            .distinct()
        )
        read_push_result = await db.execute(read_push_stmt)
        read_push_user_ids = [row[0] for row in read_push_result.all()]

        logger.debug(
            f"检查 {len(read_push_user_ids)} 个最近24小时内有已读推送的用户是否需要重新召回 (stage={stage})"
        )

        # 检查已读推送用户是否需要重新召回
        if read_push_user_ids:
            recalled_users = await _check_read_push_users_for_recall(
                db, read_push_user_ids, stage, expected_unread_count, threshold_time
            )
            users_with_unread_count.extend(recalled_users)

        if not users_with_unread_count:
            return []

        # 获取这些用户的详细信息
        user_ids = [row.user_id for row in users_with_unread_count[: batch_size * 3]]

        logger.debug(f"开始处理 {len(user_ids)} 个用户，检查推送条件 (stage={stage})")

        # 按推送条件过滤用户
        users_needing_push = await _filter_users_by_push_conditions(
            db,
            user_ids,
            stage,
            expected_unread_count,
            threshold_time,
            popular_agent,
            batch_size,
        )

        logger.info(
            f"查询完成: 找到 {len(users_needing_push)} 个符合条件的用户 (stage={stage})"
        )

        # 按时间排序（最早的优先），取前 batch_size 个
        users_needing_push.sort(key=lambda x: x[2] if x[2] else datetime.datetime.max)
        return users_needing_push[:batch_size]

    except Exception as e:
        logger.error(f"查询需要推送的用户失败: stage={stage}, error={str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return []


async def get_users_needing_no_chat_push(
    db: AsyncSession,
    stage: str,
    time_delta_hours: int,
    batch_size: int = 50,
) -> List[Tuple[User, Agent]]:
    """
    查询需要"无聊天"推送的用户（基于推送记录表查询）

    主要从推送记录表查询未读推送的用户，根据未读推送记录数确定当前应该推送的阶段。
    推送顺序：24h (未读记录数=3) -> 48h (未读记录数=4)

    Args:
        db: 数据库会话
        stage: 推送阶段（如 "24h", "48h"）
        time_delta_hours: 距离用户注册/首次打开 app 的时间（小时）
        batch_size: 批次大小（用于限制返回数量）

    Returns:
        (用户, 热门角色) 的元组列表
    """
    try:
        # 计算时间阈值
        threshold_time = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(hours=time_delta_hours)

        # 根据 stage 确定期望的未读推送记录数
        expected_unread_count = NO_CHAT_STAGE_TO_COUNT.get(stage)
        if expected_unread_count is None:
            logger.error(f"无效的推送阶段: {stage}")
            return []

        # 获取热门角色
        popular_agent = await get_popular_agent(db, limit=1)
        if not popular_agent:
            logger.warning("没有找到热门角色，无法进行无聊天推送")
            return []

        logger.info(
            f"[用户维度] 开始基于推送记录表查询需要无聊天推送的用户 (stage={stage}, expected_unread_count={expected_unread_count}, time_delta_hours={time_delta_hours})"
        )

        # 查询推送记录表中未读推送的用户，按用户分组统计未读推送数
        stmt = (
            select(
                PushNotificationHistory.user_id,
                func.count(PushNotificationHistory.id).label("unread_count"),
            )
            .where(PushNotificationHistory.read_at.is_(None))
            .group_by(PushNotificationHistory.user_id)
            .having(func.count(PushNotificationHistory.id) == expected_unread_count)
        )

        # 查询推送记录表中未读推送的用户
        users_with_unread_count = await _query_users_by_unread_count(
            db, expected_unread_count, batch_size
        )

        logger.info(
            f"[用户维度] 找到 {len(users_with_unread_count)} 个未读推送记录数为 {expected_unread_count} 的用户 (stage={stage})"
        )

        # 处理已读推送的重新召回：检查已读推送的用户是否不聊了
        # 查询有已读推送的用户（无聊天推送）
        read_push_stmt = (
            select(PushNotificationHistory.user_id)
            .where(
                and_(
                    PushNotificationHistory.read_at.isnot(None),
                    PushNotificationHistory.push_type == PUSH_TYPE_NO_CHAT,
                )
            )
            .distinct()
            .limit(batch_size * 2)  # 限制检查数量
        )
        read_push_result = await db.execute(read_push_stmt)
        read_push_user_ids = [row[0] for row in read_push_result.all()]

        logger.info(
            f"[用户维度] 检查 {len(read_push_user_ids)} 个有已读推送的用户是否需要重新召回 (stage={stage})"
        )

        # 检查已读推送用户是否需要重新召回（针对无聊天推送的特殊逻辑）
        if read_push_user_ids:
            recalled_users = []
            for read_user_id in read_push_user_ids:
                try:
                    # 检查用户是否创建了聊天
                    chat_stmt = (
                        select(Chat)
                        .where(
                            and_(
                                Chat.user_id == read_user_id,
                                Chat.is_active == True,
                            )
                        )
                        .limit(1)
                    )
                    chat_result = await db.execute(chat_stmt)
                    if chat_result.scalar_one_or_none():
                        # 用户创建了聊天，跳过（转为 recent_chat 推送）
                        continue

                    # 用户没有聊天，检查是否达到推送时间阈值
                    user_stmt = (
                        select(User)
                        .options(load_only(User.id, User.created_at, User.deleted_at))
                        .where(and_(User.id == read_user_id, User.deleted_at.is_(None)))
                    )
                    user_result = await db.execute(user_stmt)
                    user = user_result.scalar_one_or_none()
                    if user and user.created_at and user.created_at <= threshold_time:
                        # 检查已读推送记录
                        reset_count = await reset_user_read_push_notifications(
                            db, read_user_id
                        )
                        if reset_count > 0:
                            logger.info(
                                f"[用户维度] 用户没有聊天且达到阈值，检查推送状态: user_id={read_user_id}, 已读推送记录数={reset_count}"
                            )
                            # 检查未读推送记录数
                            unread_count = await get_user_unread_push_count(
                                db, read_user_id
                            )
                            if unread_count == expected_unread_count:
                                recalled_users.append(
                                    SimpleNamespace(user_id=read_user_id)
                                )
                                logger.info(
                                    f"[用户维度] 用户重置后添加到待推送列表: user_id={read_user_id}"
                                )
                except Exception as e:
                    logger.error(
                        f"[用户维度] 检查已读推送用户时出错: user_id={read_user_id}, error={str(e)}"
                    )
                    continue
            users_with_unread_count.extend(recalled_users)

        if not users_with_unread_count:
            return []

        # 获取这些用户的详细信息
        user_ids = [row.user_id for row in users_with_unread_count[: batch_size * 3]]

        # 过滤用户：只保留没有活跃聊天且满足时间条件的用户
        users_needing_push = []
        for user_id in user_ids:
            try:
                # 获取用户信息
                user = await _get_user_by_id(db, user_id)
                if not user:
                    continue

                # 检查用户是否有 device_token
                if not await _check_user_has_device_token(db, user_id):
                    continue

                # 检查用户是否没有活跃聊天
                if await _check_user_has_active_chat(db, user_id):
                    # 用户有活跃聊天，跳过
                    continue

                # 检查用户创建时间是否达到阈值
                if user.created_at and user.created_at <= threshold_time:
                    users_needing_push.append((user, popular_agent))
                    logger.debug(
                        f"[用户维度] 用户满足推送条件: user_id={user_id}, "
                        f"unread_count={expected_unread_count}, created_at={user.created_at.isoformat()}, threshold={threshold_time.isoformat()}"
                    )

                    if len(users_needing_push) >= batch_size:
                        break

            except Exception as e:
                logger.error(
                    f"[用户维度] 处理用户时出错: user_id={user_id}, error={str(e)}"
                )
                continue

        logger.info(
            f"[用户维度] 基于推送记录表查询完成: 找到 {len(users_needing_push)} 个符合条件的用户 (stage={stage})"
        )

        return users_needing_push

    except Exception as e:
        logger.error(f"[用户维度] 查询需要无聊天推送的用户失败: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return []


async def get_users_needing_recent_chat_push(
    db: AsyncSession,
    stage: str,
    time_delta_minutes: int,
    batch_size: int = 50,
) -> List[Tuple[User, Chat, datetime.datetime]]:
    """
    查询需要"最近聊天"推送的用户（基于推送记录表查询）

    主要从推送记录表查询未读推送的用户，根据未读推送记录数确定当前应该推送的阶段。
    推送顺序：10min (未读记录数=0) -> 30min (未读记录数=1) -> 2h (未读记录数=2)

    Args:
        db: 数据库会话
        stage: 推送阶段 (10min, 30min, 2h)
        time_delta_minutes: 距离最后消息的时间（分钟）
        batch_size: 批次大小（用于限制返回数量）

    Returns:
        (用户, 最近聊天, 最后消息时间) 的元组列表
    """
    try:
        # 计算时间阈值
        threshold_time = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(minutes=time_delta_minutes)

        # 根据 stage 确定期望的未读推送记录数
        expected_unread_count = RECENT_CHAT_STAGE_TO_COUNT.get(stage)
        if expected_unread_count is None:
            logger.error(f"无效的推送阶段: {stage}")
            return []

        logger.info(
            f"[用户维度] 开始基于推送记录表查询需要推送的用户 (stage={stage}, expected_unread_count={expected_unread_count}, time_delta_minutes={time_delta_minutes})"
        )

        # 查询推送记录表中未读推送的用户
        users_with_unread_count = await _query_users_by_unread_count(
            db, expected_unread_count, batch_size
        )

        logger.info(
            f"[用户维度] 找到 {len(users_with_unread_count)} 个未读推送记录数为 {expected_unread_count} 的用户 (stage={stage})"
        )

        # 处理已读推送的重新召回：检查已读推送的用户是否不聊了
        # 查询有已读推送的用户
        read_push_stmt = (
            select(PushNotificationHistory.user_id)
            .where(
                and_(
                    PushNotificationHistory.read_at.isnot(None),
                    PushNotificationHistory.push_type == PUSH_TYPE_RECENT_CHAT,
                )
            )
            .distinct()
            .limit(batch_size * 2)  # 限制检查数量
        )
        read_push_result = await db.execute(read_push_stmt)
        read_push_user_ids = [row[0] for row in read_push_result.all()]

        logger.info(
            f"[用户维度] 检查 {len(read_push_user_ids)} 个有已读推送的用户是否需要重新召回 (stage={stage})"
        )

        # 检查已读推送用户是否需要重新召回
        if read_push_user_ids:
            recalled_users = await _check_read_push_users_for_recall(
                db, read_push_user_ids, stage, expected_unread_count, threshold_time
            )
            users_with_unread_count.extend(recalled_users)

        if not users_with_unread_count:
            return []

        # 获取这些用户的详细信息
        user_ids = [row.user_id for row in users_with_unread_count[: batch_size * 3]]

        # 查询这些用户及其最近聊天
        users_with_recent_chats = []
        for user_id in user_ids:
            try:
                # 获取用户信息
                user = await _get_user_by_id(db, user_id)
                if not user:
                    continue

                # 检查用户是否有 device_token
                if not await _check_user_has_device_token(db, user_id):
                    continue

                # 获取用户最近聊天
                recent_chat_data = await get_user_recent_chat(db, user_id, stage=stage)
                if not recent_chat_data:
                    continue

                chat, last_user_message_time = recent_chat_data

                # 检查时间是否匹配
                if last_user_message_time <= threshold_time:
                    users_with_recent_chats.append((user, chat, last_user_message_time))
                    logger.debug(
                        f"[用户维度] 用户满足推送条件: user_id={user_id}, chat_id={chat.id}, "
                        f"unread_count={expected_unread_count}, last_message_time={last_user_message_time.isoformat()}, threshold={threshold_time.isoformat()}"
                    )

                    if len(users_with_recent_chats) >= batch_size:
                        break

            except Exception as e:
                logger.error(
                    f"[用户维度] 处理用户时出错: user_id={user_id}, error={str(e)}"
                )
                continue

        logger.info(
            f"[用户维度] 基于推送记录表查询完成: 找到 {len(users_with_recent_chats)} 个符合条件的用户 (stage={stage})"
        )

        # 按最后消息时间排序（最早的优先），取前 batch_size 个
        users_with_recent_chats.sort(key=lambda x: x[2])
        return users_with_recent_chats[:batch_size]

    except Exception as e:
        logger.error(f"[用户维度] 查询需要最近聊天推送的用户失败: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return []
