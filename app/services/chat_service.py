import time
import uuid
from datetime import datetime
from typing import List, Optional, Union

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.core.config import global_config_loaded_from_config_yaml
from app.models.user import AuthType
from app.schemas.exclude_fields import EXCLUDE_FIELDS
from app.schemas.response import BizError, BusinessErrorCode, UsageLimitExceeded
from app.services import agent_service, chat_history_service
from app.services.cache_service import cache_service
from app.services.subscription_service import SubscriptionService
from app.services.user_service import build_user_info_prompt_block
from app.utils.models_catalog import NANO_BANANA_PRO, NEWAPI_NANO_BANANA_2


def generate_session_id(chat_id: str) -> str:
    """
    Generate consistent session_id based on chat_id
    Ensure the same session_id is used when creating chat and chatting
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))


async def get_chat(db: AsyncSession, chat_id: str) -> Optional[models.Chat]:
    """
    Get chat by ID
    """
    try:
        result = await db.execute(
            select(models.Chat)
            .options(
                selectinload(models.Chat.settings), selectinload(models.Chat.agent)
            )
            .where(models.Chat.id == chat_id)
        )
        chat = result.scalar_one_or_none()
        if chat:
            # Get recent message and timestamp, use unified session_id generation rule
            try:
                session_id = generate_session_id(chat.id)
                last_message_data = (
                    await chat_history_service.get_last_message_with_timestamp_async(
                        session_id
                    )
                )

                if last_message_data:
                    chat.last_message = last_message_data["content"]
                    chat.last_message_time = last_message_data["timestamp"]
                else:
                    chat.last_message = None
                    chat.last_message_time = None
            except Exception as e:
                logger.error(f"Failed to get recent message: {str(e)}")
                chat.last_message = None
                chat.last_message_time = None
            # Set agent name and avatar
            chat.agent_name = chat.agent.name if chat.agent else None
            chat.agent_avatar = chat.agent.avatar if chat.agent else None
            chat.agent_background = chat.agent.background if chat.agent else None
            chat.agent_background_animated = (
                chat.agent.background_animated if chat.agent else None
            )
            chat.agent_extensions = chat.agent.extensions if chat.agent else None
            chat.agent_is_deleted = (
                chat.agent.deleted_at is not None if chat.agent else None
            )
            chat.agent_intro = chat.agent.intro if chat.agent else None
            chat.agent_opening = chat.agent.opening if chat.agent else None
            chat.agent_opening_audio_url = (
                chat.agent.opening_audio_url if chat.agent else None
            )
        return chat
    except SQLAlchemyError as e:
        logger.error(f"Database query error - get chat {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unknown error - get chat {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_chats(
    db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100
) -> List[models.Chat]:
    """
    Get user's chat list, sorted by recent message time in descending order
    """
    try:
        # Validate parameters
        if skip < 0:
            raise HTTPException(
                status_code=400, detail="Skip parameter cannot be negative"
            )
        if limit <= 0 or limit > 1000:
            raise HTTPException(
                status_code=400, detail="Limit parameter must be between 1-1000"
            )

        result = await db.execute(
            select(models.Chat)
            .options(
                selectinload(models.Chat.settings), selectinload(models.Chat.agent)
            )
            .where(models.Chat.user_id == user_id)
        )
        all_chats = result.scalars().all()

        # Get recent message and timestamp for each chat, and filter out opening-only chats
        chats_with_message_time = []
        for chat in all_chats:
            try:
                # Use unified session_id generation rule
                session_id = generate_session_id(chat.id)
                last_message_data = (
                    await chat_history_service.get_last_message_with_timestamp_async(
                        session_id
                    )
                )

                if last_message_data:
                    chat.last_message = last_message_data["content"]
                    chat.last_message_time = last_message_data["timestamp"]
                else:
                    chat.last_message = None
                    chat.last_message_time = None

                # Check if chat has ever had user messages (including deleted ones)
                # This ensures chats remain visible even after user deletes all messages
                has_user_messages = (
                    await chat_history_service.has_user_messages_ever_async(session_id)
                )

                # Only include chats that have (or ever had) user messages
                if not has_user_messages:
                    logger.debug(f"过滤掉仅有开场白的聊天: chat_id={chat.id}")
                    continue

            except Exception as e:
                logger.error(f"Failed to get recent message: {str(e)}")
                chat.last_message = None
                chat.last_message_time = None
                # In case of error, include the chat to be safe
                pass

            chat.agent_name = chat.agent.name if chat.agent else None
            chat.agent_avatar = chat.agent.avatar if chat.agent else None
            chat.agent_background = chat.agent.background if chat.agent else None
            chat.agent_background_animated = (
                chat.agent.background_animated if chat.agent else None
            )
            chat.agent_extensions = chat.agent.extensions if chat.agent else None
            chat.agent_is_deleted = (
                chat.agent.deleted_at is not None if chat.agent else None
            )
            chat.agent_intro = chat.agent.intro if chat.agent else None
            chat.agent_opening = chat.agent.opening if chat.agent else None
            chat.agent_opening_audio_url = (
                chat.agent.opening_audio_url if chat.agent else None
            )
            chats_with_message_time.append(chat)

        # Sort by recent message time (chats without messages go last, sorted by creation time)
        chats_with_message_time.sort(
            key=lambda x: x.last_message_time if x.last_message_time else x.created_at,
            reverse=True,
        )

        # Apply pagination
        return chats_with_message_time[skip : skip + limit]
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database query error - get user chat list: {str(e)}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unknown error - get user chat list: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def create_chat(
    db: AsyncSession, chat_in: schemas.ChatCreate, user_id: str
) -> models.Chat:
    """
    Create new chat
    """
    try:
        # Generate unique ID
        chat_id = str(uuid.uuid4())

        # First get Agent's opening message
        agent_result = await db.execute(
            select(models.Agent).where(models.Agent.id == chat_in.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 排除数据库模型中不存在的字段
        chat_data = chat_in.model_dump(exclude=EXCLUDE_FIELDS)
        db_chat = models.Chat(id=chat_id, **chat_data, user_id=user_id)

        db.add(db_chat)
        await db.commit()
        await db.refresh(db_chat)

        # Add Agent opening message to chat_history, use unified session_id generation rule
        if agent.opening:
            try:
                session_id = generate_session_id(chat_id)
                # 检查是否已有消息，避免重复添加开场白
                existing_messages = (
                    await chat_history_service.get_messages_paginated_async(
                        session_id=session_id, limit=1, offset=0
                    )
                )
                if existing_messages.get("total", 0) == 0:
                    # 获取用户信息用于变量替换
                    user_result = await db.execute(
                        select(models.User.nickname).where(models.User.id == user_id)
                    )
                    user_nickname = user_result.scalar_one_or_none() or "you"

                    await chat_history_service.add_agent_opening_message(
                        db,
                        session_id,
                        agent.opening,
                        agent.opening_audio_url,
                        agent.id,
                        agent_name=agent.name,
                        user_name=user_nickname,
                    )
                    logger.debug(f"添加Agent开场白成功 - Session ID: {session_id}")
                else:
                    logger.debug(
                        f"聊天会话已有消息({existing_messages.get('total', 0)}条)，跳过开场白添加 - Session ID: {session_id}"
                    )
            except Exception as e:
                logger.error(f"处理开场白失败: {str(e)}")
                # Continue execution, don't affect chat creation

        # Re-query to load relational data
        result = await db.execute(
            select(models.Chat)
            .options(
                selectinload(models.Chat.settings), selectinload(models.Chat.agent)
            )
            .where(models.Chat.id == db_chat.id)
        )
        chat = result.scalar_one()

        # Get recent message and timestamp (should be the opening message just added) and agent name
        try:
            session_id = generate_session_id(chat.id)
            last_message_data = (
                await chat_history_service.get_last_message_with_timestamp_async(
                    session_id
                )
            )

            if last_message_data:
                chat.last_message = last_message_data["content"]
                chat.last_message_time = last_message_data["timestamp"]
            else:
                chat.last_message = None
                chat.last_message_time = None
        except Exception as e:
            logger.error(f"Failed to get recent message: {str(e)}")
            chat.last_message = None
            chat.last_message_time = None
        chat.agent_name = chat.agent.name if chat.agent else None
        chat.agent_avatar = chat.agent.avatar if chat.agent else None
        chat.agent_background_animated = (
            chat.agent.background_animated if chat.agent else None
        )
        chat.agent_is_deleted = (
            chat.agent.deleted_at is not None if chat.agent else None
        )

        return chat

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Data integrity error - create chat: {str(e)}")
        if "user_id" in str(e):
            raise HTTPException(status_code=400, detail="Invalid user ID")
        elif "agent_id" in str(e):
            raise HTTPException(status_code=400, detail="Invalid Agent ID")
        else:
            raise HTTPException(
                status_code=400, detail="Data integrity constraint violation"
            )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error - create chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        await db.rollback()
        logger.error(f"Unknown error - create chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def update_chat(
    db: AsyncSession, *, db_chat: models.Chat, chat_in: schemas.ChatUpdate
) -> models.Chat:
    """
    更新聊天
    """
    try:
        if not db_chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        update_data = chat_in.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided to update")

        for field, value in update_data.items():
            setattr(db_chat, field, value)

        await db.commit()
        await db.refresh(db_chat)
        return db_chat

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(
            f"数据完整性错误 - 更新聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}"
        )
        raise HTTPException(
            status_code=400, detail="Data integrity constraint violated"
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            f"数据库错误 - 更新聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        await db.rollback()
        logger.error(
            f"未知错误 - 更新聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")


async def delete_chat(db: AsyncSession, *, db_chat: models.Chat) -> models.Chat:
    """
    删除聊天
    """
    try:
        if not db_chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        await db.delete(db_chat)
        await db.commit()
        return db_chat

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(
            f"数据完整性错误 - 删除聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}"
        )
        raise HTTPException(
            status_code=400, detail="Cannot delete chat due to related data"
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            f"数据库错误 - 删除聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        await db.rollback()
        logger.error(
            f"未知错误 - 删除聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")


async def _finalize_existing_chat_for_agent(
    db: AsyncSession,
    user_id: str,
    agent_id: str,
    session_key: str,
    existing_chat: models.Chat,
) -> models.Chat:
    logger.debug(
        f"找到已存在的聊天会话 - Chat ID: {existing_chat.id}, Agent ID: {existing_chat.agent_id}"
    )

    if existing_chat.agent_id != agent_id:
        logger.error(
            f"聊天会话中的Agent ID不匹配！期望: {agent_id}, 实际: {existing_chat.agent_id}"
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Chat session data mismatch: expected agent ID "
                f"{agent_id}, got {existing_chat.agent_id}"
            ),
        )

    cached_agent = None
    if not hasattr(existing_chat, "_agent_loaded"):
        cached_agent = cache_service.get_agent_config(agent_id)
        if cached_agent:
            existing_chat.agent_name = cached_agent.get("name")
            existing_chat.agent_avatar = cached_agent.get("avatar")
            existing_chat.agent_background_animated = cached_agent.get(
                "background_animated"
            )
            existing_chat.agent_intro = cached_agent.get("intro")
            existing_chat.agent_opening = cached_agent.get("opening")
            existing_chat.agent_opening_audio_url = cached_agent.get(
                "opening_audio_url"
            )
            agent_result = await db.execute(
                select(models.Agent.deleted_at).where(models.Agent.id == agent_id)
            )
            agent_info = agent_result.first()
            existing_chat.agent_is_deleted = (
                agent_info[0] is not None if agent_info else None
            )
        else:
            agent_result = await db.execute(
                select(
                    models.Agent.name,
                    models.Agent.avatar,
                    models.Agent.background_animated,
                    models.Agent.intro,
                    models.Agent.opening,
                    models.Agent.opening_audio_url,
                    models.Agent.deleted_at,
                ).where(models.Agent.id == agent_id)
            )
            agent_info = agent_result.first()
            if agent_info:
                existing_chat.agent_name = agent_info[0]
                existing_chat.agent_avatar = agent_info[1]
                existing_chat.agent_background_animated = agent_info[2]
                existing_chat.agent_intro = agent_info[3]
                existing_chat.agent_opening = agent_info[4]
                existing_chat.agent_opening_audio_url = agent_info[5]
                existing_chat.agent_is_deleted = agent_info[6] is not None
                cache_service.set_agent_config(
                    agent_id,
                    {
                        "name": agent_info[0],
                        "avatar": agent_info[1],
                        "background_animated": agent_info[2],
                        "intro": agent_info[3],
                        "opening": agent_info[4],
                        "opening_audio_url": agent_info[5],
                    },
                )
            else:
                existing_chat.agent_name = None
                existing_chat.agent_avatar = None
                existing_chat.agent_intro = None
                existing_chat.agent_opening = None
                existing_chat.agent_opening_audio_url = None
                existing_chat.agent_is_deleted = None
        existing_chat._agent_loaded = True
    else:
        cached_agent = cache_service.get_agent_config(agent_id)
        if cached_agent:
            existing_chat.agent_name = cached_agent.get("name")
            existing_chat.agent_avatar = cached_agent.get("avatar")
            existing_chat.agent_background_animated = cached_agent.get(
                "background_animated"
            )
            existing_chat.agent_intro = cached_agent.get("intro")
            existing_chat.agent_opening = cached_agent.get("opening")
            existing_chat.agent_opening_audio_url = cached_agent.get(
                "opening_audio_url"
            )
        agent_result = await db.execute(
            select(models.Agent.deleted_at).where(models.Agent.id == agent_id)
        )
        agent_info = agent_result.first()
        existing_chat.agent_is_deleted = (
            agent_info[0] is not None if agent_info else None
        )

    try:
        session_id = generate_session_id(existing_chat.id)
        existing_messages = (
            await chat_history_service.get_messages_paginated_async(
                session_id=session_id, limit=1, offset=0
            )
        )
        if existing_messages.get("total", 0) == 0:
            agent_opening = None
            opening_audio_url = None
            if cached_agent:
                agent_opening = cached_agent.get("opening")
                opening_audio_url = cached_agent.get("opening_audio_url")
            else:
                agent_result = await db.execute(
                    select(models.Agent.opening, models.Agent.opening_audio_url).where(
                        models.Agent.id == agent_id
                    )
                )
                agent_info = agent_result.first()
                if agent_info:
                    agent_opening = agent_info[0]
                    opening_audio_url = agent_info[1]

            if agent_opening:
                user_result = await db.execute(
                    select(models.User.nickname).where(models.User.id == user_id)
                )
                user_nickname = user_result.scalar_one_or_none() or "you"

                agent_result = await db.execute(
                    select(models.Agent.name).where(models.Agent.id == agent_id)
                )
                agent_name = agent_result.scalar_one_or_none() or "IntelliMate"

                await chat_history_service.add_agent_opening_message(
                    db,
                    session_id,
                    agent_opening,
                    opening_audio_url,
                    agent_id,
                    agent_name=agent_name,
                    user_name=user_nickname,
                )
                logger.debug(
                    f"为已存在的空聊天会话添加Agent开场白成功 - Session ID: {session_id}"
                )
            else:
                logger.debug(f"Agent无开场白，跳过添加 - Agent ID: {agent_id}")
        else:
            logger.debug(
                f"聊天会话已有消息({existing_messages.get('total', 0)}条)，跳过开场白添加 - Session ID: {session_id}"
            )
    except Exception as e:
        logger.error(f"检查或添加现有聊天开场白失败: {str(e)}")

    session_data = {
        "chat_id": existing_chat.id,
        "user_id": user_id,
        "agent_id": agent_id,
        "agent_name": getattr(existing_chat, "agent_name", None),
        "agent_avatar": getattr(existing_chat, "agent_avatar", None),
        "agent_background": getattr(existing_chat, "agent_background", None),
        "agent_background_animated": getattr(
            existing_chat, "agent_background_animated", None
        ),
        "agent_intro": getattr(existing_chat, "agent_intro", None),
        "agent_opening": getattr(existing_chat, "agent_opening", None),
        "agent_opening_audio_url": getattr(
            existing_chat, "agent_opening_audio_url", None
        ),
        "created_at": existing_chat.created_at,
        "updated_at": existing_chat.updated_at,
    }
    cache_service.set_session_info(session_key, session_data)

    existing_chat.last_message = None
    existing_chat.last_message_time = None

    return existing_chat


async def get_or_create_chat_by_agent(
    db: AsyncSession, user_id: str, agent_id: str
) -> models.Chat:
    """
    根据用户ID和Agent ID获取或创建唯一的聊天会话（高性能优化版）
    每个用户和每个Agent只能有一个会话
    """
    try:
        logger.debug(f"获取或创建聊天会话 - 用户ID: {user_id}, Agent ID: {agent_id}")

        # 1. 先检查会话缓存
        session_key = f"{user_id}:{agent_id}"
        cached_session = cache_service.get_session_info(session_key)
        if cached_session:
            logger.debug(f"从缓存获取聊天会话: {cached_session['chat_id']}")
            # 从缓存构建Chat对象
            chat = models.Chat(
                id=cached_session["chat_id"],
                user_id=user_id,
                agent_id=agent_id,
                is_active=True,
                created_at=cached_session.get("created_at"),
                updated_at=cached_session.get("updated_at"),
            )
            chat.agent_name = cached_session.get("agent_name")
            chat.agent_avatar = cached_session.get("agent_avatar")
            chat.agent_background = cached_session.get("agent_background")
            chat.agent_background_animated = cached_session.get(
                "agent_background_animated"
            )
            chat.agent_intro = cached_session.get("agent_intro")
            chat.agent_opening = cached_session.get("agent_opening")
            chat.agent_opening_audio_url = cached_session.get("agent_opening_audio_url")
            return chat

        # 2. 数据库查询（使用简单查询，减少预加载）
        result = await db.execute(
            select(models.Chat).where(
                models.Chat.user_id == user_id,
                models.Chat.agent_id == agent_id,
                models.Chat.is_active == True,
            )
        )
        existing_chat = result.scalar_one_or_none()

        if existing_chat:
            return await _finalize_existing_chat_for_agent(
                db, user_id, agent_id, session_key, existing_chat
            )

        # 6. 如果不存在，则创建新的会话
        logger.debug(f"未找到已存在的聊天会话，创建新的会话 - Agent ID: {agent_id}")

        # 7. 优先从缓存获取Agent信息
        cached_agent = cache_service.get_agent_config(agent_id)
        if cached_agent:
            agent_name = cached_agent.get("name")
            agent_avatar = cached_agent.get("avatar")
            agent_background_animated = cached_agent.get("background_animated")
            agent_intro = cached_agent.get("intro")
            agent_opening = cached_agent.get("opening")
            opening_audio_url = cached_agent.get("opening_audio_url")
            logger.debug(f"从缓存获取Agent信息: {agent_name}")
        else:
            # 数据库查询Agent信息
            agent_result = await db.execute(
                select(
                    models.Agent.name,
                    models.Agent.avatar,
                    models.Agent.background_animated,
                    models.Agent.intro,
                    models.Agent.opening,
                    models.Agent.opening_audio_url,
                    models.Agent.deleted_at,
                ).where(models.Agent.id == agent_id)
            )
            agent_info = agent_result.first()
            if not agent_info:
                logger.error(f"Agent不存在: {agent_id}")
                raise HTTPException(status_code=404, detail="Agent not found")

            (
                agent_name,
                agent_avatar,
                agent_background_animated,
                agent_intro,
                agent_opening,
                opening_audio_url,
                agent_deleted_at,
            ) = agent_info
            # 缓存Agent信息
            cache_service.set_agent_config(
                agent_id,
                {
                    "name": agent_name,
                    "avatar": agent_avatar,
                    "background_animated": agent_background_animated,
                    "intro": agent_intro,
                    "opening": agent_opening,
                    "opening_audio_url": opening_audio_url,
                },
            )
            logger.debug(f"验证Agent存在 - Agent ID: {agent_id}, Name: {agent_name}")

        # 8. 创建新的聊天会话（ON CONFLICT 避免并发下触发唯一索引 ERROR 日志）
        chat_id = str(uuid.uuid4())

        logger.debug(
            f"创建新聊天会话 - Chat ID: {chat_id}, User ID: {user_id}, Agent ID: {agent_id}"
        )

        stmt = (
            insert(models.Chat)
            .values(id=chat_id, user_id=user_id, agent_id=agent_id)
            .on_conflict_do_nothing(
                index_elements=["user_id", "agent_id"],
                index_where=text("is_active = true"),
            )
        )
        await db.execute(stmt)
        await db.commit()

        inserted_row = (
            await db.execute(
                select(models.Chat).where(
                    models.Chat.id == chat_id,
                    models.Chat.user_id == user_id,
                    models.Chat.agent_id == agent_id,
                    models.Chat.is_active == True,
                )
            )
        ).scalar_one_or_none()

        if inserted_row is None:
            existing_after_conflict = (
                await db.execute(
                    select(models.Chat).where(
                        models.Chat.user_id == user_id,
                        models.Chat.agent_id == agent_id,
                        models.Chat.is_active == True,
                    )
                )
            ).scalar_one_or_none()
            if existing_after_conflict:
                logger.debug(
                    "并发插入跳过冲突，返回已有会话 - Chat ID: "
                    f"{existing_after_conflict.id}"
                )
                return await _finalize_existing_chat_for_agent(
                    db,
                    user_id,
                    agent_id,
                    session_key,
                    existing_after_conflict,
                )
            raise HTTPException(status_code=500, detail="Failed to create chat session")

        db_chat = inserted_row

        # 验证创建后的agent_id
        if db_chat.agent_id != agent_id:
            logger.error(
                f"创建聊天会话后Agent ID不匹配！期望: {agent_id}, 实际: {db_chat.agent_id}"
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to create chat session: agent ID mismatch",
            )

        # 9. 异步添加Agent开场白（避免阻塞）
        if agent_opening:
            try:
                session_id = generate_session_id(chat_id)
                # 检查是否已有消息，避免重复添加开场白
                existing_messages = (
                    await chat_history_service.get_messages_paginated_async(
                        session_id=session_id, limit=1, offset=0
                    )
                )
                if existing_messages.get("total", 0) == 0:
                    # 获取用户信息用于变量替换
                    user_result = await db.execute(
                        select(models.User.nickname).where(models.User.id == user_id)
                    )
                    user_nickname = user_result.scalar_one_or_none() or "you"

                    await chat_history_service.add_agent_opening_message(
                        db,
                        session_id,
                        agent_opening,
                        opening_audio_url,
                        agent_id,
                        agent_name=agent_name,
                        user_name=user_nickname,
                    )
                    logger.debug(f"添加Agent开场白成功 - Session ID: {session_id}")
                else:
                    logger.debug(
                        f"聊天会话已有消息({existing_messages.get('total', 0)}条)，跳过开场白添加 - Session ID: {session_id}"
                    )
            except Exception as e:
                logger.error(f"处理开场白失败: {str(e)}")
                # 继续执行，不影响chat创建

        # 10. 设置Agent信息并缓存会话（优化：避免重复查询）
        db_chat.agent_name = agent_name
        db_chat.agent_avatar = agent_avatar
        db_chat.agent_background_animated = (
            cached_agent.get("background_animated")
            if cached_agent
            else agent_background_animated
        )
        db_chat.agent_intro = cached_agent.get("intro") if cached_agent else agent_intro
        db_chat.agent_opening = (
            cached_agent.get("opening") if cached_agent else agent_opening
        )
        db_chat.agent_opening_audio_url = (
            cached_agent.get("opening_audio_url") if cached_agent else opening_audio_url
        )

        # Handle agent deletion status for cached vs database cases
        if cached_agent:
            # For cached agents, we need to check the database for deletion status
            agent_result = await db.execute(
                select(models.Agent.deleted_at).where(models.Agent.id == agent_id)
            )
            agent_info = agent_result.first()
            db_chat.agent_is_deleted = agent_info[0] is not None if agent_info else None
        else:
            # We already have deleted_at from the database query above
            db_chat.agent_is_deleted = agent_deleted_at is not None

        # 11. 缓存新建的会话信息
        session_data = {
            "chat_id": db_chat.id,
            "user_id": user_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "agent_avatar": agent_avatar,
            "agent_background": getattr(db_chat, "agent_background", None),
            "agent_background_animated": (
                cached_agent.get("background_animated")
                if cached_agent
                else agent_background_animated
            ),
            "agent_intro": cached_agent.get("intro") if cached_agent else agent_intro,
            "agent_opening": (
                cached_agent.get("opening") if cached_agent else agent_opening
            ),
            "agent_opening_audio_url": (
                cached_agent.get("opening_audio_url")
                if cached_agent
                else opening_audio_url
            ),
            "created_at": db_chat.created_at,
            "updated_at": db_chat.updated_at,
        }
        cache_service.set_session_info(session_key, session_data)

        # 12. 设置默认值（跳过耗时的消息查询）
        db_chat.last_message = None
        db_chat.last_message_time = None

        logger.debug(
            f"成功创建新聊天会话 - Chat ID: {db_chat.id}, Agent ID: {db_chat.agent_id}"
        )
        return db_chat

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"数据完整性错误 - 获取或创建聊天（并发冲突已重试）: {str(e)}")
        # 可能是并发创建导致的重复，尝试再次查询
        try:
            result = await db.execute(
                select(models.Chat)
                .options(
                    selectinload(models.Chat.settings), selectinload(models.Chat.agent)
                )
                .where(
                    models.Chat.user_id == user_id,
                    models.Chat.agent_id == agent_id,
                    models.Chat.is_active == True,
                )
            )
            existing_chat = result.scalar_one_or_none()
            if existing_chat:
                logger.debug(
                    f"并发创建冲突，返回已存在的聊天会话 - Chat ID: {existing_chat.id}"
                )
                return await _finalize_existing_chat_for_agent(
                    db, user_id, agent_id, session_key, existing_chat
                )
        except Exception as retry_e:
            logger.error(f"重试查询失败: {str(retry_e)}")
            pass
        raise HTTPException(status_code=500, detail="Failed to create chat session")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 获取或创建聊天: {str(e)}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 获取或创建聊天: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_or_create_chat_settings(
    db: AsyncSession, chat_id: str, user_id: str, agent_id: str
) -> models.ChatSettings:
    """
    获取或创建聊天设置（处理并发创建和外键约束）
    """
    try:
        # 先查找是否已存在设置，预加载agent关系
        result = await db.execute(
            select(models.ChatSettings)
            .options(selectinload(models.ChatSettings.agent))
            .where(models.ChatSettings.chat_id == chat_id)
        )
        settings = result.scalar_one_or_none()

        if settings:
            return settings

        # 确保chat记录存在（防止外键约束违反）
        chat_result = await db.execute(
            select(models.Chat).where(models.Chat.id == chat_id)
        )
        chat = chat_result.scalar_one_or_none()

        if not chat:
            logger.error(f"Chat记录不存在，无法创建设置 - chat_id: {chat_id}")
            raise HTTPException(status_code=404, detail="Chat history not found")

        # 如果不存在，创建新的设置
        settings_id = str(uuid.uuid4())
        db_settings = models.ChatSettings(
            id=settings_id,
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
            language="zh",  # 默认中文
            voice_enabled=False,  # 默认不启用语音自动播放
        )

        db.add(db_settings)

        try:
            await db.commit()
            await db.refresh(db_settings)

            # 重新查询以加载关系数据
            result = await db.execute(
                select(models.ChatSettings)
                .options(selectinload(models.ChatSettings.agent))
                .where(models.ChatSettings.id == db_settings.id)
            )
            settings_with_agent = result.scalar_one()

            logger.debug(f"成功创建聊天设置 - chat_id: {chat_id}")
            return settings_with_agent

        except IntegrityError:
            await db.rollback()
            logger.debug(f"并发创建聊天设置冲突，查询已存在设置 - chat_id: {chat_id}")

            # 查询已存在的设置
            result = await db.execute(
                select(models.ChatSettings)
                .options(selectinload(models.ChatSettings.agent))
                .where(models.ChatSettings.chat_id == chat_id)
            )
            existing_settings = result.scalar_one()
            return existing_settings

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 获取或创建聊天设置 {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 获取或创建聊天设置 {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def update_chat_settings(
    db: AsyncSession, chat_id: str, settings_update: schemas.ChatSettingsUpdate
) -> models.ChatSettings:
    """
    根据chat_id更新聊天设置
    """
    try:
        # 查找现有设置，预加载agent关系
        result = await db.execute(
            select(models.ChatSettings)
            .options(selectinload(models.ChatSettings.agent))
            .where(models.ChatSettings.chat_id == chat_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            raise HTTPException(status_code=404, detail="Chat settings not found")

        # 更新设置
        update_data = settings_update.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided to update")

        for field, value in update_data.items():
            setattr(settings, field, value)

        await db.commit()
        await db.refresh(settings)

        # 重新查询以确保关系数据已加载
        result = await db.execute(
            select(models.ChatSettings)
            .options(selectinload(models.ChatSettings.agent))
            .where(models.ChatSettings.id == settings.id)
        )
        updated_settings = result.scalar_one()

        return updated_settings

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 更新聊天设置 {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 更新聊天设置 {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_chat_by_agent_and_user(
    db: AsyncSession, agent_id: str, user_id: str
) -> Optional[models.Chat]:
    """
    根据agent_id和user_id获取唯一的聊天会话
    """
    try:
        result = await db.execute(
            select(models.Chat)
            .options(
                selectinload(models.Chat.settings), selectinload(models.Chat.agent)
            )
            .where(
                models.Chat.agent_id == agent_id,
                models.Chat.user_id == user_id,
                models.Chat.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    except SQLAlchemyError as e:
        logger.error(
            f"数据库查询错误 - 获取聊天会话 agent_id={agent_id}, user_id={user_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(
            f"未知错误 - 获取聊天会话 agent_id={agent_id}, user_id={user_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_chat_by_user_and_agent(
    db: AsyncSession, user_id: str, agent_id: str
) -> Optional[models.Chat]:
    """
    根据user_id和agent_id获取唯一的聊天会话
    """
    return await get_chat_by_agent_and_user(db, agent_id, user_id)


async def delete_chats_by_agent_id(
    db: AsyncSession, agent_id: str, user_id: str
) -> dict:
    """
    删除用户与指定agent的所有聊天记录

    Args:
        db: 数据库会话
        agent_id: Agent ID
        user_id: 用户ID

    Returns:
        dict: 删除结果摘要
    """
    try:
        logger.info(f"开始删除聊天记录 - Agent ID: {agent_id}, User ID: {user_id}")

        # 查找所有匹配的聊天记录
        result = await db.execute(
            select(models.Chat).where(
                models.Chat.agent_id == agent_id, models.Chat.user_id == user_id
            )
        )
        chats = result.scalars().all()

        if not chats:
            logger.debug(f"未找到聊天记录 - Agent ID: {agent_id}, User ID: {user_id}")
            return {
                "chats_deleted": 0,
                "messages_deleted": 0,
                "agent_id": agent_id,
                "user_id": user_id,
                "status": "no_chats_found",
            }

        deleted_chats_count = len(chats)
        total_messages_deleted = 0

        # 开始事务删除
        for chat in chats:
            try:
                # 生成session_id并删除聊天历史
                session_id = generate_session_id(chat.id)

                # 统计消息数量（在删除前）
                try:
                    messages_data = (
                        await chat_history_service.get_messages_paginated_async(
                            session_id=session_id,
                            limit=1000,  # 获取所有消息进行计数
                            offset=0,
                        )
                    )
                    message_count = messages_data.get("total", 0)
                    total_messages_deleted += message_count

                    # 删除聊天历史
                    await chat_history_service.clear_session_async(session_id)
                    logger.debug(
                        f"已删除聊天历史 - Chat ID: {chat.id}, Session ID: {session_id}, 消息数: {message_count}"
                    )

                except Exception as e:
                    logger.warning(
                        f"删除聊天历史失败 - Chat ID: {chat.id}, Error: {str(e)}"
                    )
                    # 继续删除数据库记录，即使聊天历史删除失败

                # 删除数据库中的聊天记录（会级联删除chat_settings）
                await db.delete(chat)
                logger.debug(f"已删除聊天记录 - Chat ID: {chat.id}")

            except Exception as e:
                logger.error(
                    f"删除单个聊天记录失败 - Chat ID: {chat.id}, Error: {str(e)}"
                )
                # 继续处理其他聊天记录
                continue

        # 提交事务
        await db.commit()

        logger.info(
            f"聊天记录删除完成 - Agent ID: {agent_id}, User ID: {user_id}, "
            f"删除聊天数: {deleted_chats_count}, 删除消息数: {total_messages_deleted}"
        )

        return {
            "chats_deleted": deleted_chats_count,
            "messages_deleted": total_messages_deleted,
            "agent_id": agent_id,
            "user_id": user_id,
            "status": "success",
        }

    except Exception as e:
        await db.rollback()
        logger.error(
            f"删除聊天记录失败 - Agent ID: {agent_id}, User ID: {user_id}, Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to delete chat history: {str(e)}"
        )


async def save_debug_messages(
    db: AsyncSession, session_id: str, messages: List[dict]
) -> None:
    """
    保存调试信息到数据库

    Args:
        db: 数据库会话
        session_id: 会话ID
        messages: 要保存的消息列表
    """
    try:
        # 根据 session_id 推算出 chat_id
        # session_id 是通过 generate_session_id(chat_id) 生成的
        # 需要通过查询数据库找到对应的 chat 记录
        from app.core.config import global_config_loaded_from_config_yaml

        # 如果调试功能未启用，直接返回
        if not global_config_loaded_from_config_yaml.app.debug_messages:
            return

        # 查找对应的 chat 记录
        # 这里需要通过遍历来找到对应的 chat（因为 session_id 是基于 chat_id 生成的）
        result = await db.execute(select(models.Chat))
        chats = result.scalars().all()

        target_chat = None
        for chat in chats:
            if generate_session_id(chat.id) == session_id:
                target_chat = chat
                break

        if not target_chat:
            logger.warning(f"未找到对应的 chat 记录，session_id: {session_id}")
            return

        # 将消息列表转换为 JSON 格式并保存
        # 需要处理消息对象，确保它们可以被序列化
        serializable_messages = []
        for msg in messages:
            if hasattr(msg, "dict"):
                # 如果是 Pydantic 模型或类似对象
                serializable_messages.append(msg.model_dump())
            elif hasattr(msg, "__dict__"):
                # 如果是普通对象
                serializable_messages.append(msg.__dict__)
            else:
                # 如果已经是字典
                serializable_messages.append(msg)

        target_chat.debug_messages = serializable_messages

        await db.commit()
        logger.debug(
            f"成功保存调试信息，session_id: {session_id}, 消息数量: {len(messages)}"
        )

    except Exception as e:
        logger.error(f"保存调试信息失败，session_id: {session_id}, 错误: {str(e)}")
        await db.rollback()
        # 不抛出异常，避免影响正常的聊天流程


def _is_network_error(error_message: str, error_type: str) -> bool:
    """
    检查是否是网络相关的错误

    Args:
        error_message: 错误消息
        error_type: 错误类型名称

    Returns:
        是否是网络错误
    """
    error_message_lower = error_message.lower()
    error_type_lower = error_type.lower()

    network_keywords = [
        "connection",
        "timeout",
        "network",
        "socket",
        "ssl",
        "dns",
        "refused",
        "unreachable",
        "reset",
        "eof",
        "connectionerror",
        "timeouterror",
        "socketerror",
        "sslerror",
        "gaierror",
        "httpx",
        "httpcore",
        "transport",
        "connect",
    ]

    # 检查错误消息中是否包含网络相关关键词
    for keyword in network_keywords:
        if keyword in error_message_lower or keyword in error_type_lower:
            return True

    return False


def _is_429_resource_exhausted(exception: Exception) -> bool:
    """判定是否为 Vertex/Gemini 429 RESOURCE_EXHAUSTED 错误。"""
    if getattr(exception, "status_code", None) == 429:
        return True
    msg = str(exception)
    return "429" in msg and "RESOURCE_EXHAUSTED" in msg.upper()


def _is_image_generation_policy_block(error_message: str) -> bool:
    """判定是否为内容安全/合规拦截（Gemini/Fal 等）。"""
    error_message_lower = error_message.lower()
    return (
        "被阻止" in error_message
        or "安全过滤器" in error_message
        or "blocked" in error_message_lower
        or "safety" in error_message_lower
        or "image_prohibited_content" in error_message_lower
        or "finishreason.image_" in error_message_lower
        or "content_policy_violation" in error_message_lower
        or "content checker" in error_message_lower
    )


_DEFAULT_CHAT_IMAGE_TIMEOUT_SECONDS = 30
_SUBSCRIBED_PREMIUM_CHAT_IMAGE_TIMEOUT_SECONDS = 60


def _resolve_chat_image_timeout_seconds(*, is_subscribed: bool, model_id: str) -> int:
    if model_id in (
        NANO_BANANA_PRO.id_on_provider,
        NEWAPI_NANO_BANANA_2.id_on_provider,
    ):
        return _SUBSCRIBED_PREMIUM_CHAT_IMAGE_TIMEOUT_SECONDS
    return _DEFAULT_CHAT_IMAGE_TIMEOUT_SECONDS


async def _record_chat_image_failure(
    db: AsyncSession,
    subscription_service: SubscriptionService,
    session_id: str,
    message_id: int,
    user_id: str,
    agent_id: str,
    message_content: str,
    resolved_model_id: str,
    current_prompt: Optional[str],
    failure_reason: str,
    failure_type: str,
) -> None:
    """记录生图失败：更新消息 meta_data（generated_image_attempt）并记录用量（0）。"""
    try:
        await chat_history_service.update_message_metadata(
            db=db,
            session_id=session_id,
            message_id=message_id,
            metadata_update={
                "generated_image_attempt": {
                    "prompt": current_prompt,
                    "failure_reason": failure_reason,
                    "failure_type": failure_type,
                }
            },
        )
    except Exception as meta_err:
        logger.warning(f"更新失败尝试元数据失败: {meta_err}")
    try:
        await subscription_service.record_usage(
            db,
            user_id,
            "image_generation",
            0,
            extra_data={
                "agent_id": agent_id,
                "message_content": message_content[:100],
                "success": False,
                "failure_reason": failure_reason,
                "failure_type": failure_type,
                "session_id": session_id,
                "message_id": message_id,
                "model": resolved_model_id,
                "prompt": current_prompt,
            },
        )
        logger.debug(f"图片生成失败记录成功: user_id={user_id}")
    except Exception as e:
        logger.warning(f"记录图片生成失败信息失败: {str(e)}")


async def _try_match_existing_image(
    db: AsyncSession,
    chat_id: str,
    agent_id: str,
    user_id: str,
    message_id: int,
    session_id: str,
    current_prompt: str,
    message_content: str,
    subscription_service: SubscriptionService,
    is_network_error: bool = False,
) -> Optional[schemas.ChatImageGenerationResponse]:
    """
    尝试匹配已生成的图片（仅从带 only_include_ai_character 的图中选，并排除已展示过的兜底图）。
    顺序：1) 查询 fallback 候选 2) 去除 sent_fallback_images 3) 剩余图片中相似度匹配。
    """
    from app.services.image_generation_service import image_generation_service
    from app.services.image_transform_service import image_transform_service

    try:
        logger.info(
            f"图片生成失败（{'网络错误' if is_network_error else '安全过滤器'}），"
            f"尝试匹配已生成图片 - Agent ID: {agent_id}, User ID: {user_id}"
        )

        # 读取该 chat 已展示的兜底图 id，避免重复展示
        chat_result = await db.execute(
            select(models.Chat).where(models.Chat.id == chat_id)
        )
        chat = chat_result.scalar_one_or_none()
        sent_fallback_images = list(chat.sent_fallback_images or []) if chat else []

        similar_image = await image_generation_service.find_most_similar_image(
            db=db,
            agent_id=agent_id,
            current_prompt=current_prompt,
            current_user_id=user_id,
            only_include_ai_character=True,
            exclude_image_ids=sent_fallback_images,
        )

        if similar_image:
            matched_user_id = similar_image.get("user_id")
            is_other_user = matched_user_id != user_id
            logger.info(
                f"找到匹配图片，相似度: {similar_image.get('similarity', 0):.3f}, "
                f"来自{'其他用户' if is_other_user else '当前用户'}: {matched_user_id}"
            )

            # 记录已展示的兜底图 id（按 image_id 去重），供后续兜底排除
            image_id = similar_image.get("image_id") or similar_image.get("image_url")
            if chat and image_id and image_id not in sent_fallback_images:
                chat.sent_fallback_images = sent_fallback_images + [image_id]
                await db.flush()

            # 获取GCS URI并转换为CDN URL
            gcs_uri = similar_image.get("image_url", "")
            cdn_url = image_transform_service.transform_desktop(gcs_uri)

            # 更新消息的 meta_data，记录使用的是匹配的图片
            metadata_update = {
                "generated_image": {
                    "image_url": gcs_uri,
                    "width": similar_image.get("width"),
                    "height": similar_image.get("height"),
                    "format": similar_image.get("format", "jpeg"),
                    "prompt": current_prompt,
                    "original_request": message_content,
                    "generation_mode": "fallback_matched_image",
                    "fallback_reason": (
                        "primary_network_error"
                        if is_network_error
                        else "primary_generation_failed"
                    ),
                    "generated_at": datetime.utcnow().isoformat(),
                    "is_matched": True,
                    "similarity": similar_image.get("similarity", 0),
                    "matched_from_user_id": matched_user_id,
                    "matched_from_image_url": gcs_uri,
                }
            }

            await chat_history_service.update_message_metadata(
                db=db,
                session_id=session_id,
                message_id=message_id,
                metadata_update=metadata_update,
            )

            # 记录成功用量（匹配的图片也计入用量）
            try:
                await subscription_service.record_usage(
                    db,
                    user_id,
                    "image_generation",
                    1,
                    extra_data={
                        "agent_id": agent_id,
                        "message_content": message_content[:100],
                        "success": True,
                        "is_matched": True,
                        "generation_mode": "fallback_matched_image",
                        "similarity": similar_image.get("similarity", 0),
                        "matched_from_user_id": matched_user_id,
                        "is_from_other_user": is_other_user,
                        "session_id": session_id,
                        "message_id": message_id,
                        "prompt": current_prompt,
                    },
                )
                logger.debug(f"匹配图片用量记录成功: user_id={user_id}")
            except Exception as e:
                logger.warning(f"记录匹配图片用量失败: {str(e)}")

            return schemas.ChatImageGenerationResponse(
                message_id=message_id,
                image_url=cdn_url,
                image_metadata={
                    "width": similar_image.get("width"),
                    "height": similar_image.get("height"),
                    "format": similar_image.get("format", "jpeg"),
                    "is_matched": True,
                    "similarity": similar_image.get("similarity", 0),
                },
                prompt=current_prompt,
            )
        else:
            logger.info(f"未找到匹配的图片 - Agent ID: {agent_id}")
            return None

    except Exception as e:
        logger.error(f"匹配已生成图片失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def _log_matched_fallback_result(
    agent_id: str,
    request_message_id: int,
    fallback_result: schemas.ChatImageGenerationResponse,
) -> None:
    image_metadata = fallback_result.image_metadata or {}
    logger.info(
        f"消息生图兜底匹配返回结果 - agent_id={agent_id} "
        f"request_message_id={request_message_id} "
        f"response_message_id={fallback_result.message_id} "
        f"image_url={fallback_result.image_url} "
        f"is_matched={image_metadata.get('is_matched')} "
        f"similarity={image_metadata.get('similarity')}"
    )


async def generate_chat_image(
    db: AsyncSession,
    agent_id: str,
    user_id: str,
    message_id: int,
    subscription_service: SubscriptionService,
    history_count: Optional[int] = None,
    model: Optional[
        str
    ] = None,  # TODO: 移除未使用的 model 参数，与 schema/API 一并清理
) -> Union[schemas.ChatImageGenerationResponse, UsageLimitExceeded, BizError]:
    """
    基于聊天上下文生成图片（公共函数）

    流程：
    1. 验证Agent是否存在
    2. 获取或创建聊天会话
    3. 检查图片生成限额
    4. 根据用户订阅状态选择模型
    5. 调用图片生成服务
    6. 记录用量
    7. 返回图片信息

    Args:
        db: 数据库会话
        agent_id: Agent ID
        user_id: 用户ID
        message_id: 要生成图片的消息ID
        history_count: 使用的历史消息数量
        model: 未使用；模型仅按订阅状态选择。保留仅为 API 兼容，待清理。

    Returns:
        成功时返回 `ChatImageGenerationResponse`，业务限制错误时返回 `UsageLimitExceeded` 或 `BizError`

    Raises:
        HTTPException: 其他错误情况（Agent未找到、消息未找到等）
    """
    from app.services.image_generation_service import image_generation_service

    logger.info(f"开始生成聊天图片 - Agent ID: {agent_id}, User ID: {user_id}")

    # 验证Agent是否存在
    result = await db.execute(
        select(models.Agent.id, models.Agent.name).where(models.Agent.id == agent_id)
    )
    agent_basic = result.first()
    if not agent_basic:
        logger.error(f"Agent未找到: {agent_id}")
        raise HTTPException(status_code=404, detail="Agent not found")

    # 获取或创建聊天会话
    chat = await get_or_create_chat_by_agent(db=db, user_id=user_id, agent_id=agent_id)

    # 验证chat中的agent_id是否与传入的一致
    if chat.agent_id != agent_id:
        logger.error(f"Agent ID不匹配: 传入={agent_id}, 实际={chat.agent_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent ID mismatch: expected={agent_id}, actual={chat.agent_id}",
        )

    session_id = generate_session_id(chat.id)

    # 获取用户对象用于限额检查
    user_result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 检查图片生成限额
    is_allowed, used_count, daily_limit = (
        await subscription_service.check_image_gen_limit(db, user)
    )

    if not is_allowed:
        logger.warning(f"用户 {user_id} 已达到图片生成限额: {used_count}/{daily_limit}")

        # 返回业务错误信息，而非抛出异常
        if user.auth_type == AuthType.GUEST:
            error_code = BusinessErrorCode.GUEST_LOGIN_REQUIRED
        else:
            # 获取订阅状态以判断错误码
            subscription_status = (
                await subscription_service.get_user_subscription_status(db, user.id)
            )
            if subscription_status.is_subscribed:
                error_code = BusinessErrorCode.IMAGE_GENERATION_LIMIT_REACHED
            else:
                error_code = BusinessErrorCode.SUBSCRIPTION_REQUIRED

        return UsageLimitExceeded(
            code=error_code["code"],
            error_code=error_code["error_code"],
            message=error_code["message"],
            used_count=used_count,
            daily_limit=daily_limit,
        )

    # 获取Agent完整数据
    agent_data = await agent_service.get_agent_for_chat(db, agent_id=chat.agent_id)
    if not agent_data:
        logger.error(f"Agent数据未找到: {chat.agent_id}")
        raise HTTPException(status_code=404, detail="Agent data not found")

    # 根据 message_id 查询消息内容
    message_content = await chat_history_service.get_message_content(
        db=db,
        session_id=session_id,
        message_id=str(message_id),
    )

    if not message_content:
        logger.error(f"消息未找到: message_id={message_id}")
        raise HTTPException(status_code=404, detail=f"Message not found: {message_id}")

    logger.debug(f"查询到消息内容: {message_content[:100]}...")

    # 验证只能对最后一条AI回复生成图片
    latest_ai_message_id = await chat_history_service.get_latest_ai_message_id(
        db, session_id
    )
    if latest_ai_message_id != message_id:
        logger.warning(
            f"只能对最后一条AI回复生成图片: latest={latest_ai_message_id}, "
            f"requested={message_id}"
        )
        raise HTTPException(
            status_code=400,
            detail="Only the latest AI reply can be used to generate an image",
        )

    # 模型选择仅按订阅状态，使用 config 中的 nickname 解析为 GenAIModel（无请求覆盖）
    from app.core.model_selection import select_chat_image_model
    from app.utils.models_catalog import ModelNameFamily, detect_model_name_family

    subscription_status = await subscription_service.get_user_subscription_status(
        db, user.id
    )
    is_subscribed = subscription_status.is_subscribed

    try:
        resolved_model = select_chat_image_model(user=user, is_subscribed=is_subscribed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    logger.info(
        f"消息生图模型选择 - 订阅: {is_subscribed}, 模型: {resolved_model.nickname} ({resolved_model.id_on_provider})"
    )

    # 调用图片生成服务
    # 重复生成会直接覆盖 meta_data 中的 generated_image，无需删除旧数据
    image_generation_result = None
    failure_reason = None
    failure_type = None

    enable_chat_image_match_fallback = (
        global_config_loaded_from_config_yaml.agent.enable_chat_image_match_fallback
    )
    logger.info(
        f"消息生图兜底配置 - enabled={enable_chat_image_match_fallback} "
        f"agent_id={agent_id} message_id={message_id}"
    )

    # 预先构建提示词，用于匹配已生成图片（可按配置禁用）
    current_prompt = None
    if enable_chat_image_match_fallback:
        try:
            # 获取聊天历史以构建提示词
            messages_data = await chat_history_service.get_messages_paginated_async(
                session_id=session_id,
                limit=history_count
                or global_config_loaded_from_config_yaml.agent.image_generation_default_history_count,
                offset=0,
            )
            chat_history = messages_data.get("messages", [])
            # 获取用户信息（与 image_generation_service 的统一生图入口保持一致）
            user_info = (
                await build_user_info_prompt_block(db, user_id) if user_id else ""
            )
            char_name, user_name = (
                await image_generation_service.get_char_user_names_for_image_prompt(
                    db, user_id, agent_data
                )
            )
            current_prompt = image_generation_service.build_image_prompt(
                agent_data=agent_data,
                chat_history=chat_history,
                user_message=message_content,
                user_info=user_info,
                char_name=char_name,
                user_name=user_name,
            )
            logger.info(
                f"消息生图兜底提示词已构建 - agent_id={agent_id} "
                f"message_id={message_id} prompt_length={len(current_prompt)}"
            )
        except Exception as e:
            logger.info(
                f"消息生图兜底提示词构建失败，兜底可能跳过 - agent_id={agent_id} "
                f"message_id={message_id} error_type={type(e).__name__}"
            )
            logger.warning(f"构建提示词失败，将无法匹配已生成图片: {e}")

    generation_start_time = time.time()
    actual_model = resolved_model.id_on_provider
    model_fallback_due_to_429 = False

    try:
        primary_model = resolved_model.id_on_provider
        primary_model_family = detect_model_name_family(primary_model)
        primary_timeout_seconds = _resolve_chat_image_timeout_seconds(
            is_subscribed=is_subscribed,
            model_id=primary_model,
        )
        if is_subscribed and primary_model_family == ModelNameFamily.GEMINI:
            fallback_model = (
                global_config_loaded_from_config_yaml.agent.sub_user_chat_image_gemini_fallback_model
            )
            try:
                image_generation_result = (
                    await image_generation_service.generate_chat_image(
                        db=db,
                        session_id=session_id,
                        message_id=message_id,
                        agent_data=agent_data,
                        message_content=message_content,
                        user_id=user_id,
                        history_count=history_count,
                        model=primary_model,
                        timeout_seconds=primary_timeout_seconds,
                    )
                )
                actual_model = primary_model
                model_fallback_due_to_429 = False
            except Exception as e:
                if _is_429_resource_exhausted(e):
                    logger.info(
                        f"消息生图 429，重试备用模型 - agent_id={agent_id} "
                        f"message_id={message_id} primary={primary_model} "
                        f"fallback={fallback_model}"
                    )
                    image_generation_result = (
                        await image_generation_service.generate_chat_image(
                            db=db,
                            session_id=session_id,
                            message_id=message_id,
                            agent_data=agent_data,
                            message_content=message_content,
                            user_id=user_id,
                            history_count=history_count,
                            model=fallback_model,
                            timeout_seconds=_resolve_chat_image_timeout_seconds(
                                is_subscribed=is_subscribed,
                                model_id=fallback_model,
                            ),
                        )
                    )
                    actual_model = fallback_model
                    model_fallback_due_to_429 = True
                else:
                    raise
        else:
            image_generation_result = (
                await image_generation_service.generate_chat_image(
                    db=db,
                    session_id=session_id,
                    message_id=message_id,
                    agent_data=agent_data,
                    message_content=message_content,
                    user_id=user_id,
                    history_count=history_count,
                    model=primary_model,
                    timeout_seconds=primary_timeout_seconds,
                )
            )
            actual_model = primary_model
        # 计算生成耗时
        generation_time_ms = int((time.time() - generation_start_time) * 1000)
        image_generation_result["model"] = actual_model
        image_generation_result["generation_time_ms"] = generation_time_ms
        image_generation_result["model_fallback_due_to_429"] = model_fallback_due_to_429
        logger.info(
            f"图片生成完成 - 模型: {actual_model}, 耗时: {generation_time_ms}ms"
            + (", 因429使用备用模型" if model_fallback_due_to_429 else "")
        )
    except ValueError as e:
        error_message = str(e)
        is_network_error = _is_network_error(error_message, type(e).__name__)

        # 若启用兜底，生图失败时尝试匹配已生成图片
        if enable_chat_image_match_fallback and current_prompt:
            logger.info(
                f"消息生图失败后尝试兜底匹配 - agent_id={agent_id} "
                f"message_id={message_id} failure_type={type(e).__name__}"
            )
            fallback_result = await _try_match_existing_image(
                db=db,
                chat_id=chat.id,
                agent_id=agent_id,
                user_id=user_id,
                message_id=message_id,
                session_id=session_id,
                current_prompt=current_prompt,
                message_content=message_content,
                subscription_service=subscription_service,
                is_network_error=is_network_error,
            )
            if fallback_result:
                _log_matched_fallback_result(
                    agent_id=agent_id,
                    request_message_id=message_id,
                    fallback_result=fallback_result,
                )
                return fallback_result
        else:
            fallback_skip_reason = (
                "fallback_disabled"
                if not enable_chat_image_match_fallback
                else "fallback_prompt_unavailable"
            )
            logger.info(
                f"消息生图失败后跳过兜底匹配 - agent_id={agent_id} "
                f"message_id={message_id} reason={fallback_skip_reason}"
            )

        # 检查是否是安全过滤器阻止（用于记录日志和返回业务错误）
        is_safety_filter = _is_image_generation_policy_block(error_message)

        if is_safety_filter:
            block_reason = None
            if "原因:" in error_message:
                reason_part = error_message.split("原因:", 1)[1].strip()
                if reason_part:
                    block_reason = reason_part
            elif ":" in error_message and "阻止" in error_message:
                parts = error_message.split(":", 1)
                if len(parts) > 1:
                    block_reason = parts[1].strip()

            failure_reason = block_reason or error_message
            failure_type = "safety_filter"

            logger.warning(
                f"图片生成被安全过滤器阻止 - Agent ID: {agent_id}, "
                f"Message ID: {message_id}, Reason: {failure_reason}"
            )
            await _record_chat_image_failure(
                db=db,
                subscription_service=subscription_service,
                session_id=session_id,
                message_id=message_id,
                user_id=user_id,
                agent_id=agent_id,
                message_content=message_content,
                resolved_model_id=resolved_model.id_on_provider,
                current_prompt=current_prompt,
                failure_reason=failure_reason,
                failure_type=failure_type,
            )
            return BizError(
                code=BusinessErrorCode.IMAGE_GENERATION_BLOCKED["code"],
                error_code=BusinessErrorCode.IMAGE_GENERATION_BLOCKED["error_code"],
                message=BusinessErrorCode.IMAGE_GENERATION_BLOCKED["message"],
            )
        else:
            # 其他 ValueError 异常
            failure_reason = error_message
            failure_type = "value_error"
            raise
    except Exception as e:
        # 捕获所有其他异常（网络错误、超时等）
        error_message = str(e)
        failure_reason = error_message
        failure_type = type(e).__name__.lower()
        is_network_error = _is_network_error(error_message, failure_type)

        # 若启用兜底，生图失败时尝试匹配已生成图片
        if enable_chat_image_match_fallback and current_prompt:
            logger.info(
                f"消息生图失败后尝试兜底匹配 - agent_id={agent_id} "
                f"message_id={message_id} failure_type={failure_type}"
            )
            fallback_result = await _try_match_existing_image(
                db=db,
                chat_id=chat.id,
                agent_id=agent_id,
                user_id=user_id,
                message_id=message_id,
                session_id=session_id,
                current_prompt=current_prompt,
                message_content=message_content,
                subscription_service=subscription_service,
                is_network_error=is_network_error,
            )
            if fallback_result:
                _log_matched_fallback_result(
                    agent_id=agent_id,
                    request_message_id=message_id,
                    fallback_result=fallback_result,
                )
                return fallback_result
        else:
            fallback_skip_reason = (
                "fallback_disabled"
                if not enable_chat_image_match_fallback
                else "fallback_prompt_unavailable"
            )
            logger.info(
                f"消息生图失败后跳过兜底匹配 - agent_id={agent_id} "
                f"message_id={message_id} reason={fallback_skip_reason}"
            )

        if _is_image_generation_policy_block(error_message):
            failure_type = "safety_filter"
            logger.warning(
                f"图片生成被安全策略阻止 - Agent ID: {agent_id}, "
                f"Message ID: {message_id}, Reason: {failure_reason}"
            )
            await _record_chat_image_failure(
                db=db,
                subscription_service=subscription_service,
                session_id=session_id,
                message_id=message_id,
                user_id=user_id,
                agent_id=agent_id,
                message_content=message_content,
                resolved_model_id=resolved_model.id_on_provider,
                current_prompt=current_prompt,
                failure_reason=failure_reason,
                failure_type=failure_type,
            )
            return BizError(
                code=BusinessErrorCode.IMAGE_GENERATION_BLOCKED["code"],
                error_code=BusinessErrorCode.IMAGE_GENERATION_BLOCKED["error_code"],
                message=BusinessErrorCode.IMAGE_GENERATION_BLOCKED["message"],
            )

        logger.error(
            f"图片生成失败 - Agent ID: {agent_id}, "
            f"Message ID: {message_id}, Error Type: {failure_type}, "
            f"Reason: {failure_reason}"
        )
        await _record_chat_image_failure(
            db=db,
            subscription_service=subscription_service,
            session_id=session_id,
            message_id=message_id,
            user_id=user_id,
            agent_id=agent_id,
            message_content=message_content,
            resolved_model_id=resolved_model.id_on_provider,
            current_prompt=current_prompt,
            failure_reason=failure_reason,
            failure_type=failure_type,
        )
        raise

    # 记录成功用量
    try:
        await subscription_service.record_usage(
            db,
            user_id,
            "image_generation",
            1,
            extra_data={
                "agent_id": agent_id,
                "message_content": message_content[:100],  # 只记录前100个字符
                "success": True,
                "session_id": session_id,
                "message_id": message_id,
                "model": actual_model,
                "generation_time_ms": image_generation_result.get("generation_time_ms"),
                "model_fallback_due_to_429": model_fallback_due_to_429,
                "prompt": image_generation_result.get("prompt"),
            },
        )
        logger.debug(f"图片生成用量记录成功: user_id={user_id}")
    except Exception as e:
        logger.warning(f"记录图片生成用量失败: {str(e)}")

    # 追加更新 meta_data，添加模型、耗时、是否因429使用备用模型及提示词
    try:
        await chat_history_service.update_message_metadata(
            db=db,
            session_id=session_id,
            message_id=message_id,
            metadata_update={
                "generated_image": {
                    "model": actual_model,
                    "generation_time_ms": generation_time_ms,
                    "model_fallback_due_to_429": model_fallback_due_to_429,
                    "prompt": image_generation_result.get("prompt"),
                    "original_request": message_content,
                    "generation_mode": "fresh_generation",
                }
            },
        )
        logger.debug(
            f"消息 meta_data 已更新，添加模型和耗时信息: message_id={message_id}"
        )
    except Exception as e:
        logger.warning(f"更新消息 meta_data 失败: {str(e)}")

    response = schemas.ChatImageGenerationResponse(**image_generation_result)

    logger.info(
        f"聊天图片生成成功 - Agent ID: {agent_id}, Message ID: {response.message_id}"
    )

    return response


async def generate_chat_music(
    db: AsyncSession,
    agent_id: str,
    user_id: str,
    message_id: int,
    subscription_service: SubscriptionService,
    history_count: Optional[int] = None,
    model: Optional[str] = None,
) -> Union[schemas.ChatMusicGenerationResponse, UsageLimitExceeded]:
    """
    基于聊天上下文生成音乐（MVP）

    流程：
    1. 验证 Agent / Chat / 用户
    2. 检查音乐生成限额
    3. 选择模型并调用音乐生成服务
    4. 写入消息 audio_url 与 generated_music 元数据
    5. 记录用量并返回结果
    """
    from app.core.model_selection import select_chat_music_model
    from app.services.music_generation_service import music_generation_service

    logger.info(f"开始生成聊天音乐 - Agent ID: {agent_id}, User ID: {user_id}")

    # 验证 Agent 是否存在
    result = await db.execute(
        select(models.Agent.id, models.Agent.name).where(models.Agent.id == agent_id)
    )
    agent_basic = result.first()
    if not agent_basic:
        logger.error(f"Agent未找到: {agent_id}")
        raise HTTPException(status_code=404, detail="Agent not found")

    chat = await get_or_create_chat_by_agent(db=db, user_id=user_id, agent_id=agent_id)
    if chat.agent_id != agent_id:
        logger.error(f"Agent ID不匹配: 传入={agent_id}, 实际={chat.agent_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent ID mismatch: expected={agent_id}, actual={chat.agent_id}",
        )

    session_id = generate_session_id(chat.id)

    user_result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_allowed, used_count, daily_limit = (
        await subscription_service.check_music_gen_limit(db, user)
    )
    if not is_allowed:
        logger.warning(f"用户 {user_id} 已达到音乐生成限额: {used_count}/{daily_limit}")
        if user.auth_type == AuthType.GUEST:
            error_code = BusinessErrorCode.GUEST_LOGIN_REQUIRED
        else:
            subscription_status = (
                await subscription_service.get_user_subscription_status(db, user.id)
            )
            if subscription_status.is_subscribed:
                error_code = BusinessErrorCode.MUSIC_GENERATION_LIMIT_REACHED
            else:
                error_code = BusinessErrorCode.SUBSCRIPTION_REQUIRED
        return UsageLimitExceeded(
            code=error_code["code"],
            error_code=error_code["error_code"],
            message=error_code["message"],
            used_count=used_count,
            daily_limit=daily_limit,
        )

    message_content = await chat_history_service.get_message_content(
        db=db,
        session_id=session_id,
        message_id=str(message_id),
    )
    if not message_content:
        logger.error(f"消息未找到: message_id={message_id}")
        raise HTTPException(status_code=404, detail=f"Message not found: {message_id}")

    latest_ai_message_id = await chat_history_service.get_latest_ai_message_id(
        db, session_id
    )
    if latest_ai_message_id != message_id:
        logger.warning(
            f"只能对最后一条AI回复生成音乐: latest={latest_ai_message_id}, requested={message_id}"
        )
        raise HTTPException(
            status_code=400,
            detail="Only the latest AI reply can be used to generate music",
        )

    agent_data = await agent_service.get_agent_for_chat(db, agent_id=chat.agent_id)
    if not agent_data:
        logger.error(f"Agent数据未找到: {chat.agent_id}")
        raise HTTPException(status_code=404, detail="Agent data not found")

    subscription_status = await subscription_service.get_user_subscription_status(
        db, user.id
    )
    resolved_model = model
    if not resolved_model:
        resolved_model = select_chat_music_model(
            user=user, is_subscribed=subscription_status.is_subscribed
        )

    generation_start_time = time.time()
    music_generation_result = (
        await music_generation_service.generate_chat_music_for_message(
            db=db,
            session_id=session_id,
            message_id=message_id,
            agent_data=agent_data,
            message_content=message_content,
            model=resolved_model,
            user_id=user_id,
            history_count=history_count,
        )
    )
    generation_time_ms = int((time.time() - generation_start_time) * 1000)

    music_generation_result["model"] = resolved_model
    music_generation_result["generation_time_ms"] = generation_time_ms

    audio_url = music_generation_result["audio_url"]
    audio_metadata = music_generation_result.get("audio_metadata", {})
    audio_duration = audio_metadata.get("duration_sec")
    if audio_duration is not None:
        try:
            audio_duration = float(audio_duration)
        except (TypeError, ValueError):
            audio_duration = None

    # 写入统一 metadata 与 audio_url 字段，方便 Android 直接复用现有播放能力。
    await chat_history_service.update_message_metadata(
        db=db,
        session_id=session_id,
        message_id=message_id,
        metadata_update={
            "generated_music": {
                "audio_url": audio_url,
                "prompt": music_generation_result.get("prompt"),
                "model": resolved_model,
                "generation_time_ms": generation_time_ms,
                "generated_at": datetime.utcnow().isoformat(),
                **audio_metadata,
            }
        },
    )
    await chat_history_service.update_message_audio_url(
        db=db,
        session_id=session_id,
        message_id=str(message_id),
        audio_url=audio_url,
        audio_duration=audio_duration,
    )

    try:
        await subscription_service.record_usage(
            db,
            user_id,
            "music_generation",
            1,
            extra_data={
                "agent_id": agent_id,
                "message_id": message_id,
                "session_id": session_id,
                "message_content": message_content[:100],
                "model": resolved_model,
                "prompt": music_generation_result.get("prompt"),
                "generation_time_ms": generation_time_ms,
                "success": True,
            },
        )
        logger.debug(f"音乐生成用量记录成功: user_id={user_id}")
    except Exception as e:
        logger.warning(f"记录音乐生成用量失败: {str(e)}")

    response = schemas.ChatMusicGenerationResponse(**music_generation_result)
    logger.info(
        f"聊天音乐生成成功 - Agent ID: {agent_id}, Message ID: {response.message_id}"
    )
    return response
