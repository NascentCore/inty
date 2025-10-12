import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_postgres import PostgresChatMessageHistory
from loguru import logger
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent.prompt_template import (
    has_template_variable,
    render_prompt_jinja2_template,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.models.chat_history import ChatHistory


def _parse_message_content(message_raw) -> Dict[str, str]:
    """
    解析消息内容，提取文本内容和角色

    Args:
        message_raw: 原始消息数据

    Returns:
        包含content和role的字典
    """
    try:
        # 处理消息数据
        if isinstance(message_raw, str):
            message_data = json.loads(message_raw)
        elif isinstance(message_raw, dict):
            message_data = message_raw
        else:
            message_data = json.loads(str(message_raw))

        # 解析消息类型和内容
        message_type = message_data.get("type", "human")
        content = ""

        if "data" in message_data and "content" in message_data["data"]:
            content = message_data["data"]["content"]
        elif "content" in message_data:
            content = message_data["content"]

        # 确定角色
        role = "user" if message_type in ["human", "HumanMessage"] else "assistant"

        return {"content": content, "role": role}

    except Exception as e:
        logger.warning(f"解析消息内容失败: {str(e)}")
        return {"content": str(message_raw) if message_raw else "", "role": "unknown"}


# Keep the legacy connection function for PostgresChatMessageHistory compatibility
_connection = None


def get_chat_history_connection():
    """Legacy function for PostgresChatMessageHistory - keep for backward compatibility"""
    global _connection
    if _connection is None or _connection.closed:
        try:
            import psycopg

            _connection = psycopg.connect(
                global_config_loaded_from_config_yaml.database.url, autocommit=True
            )
            logger.info("chat_history数据库连接已建立")
        except Exception as e:
            logger.error(f"建立chat_history数据库连接失败: {str(e)}")
            raise
    return _connection


# chat_history表现在由Alembic迁移管理，不需要手动初始化


def get_chat_history(session_id: str) -> PostgresChatMessageHistory:
    """获取聊天历史"""
    conn = get_chat_history_connection()
    return PostgresChatMessageHistory("chat_history", session_id, sync_connection=conn)


async def add_agent_opening_message(
    db: AsyncSession,
    session_id: str,
    opening_message: str,
    audio_url: Optional[str] = None,
    agent_id: Optional[str] = None,
    audio_duration: Optional[float] = None,
    agent_name: Optional[str] = "I",
    user_name: Optional[str] = "you",
) -> None:
    """添加Agent开场白到聊天历史"""
    try:
        if has_template_variable(opening_message):
            opening_message = render_prompt_jinja2_template(
                opening_message, char=agent_name, user=user_name
            )

        # 构建AIMessage的JSON格式数据
        message_data = {
            "type": "ai",
            "data": {"content": opening_message},
        }

        # 构建meta_data
        meta_data = None
        if agent_id or audio_duration is not None:
            meta_data = {}
            if agent_id:
                meta_data["agentId"] = agent_id
                meta_data["isOpening"] = True
            if audio_duration is not None:
                meta_data["audioDuration"] = audio_duration

        # 使用ORM创建新记录
        chat_history = ChatHistory(
            session_id=session_id,
            message=message_data,
            audio_url=audio_url,
            meta_data=meta_data,
        )

        db.add(chat_history)
        await db.commit()

        logger.debug(
            f"添加开场白到会话 {session_id}: {processed_opening}, audio_url: {audio_url}"
        )

    except Exception as e:
        logger.error(f"添加开场白失败 {session_id}: {str(e)}")
        await db.rollback()
        raise


def get_last_message(session_id: str) -> Optional[str]:
    """获取最近一条消息内容"""
    try:
        history = get_chat_history(session_id)
        messages = history.messages
        if messages:
            last_message = messages[-1]
            return last_message.content
        return None
    except Exception as e:
        logger.error(f"获取最近消息失败 {session_id}: {str(e)}")
        # 返回None而不是抛出异常，让主要功能继续工作
        return None


def get_last_message_with_timestamp(session_id: str) -> Optional[Dict[str, Any]]:
    """获取最近一条消息内容和时间戳"""
    try:
        conn = get_chat_history_connection()

        # 查询最近一条消息
        query = """
            SELECT message, created_at
            FROM chat_history 
            WHERE session_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1
        """

        with conn.cursor() as cur:
            cur.execute(query, (session_id,))
            row = cur.fetchone()

            if row:
                try:
                    # 处理消息数据
                    message_raw = row[0]
                    if isinstance(message_raw, str):
                        message_data = json.loads(message_raw)
                    elif isinstance(message_raw, dict):
                        message_data = message_raw
                    else:
                        message_data = json.loads(str(message_raw))

                    created_at = row[1]

                    # 解析消息内容
                    content = ""
                    if "data" in message_data and "content" in message_data["data"]:
                        content = message_data["data"]["content"]
                    elif "content" in message_data:
                        content = message_data["content"]

                    return {"content": content, "timestamp": created_at}

                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    logger.warning(
                        f"解析最近消息失败 {session_id}: {str(e)}, 原始数据: {row[0]}"
                    )
                    return None

            return None

    except Exception as e:
        logger.error(f"获取最近消息失败 {session_id}: {str(e)}")
        return None


def add_user_message(session_id: str, message: str) -> None:
    """添加用户消息到聊天历史"""
    try:
        history = get_chat_history(session_id)
        history.add_messages([HumanMessage(content=message)])
        logger.debug(f"添加用户消息到会话 {session_id}: {message}")
    except Exception as e:
        logger.error(f"添加用户消息失败 {session_id}: {str(e)}")
        raise


async def add_ai_message(
    db: AsyncSession,
    session_id: str,
    message: str,
    agent_id: Optional[str] = None,
    audio_duration: Optional[float] = None,
) -> Optional[int]:
    """添加AI消息到聊天历史，返回插入的消息ID"""
    try:
        # 构建AIMessage的JSON格式数据
        message_data = {"type": "ai", "data": {"content": message}}

        # 构建meta_data
        meta_data = None
        if agent_id or audio_duration is not None:
            meta_data = {}
            if agent_id:
                meta_data["agentId"] = agent_id
                meta_data["isOpening"] = False
            if audio_duration is not None:
                meta_data["audioDuration"] = audio_duration

        # 使用ORM创建新记录
        chat_history = ChatHistory(
            session_id=session_id, message=message_data, meta_data=meta_data
        )

        db.add(chat_history)
        await db.commit()
        await db.refresh(chat_history)  # 获取生成的ID

        logger.debug(f"添加AI消息到会话 {session_id}: {message}, ID: {chat_history.id}")
        return chat_history.id

    except Exception as e:
        logger.error(f"添加AI消息失败 {session_id}: {str(e)}")
        await db.rollback()
        raise


async def get_latest_ai_message_id(db: AsyncSession, session_id: str) -> Optional[int]:
    """获取会话中最新的AI消息ID"""
    try:
        # 使用ORM查询最新的AI消息ID
        stmt = (
            select(ChatHistory.id)
            .where(
                and_(
                    ChatHistory.session_id == session_id,
                    ChatHistory.message["type"].astext == "ai",
                )
            )
            .order_by(desc(ChatHistory.created_at), desc(ChatHistory.id))
            .limit(1)
        )

        result = await db.execute(stmt)
        row = result.first()

        return row[0] if row else None

    except Exception as e:
        logger.error(f"获取最新AI消息ID失败 {session_id}: {str(e)}")
        return None


async def get_latest_ai_message_info(
    db: AsyncSession, session_id: str
) -> Optional[Dict[str, Any]]:
    """获取会话中最新AI消息的完整信息"""
    try:
        # 使用ORM查询最新的AI消息完整信息
        stmt = (
            select(ChatHistory)
            .where(
                and_(
                    ChatHistory.session_id == session_id,
                    ChatHistory.message["type"].astext == "ai",
                )
            )
            .order_by(desc(ChatHistory.created_at), desc(ChatHistory.id))
            .limit(1)
        )

        result = await db.execute(stmt)
        chat_history = result.scalar_one_or_none()

        if not chat_history:
            return None

        # 解析消息内容
        content = ""
        try:
            message_data = chat_history.message
            if "data" in message_data and "content" in message_data["data"]:
                content = message_data["data"]["content"]
            elif "content" in message_data:
                content = message_data["content"]

        except (TypeError, KeyError) as e:
            logger.warning(f"解析AI消息内容失败: {str(e)}")
            content = str(chat_history.message) if chat_history.message else ""

        return {
            "id": chat_history.id,
            "content": content,
            "audio_url": chat_history.audio_url,
            "meta_data": chat_history.meta_data,
            "timestamp": (
                chat_history.created_at.isoformat() if chat_history.created_at else None
            ),
        }

    except Exception as e:
        logger.error(f"获取最新AI消息信息失败 {session_id}: {str(e)}")
        return None


def get_messages_paginated(
    session_id: str, limit: int = 20, offset: int = 0
) -> Dict[str, Any]:
    """
    分页获取聊天消息

    Args:
        session_id: 会话ID
        limit: 每页消息数量
        offset: 偏移量（跳过的消息数量）

    Returns:
        包含消息列表和分页信息的字典
    """
    try:
        conn = get_chat_history_connection()

        # 查询总消息数
        count_query = """
            SELECT COUNT(*) 
            FROM chat_history 
            WHERE session_id = %s
        """

        with conn.cursor() as cur:
            cur.execute(count_query, (session_id,))
            total_count = cur.fetchone()[0]

        # 分页查询消息（按时间倒序，最新的在前）- 包括消息ID、audio_url和meta_data
        messages_query = """
            SELECT id, message, created_at, audio_url, meta_data
            FROM chat_history 
            WHERE session_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        """

        messages = []
        with conn.cursor() as cur:
            cur.execute(messages_query, (session_id, limit, offset))
            rows = cur.fetchall()

            for row in rows:
                try:
                    # 提取消息ID、消息数据、创建时间、audio_url和meta_data
                    message_id = row[0]
                    message_raw = row[1]
                    created_at = row[2]
                    audio_url = row[3]
                    meta_data_raw = row[4]

                    # 处理消息数据，可能是字符串或已经是字典
                    if isinstance(message_raw, str):
                        message_data = json.loads(message_raw)
                    elif isinstance(message_raw, dict):
                        message_data = message_raw
                    else:
                        # 尝试转换为字符串再解析
                        message_data = json.loads(str(message_raw))

                    # 解析消息类型和内容
                    message_type = message_data.get("type", "human")
                    content = ""

                    if "data" in message_data and "content" in message_data["data"]:
                        content = message_data["data"]["content"]
                    elif "content" in message_data:
                        content = message_data["content"]

                    # 确定角色
                    role = (
                        "user"
                        if message_type in ["human", "HumanMessage"]
                        else "assistant"
                    )

                    # 处理meta_data
                    meta_data = None
                    if meta_data_raw:
                        if isinstance(meta_data_raw, str):
                            meta_data = json.loads(meta_data_raw)
                        elif isinstance(meta_data_raw, dict):
                            meta_data = meta_data_raw

                    messages.append(
                        {
                            "id": message_id,  # 添加消息ID
                            "role": role,
                            "content": content,
                            "audio_url": audio_url,  # 添加audio_url字段
                            "meta_data": meta_data,  # 添加meta_data字段
                            "timestamp": created_at.isoformat() if created_at else None,
                        }
                    )

                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    logger.warning(
                        f"解析消息失败 {session_id}: {str(e)}, 原始数据: {row[0]}"
                    )
                    # 跳过无法解析的消息，继续处理其他消息
                    continue

        # 因为我们是按时间倒序查询的，但返回时希望按正常时间顺序（旧消息在前）
        messages.reverse()

        return {
            "messages": messages,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
            "page": (offset // limit) + 1 if limit > 0 else 1,
        }

    except Exception as e:
        logger.error(f"分页获取消息失败 {session_id}: {str(e)}")
        return {
            "messages": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "has_more": False,
            "page": 1,
        }


def get_all_messages(session_id: str) -> List[Dict[str, Any]]:
    """
    获取所有聊天消息（不分页）

    Args:
        session_id: 会话ID

    Returns:
        消息列表
    """
    try:
        history = get_chat_history(session_id)
        messages = history.messages

        result = []
        for message in messages:
            role = "user" if isinstance(message, HumanMessage) else "assistant"
            result.append(
                {
                    "role": role,
                    "content": message.content,
                    "timestamp": None,  # PostgresChatMessageHistory 默认没有时间戳
                }
            )

        return result

    except Exception as e:
        logger.error(f"获取所有消息失败 {session_id}: {str(e)}")
        return []


def clear_session(session_id: str) -> None:
    """
    清除指定会话的所有聊天历史记录

    Args:
        session_id: 会话ID
    """
    try:
        conn = get_chat_history_connection()

        # 删除指定会话的所有消息
        delete_query = """
            DELETE FROM chat_history 
            WHERE session_id = %s
        """

        with conn.cursor() as cur:
            cur.execute(delete_query, (session_id,))
            deleted_count = cur.rowcount

        logger.info(f"已清除会话 {session_id} 的聊天历史，删除消息数: {deleted_count}")

    except Exception as e:
        logger.error(f"清除会话聊天历史失败 {session_id}: {str(e)}")
        raise


async def get_message_content(
    db: AsyncSession, session_id: str, message_id: str
) -> Optional[str]:
    """
    根据消息ID获取消息内容

    Args:
        db: 数据库会话
        session_id: 会话ID
        message_id: 消息ID（数据库的真实ID）

    Returns:
        消息内容，如果找不到则返回None
    """
    try:
        # 尝试将message_id转换为整数
        try:
            db_message_id = int(message_id)
        except ValueError:
            logger.warning(f"无法解析消息ID为整数: {message_id}")
            return None

        # 使用ORM查询消息
        stmt = select(ChatHistory).where(
            and_(ChatHistory.session_id == session_id, ChatHistory.id == db_message_id)
        )

        result = await db.execute(stmt)
        chat_history = result.scalar_one_or_none()

        if chat_history:
            # 解析消息内容
            parsed = _parse_message_content(chat_history.message)
            return parsed["content"]
        else:
            logger.warning(
                f"消息未找到: session_id={session_id}, message_id={db_message_id}"
            )
            return None

    except Exception as e:
        logger.error(f"获取消息内容失败 {session_id}, {message_id}: {str(e)}")
        return None


async def update_message_audio_url(
    db: AsyncSession,
    session_id: str,
    message_id: str,
    audio_url: str,
    audio_duration: Optional[float] = None,
) -> bool:
    """
    更新指定消息的audio_url字段和音频时长

    Args:
        db: 数据库会话
        session_id: 会话ID
        message_id: 消息ID（数据库的真实ID）
        audio_url: 语音文件URL
        audio_duration: 音频时长（秒）

    Returns:
        bool: 更新是否成功
    """
    try:
        # 尝试将message_id转换为整数
        try:
            db_message_id = int(message_id)
        except ValueError:
            logger.warning(f"无法解析消息ID为整数: {message_id}")
            return False

        # 构建更新语句
        if audio_duration is not None:
            # 使用SQLAlchemy的JSONB操作更新audio_url和meta_data
            stmt = (
                update(ChatHistory)
                .where(
                    and_(
                        ChatHistory.session_id == session_id,
                        ChatHistory.id == db_message_id,
                    )
                )
                .values(
                    audio_url=audio_url,
                    meta_data=func.coalesce(
                        ChatHistory.meta_data,
                        func.cast({}, type_=ChatHistory.meta_data.type),
                    ).op("||")({"audioDuration": audio_duration}),
                )
            )
        else:
            # 只更新audio_url
            stmt = (
                update(ChatHistory)
                .where(
                    and_(
                        ChatHistory.session_id == session_id,
                        ChatHistory.id == db_message_id,
                    )
                )
                .values(audio_url=audio_url)
            )

        result = await db.execute(stmt)
        await db.commit()

        updated_rows = result.rowcount

        if updated_rows > 0:
            logger.debug(
                f"成功更新消息audio_url: session_id={session_id}, message_id={db_message_id}, audio_url={audio_url}"
            )
            return True
        else:
            logger.warning(
                f"消息未找到，无法更新audio_url: session_id={session_id}, message_id={db_message_id}"
            )
            return False

    except Exception as e:
        logger.error(
            f"更新消息audio_url失败: session_id={session_id}, message_id={message_id}, audio_url={audio_url}, 错误: {str(e)}"
        )
        await db.rollback()
        return False


def clear_messages_after_id(session_id: str, message_id: int) -> Dict[str, Any]:
    """
    清除包括指定消息ID在内的后续所有聊天记录

    Args:
        session_id: 会话ID
        message_id: 消息ID（数据库自增ID）

    Returns:
        包含删除结果的字典
    """
    try:
        conn = get_chat_history_connection()

        # 首先验证指定的消息是否存在
        check_query = """
            SELECT id, message, created_at
            FROM chat_history 
            WHERE session_id = %s AND id = %s
        """

        with conn.cursor() as cur:
            cur.execute(check_query, (session_id, message_id))
            target_message = cur.fetchone()

            if not target_message:
                return {
                    "success": False,
                    "message": f"指定的消息ID {message_id} 不存在",
                    "deleted_count": 0,
                    "target_message": None,
                }

            # 查询将要删除的消息数量和详情（包括指定ID）
            count_query = """
                SELECT COUNT(*), MIN(created_at), MAX(created_at)
                FROM chat_history 
                WHERE session_id = %s AND id >= %s
            """

            cur.execute(count_query, (session_id, message_id))
            count_result = cur.fetchone()
            messages_to_delete = count_result[0] if count_result else 0

            if messages_to_delete == 0:
                # 解析目标消息内容
                parsed_target = _parse_message_content(target_message[1])
                return {
                    "success": True,
                    "message": f"指定消息ID {message_id} 包括其后续消息，没有需要删除的记录",
                    "deleted_count": 0,
                    "target_message": {
                        "id": target_message[0],
                        "content": parsed_target["content"],
                        "role": parsed_target["role"],
                        "timestamp": (
                            target_message[2].isoformat() if target_message[2] else None
                        ),
                    },
                }

            # 执行删除操作（包括指定ID）
            delete_query = """
                DELETE FROM chat_history 
                WHERE session_id = %s AND id >= %s
            """

            cur.execute(delete_query, (session_id, message_id))
            actual_deleted = cur.rowcount

            logger.info(
                f"已清除会话 {session_id} 中包括消息ID {message_id} 在内的 {actual_deleted} 条记录"
            )

            # 解析目标消息内容
            parsed_target = _parse_message_content(target_message[1])
            return {
                "success": True,
                "message": f"成功删除包括消息ID {message_id} 在内的 {actual_deleted} 条记录",
                "deleted_count": actual_deleted,
                "target_message": {
                    "id": target_message[0],
                    "content": parsed_target["content"],
                    "role": parsed_target["role"],
                    "timestamp": (
                        target_message[2].isoformat() if target_message[2] else None
                    ),
                },
                "deleted_time_range": (
                    {
                        "from": (
                            count_result[1].isoformat() if count_result[1] else None
                        ),
                        "to": count_result[2].isoformat() if count_result[2] else None,
                    }
                    if count_result[1]
                    else None
                ),
            }

    except Exception as e:
        logger.error(
            f"清除指定消息后记录失败 {session_id}, message_id {message_id}: {str(e)}"
        )
        return {
            "success": False,
            "message": f"清除操作失败: {str(e)}",
            "deleted_count": 0,
            "target_message": None,
        }


def clear_messages_after_timestamp(session_id: str, timestamp: str) -> Dict[str, Any]:
    """
    清除指定时间戳之后的所有聊天记录

    Args:
        session_id: 会话ID
        timestamp: 时间戳（ISO格式字符串）

    Returns:
        包含删除结果的字典
    """
    try:
        conn = get_chat_history_connection()
        from datetime import datetime

        # 解析时间戳
        try:
            target_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as e:
            return {
                "success": False,
                "message": f"时间戳格式错误: {str(e)}",
                "deleted_count": 0,
            }

        # 查询将要删除的消息数量
        count_query = """
            SELECT COUNT(*)
            FROM chat_history 
            WHERE session_id = %s AND created_at > %s
        """

        with conn.cursor() as cur:
            cur.execute(count_query, (session_id, target_time))
            messages_to_delete = cur.fetchone()[0]

            if messages_to_delete == 0:
                return {
                    "success": True,
                    "message": f"指定时间 {timestamp} 之后没有消息需要删除",
                    "deleted_count": 0,
                }

            # 执行删除操作
            delete_query = """
                DELETE FROM chat_history 
                WHERE session_id = %s AND created_at > %s
            """

            cur.execute(delete_query, (session_id, target_time))
            actual_deleted = cur.rowcount

            logger.info(
                f"已清除会话 {session_id} 中时间 {timestamp} 之后的 {actual_deleted} 条记录"
            )

            return {
                "success": True,
                "message": f"成功删除时间 {timestamp} 之后的 {actual_deleted} 条记录",
                "deleted_count": actual_deleted,
                "cutoff_timestamp": timestamp,
            }

    except Exception as e:
        logger.error(
            f"按时间戳清除消息失败 {session_id}, timestamp {timestamp}: {str(e)}"
        )
        return {
            "success": False,
            "message": f"清除操作失败: {str(e)}",
            "deleted_count": 0,
        }
