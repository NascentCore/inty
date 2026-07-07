# CREATED_BY_AGENT
"""
数据库服务模块

提供用户查询和聊天历史获取功能
"""

import json
import uuid
from dataclasses import dataclass
from typing import List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from config import get_config


def generate_session_id(chat_id: str) -> str:
    """
    生成 session_id，与 app/services/chat_service.py 中的逻辑一致
    使用 UUID5 基于 chat_id 生成确定性的 session_id
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))


@dataclass
class UserInfo:
    """用户信息"""

    id: str
    email: Optional[str]
    nickname: Optional[str]
    message_count: int


@dataclass
class ChatSession:
    """聊天会话信息"""

    chat_id: str
    agent_id: str
    agent_name: str


@dataclass
class ChatMessage:
    """聊天消息"""

    role: str  # "user" or "assistant"
    content: str


@dataclass
class UserChatHistory:
    """用户与单个角色的聊天历史"""

    agent_name: str
    messages: List[ChatMessage]


def get_db_connection():
    """获取数据库连接"""
    config = get_config()
    return psycopg2.connect(
        host=config.database.host,
        port=config.database.port,
        user=config.database.user,
        password=config.database.password,
        dbname=config.database.db,
    )


def get_users_by_emails(emails: List[str]) -> List[UserInfo]:
    """通过邮箱列表获取用户"""
    if not emails:
        return []

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 先获取所有 chat_id 和对应的 session_id
            cur.execute("SELECT id, user_id FROM chats")
            all_chats = cur.fetchall()

            # 构建 session_id 到 user_id 的映射
            session_to_user = {}
            for chat in all_chats:
                session_id = generate_session_id(chat["id"])
                session_to_user[session_id] = chat["user_id"]

            # 查询消息数量
            cur.execute("""
                SELECT session_id::text, COUNT(*) as msg_count 
                FROM chat_history 
                GROUP BY session_id
            """)
            session_counts = cur.fetchall()

            # 按用户聚合消息数
            user_msg_counts = {}
            for row in session_counts:
                session_id = row["session_id"]
                if session_id in session_to_user:
                    user_id = session_to_user[session_id]
                    user_msg_counts[user_id] = (
                        user_msg_counts.get(user_id, 0) + row["msg_count"]
                    )

            # 查询用户信息
            query = """
                SELECT id, email, nickname
                FROM users
                WHERE email = ANY(%s)
                AND deleted_at IS NULL
            """
            cur.execute(query, (emails,))
            rows = cur.fetchall()

            result = []
            for row in rows:
                result.append(
                    UserInfo(
                        id=row["id"],
                        email=row["email"],
                        nickname=row["nickname"],
                        message_count=user_msg_counts.get(row["id"], 0),
                    )
                )
            # 按消息数排序
            result.sort(key=lambda x: x.message_count, reverse=True)
            return result
    finally:
        conn.close()


def get_top_users_by_message_count(limit: int = 20) -> List[UserInfo]:
    """获取消息数量最多的用户"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 获取所有 chat 及其 user_id
            cur.execute("SELECT id, user_id FROM chats")
            all_chats = cur.fetchall()

            # 构建 session_id 到 user_id 的映射
            session_to_user = {}
            for chat in all_chats:
                session_id = generate_session_id(chat["id"])
                session_to_user[session_id] = chat["user_id"]

            # 查询每个 session 的消息数量
            cur.execute("""
                SELECT session_id::text, COUNT(*) as msg_count 
                FROM chat_history 
                GROUP BY session_id
            """)
            session_counts = cur.fetchall()

            # 按用户聚合消息数
            user_msg_counts = {}
            for row in session_counts:
                session_id = row["session_id"]
                if session_id in session_to_user:
                    user_id = session_to_user[session_id]
                    user_msg_counts[user_id] = (
                        user_msg_counts.get(user_id, 0) + row["msg_count"]
                    )

            # 过滤出有消息的用户并排序
            user_ids_with_msgs = sorted(
                user_msg_counts.keys(),
                key=lambda uid: user_msg_counts[uid],
                reverse=True,
            )[:limit]

            if not user_ids_with_msgs:
                return []

            # 查询用户信息
            cur.execute(
                """
                SELECT id, email, nickname
                FROM users
                WHERE id = ANY(%s)
                AND deleted_at IS NULL
            """,
                (user_ids_with_msgs,),
            )
            rows = cur.fetchall()

            # 构建结果
            user_info_map = {row["id"]: row for row in rows}
            result = []
            for user_id in user_ids_with_msgs:
                if user_id in user_info_map:
                    row = user_info_map[user_id]
                    result.append(
                        UserInfo(
                            id=row["id"],
                            email=row["email"],
                            nickname=row["nickname"],
                            message_count=user_msg_counts[user_id],
                        )
                    )
            return result
    finally:
        conn.close()


def get_user_chat_sessions(user_id: str) -> List[ChatSession]:
    """获取用户的所有聊天会话"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    c.id as chat_id,
                    c.agent_id,
                    a.name as agent_name
                FROM chats c
                JOIN agents a ON a.id = c.agent_id
                WHERE c.user_id = %s
                AND c.is_active = true
                AND a.deleted_at IS NULL
            """
            cur.execute(query, (user_id,))
            rows = cur.fetchall()

            return [
                ChatSession(
                    chat_id=row["chat_id"],
                    agent_id=row["agent_id"],
                    agent_name=row["agent_name"],
                )
                for row in rows
            ]
    finally:
        conn.close()


def get_chat_messages(chat_id: str, limit: int = 500) -> List[ChatMessage]:
    """获取聊天会话的消息"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            session_id = generate_session_id(chat_id)
            query = """
                SELECT message
                FROM chat_history
                WHERE session_id::text = %s
                AND deleted_at IS NULL
                ORDER BY created_at ASC
                LIMIT %s
            """
            cur.execute(query, (session_id, limit))
            rows = cur.fetchall()

            messages = []
            for row in rows:
                message_raw = row["message"]

                # 解析消息数据
                if isinstance(message_raw, str):
                    message_data = json.loads(message_raw)
                elif isinstance(message_raw, dict):
                    message_data = message_raw
                else:
                    continue

                # 提取消息类型和内容
                message_type = message_data.get("type", "human")
                content = ""

                if "data" in message_data and "content" in message_data["data"]:
                    content = message_data["data"]["content"]
                elif "content" in message_data:
                    content = message_data["content"]

                if not content:
                    continue

                # 确定角色
                role = (
                    "user" if message_type in ["human", "HumanMessage"] else "assistant"
                )
                messages.append(ChatMessage(role=role, content=content))

            return messages
    finally:
        conn.close()


def get_user_all_chat_history(user_id: str) -> List[UserChatHistory]:
    """获取用户与所有角色的聊天历史"""
    sessions = get_user_chat_sessions(user_id)
    histories = []

    for session in sessions:
        messages = get_chat_messages(session.chat_id)
        if messages:
            histories.append(
                UserChatHistory(
                    agent_name=session.agent_name,
                    messages=messages,
                )
            )

    return histories


def format_chat_history_for_analysis(histories: List[UserChatHistory]) -> str:
    """将聊天历史格式化为适合 LLM 分析的文本"""
    if not histories:
        return "（没有聊天记录）"

    parts = []
    for history in histories:
        parts.append(f"\n## 与角色「{history.agent_name}」的对话\n")
        for msg in history.messages:
            role_label = "用户" if msg.role == "user" else "AI"
            parts.append(f"**{role_label}**: {msg.content}\n")

    return "\n".join(parts)


def get_random_agent(exclude_ids: Optional[List[str]] = None) -> Optional[dict]:
    """获取一个随机角色用于测试对话"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            exclude_clause = ""
            params = []
            if exclude_ids:
                exclude_clause = "AND id != ALL(%s)"
                params.append(exclude_ids)

            query = f"""
                SELECT 
                    id,
                    name,
                    personality,
                    intro,
                    opening,
                    main_prompt,
                    mode_prompt
                FROM agents
                WHERE deleted_at IS NULL
                AND visibility = 'PUBLIC'
                AND status = 'APPROVED'
                {exclude_clause}
                ORDER BY RANDOM()
                LIMIT 1
            """
            cur.execute(query, params if params else None)
            row = cur.fetchone()

            if row:
                return dict(row)
            return None
    finally:
        conn.close()
