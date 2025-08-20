import json
import logging
import uuid
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.services import chat_history_service
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


async def _get_agent_info(db: AsyncSession, agent_id: str) -> tuple[str, str, str]:
    """
    获取Agent信息（名称、头像、开场白）
    优先从缓存获取，缓存未命中则查询数据库
    """
    # 优先从缓存获取
    cached_agent = cache_service.get_agent_config(agent_id)
    if cached_agent:
        return (
            cached_agent.get("name"),
            cached_agent.get("avatar"),
            cached_agent.get("opening"),
        )

    # 缓存未命中，查询数据库
    result = await db.execute(
        select(models.Agent.name, models.Agent.avatar, models.Agent.opening).where(
            models.Agent.id == agent_id
        )
    )
    agent_row = result.first()

    if not agent_row:
        raise HTTPException(status_code=404, detail="Agent不存在")

    agent_name, agent_avatar, agent_opening = agent_row

    # 缓存Agent信息
    cache_service.set_agent_config(
        agent_id, {"name": agent_name, "avatar": agent_avatar, "opening": agent_opening}
    )

    return agent_name, agent_avatar, agent_opening


async def _load_agent_info_and_cache(
    db: AsyncSession, chat: models.Chat, agent_id: str, session_key: str
) -> None:
    """
    为现有聊天加载Agent信息并缓存会话数据
    """
    try:
        agent_name, agent_avatar, agent_opening = await _get_agent_info(db, agent_id)

        chat.agent_name = agent_name
        chat.agent_avatar = agent_avatar

        # 检查是否需要添加开场白
        await _add_opening_message_if_needed(chat.id, agent_opening)

        # 缓存会话信息
        session_data = {
            "chat_id": chat.id,
            "user_id": chat.user_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "agent_avatar": agent_avatar,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
        }
        cache_service.set_session_info(session_key, session_data)

        # 设置默认值
        chat.last_message = None
        chat.last_message_time = None

    except Exception as e:
        logger.error(f"加载Agent信息失败: {str(e)}")
        # 不抛出异常，但记录错误


async def _add_opening_message_if_needed(chat_id: str, agent_opening: str) -> None:
    """
    如果聊天会话为空且有开场白，则添加开场白
    """
    if not agent_opening:
        return

    try:
        session_id = generate_session_id(chat_id)
        existing_messages = chat_history_service.get_messages_paginated(
            session_id=session_id, limit=1, offset=0
        )

        if existing_messages.get("total", 0) == 0:
            chat_history_service.add_agent_opening_message(session_id, agent_opening)
            logger.info(f"添加Agent开场白 - Session ID: {session_id}")

    except Exception as e:
        logger.error(f"添加开场白失败: {str(e)}")
        # 不影响主流程


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
                    chat_history_service.get_last_message_with_timestamp(session_id)
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
            .where(models.Chat.user_id == user_id, models.Chat.is_active == True)
        )
        all_chats = result.scalars().all()

        # Get recent message and timestamp for each chat, and filter out opening-only chats
        chats_with_message_time = []
        for chat in all_chats:
            try:
                # Use unified session_id generation rule
                session_id = generate_session_id(chat.id)
                last_message_data = (
                    chat_history_service.get_last_message_with_timestamp(session_id)
                )

                if last_message_data:
                    chat.last_message = last_message_data["content"]
                    chat.last_message_time = last_message_data["timestamp"]
                else:
                    chat.last_message = None
                    chat.last_message_time = None

                # Check if chat has user messages (not just opening messages)
                messages_data = chat_history_service.get_messages_paginated(
                    session_id=session_id, limit=10, offset=0  # Check first 10 messages
                )

                # Filter out chats that only have opening messages
                has_user_messages = False
                if messages_data and messages_data.get("messages"):
                    for message in messages_data["messages"]:
                        if message.get("role") == "user":
                            has_user_messages = True
                            break

                # Only include chats that have user messages
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

        db_chat = models.Chat(id=chat_id, **chat_in.dict(), user_id=user_id)

        db.add(db_chat)
        await db.commit()
        await db.refresh(db_chat)

        # Add Agent opening message to chat_history, use unified session_id generation rule
        if agent.opening:
            try:
                session_id = generate_session_id(chat_id)
                # 检查是否已有消息，避免重复添加开场白
                existing_messages = chat_history_service.get_messages_paginated(
                    session_id=session_id, limit=1, offset=0
                )
                if existing_messages.get("total", 0) == 0:
                    chat_history_service.add_agent_opening_message(
                        session_id, agent.opening
                    )
                    logger.info(f"添加Agent开场白成功 - Session ID: {session_id}")
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
            last_message_data = chat_history_service.get_last_message_with_timestamp(
                session_id
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
            raise HTTPException(status_code=404, detail="聊天不存在")

        update_data = chat_in.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的数据")

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
        raise HTTPException(status_code=400, detail="数据完整性约束违反")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            f"数据库错误 - 更新聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(
            f"未知错误 - 更新聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="服务器内部错误")


async def delete_chat(db: AsyncSession, *, db_chat: models.Chat) -> models.Chat:
    """
    删除聊天
    """
    try:
        if not db_chat:
            raise HTTPException(status_code=404, detail="聊天不存在")

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
        raise HTTPException(status_code=400, detail="无法删除聊天，存在关联数据")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            f"数据库错误 - 删除聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(
            f"未知错误 - 删除聊天 {db_chat.id if db_chat else 'unknown'}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="服务器内部错误")


async def get_or_create_chat_by_agent(
    db: AsyncSession, user_id: str, agent_id: str
) -> models.Chat:
    """
    根据用户ID和Agent ID获取或创建唯一的聊天会话
    每个用户和每个Agent只能有一个活跃会话
    依赖数据库唯一索引确保数据一致性
    """
    try:
        logger.info(f"获取或创建聊天会话 - 用户ID: {user_id}, Agent ID: {agent_id}")

        session_key = f"{user_id}:{agent_id}"

        # 1. 检查缓存
        cached_session = cache_service.get_session_info(session_key)
        if cached_session:
            logger.debug(f"从缓存获取聊天会话: {cached_session['chat_id']}")
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
            return chat

        # 2. 查询现有聊天会话
        result = await db.execute(
            select(models.Chat).where(
                models.Chat.user_id == user_id,
                models.Chat.agent_id == agent_id,
                models.Chat.is_active == True,
            )
        )
        existing_chat = result.scalar_one_or_none()

        if existing_chat:
            logger.info(f"找到现有聊天会话 - Chat ID: {existing_chat.id}")
            await _load_agent_info_and_cache(db, existing_chat, agent_id, session_key)
            return existing_chat

        # 3. 获取Agent信息
        agent_info = await _get_agent_info(db, agent_id)
        agent_name, agent_avatar, agent_opening = agent_info

        # 4. 创建新聊天会话（依赖唯一约束处理并发）
        chat_id = str(uuid.uuid4())
        logger.info(f"创建新聊天会话 - Chat ID: {chat_id}")

        new_chat = models.Chat(
            id=chat_id, user_id=user_id, agent_id=agent_id, is_active=True
        )

        db.add(new_chat)

        try:
            await db.commit()
            await db.refresh(new_chat)
            logger.info(f"成功创建新聊天会话 - Chat ID: {new_chat.id}")

        except IntegrityError as e:
            # 并发冲突：另一个请求已创建了记录
            await db.rollback()
            logger.info(f"并发创建冲突，查询现有记录 - {str(e)}")

            result = await db.execute(
                select(models.Chat).where(
                    models.Chat.user_id == user_id,
                    models.Chat.agent_id == agent_id,
                    models.Chat.is_active == True,
                )
            )
            new_chat = result.scalar_one()
            logger.info(f"并发冲突解决，使用现有聊天会话 - Chat ID: {new_chat.id}")

        # 5. 设置Agent信息
        new_chat.agent_name = agent_name
        new_chat.agent_avatar = agent_avatar

        # 6. 添加开场白（如果需要）
        await _add_opening_message_if_needed(new_chat.id, agent_opening)

        # 7. 缓存会话信息
        session_data = {
            "chat_id": new_chat.id,
            "user_id": user_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "agent_avatar": agent_avatar,
            "created_at": new_chat.created_at,
            "updated_at": new_chat.updated_at,
        }
        cache_service.set_session_info(session_key, session_data)

        # 8. 设置默认值
        new_chat.last_message = None
        new_chat.last_message_time = None

        return new_chat

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 获取或创建聊天: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 获取或创建聊天: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


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
            raise HTTPException(status_code=404, detail="聊天记录不存在")

        # 如果不存在，尝试创建新的设置
        settings_id = str(uuid.uuid4())
        db_settings = models.ChatSettings(
            id=settings_id,
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
            language="zh",  # 默认中文
            voice_enabled=False,  # 默认不启用语音自动播放
            keep_talking=True,
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
            return settings_with_agent

        except IntegrityError:
            # 并发创建冲突，回滚并查询已存在的设置
            await db.rollback()
            logger.info(f"并发创建聊天设置冲突，查询已存在设置 - chat_id: {chat_id}")

            result = await db.execute(
                select(models.ChatSettings)
                .options(selectinload(models.ChatSettings.agent))
                .where(models.ChatSettings.chat_id == chat_id)
            )
            settings = result.scalar_one()
            return settings

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 获取或创建聊天设置 {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 获取或创建聊天设置 {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


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
            raise HTTPException(status_code=404, detail="聊天设置不存在")

        # 更新设置
        update_data = settings_update.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的数据")

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
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 更新聊天设置 {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


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
        raise HTTPException(status_code=500, detail="数据库查询失败")
    except Exception as e:
        logger.error(
            f"未知错误 - 获取聊天会话 agent_id={agent_id}, user_id={user_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="服务器内部错误")


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
            logger.info(f"未找到聊天记录 - Agent ID: {agent_id}, User ID: {user_id}")
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
                    messages_data = chat_history_service.get_messages_paginated(
                        session_id=session_id,
                        limit=1000,  # 获取所有消息进行计数
                        offset=0,
                    )
                    message_count = messages_data.get("total", 0)
                    total_messages_deleted += message_count

                    # 删除聊天历史
                    chat_history_service.clear_session(session_id)
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
        raise HTTPException(status_code=500, detail=f"删除聊天记录失败: {str(e)}")


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
        from app.core.config import settings

        # 如果调试功能未启用，直接返回
        if not settings.app.debug_messages:
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
                serializable_messages.append(msg.dict())
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


async def get_debug_messages(
    db: AsyncSession,
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> dict:
    """
    查询debug messages

    Args:
        db: 数据库会话
        user_id: 用户ID过滤（可选）
        agent_id: Agent ID过滤（可选）
        skip: 跳过记录数
        limit: 限制记录数

    Returns:
        dict: 包含总数和分页数据的字典
    """
    try:
        from sqlalchemy import and_, func

        # 构建基础查询
        query = (
            select(
                models.Chat.id.label("chat_id"),
                models.Chat.user_id,
                models.Chat.agent_id,
                models.Chat.debug_messages,
                models.Chat.created_at,
                models.Chat.updated_at,
                models.User.nickname.label("user_nickname"),
                models.Agent.name.label("agent_name"),
            )
            .select_from(
                models.Chat.__table__.join(
                    models.User.__table__, models.Chat.user_id == models.User.id
                ).join(models.Agent.__table__, models.Chat.agent_id == models.Agent.id)
            )
            .where(
                models.Chat.debug_messages.isnot(None)  # 只查询有debug_messages的记录
            )
        )

        # 添加过滤条件
        conditions = []
        if user_id:
            conditions.append(models.Chat.user_id == user_id)
        if agent_id:
            conditions.append(models.Chat.agent_id == agent_id)

        if conditions:
            query = query.where(and_(*conditions))

        # 获取总数
        count_query = (
            select(func.count())
            .select_from(
                models.Chat.__table__.join(
                    models.User.__table__, models.Chat.user_id == models.User.id
                ).join(models.Agent.__table__, models.Chat.agent_id == models.Agent.id)
            )
            .where(models.Chat.debug_messages.isnot(None))
        )

        if conditions:
            count_query = count_query.where(and_(*conditions))

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # 添加排序和分页
        query = query.order_by(models.Chat.updated_at.desc()).offset(skip).limit(limit)

        # 执行查询
        result = await db.execute(query)
        rows = result.fetchall()

        # 转换为响应格式
        items = []
        for row in rows:
            items.append(
                {
                    "chat_id": row.chat_id,
                    "user_id": row.user_id,
                    "user_nickname": row.user_nickname,
                    "agent_id": row.agent_id,
                    "agent_name": row.agent_name,
                    "debug_messages": row.debug_messages,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
            )

        has_more = total > skip + len(items)

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": items,
            "has_more": has_more,
        }

    except Exception as e:
        logger.error(f"查询debug messages失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询debug messages失败: {str(e)}")
