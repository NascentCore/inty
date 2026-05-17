"""Surprise Snap：用户与角色对话达到指定轮数时插入专属照消息。"""

import json
from typing import List, Optional

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.models.agent import Agent
from app.models.chat import Chat
from app.models.chat_history import ChatHistory
from app.models.surprise_snap import SurpriseSnapProgress, SurpriseSnapUnlock
from app.services import chat_history_service


async def _get_agent_exclusive_photos(
    db: AsyncSession, agent_id: str
) -> List[dict]:
    """返回角色的 exclusive_photos 列表，每项含 image_url, caption, credits_required。"""
    stmt = select(Agent.exclusive_photos).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    val = result.scalar_one_or_none()
    if not val or not isinstance(val, list):
        return []
    photos = val
    return [p for p in photos if isinstance(p, dict) and p.get("image_url")]


async def _get_or_create_progress(
    db: AsyncSession, user_id: str, agent_id: str
) -> Optional[SurpriseSnapProgress]:
    """获取或创建 user+agent 的发放进度。"""
    stmt = select(SurpriseSnapProgress).where(
        and_(
            SurpriseSnapProgress.user_id == user_id,
            SurpriseSnapProgress.agent_id == agent_id,
        )
    )
    result = await db.execute(stmt)
    progress = result.scalar_one_or_none()
    if progress is not None:
        return progress
    progress = SurpriseSnapProgress(
        user_id=user_id,
        agent_id=agent_id,
        next_photo_index=0,
    )
    db.add(progress)
    try:
        await db.commit()
        await db.refresh(progress)
        return progress
    except IntegrityError:
        await db.rollback()
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


async def try_trigger_surprise_snap(
    db: AsyncSession,
    session_id: str,
    user_id: str,
    agent_id: str,
) -> Optional[int]:
    """
    用户发送消息并记录 usage 后调用：若满足配置与轮数，则插入一条 surprise_snap 消息并更新进度。
    同一 user+agent 按 exclusive_photos 顺序发放，发完或图库为空则不触发。
    返回本次插入的消息 ID，未插入或失败时返回 None。
    """
    config = global_config_loaded_from_config_yaml.surprise_snap
    if config.enabled_since is None:
        return None
    photos = await _get_agent_exclusive_photos(db, agent_id)
    if not photos:
        return None
    progress = await _get_or_create_progress(db, user_id, agent_id)
    if progress is None:
        return None
    idx = progress.next_photo_index
    if idx >= len(photos):
        return None
    count = await chat_history_service.count_user_messages_since(
        db, session_id, config.enabled_since
    )
    if count not in config.trigger_rounds:
        return None
    item = photos[idx]
    image_url = item.get("image_url") or ""
    caption = item.get("caption") or ""
    credits_required = int(item.get("credits_required", 0))
    try:
        message_id = await chat_history_service.add_surprise_snap_message(
            db,
            session_id=session_id,
            agent_id=agent_id,
            image_url=image_url,
            caption=caption,
            credits_required=credits_required,
            exclusive_photo_index=idx,
        )
        if message_id is not None:
            progress.next_photo_index = idx + 1
            await db.commit()
            logger.debug(
                f"Surprise Snap 已插入 session_id={session_id} agent_id={agent_id} "
                f"index={idx} message_id={message_id}"
            )
            return message_id
    except Exception as e:
        logger.warning(f"Surprise Snap 插入失败: {e}")
        await db.rollback()
    return None


async def get_unlocked_surprise_snap_message_ids(
    db: AsyncSession, user_id: str
) -> set:
    """返回该用户已解锁的 surprise_snap 消息 ID 集合。"""
    stmt = select(SurpriseSnapUnlock.message_id).where(
        SurpriseSnapUnlock.user_id == user_id
    )
    result = await db.execute(stmt)
    return {row[0] for row in result.fetchall()}


async def record_surprise_snap_unlock(
    db: AsyncSession, user_id: str, message_id: int
) -> bool:
    """
    记录用户解锁某条 surprise_snap 消息（免费用户用 credit 解锁，扣费在 app 端）。
    校验消息为 surprise_snap 且属于该用户的会话；重复解锁视为成功（幂等）。
    """
    from app.services.chat_service import generate_session_id

    stmt = (
        select(ChatHistory)
        .where(ChatHistory.id == message_id)
        .where(ChatHistory.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    ch_row = result.scalar_one_or_none()
    if not ch_row:
        return False
    message_data = ch_row.message
    if isinstance(message_data, str):
        message_data = json.loads(message_data)
    if message_data.get("type") != "surprise_snap":
        return False
    session_id = str(ch_row.session_id) if ch_row.session_id else None
    if not session_id:
        return False
    chat_stmt = select(Chat).where(Chat.user_id == user_id)
    chats_result = await db.execute(chat_stmt)
    for chat in chats_result.scalars().all():
        if generate_session_id(chat.id) == session_id:
            break
    else:
        return False
    unlock = SurpriseSnapUnlock(user_id=user_id, message_id=message_id)
    db.add(unlock)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return True
    return True
