from typing import Optional, Dict, Any, List
from langchain_postgres import PostgresChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
import psycopg
from app.core.config import settings
import json
import logging
from datetime import datetime

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

def get_messages_paginated(session_id: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
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
        ensure_table_initialized()
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
        
        # 分页查询消息（按时间倒序，最新的在前）
        messages_query = """
            SELECT message, created_at
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
                    # 处理消息数据，可能是字符串或已经是字典
                    message_raw = row[0]
                    if isinstance(message_raw, str):
                        message_data = json.loads(message_raw)
                    elif isinstance(message_raw, dict):
                        message_data = message_raw
                    else:
                        # 尝试转换为字符串再解析
                        message_data = json.loads(str(message_raw))
                    
                    created_at = row[1]
                    
                    # 解析消息类型和内容
                    message_type = message_data.get('type', 'human')
                    content = ''
                    
                    if 'data' in message_data and 'content' in message_data['data']:
                        content = message_data['data']['content']
                    elif 'content' in message_data:
                        content = message_data['content']
                    
                    # 确定角色
                    role = 'user' if message_type in ['human', 'HumanMessage'] else 'assistant'
                    
                    messages.append({
                        'role': role,
                        'content': content,
                        'timestamp': created_at.isoformat() if created_at else None
                    })
                    
                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    logger.warning(f"解析消息失败 {session_id}: {str(e)}, 原始数据: {row[0]}")
                    # 跳过无法解析的消息，继续处理其他消息
                    continue
        
        # 因为我们是按时间倒序查询的，但返回时希望按正常时间顺序（旧消息在前）
        messages.reverse()
        
        return {
            'messages': messages,
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total_count,
            'page': (offset // limit) + 1 if limit > 0 else 1
        }
        
    except Exception as e:
        logger.error(f"分页获取消息失败 {session_id}: {str(e)}")
        return {
            'messages': [],
            'total': 0,
            'limit': limit,
            'offset': offset,
            'has_more': False,
            'page': 1
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
            role = 'user' if isinstance(message, HumanMessage) else 'assistant'
            result.append({
                'role': role,
                'content': message.content,
                'timestamp': None  # PostgresChatMessageHistory 默认没有时间戳
            })
        
        return result
        
    except Exception as e:
        logger.error(f"获取所有消息失败 {session_id}: {str(e)}")
        return [] 