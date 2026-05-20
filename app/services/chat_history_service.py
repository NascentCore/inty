import asyncio
import json
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set, Union

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_postgres import PostgresChatMessageHistory
from loguru import logger
from sqlalchemy import and_, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent.prompt_template import (
    has_template_variable,
    render_prompt_jinja2_template,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.models.chat_history import ChatHistory


def _extract_text_from_content(content: Any) -> str:
    """从消息 content 中提取可读文本；支持字符串与 OpenAI content parts。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: List[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text.strip())
        return "\n".join(text_parts)
    return ""


def _message_preview_for_log(message: Any) -> str:
    """生成日志预览，避免多模态 content 直接切片报错。"""
    text = _extract_text_from_content(message)
    if text:
        return f"{text[:50]}..."
    if isinstance(message, list):
        return f"[{len(message)} content parts]"
    if isinstance(message, str):
        return f"{message[:50]}..."
    return "[unsupported message content]"


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
            content = _extract_text_from_content(
                message_data["data"]["content"]
            )
        elif "content" in message_data:
            content = _extract_text_from_content(message_data["content"])

        # 确定角色
        if message_type == "system":
            role = "system"
        elif message_type in ["human", "HumanMessage"]:
            role = "user"
        else:
            role = "assistant"

        return {"content": content, "role": role}

    except Exception as e:
        logger.warning(f"解析消息内容失败: {str(e)}")
        return {
            "content": str(message_raw) if message_raw else "",
            "role": "unknown",
        }


# Keep the legacy connection function for PostgresChatMessageHistory compatibility
_connection = None
_replica_connection = None


def get_chat_history_connection():
    """Legacy function for PostgresChatMessageHistory - keep for backward compatibility"""
    global _connection
    if _connection is None or _connection.closed:
        try:
            import psycopg

            logger.debug(
                f"connecting to database: {global_config_loaded_from_config_yaml.database.url}"
            )
            _connection = psycopg.connect(
                global_config_loaded_from_config_yaml.database.url,
                autocommit=True,
            )
            logger.info("chat_history 数据库连接已建立")
        except Exception as e:
            logger.error(f"建立chat_history数据库连接失败: {str(e)}")
            raise
    return _connection


def _sync_url_from_async_replica(
    async_replica_url: Optional[str],
) -> Optional[str]:
    """从 async_replica_url（postgresql+asyncpg://...）得到同步驱动用 URL（postgresql://...）。"""
    if not async_replica_url:
        return None
    return async_replica_url.replace(
        "postgresql+asyncpg://", "postgresql://", 1
    )


def get_chat_history_replica_connection():
    """
    只读副本连接，用于 chat_history/chats 的只读查询（如按日期查会话对与消息）。
    当 config.database.async_replica_url 未配置时返回 None。
    """
    global _replica_connection
    async_replica_url = (
        global_config_loaded_from_config_yaml.database.async_replica_url
    )
    sync_url = _sync_url_from_async_replica(async_replica_url)
    if not sync_url:
        return None
    if _replica_connection is None or _replica_connection.closed:
        try:
            import psycopg

            # 5 秒连接超时，避免副本不可达时长时间阻塞（如从本机连生产副本）
            conninfo = (
                f"{sync_url}?connect_timeout=5"
                if "?" not in sync_url
                else f"{sync_url}&connect_timeout=5"
            )
            _replica_connection = psycopg.connect(conninfo, autocommit=True)
            logger.info("chat_history 副本数据库连接已建立")
        except Exception as e:
            logger.error("建立 chat_history 副本连接失败: %s", e)
            raise
    return _replica_connection


# chat_history表现在由Alembic迁移管理，不需要手动初始化


def get_chat_history(session_id: str) -> PostgresChatMessageHistory:
    """获取聊天历史"""
    conn = get_chat_history_connection()
    return PostgresChatMessageHistory(
        "chat_history", session_id, sync_connection=conn
    )


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
            f"添加开场白到会话 {session_id}: {opening_message}, audio_url: {audio_url}"
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
            return _extract_text_from_content(last_message.content)
        return None
    except Exception as e:
        logger.error(f"获取最近消息失败 {session_id}: {str(e)}")
        # 返回None而不是抛出异常，让主要功能继续工作
        return None


def get_last_message_with_timestamp(
    session_id: str,
) -> Optional[Dict[str, Any]]:
    """获取最近一条消息内容和时间戳（排除已软删除的）"""
    try:
        conn = get_chat_history_connection()

        # 查询最近一条消息（排除已软删除的）
        query = """
            SELECT message, created_at
            FROM chat_history 
            WHERE session_id = %s AND deleted_at IS NULL
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
                    if (
                        "data" in message_data
                        and "content" in message_data["data"]
                    ):
                        content = _extract_text_from_content(
                            message_data["data"]["content"]
                        )
                    elif "content" in message_data:
                        content = _extract_text_from_content(
                            message_data["content"]
                        )

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


def has_user_messages_ever(session_id: str) -> bool:
    """
    检查会话是否曾经有用户消息（包括已删除的）

    用于判断聊天会话是否应该显示在列表中：
    - 如果曾经有用户消息（即使后来被软删除），返回 True
    - 如果只有开场白消息，返回 False

    Args:
        session_id: 会话ID

    Returns:
        是否曾经有用户消息
    """
    try:
        conn = get_chat_history_connection()

        query = """
            SELECT EXISTS(
                SELECT 1 FROM chat_history 
                WHERE session_id = %s 
                AND message->>'type' IN ('human', 'HumanMessage')
            )
        """

        with conn.cursor() as cur:
            cur.execute(query, (session_id,))
            result = cur.fetchone()
            return result[0] if result else False

    except Exception as e:
        logger.error(f"检查用户消息历史失败 {session_id}: {str(e)}")
        return False


def add_user_message(
    session_id: str,
    message: str | List[Dict[str, Any]],
    meta_data: Optional[dict] = None,
) -> Optional[int]:
    """添加用户消息到聊天历史。meta_data 非空时用 raw INSERT 写入元数据并返回插入 id，否则走 PostgresChatMessageHistory 并返回 None。"""
    try:
        if meta_data is None and isinstance(message, str):
            history = get_chat_history(session_id)
            history.add_messages([HumanMessage(content=message)])
            logger.debug(
                f"添加用户消息到会话 {session_id}: {_message_preview_for_log(message)}"
            )
            return None
        conn = get_chat_history_connection()
        message_data = {"type": "human", "data": {"content": message}}
        insert_query = """
            INSERT INTO chat_history (session_id, message, meta_data)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        with conn.cursor() as cur:
            cur.execute(
                insert_query,
                (
                    session_id,
                    json.dumps(message_data),
                    json.dumps(meta_data) if meta_data is not None else None,
                ),
            )
            result = cur.fetchone()
            message_id = result[0] if result else None
        logger.debug(
            f"添加用户消息到会话 {session_id}: {_message_preview_for_log(message)}, ID: {message_id}"
        )
        return message_id
    except Exception as e:
        logger.error(f"添加用户消息失败 {session_id}: {str(e)}")
        raise


def add_ai_message_sync(
    session_id: str,
    message: str | List[Dict[str, Any]],
    agent_id: Optional[str] = None,
    meta_data: Optional[dict] = None,
) -> Optional[int]:
    """
    同步版本：添加AI消息到聊天历史，返回插入的消息ID

    Args:
        session_id: 会话ID
        message: 消息内容
        agent_id: Agent ID（可选）
        meta_data: 自定义元数据（可选，会与默认元数据合并）

    Returns:
        插入的消息ID
    """
    try:
        conn = get_chat_history_connection()

        # 构建AIMessage的JSON格式数据
        message_data = {"type": "ai", "data": {"content": message}}

        # 构建meta_data
        final_meta_data = meta_data.copy() if meta_data else {}

        if agent_id:
            final_meta_data["agentId"] = agent_id
            if "isOpening" not in final_meta_data:
                final_meta_data["isOpening"] = False

        # 执行SQL插入
        insert_query = """
            INSERT INTO chat_history (session_id, message, meta_data)
            VALUES (%s, %s, %s)
            RETURNING id
        """

        with conn.cursor() as cur:
            cur.execute(
                insert_query,
                (
                    session_id,
                    json.dumps(message_data),
                    json.dumps(final_meta_data) if final_meta_data else None,
                ),
            )
            result = cur.fetchone()
            message_id = result[0] if result else None

        logger.debug(
            f"添加AI消息到会话 {session_id}: {_message_preview_for_log(message)}, ID: {message_id}"
        )
        return message_id

    except Exception as e:
        logger.error(f"添加AI消息失败(sync) {session_id}: {str(e)}")
        raise


def add_system_message_sync(
    session_id: str,
    message: str | List[Dict[str, Any]],
    meta_data: Optional[dict] = None,
) -> Optional[int]:
    """Persist a system role line for chat history (e.g. companion WS session gate)."""
    try:
        conn = get_chat_history_connection()
        message_data = {"type": "system", "data": {"content": message}}
        final_meta = meta_data.copy() if meta_data else None
        insert_query = """
            INSERT INTO chat_history (session_id, message, meta_data)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        with conn.cursor() as cur:
            cur.execute(
                insert_query,
                (
                    session_id,
                    json.dumps(message_data),
                    json.dumps(final_meta) if final_meta else None,
                ),
            )
            result = cur.fetchone()
            message_id = result[0] if result else None
        logger.debug(
            "添加 system 消息到会话 {}: {} ID={}",
            session_id,
            _message_preview_for_log(message),
            message_id,
        )
        return message_id
    except Exception as e:
        logger.error(f"添加 system 消息失败(sync) {session_id}: {str(e)}")
        raise


# Legacy IntelliMate role-play stack (festival_memory_prompt); not companion harness proactive chat.
FESTIVAL_MEMORY_PROMPT_CONTENT = (
    "{char} wrote you a secret heartbeat diary. Take a quiet look."
)
META_MESSAGE_TYPE_FESTIVAL_MEMORY_PROMPT = "festival_memory_prompt"
DAILY_MEMORY_PROMPT_CONTENT = (
    "{char} kept a small note from yesterday. Want to read it?"
)
META_MESSAGE_TYPE_DAILY_MEMORY_PROMPT = "daily_memory_prompt"
META_MESSAGE_TYPE_SURPRISE_SNAP = "surprise_snap"


def get_festival_memory_prompt_content_for_agent_sync(agent_id: str) -> str:
    """
    返回用于展示的节日记忆提示文案（与 add_festival_memory_prompt_message_sync 落库一致）。
    供按需投递时构建 chat completion choices 中的 message 使用。
    """
    agent_name = "角色"
    try:
        conn = get_chat_history_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name FROM agents WHERE id = %s LIMIT 1",
                (agent_id,),
            )
            row = cur.fetchone()
            if row and row[0]:
                agent_name = str(row[0]).strip() or agent_name
    except Exception as e:
        logger.debug(f"获取 agent 名称失败 agent_id={agent_id}: {e}")
    return FESTIVAL_MEMORY_PROMPT_CONTENT.replace("{char}", agent_name)


def get_daily_memory_prompt_content_for_agent_sync(agent_id: str) -> str:
    """
    返回用于展示的日常记忆提示文案（与 add_daily_memory_prompt_message_sync 落库一致）。
    """
    agent_name = "Character"
    try:
        conn = get_chat_history_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name FROM agents WHERE id = %s LIMIT 1",
                (agent_id,),
            )
            row = cur.fetchone()
            if row and row[0]:
                agent_name = str(row[0]).strip() or agent_name
    except Exception as e:
        logger.debug(f"获取 agent 名称失败 agent_id={agent_id}: {e}")
    return DAILY_MEMORY_PROMPT_CONTENT.replace("{char}", agent_name)


def add_festival_memory_prompt_message_sync(
    session_id: str,
    agent_id: str,
    memory_id: int,
    festival_name: str,
    festival_date: Union[date, str],
) -> Optional[int]:
    """
    向 chat_history 插入一条「节日记忆/心跳日记」提示类 AI 消息。
    按 (session_id, agent_id, festival_name, festival_date) 幂等：已存在则返回已有 id 不插入。
    写入时用该会话的角色名称替换模板中的 {char}，落库即为最终文案；
    meta_data 中记录 festivalMemoryId、festivalName、festivalDate。
    返回插入或已存在消息的 ID，失败返回 None。
    """
    festival_date_str = (
        festival_date.isoformat()
        if isinstance(festival_date, date)
        else str(festival_date)
    )
    try:
        conn = get_chat_history_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM chat_history
                WHERE session_id = %s AND deleted_at IS NULL
                  AND meta_data->>'messageType' = %s AND meta_data->>'agentId' = %s
                  AND meta_data->>'festivalName' = %s AND meta_data->>'festivalDate' = %s
                LIMIT 1
                """,
                (
                    session_id,
                    META_MESSAGE_TYPE_FESTIVAL_MEMORY_PROMPT,
                    agent_id,
                    festival_name,
                    festival_date_str,
                ),
            )
            row = cur.fetchone()
            if row:
                logger.debug(
                    f"节日记忆提示消息已存在 session_id={session_id} agent_id={agent_id} "
                    f"festival={festival_name} {festival_date_str}, id={row[0]}"
                )
                return row[0]
        agent_name = "角色"
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name FROM agents WHERE id = %s LIMIT 1",
                (agent_id,),
            )
            row = cur.fetchone()
            if row and row[0]:
                agent_name = str(row[0]).strip() or agent_name
        content = FESTIVAL_MEMORY_PROMPT_CONTENT.replace("{char}", agent_name)
        message_data = {
            "type": "ai",
            "data": {"content": content},
        }
        meta_data = {
            "agentId": agent_id,
            "messageType": META_MESSAGE_TYPE_FESTIVAL_MEMORY_PROMPT,
            "festivalMemoryId": memory_id,
            "festivalName": festival_name,
            "festivalDate": festival_date_str,
        }
        insert_query = """
            INSERT INTO chat_history (session_id, message, meta_data)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        with conn.cursor() as cur:
            cur.execute(
                insert_query,
                (session_id, json.dumps(message_data), json.dumps(meta_data)),
            )
            result = cur.fetchone()
            message_id = result[0] if result else None
        logger.debug(
            f"添加节日记忆提示消息到会话 {session_id} agent_id={agent_id}, ID={message_id}"
        )
        return message_id
    except Exception as e:
        logger.error(
            f"添加节日记忆提示消息失败 session_id={session_id}: {str(e)}"
        )
        return None


def add_daily_memory_prompt_message_sync(
    session_id: str,
    agent_id: str,
    memory_id: int,
    local_date: Union[date, str],
) -> Optional[int]:
    """
    向 chat_history 插入一条日常记忆提示消息。
    按 (session_id, agent_id, local_date) 幂等：已存在则返回已有 id 不插入。
    """
    local_date_str = (
        local_date.isoformat()
        if isinstance(local_date, date)
        else str(local_date)
    )
    try:
        conn = get_chat_history_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM chat_history
                WHERE session_id = %s AND deleted_at IS NULL
                  AND meta_data->>'messageType' = %s AND meta_data->>'agentId' = %s
                  AND meta_data->>'localDate' = %s
                LIMIT 1
                """,
                (
                    session_id,
                    META_MESSAGE_TYPE_DAILY_MEMORY_PROMPT,
                    agent_id,
                    local_date_str,
                ),
            )
            row = cur.fetchone()
            if row:
                logger.debug(
                    f"日常记忆提示消息已存在 session_id={session_id} agent_id={agent_id} "
                    f"local_date={local_date_str}, id={row[0]}"
                )
                return row[0]
        agent_name = "Character"
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name FROM agents WHERE id = %s LIMIT 1",
                (agent_id,),
            )
            row = cur.fetchone()
            if row and row[0]:
                agent_name = str(row[0]).strip() or agent_name
        content = DAILY_MEMORY_PROMPT_CONTENT.replace("{char}", agent_name)
        message_data = {"type": "ai", "data": {"content": content}}
        meta_data = {
            "agentId": agent_id,
            "messageType": META_MESSAGE_TYPE_DAILY_MEMORY_PROMPT,
            "dailyMemoryId": memory_id,
            "localDate": local_date_str,
        }
        insert_query = """
            INSERT INTO chat_history (session_id, message, meta_data)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        with conn.cursor() as cur:
            cur.execute(
                insert_query,
                (session_id, json.dumps(message_data), json.dumps(meta_data)),
            )
            result = cur.fetchone()
            message_id = result[0] if result else None
        logger.debug(
            f"添加日常记忆提示消息到会话 {session_id} agent_id={agent_id}, ID={message_id}"
        )
        return message_id
    except Exception as e:
        logger.error(
            f"添加日常记忆提示消息失败 session_id={session_id}: {str(e)}"
        )
        return None


async def add_ai_message(
    db: AsyncSession,
    session_id: str,
    message: str | List[Dict[str, Any]],
    agent_id: Optional[str] = None,
    audio_duration: Optional[float] = None,
    meta_data: Optional[dict] = None,
) -> Optional[int]:
    """
    添加AI消息到聊天历史，返回插入的消息ID

    Args:
        db: 数据库会话
        session_id: 会话ID
        message: 消息内容
        agent_id: Agent ID（可选）
        audio_duration: 音频时长（可选）
        meta_data: 自定义元数据（可选，会与默认元数据合并）

    Returns:
        插入的消息ID
    """
    try:
        # 构建AIMessage的JSON格式数据
        message_data = {"type": "ai", "data": {"content": message}}

        # 构建meta_data
        final_meta_data = meta_data.copy() if meta_data else {}

        if agent_id:
            final_meta_data["agentId"] = agent_id
            if "isOpening" not in final_meta_data:
                final_meta_data["isOpening"] = False
        if audio_duration is not None:
            final_meta_data["audioDuration"] = audio_duration

        # 使用ORM创建新记录
        chat_history = ChatHistory(
            session_id=session_id,
            message=message_data,
            meta_data=final_meta_data if final_meta_data else None,
        )

        db.add(chat_history)
        await db.commit()
        await db.refresh(chat_history)  # 获取生成的ID

        logger.debug(
            f"添加AI消息到会话 {session_id}: {_message_preview_for_log(message)}, ID: {chat_history.id}"
        )
        return chat_history.id

    except Exception as e:
        logger.error(f"添加AI消息失败 {session_id}: {str(e)}")
        await db.rollback()
        raise


async def add_surprise_snap_message(
    db: AsyncSession,
    session_id: str,
    agent_id: str,
    image_url: str,
    caption: str,
    credits_required: int,
    exclusive_photo_index: int,
) -> Optional[int]:
    """插入一条 Surprise Snap 专属照消息，返回消息 ID。"""
    try:
        message_data = {
            "type": META_MESSAGE_TYPE_SURPRISE_SNAP,
            "data": {
                "image_url": image_url,
                "caption": caption,
                "credits_required": credits_required,
            },
        }
        meta_data = {
            "messageType": META_MESSAGE_TYPE_SURPRISE_SNAP,
            "agentId": agent_id,
            "exclusive_photo_index": exclusive_photo_index,
        }
        sid = (
            uuid.UUID(session_id) if isinstance(session_id, str) else session_id
        )
        ch = ChatHistory(
            session_id=sid,
            message=message_data,
            meta_data=meta_data,
        )
        db.add(ch)
        await db.commit()
        await db.refresh(ch)
        return ch.id
    except Exception as e:
        logger.error(
            f"添加 Surprise Snap 消息失败 session_id={session_id}: {e}"
        )
        await db.rollback()
        raise


async def count_user_messages_since(
    db: AsyncSession,
    session_id: str,
    since_at: datetime,
) -> int:
    """统计该会话中自 since_at 以来的用户（human）消息条数。"""
    sid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
    stmt = (
        select(func.count())
        .select_from(ChatHistory)
        .where(
            ChatHistory.session_id == sid,
            ChatHistory.deleted_at.is_(None),
            ChatHistory.created_at >= since_at,
            or_(
                ChatHistory.message["type"].astext == "human",
                ChatHistory.message["type"].astext == "HumanMessage",
            ),
        )
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


async def update_message_metadata(
    db: AsyncSession,
    session_id: str,
    message_id: int,
    metadata_update: dict,
) -> bool:
    """
    更新消息的 meta_data 字段

    Args:
        db: 数据库会话
        session_id: 会话ID
        message_id: 消息ID
        metadata_update: 要更新/合并的元数据

    Returns:
        是否更新成功
    """
    try:
        # 查询现有消息（排除已软删除的）
        stmt = select(ChatHistory).where(
            and_(
                ChatHistory.session_id == session_id,
                ChatHistory.id == message_id,
                ChatHistory.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        chat_history = result.scalar_one_or_none()

        if not chat_history:
            logger.warning(
                f"消息不存在: session_id={session_id}, message_id={message_id}"
            )
            return False

        # 合并现有 meta_data 和新数据（对 generated_image 进行深度合并）
        existing_meta = chat_history.meta_data or {}
        merged_meta = {**existing_meta}

        for key, value in metadata_update.items():
            if (
                key == "generated_image"
                and key in existing_meta
                and isinstance(existing_meta[key], dict)
                and isinstance(value, dict)
            ):
                # 深度合并 generated_image 字段
                merged_meta[key] = {**existing_meta[key], **value}
            else:
                merged_meta[key] = value

        # 更新消息
        chat_history.meta_data = merged_meta
        await db.commit()

        logger.debug(
            f"更新消息 meta_data 成功: session_id={session_id}, message_id={message_id}"
        )
        return True

    except Exception as e:
        logger.error(f"更新消息 meta_data 失败: {str(e)}")
        await db.rollback()
        return False


async def update_message_vote(
    db: AsyncSession,
    session_id: str,
    message_id: int,
    user_id: str,  # 保留参数以保持API兼容性，但不再使用
    vote: Optional[str],
) -> bool:
    """
    更新消息的用户投票（点赞/点踩）

    Args:
        db: 数据库会话
        session_id: 会话ID
        message_id: 消息ID
        user_id: 用户ID（保留以保持API兼容性，但不再存储）
        vote: 投票类型，"like" | "dislike" | None（取消投票）

    Returns:
        是否更新成功
    """
    try:
        # 查询现有消息（排除已软删除的）
        stmt = select(ChatHistory).where(
            and_(
                ChatHistory.session_id == session_id,
                ChatHistory.id == message_id,
                ChatHistory.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        chat_history = result.scalar_one_or_none()

        if not chat_history:
            logger.warning(
                f"消息不存在: session_id={session_id}, message_id={message_id}"
            )
            return False

        # 获取现有 meta_data
        existing_meta = chat_history.meta_data or {}
        logger.debug(
            f"更新前 meta_data: {existing_meta}, session_id={session_id}, message_id={message_id}"
        )

        # 更新或删除 user_vote（直接存储vote值，不存储user_id）
        # 兼容旧字段名 user_feedback
        if vote is None:
            # 取消投票：删除 user_vote 和 user_feedback 字段（兼容旧数据）
            if "user_vote" in existing_meta:
                del existing_meta["user_vote"]
            if "user_feedback" in existing_meta:
                del existing_meta["user_feedback"]
        else:
            # 设置投票（直接存储vote值）
            existing_meta["user_vote"] = vote
            # 同时删除旧的 user_feedback 字段（如果存在）
            if "user_feedback" in existing_meta:
                del existing_meta["user_feedback"]

        # 创建新的字典对象，确保SQLAlchemy能检测到变化
        updated_meta = dict(existing_meta)

        # 更新消息（使用flag_modified确保SQLAlchemy检测到JSONB字段的变化）
        from sqlalchemy.orm.attributes import flag_modified

        chat_history.meta_data = updated_meta
        flag_modified(chat_history, "meta_data")
        await db.commit()

        # 刷新对象以获取最新数据
        await db.refresh(chat_history)

        logger.debug(
            f"更新消息投票成功: session_id={session_id}, message_id={message_id}, user_id={user_id}, vote={vote}, 更新后 meta_data: {chat_history.meta_data}"
        )
        return True

    except Exception as e:
        logger.error(f"更新消息投票失败: {str(e)}")
        await db.rollback()
        return False


async def add_ai_image_message(
    db: AsyncSession,
    session_id: str,
    image_url: str,
    image_metadata: dict,
    prompt: str,
    agent_id: Optional[str] = None,
    source_message_id: Optional[int] = None,
) -> Optional[int]:
    """
    添加AI图片消息到聊天历史，返回插入的消息ID

    Args:
        db: 数据库会话
        session_id: 会话ID
        image_url: 图片URL（GCS URI）
        image_metadata: 图片元数据
        prompt: 生成图片的提示词
        agent_id: Agent ID
        source_message_id: 来源消息ID（用于标记这张图片是基于哪条消息生成的）

    Returns:
        插入的消息ID
    """
    try:
        # 构建图片消息的JSON格式数据
        message_data = {
            "type": "image",
            "data": {
                "image_url": image_url,
                "width": image_metadata.get("width", 0),
                "height": image_metadata.get("height", 0),
                "format": image_metadata.get("format", "jpeg"),
                "prompt": prompt,
            },
        }

        # 构建meta_data
        meta_data = {}
        if agent_id:
            meta_data["agentId"] = agent_id
            meta_data["isOpening"] = False
        if source_message_id:
            meta_data["source_message_id"] = source_message_id
        meta_data["messageType"] = "image"

        # 使用ORM创建新记录
        chat_history = ChatHistory(
            session_id=session_id, message=message_data, meta_data=meta_data
        )

        db.add(chat_history)
        await db.commit()
        await db.refresh(chat_history)  # 获取生成的ID

        logger.debug(
            f"添加AI图片消息到会话 {session_id}: {image_url}, ID: {chat_history.id}"
        )
        return chat_history.id

    except Exception as e:
        logger.error(f"添加AI图片消息失败 {session_id}: {str(e)}")
        await db.rollback()
        raise


async def get_latest_ai_message_id(
    db: AsyncSession, session_id: str
) -> Optional[int]:
    """获取会话中最新的AI消息ID（排除已软删除的）"""
    try:
        # 使用ORM查询最新的AI消息ID（排除已软删除的）
        stmt = (
            select(ChatHistory.id)
            .where(
                and_(
                    ChatHistory.session_id == session_id,
                    ChatHistory.message["type"].astext == "ai",
                    ChatHistory.deleted_at.is_(None),
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


async def get_latest_user_message_id(
    db: AsyncSession, session_id: str
) -> Optional[int]:
    """获取会话中最新的用户消息ID（排除已软删除的）"""
    try:
        stmt = (
            select(ChatHistory.id)
            .where(
                and_(
                    ChatHistory.session_id == session_id,
                    ChatHistory.message["type"].astext.in_(
                        ["human", "HumanMessage"]
                    ),
                    ChatHistory.deleted_at.is_(None),
                )
            )
            .order_by(desc(ChatHistory.created_at), desc(ChatHistory.id))
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.first()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"获取最新用户消息ID失败 {session_id}: {str(e)}")
        return None


async def delete_image_by_source_message(
    db: AsyncSession, session_id: str, source_message_id: int
) -> Optional[str]:
    """
    删除指定来源消息生成的图片消息

    Args:
        db: 数据库会话
        session_id: 会话ID
        source_message_id: 来源消息ID

    Returns:
        被删除的图片URL（GCS URI），如果没有找到则返回None
    """
    try:
        # 查询并删除该来源消息的图片（排除已软删除的）
        stmt = select(ChatHistory).where(
            and_(
                ChatHistory.session_id == session_id,
                ChatHistory.message["type"].astext == "image",
                ChatHistory.meta_data["source_message_id"].astext
                == str(source_message_id),
                ChatHistory.deleted_at.is_(None),
            )
        )

        result = await db.execute(stmt)
        image_message = result.scalar_one_or_none()

        if image_message:
            # 提取图片URL
            message_data = image_message.message
            if isinstance(message_data, str):
                message_data = json.loads(message_data)

            image_url = message_data.get("data", {}).get("image_url")

            # 删除记录
            await db.delete(image_message)
            await db.commit()

            logger.info(
                f"删除图片消息: session_id={session_id}, "
                f"source_message_id={source_message_id}, image_url={image_url}"
            )

            return image_url
        else:
            logger.debug(
                f"未找到需要删除的图片消息: session_id={session_id}, "
                f"source_message_id={source_message_id}"
            )
            return None

    except Exception as e:
        logger.error(
            f"删除图片消息失败: session_id={session_id}, "
            f"source_message_id={source_message_id}, error={str(e)}"
        )
        await db.rollback()
        return None


async def get_latest_ai_message_info(
    db: AsyncSession, session_id: str
) -> Optional[Dict[str, Any]]:
    """获取会话中最新AI消息的完整信息（排除已软删除的）"""
    try:
        # 使用ORM查询最新的AI消息完整信息（排除已软删除的）
        stmt = (
            select(ChatHistory)
            .where(
                and_(
                    ChatHistory.session_id == session_id,
                    ChatHistory.message["type"].astext == "ai",
                    ChatHistory.deleted_at.is_(None),
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
                content = _extract_text_from_content(
                    message_data["data"]["content"]
                )
            elif "content" in message_data:
                content = _extract_text_from_content(message_data["content"])

        except (TypeError, KeyError) as e:
            logger.warning(f"解析AI消息内容失败: {str(e)}")
            content = str(chat_history.message) if chat_history.message else ""

        return {
            "id": chat_history.id,
            "content": content,
            "audio_url": chat_history.audio_url,
            "meta_data": chat_history.meta_data,
            "timestamp": (
                chat_history.created_at.isoformat()
                if chat_history.created_at
                else None
            ),
        }

    except Exception as e:
        logger.error(f"获取最新AI消息信息失败 {session_id}: {str(e)}")
        return None


async def get_ai_message_info_by_id(
    db: AsyncSession, message_id: int
) -> Optional[Dict[str, Any]]:
    """根据消息 ID 获取 AI 消息的完整信息（与 get_latest_ai_message_info 返回结构一致）。"""
    try:
        stmt = (
            select(ChatHistory)
            .where(
                ChatHistory.id == message_id,
                ChatHistory.message["type"].astext == "ai",
                ChatHistory.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        chat_history = result.scalar_one_or_none()
        if not chat_history:
            return None

        content = ""
        try:
            message_data = chat_history.message
            if "data" in message_data and "content" in message_data["data"]:
                content = _extract_text_from_content(
                    message_data["data"]["content"]
                )
            elif "content" in message_data:
                content = _extract_text_from_content(message_data["content"])
        except (TypeError, KeyError) as e:
            logger.warning(f"解析AI消息内容失败: {str(e)}")
            content = str(chat_history.message) if chat_history.message else ""

        return {
            "id": chat_history.id,
            "content": content,
            "audio_url": chat_history.audio_url,
            "meta_data": chat_history.meta_data,
            "timestamp": (
                chat_history.created_at.isoformat()
                if chat_history.created_at
                else None
            ),
        }
    except Exception as e:
        logger.error(
            f"根据ID获取AI消息信息失败 message_id={message_id}: {str(e)}"
        )
        return None


async def get_ai_message_infos_by_ids(
    db: AsyncSession, message_ids: List[int]
) -> Dict[int, Dict[str, Any]]:
    """
    根据消息 ID 列表批量获取 AI 消息完整信息（与 get_ai_message_info_by_id 单条结构一致）。
    返回 id -> info 的映射；未找到或非 AI 消息的 id 不会出现在结果中。
    """
    if not message_ids:
        return {}
    try:
        stmt = select(ChatHistory).where(
            ChatHistory.id.in_(message_ids),
            ChatHistory.message["type"].astext == "ai",
            ChatHistory.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        out = {}
        for chat_history in rows:
            content = ""
            try:
                message_data = chat_history.message
                if "data" in message_data and "content" in message_data["data"]:
                    content = _extract_text_from_content(
                        message_data["data"]["content"]
                    )
                elif "content" in message_data:
                    content = _extract_text_from_content(
                        message_data["content"]
                    )
            except (TypeError, KeyError) as e:
                logger.warning(f"解析AI消息内容失败: {str(e)}")
                content = (
                    str(chat_history.message) if chat_history.message else ""
                )
            out[chat_history.id] = {
                "id": chat_history.id,
                "content": content,
                "audio_url": chat_history.audio_url,
                "meta_data": chat_history.meta_data,
                "timestamp": (
                    chat_history.created_at.isoformat()
                    if chat_history.created_at
                    else None
                ),
            }
        return out
    except Exception as e:
        logger.error(
            f"批量根据ID获取AI消息信息失败 message_ids={message_ids}: {str(e)}"
        )
        return {}


async def get_surprise_snap_message_display_info(
    db: AsyncSession, message_id: int
) -> Optional[Dict[str, Any]]:
    """
    根据消息 ID 获取单条 surprise_snap 消息的展示信息（与 get_messages_paginated 中
    surprise_snap 项结构一致），供聊天接口作为 choice 返回。未找到或非 surprise_snap 返回 None。
    """
    try:
        stmt = (
            select(ChatHistory)
            .where(
                ChatHistory.id == message_id,
                ChatHistory.message["type"].astext
                == META_MESSAGE_TYPE_SURPRISE_SNAP,
                ChatHistory.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        msg = row.message
        if isinstance(msg, str):
            msg = json.loads(msg) if msg else {}
        elif not isinstance(msg, dict):
            msg = {}
        data = msg.get("data") or {}
        if not isinstance(data, dict):
            data = {}
        image_url_raw = data.get("image_url")
        media_url = None
        if image_url_raw:
            from app.services.image_transform_service import (
                image_transform_service,
            )

            media_url = image_transform_service.transform_desktop(image_url_raw)
        return {
            "id": row.id,
            "timestamp": (
                row.created_at.isoformat() if row.created_at else None
            ),
            "meta_data": row.meta_data,
            "media_url": media_url,
            "caption": data.get("caption") or "",
            "price": int(data.get("credits_required", 0)),
        }
    except Exception as e:
        logger.error(
            f"获取 Surprise Snap 展示信息失败 message_id={message_id}: {str(e)}"
        )
        return None


def get_messages_paginated(
    session_id: str,
    limit: int = 20,
    offset: int = 0,
    user_id: Optional[str] = None,
    *,
    is_subscribed: Optional[bool] = None,
    unlocked_surprise_snap_message_ids: Optional[Set[int]] = None,
) -> Dict[str, Any]:
    """
    分页获取聊天消息

    Args:
        session_id: 会话ID
        limit: 每页消息数量
        offset: 偏移量（跳过的消息数量）
        user_id: 用户ID（保留以保持API兼容性，但不再用于过滤反馈）
        is_subscribed: 保留以兼容调用方，不参与 is_locked 计算
        unlocked_surprise_snap_message_ids: 当前用户已解锁的 surprise_snap 消息 ID 集合；is_locked 仅据此计算，订阅状态由 App 端判断

    Returns:
        包含消息列表和分页信息的字典
    """
    try:
        conn = get_chat_history_connection()

        # 查询总消息数（排除已软删除的）
        count_query = """
            SELECT COUNT(*) 
            FROM chat_history 
            WHERE session_id = %s AND deleted_at IS NULL
        """

        with conn.cursor() as cur:
            cur.execute(count_query, (session_id,))
            total_count = cur.fetchone()[0]

        # 分页查询消息（按时间倒序，最新的在前，排除已软删除的）- 包括消息ID、audio_url和meta_data
        messages_query = """
            SELECT id, message, created_at, audio_url, meta_data
            FROM chat_history 
            WHERE session_id = %s AND deleted_at IS NULL
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
                    raw_content = ""
                    if (
                        "data" in message_data
                        and "content" in message_data["data"]
                    ):
                        raw_content = message_data["data"]["content"]
                    elif "content" in message_data:
                        raw_content = message_data["content"]
                    content = _extract_text_from_content(raw_content)

                    # 确定角色
                    if message_type == "system":
                        role = "system"
                        sender_type = "SYSTEM"
                    elif message_type in ["human", "HumanMessage"]:
                        role = "user"
                        sender_type = "USER"
                    else:
                        role = "assistant"
                        sender_type = "AI"

                    # 处理meta_data
                    meta_data = None
                    if meta_data_raw:
                        if isinstance(meta_data_raw, str):
                            meta_data = json.loads(meta_data_raw)
                        elif isinstance(meta_data_raw, dict):
                            meta_data = meta_data_raw

                    # 构建基础消息对象
                    timestamp_str = (
                        created_at.isoformat() if created_at else None
                    )
                    message_obj = {
                        "id": message_id,  # 添加消息ID
                        "role": role,
                        "sender_type": sender_type,
                        "content": content,
                        "audio_url": audio_url,  # 添加audio_url字段
                        "meta_data": meta_data,  # 添加meta_data字段
                        "timestamp": timestamp_str,
                        "created_at": timestamp_str,  # 添加 created_at 以保持向后兼容
                    }
                    if (
                        role == "user"
                        and meta_data
                        and isinstance(meta_data.get("localId"), str)
                        and meta_data["localId"].strip()
                    ):
                        message_obj["local_id"] = meta_data["localId"]
                    if isinstance(raw_content, list):
                        message_obj["content_parts"] = raw_content

                    # 检查是否是图片消息（独立的图片消息，兼容旧数据）
                    if message_type == "image" and "data" in message_data:
                        image_data = message_data["data"]
                        message_obj["type"] = "image"

                        # 转换 GCS URI 为 CDN URL
                        gcs_uri = image_data.get("image_url")
                        if gcs_uri:
                            from app.services.image_transform_service import (
                                image_transform_service,
                            )

                            message_obj["image_url"] = (
                                image_transform_service.transform_desktop(
                                    gcs_uri
                                )
                            )
                        else:
                            message_obj["image_url"] = None

                        # 不返回 image_metadata 和 prompt 字段
                    elif (
                        message_type == "ai"
                        and meta_data
                        and meta_data.get("messageType")
                        == META_MESSAGE_TYPE_FESTIVAL_MEMORY_PROMPT
                    ):
                        message_obj["type"] = (
                            META_MESSAGE_TYPE_FESTIVAL_MEMORY_PROMPT
                        )
                        message_obj["role"] = None
                        message_obj["sender_type"] = None
                        raw_id = meta_data.get("festivalMemoryId")
                        if raw_id is not None:
                            try:
                                message_obj["festival_memory_id"] = int(raw_id)
                            except (TypeError, ValueError):
                                pass
                    elif (
                        message_type == "ai"
                        and meta_data
                        and meta_data.get("messageType")
                        == META_MESSAGE_TYPE_DAILY_MEMORY_PROMPT
                    ):
                        message_obj["type"] = (
                            META_MESSAGE_TYPE_DAILY_MEMORY_PROMPT
                        )
                        message_obj["role"] = None
                        message_obj["sender_type"] = None
                        raw_id = meta_data.get("dailyMemoryId")
                        if raw_id is not None:
                            try:
                                message_obj["daily_memory_id"] = int(raw_id)
                            except (TypeError, ValueError):
                                pass
                    elif message_type == META_MESSAGE_TYPE_SURPRISE_SNAP:
                        message_obj["type"] = META_MESSAGE_TYPE_SURPRISE_SNAP
                        message_obj["role"] = None
                        message_obj["sender_type"] = None
                        data = message_data.get("data") or {}
                        image_url_raw = data.get("image_url")
                        if image_url_raw:
                            from app.services.image_transform_service import (
                                image_transform_service,
                            )

                            message_obj["media_url"] = (
                                image_transform_service.transform_desktop(
                                    image_url_raw
                                )
                            )
                        else:
                            message_obj["media_url"] = None
                        message_obj["caption"] = data.get("caption") or ""
                        message_obj["price"] = data.get("credits_required", 0)
                        unlocked_ids = (
                            unlocked_surprise_snap_message_ids or set()
                        )
                        message_obj["is_locked"] = not (
                            message_id in unlocked_ids
                        )
                    else:
                        message_obj["type"] = "text"

                    # 解析 meta_data 中的 generated_image 字段（新数据格式）
                    if meta_data and "generated_image" in meta_data:
                        from app.services.image_transform_service import (
                            image_transform_service,
                        )

                        generated_image = meta_data["generated_image"]
                        image_url = generated_image.get("image_url")

                        if image_url:
                            # 转换 GCS URI 为 CDN URL
                            cdn_url = image_transform_service.transform_desktop(
                                image_url
                            )

                            # 在 meta_data 中添加转换后的 CDN URL
                            if "meta_data" not in message_obj:
                                message_obj["meta_data"] = {}

                            message_obj["meta_data"]["generated_image"] = {
                                "image_url": cdn_url,
                                "width": generated_image.get("width"),
                                "height": generated_image.get("height"),
                                "is_matched": generated_image.get("is_matched"),
                                "similarity": generated_image.get("similarity"),
                                "matched_from_user_id": generated_image.get(
                                    "matched_from_user_id"
                                ),
                                "model": generated_image.get("model"),
                                "generation_time_ms": generated_image.get(
                                    "generation_time_ms"
                                ),
                            }
                            # 不包含 prompt 字段

                    # 提取用户投票（仅对 AI 消息）
                    if role == "assistant" and meta_data:
                        # 优先使用新字段名 user_vote，兼容旧字段名 user_feedback
                        user_vote = meta_data.get("user_vote") or meta_data.get(
                            "user_feedback"
                        )
                        # 兼容旧格式（dict格式）和新格式（直接存储vote值）
                        if isinstance(user_vote, dict):
                            # 旧格式：{"user_id": "...", "feedback": "like"}
                            message_obj["user_vote"] = user_vote.get("feedback")
                        elif user_vote in ["like", "dislike"]:
                            # 新格式：直接存储 "like" 或 "dislike"
                            message_obj["user_vote"] = user_vote
                        else:
                            message_obj["user_vote"] = None
                        # 添加调试日志
                        if user_vote:
                            logger.debug(
                                f"提取用户投票: message_id={message_id}, user_vote={user_vote}, meta_data_keys={list(meta_data.keys()) if meta_data else []}"
                            )
                    elif role == "assistant":
                        # AI 消息但没有 meta_data，设置为 None
                        message_obj["user_vote"] = None

                    messages.append(message_obj)

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
    使用 get_messages_paginated 获取完整数据，包括图片消息

    Args:
        session_id: 会话ID

    Returns:
        消息列表
    """
    try:
        # 使用 get_messages_paginated 获取所有消息（设置一个很大的 limit）
        result_data = get_messages_paginated(session_id, limit=10000, offset=0)
        return result_data.get("messages", [])

    except Exception as e:
        logger.error(f"获取所有消息失败 {session_id}: {str(e)}")
        return []


def get_history_messages(session_id: str) -> List[BaseMessage]:
    """
    获取会话的历史消息，返回 LangChain BaseMessage 格式（排除已软删除的）

    用于 Agent 对话时获取上下文历史，替代 PostgresChatMessageHistory.messages
    以支持软删除过滤。会排除 festival_memory_prompt、daily_memory_prompt、surprise_snap 等非对话类消息，
    避免其进入 Agent 上下文导致重复或干扰。

    Args:
        session_id: 会话ID

    Returns:
        LangChain BaseMessage 列表，按时间正序排列（最早的在前）
    """
    try:
        conn = get_chat_history_connection()

        # 排除 festival_memory_prompt、surprise_snap 等非对话类消息，避免进入 Agent 上下文
        query = """
            SELECT message, created_at
            FROM chat_history
            WHERE session_id = %s AND deleted_at IS NULL
              AND (meta_data IS NULL
                   OR meta_data->>'messageType' IS NULL
                   OR (
                       meta_data->>'messageType' != %s
                       AND meta_data->>'messageType' != %s
                       AND meta_data->>'messageType' != %s
                   ))
            ORDER BY created_at ASC
        """

        messages: List[BaseMessage] = []
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    session_id,
                    META_MESSAGE_TYPE_FESTIVAL_MEMORY_PROMPT,
                    META_MESSAGE_TYPE_DAILY_MEMORY_PROMPT,
                    META_MESSAGE_TYPE_SURPRISE_SNAP,
                ),
            )
            rows = cur.fetchall()

            for row in rows:
                try:
                    message_raw = row[0]
                    created_at = row[1]
                    if isinstance(message_raw, str):
                        message_data = json.loads(message_raw)
                    elif isinstance(message_raw, dict):
                        message_data = message_raw
                    else:
                        message_data = json.loads(str(message_raw))

                    message_type = message_data.get("type", "human")
                    content: Any = ""
                    if (
                        "data" in message_data
                        and "content" in message_data["data"]
                    ):
                        content = message_data["data"]["content"]
                    elif "content" in message_data:
                        content = message_data["content"]
                    if not isinstance(content, list):
                        content = _extract_text_from_content(content)

                    # 关键步骤：把 created_at 放入 additional_kwargs，供上层按自然日插入日期 system message。
                    message_kwargs = (
                        {
                            "additional_kwargs": {
                                "created_at": created_at.isoformat()
                            }
                        }
                        if created_at
                        else {}
                    )

                    if message_type in ["human", "HumanMessage"]:
                        messages.append(
                            HumanMessage(content=content, **message_kwargs)
                        )
                    elif message_type == "system":
                        messages.append(
                            SystemMessage(content=content, **message_kwargs)
                        )
                    else:
                        messages.append(
                            AIMessage(content=content, **message_kwargs)
                        )

                except Exception as e:
                    logger.warning(f"解析历史消息失败: {str(e)}")
                    continue

        return messages

    except Exception as e:
        logger.error(f"获取历史消息失败 {session_id}: {str(e)}")
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

        logger.info(
            f"已清除会话 {session_id} 的聊天历史，删除消息数: {deleted_count}"
        )

    except Exception as e:
        logger.error(f"清除会话聊天历史失败 {session_id}: {str(e)}")
        raise


async def get_last_message_with_timestamp_async(
    session_id: str,
) -> Optional[Dict[str, Any]]:
    """在线程池中执行同步最近消息查询，避免阻塞事件循环。"""
    return await asyncio.to_thread(get_last_message_with_timestamp, session_id)


async def has_user_messages_ever_async(session_id: str) -> bool:
    """在线程池中执行同步用户消息存在性查询。"""
    return await asyncio.to_thread(has_user_messages_ever, session_id)


async def add_user_message_async(
    session_id: str,
    message: str | List[Dict[str, Any]],
    meta_data: Optional[dict] = None,
) -> Optional[int]:
    """在线程池中执行同步用户消息写入。"""
    return await asyncio.to_thread(
        add_user_message, session_id, message, meta_data
    )


async def add_ai_message_sync_async(
    session_id: str,
    message: str | List[Dict[str, Any]],
    agent_id: Optional[str] = None,
    meta_data: Optional[dict] = None,
) -> Optional[int]:
    """在线程池中执行同步 AI 消息写入。"""
    return await asyncio.to_thread(
        add_ai_message_sync,
        session_id,
        message,
        agent_id,
        meta_data,
    )


async def add_system_message_async(
    session_id: str,
    message: str | List[Dict[str, Any]],
    meta_data: Optional[dict] = None,
) -> Optional[int]:
    """在线程池中执行同步 system 消息写入。"""
    return await asyncio.to_thread(
        add_system_message_sync,
        session_id,
        message,
        meta_data,
    )


async def get_messages_paginated_async(
    session_id: str,
    limit: int = 20,
    offset: int = 0,
    user_id: Optional[str] = None,
    *,
    is_subscribed: Optional[bool] = None,
    unlocked_surprise_snap_message_ids: Optional[Set[int]] = None,
) -> Dict[str, Any]:
    """在线程池中执行同步分页查询。"""
    return await asyncio.to_thread(
        get_messages_paginated,
        session_id,
        limit,
        offset,
        user_id,
        is_subscribed=is_subscribed,
        unlocked_surprise_snap_message_ids=unlocked_surprise_snap_message_ids,
    )


async def clear_session_async(session_id: str) -> None:
    """在线程池中执行会话清理。"""
    await asyncio.to_thread(clear_session, session_id)


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

        # 使用ORM查询消息（排除已软删除的）
        stmt = select(ChatHistory).where(
            and_(
                ChatHistory.session_id == session_id,
                ChatHistory.id == db_message_id,
                ChatHistory.deleted_at.is_(None),
            )
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

        # 构建更新语句（只更新未被软删除的消息）
        if audio_duration is not None:
            # 使用SQLAlchemy的JSONB操作更新audio_url和meta_data
            stmt = (
                update(ChatHistory)
                .where(
                    and_(
                        ChatHistory.session_id == session_id,
                        ChatHistory.id == db_message_id,
                        ChatHistory.deleted_at.is_(None),
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
                        ChatHistory.deleted_at.is_(None),
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
    软删除包括指定消息ID在内的后续所有聊天记录

    Args:
        session_id: 会话ID
        message_id: 消息ID（数据库自增ID）

    Returns:
        包含删除结果的字典
    """
    try:
        conn = get_chat_history_connection()

        # 首先验证指定的消息是否存在（未被软删除的）
        check_query = """
            SELECT id, message, created_at
            FROM chat_history 
            WHERE session_id = %s AND id = %s AND deleted_at IS NULL
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

            # 查询将要软删除的消息数量和详情（包括指定ID，未被软删除的）
            count_query = """
                SELECT COUNT(*), MIN(created_at), MAX(created_at)
                FROM chat_history 
                WHERE session_id = %s AND id >= %s AND deleted_at IS NULL
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
                            target_message[2].isoformat()
                            if target_message[2]
                            else None
                        ),
                    },
                }

            # 执行软删除操作（包括指定ID）
            soft_delete_query = """
                UPDATE chat_history 
                SET deleted_at = NOW()
                WHERE session_id = %s AND id >= %s AND deleted_at IS NULL
            """

            cur.execute(soft_delete_query, (session_id, message_id))
            actual_deleted = cur.rowcount

            logger.info(
                f"已软删除会话 {session_id} 中包括消息ID {message_id} 在内的 {actual_deleted} 条记录"
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
                        target_message[2].isoformat()
                        if target_message[2]
                        else None
                    ),
                },
                "deleted_time_range": (
                    {
                        "from": (
                            count_result[1].isoformat()
                            if count_result[1]
                            else None
                        ),
                        "to": (
                            count_result[2].isoformat()
                            if count_result[2]
                            else None
                        ),
                    }
                    if count_result[1]
                    else None
                ),
            }

    except Exception as e:
        logger.error(
            f"软删除指定消息后记录失败 {session_id}, message_id {message_id}: {str(e)}"
        )
        return {
            "success": False,
            "message": f"清除操作失败: {str(e)}",
            "deleted_count": 0,
            "target_message": None,
        }


def clear_messages_after_timestamp(
    session_id: str, timestamp: str
) -> Dict[str, Any]:
    """
    软删除指定时间戳之后的所有聊天记录

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
            target_time = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )
        except ValueError as e:
            return {
                "success": False,
                "message": f"时间戳格式错误: {str(e)}",
                "deleted_count": 0,
            }

        # 查询将要软删除的消息数量（未被软删除的）
        count_query = """
            SELECT COUNT(*)
            FROM chat_history 
            WHERE session_id = %s AND created_at > %s AND deleted_at IS NULL
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

            # 执行软删除操作
            soft_delete_query = """
                UPDATE chat_history 
                SET deleted_at = NOW()
                WHERE session_id = %s AND created_at > %s AND deleted_at IS NULL
            """

            cur.execute(soft_delete_query, (session_id, target_time))
            actual_deleted = cur.rowcount

            logger.info(
                f"已软删除会话 {session_id} 中时间 {timestamp} 之后的 {actual_deleted} 条记录"
            )

            return {
                "success": True,
                "message": f"成功删除时间 {timestamp} 之后的 {actual_deleted} 条记录",
                "deleted_count": actual_deleted,
                "cutoff_timestamp": timestamp,
            }

    except Exception as e:
        logger.error(
            f"按时间戳软删除消息失败 {session_id}, timestamp {timestamp}: {str(e)}"
        )
        return {
            "success": False,
            "message": f"清除操作失败: {str(e)}",
            "deleted_count": 0,
        }


def clear_all_messages(session_id: str) -> Dict[str, Any]:
    """
    软删除指定会话的所有聊天记录

    Args:
        session_id: 会话ID

    Returns:
        包含删除结果的字典
    """
    try:
        conn = get_chat_history_connection()

        # 查询将要软删除的消息数量（未被软删除的）
        count_query = """
            SELECT COUNT(*)
            FROM chat_history 
            WHERE session_id = %s AND deleted_at IS NULL
        """

        with conn.cursor() as cur:
            cur.execute(count_query, (session_id,))
            messages_to_delete = cur.fetchone()[0]

            if messages_to_delete == 0:
                return {
                    "success": True,
                    "message": "没有消息需要删除",
                    "deleted_count": 0,
                }

            # 执行软删除操作
            soft_delete_query = """
                UPDATE chat_history 
                SET deleted_at = NOW()
                WHERE session_id = %s AND deleted_at IS NULL
            """

            cur.execute(soft_delete_query, (session_id,))
            actual_deleted = cur.rowcount

            logger.info(
                f"已软删除会话 {session_id} 中的全部 {actual_deleted} 条记录"
            )

            return {
                "success": True,
                "message": f"成功删除全部 {actual_deleted} 条记录",
                "deleted_count": actual_deleted,
            }

    except Exception as e:
        logger.error(f"软删除全部消息失败 {session_id}: {str(e)}")
        return {
            "success": False,
            "message": f"清除操作失败: {str(e)}",
            "deleted_count": 0,
        }
