from typing import Optional, Dict, Any
from langchain_postgres import PostgresChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
import psycopg
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

# 全局连接，避免重复创建
_connection = None

# 获取数据库连接
def get_chat_history_connection():
    global _connection
    if _connection is None or _connection.closed:
        try:
            _connection = psycopg.connect(
                settings.database.url,
                autocommit=True
            )
            logger.info("chat_history数据库连接已建立")
        except Exception as e:
            logger.error(f"建立chat_history数据库连接失败: {str(e)}")
            raise
    return _connection

# 初始化chat_history表
def init_chat_history_table():
    """初始化chat_history表"""
    try:
        conn = get_chat_history_connection()
        PostgresChatMessageHistory.create_tables(conn, "chat_history")
        logger.info("chat_history表已初始化")
    except Exception as e:
        logger.error(f"初始化chat_history表失败: {str(e)}")
        # 不抛出异常，因为表可能已经存在

# 延迟初始化，避免在导入时就连接数据库
_table_initialized = False

def ensure_table_initialized():
    """确保表已初始化"""
    global _table_initialized
    if not _table_initialized:
        init_chat_history_table()
        _table_initialized = True

def get_chat_history(session_id: str) -> PostgresChatMessageHistory:
    """获取聊天历史"""
    ensure_table_initialized()
    conn = get_chat_history_connection()
    return PostgresChatMessageHistory(
        "chat_history",
        session_id,
        sync_connection=conn
    )

def add_agent_opening_message(session_id: str, opening_message: str) -> None:
    """添加Agent开场白到聊天历史"""
    try:
        history = get_chat_history(session_id)
        history.add_messages([AIMessage(content=opening_message)])
        logger.info(f"添加开场白到会话 {session_id}: {opening_message}")
    except Exception as e:
        logger.error(f"添加开场白失败 {session_id}: {str(e)}")
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

def add_user_message(session_id: str, message: str) -> None:
    """添加用户消息到聊天历史"""
    try:
        history = get_chat_history(session_id)
        history.add_messages([HumanMessage(content=message)])
        logger.info(f"添加用户消息到会话 {session_id}: {message}")
    except Exception as e:
        logger.error(f"添加用户消息失败 {session_id}: {str(e)}")
        raise

def add_ai_message(session_id: str, message: str) -> None:
    """添加AI消息到聊天历史"""
    try:
        history = get_chat_history(session_id)
        history.add_messages([AIMessage(content=message)])
        logger.info(f"添加AI消息到会话 {session_id}: {message}")
    except Exception as e:
        logger.error(f"添加AI消息失败 {session_id}: {str(e)}")
        raise 