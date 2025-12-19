#!/usr/bin/env python3
"""
CREATED_BY_AGENT

导出 AI 消息内容包含独立 "ext" 单词的对话及其上下文

筛选条件：精确匹配独立的 "ext" 单词（前后是空格、标点或边界），
不匹配包含 ext 的单词如 "next"、"text" 等。

使用方法：
    # 默认导出到 ext_conversations.csv
    python scripts/export_ext_conversations.py

    # 指定输出文件
    python scripts/export_ext_conversations.py --output my_output.csv

    # 限制导出数量
    python scripts/export_ext_conversations.py --limit 100

    # 指定上下文消息数量（默认10条）
    python scripts/export_ext_conversations.py --context-size 20
"""

import asyncio
import csv
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import cyclopts
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal


def generate_session_id(chat_id: str) -> str:
    """根据 chat_id 生成 session_id"""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))


@dataclass
class MatchedMessage:
    """匹配到的消息数据"""

    message_id: int
    session_id: str
    content: str
    created_at: datetime


@dataclass
class ConversationExport:
    """导出的对话数据"""

    session_id: str
    agent_id: Optional[str]
    agent_name: Optional[str]
    user_id: Optional[str]
    matched_message_id: int
    matched_message_content: str
    matched_at: str
    context_messages: str


async def find_messages_with_ext(
    db: AsyncSession, limit: Optional[int] = None
) -> List[MatchedMessage]:
    """
    查找 AI 消息内容包含独立 ext 单词的记录
    
    使用正则表达式匹配独立的 "ext" 单词：
    - ext 作为整个内容
    - ext 前后是空格
    - ext 前后是标点符号
    """
    limit_clause = f"LIMIT {limit}" if limit else ""

    # 使用正则表达式匹配独立的 ext 单词
    # (^|\s|[[:punct:]]) - 开头、空白字符或标点
    # ext - 精确匹配 ext
    # ($|\s|[[:punct:]]) - 结尾、空白字符或标点
    query = text(
        f"""
        SELECT 
            id,
            session_id::text,
            message->'data'->>'content' as content,
            created_at
        FROM chat_history
        WHERE message->>'type' = 'ai'
          AND message->'data'->>'content' ~ '(^|\\s|[[:punct:]])ext($|\\s|[[:punct:]])'
          AND deleted_at IS NULL
        ORDER BY created_at DESC
        {limit_clause}
    """
    )

    result = await db.execute(query)
    rows = result.fetchall()

    return [
        MatchedMessage(
            message_id=row[0],
            session_id=row[1],
            content=row[2] or "",
            created_at=row[3],
        )
        for row in rows
    ]


async def get_context_messages(
    db: AsyncSession, session_id: str, target_message_id: int, context_size: int = 10
) -> List[Dict[str, Any]]:
    """获取指定消息前后的上下文消息"""
    half_size = context_size // 2

    # 将 session_id 转换为 UUID 对象
    session_uuid = uuid.UUID(session_id)

    query = text(
        """
        WITH target_msg AS (
            SELECT created_at as target_time
            FROM chat_history
            WHERE id = :message_id
        ),
        before_msgs AS (
            SELECT id, message, created_at, 'before' as position
            FROM chat_history, target_msg
            WHERE session_id = :session_id
              AND created_at < target_msg.target_time
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT :half_size
        ),
        after_msgs AS (
            SELECT id, message, created_at, 'after' as position
            FROM chat_history, target_msg
            WHERE session_id = :session_id
              AND created_at > target_msg.target_time
              AND deleted_at IS NULL
            ORDER BY created_at ASC
            LIMIT :half_size
        ),
        target AS (
            SELECT id, message, created_at, 'target' as position
            FROM chat_history
            WHERE id = :message_id
        )
        SELECT id, message, created_at, position
        FROM (
            SELECT * FROM before_msgs
            UNION ALL
            SELECT * FROM target
            UNION ALL
            SELECT * FROM after_msgs
        ) combined
        ORDER BY created_at ASC
    """
    )

    result = await db.execute(
        query,
        {"session_id": session_uuid, "message_id": target_message_id, "half_size": half_size},
    )
    rows = result.fetchall()

    messages = []
    for row in rows:
        msg_id, message_data, created_at, position = row

        if isinstance(message_data, str):
            message_data = json.loads(message_data)

        msg_type = message_data.get("type", "unknown")
        content = ""
        if "data" in message_data and "content" in message_data["data"]:
            content = message_data["data"]["content"]
        elif "content" in message_data:
            content = message_data["content"]

        role = "user" if msg_type in ["human", "HumanMessage"] else "assistant"

        messages.append(
            {
                "id": msg_id,
                "role": role,
                "content": content,
                "timestamp": created_at.isoformat() if created_at else None,
                "is_target": position == "target",
            }
        )

    return messages


async def get_session_metadata(
    db: AsyncSession, session_ids: List[str]
) -> Dict[str, Dict[str, Any]]:
    """批量获取会话的元数据（agent_id, agent_name, user_id）"""
    if not session_ids:
        return {}

    query = text(
        """
        SELECT 
            c.id as chat_id,
            c.user_id,
            c.agent_id,
            a.name as agent_name
        FROM chats c
        LEFT JOIN agents a ON c.agent_id = a.id
    """
    )

    result = await db.execute(query)
    rows = result.fetchall()

    chat_id_to_metadata = {}
    for row in rows:
        chat_id = row[0]
        session_id = generate_session_id(chat_id)
        chat_id_to_metadata[session_id] = {
            "user_id": row[1],
            "agent_id": row[2],
            "agent_name": row[3],
        }

    return chat_id_to_metadata


async def export_ext_conversations(
    db: AsyncSession,
    output_path: str,
    limit: Optional[int] = None,
    context_size: int = 10,
) -> int:
    """导出包含独立 ext 单词的对话到 CSV"""
    logger.info("正在查找包含独立 ext 单词的 AI 消息...")
    matched_messages = await find_messages_with_ext(db, limit)
    logger.info(f"找到 {len(matched_messages)} 条匹配的消息")

    if not matched_messages:
        logger.info("没有找到匹配的消息")
        return 0

    session_ids = list(set(m.session_id for m in matched_messages))
    logger.info(f"涉及 {len(session_ids)} 个不同的会话")

    logger.info("正在获取会话元数据...")
    metadata = await get_session_metadata(db, session_ids)

    exports = []
    for i, msg in enumerate(matched_messages):
        if (i + 1) % 100 == 0:
            logger.info(f"处理进度: {i + 1}/{len(matched_messages)}")

        context = await get_context_messages(db, msg.session_id, msg.message_id, context_size)
        meta = metadata.get(msg.session_id, {})

        exports.append(
            ConversationExport(
                session_id=msg.session_id,
                agent_id=meta.get("agent_id"),
                agent_name=meta.get("agent_name"),
                user_id=meta.get("user_id"),
                matched_message_id=msg.message_id,
                matched_message_content=msg.content,
                matched_at=msg.created_at.isoformat() if msg.created_at else "",
                context_messages=json.dumps(context, ensure_ascii=False),
            )
        )

    logger.info(f"正在写入 CSV 文件: {output_path}")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "session_id",
                "agent_id",
                "agent_name",
                "user_id",
                "matched_message_id",
                "matched_message_content",
                "matched_at",
                "context_messages",
            ]
        )

        for export in exports:
            writer.writerow(
                [
                    export.session_id,
                    export.agent_id or "",
                    export.agent_name or "",
                    export.user_id or "",
                    export.matched_message_id,
                    export.matched_message_content,
                    export.matched_at,
                    export.context_messages,
                ]
            )

    logger.info(f"导出完成，共 {len(exports)} 条记录")
    return len(exports)


app = cyclopts.App(
    help="导出 AI 消息内容包含独立 ext 单词的对话及其上下文"
)


@app.default
def main(
    output: str = "ext_conversations.csv",
    limit: Optional[int] = None,
    context_size: int = 10,
):
    """
    导出包含独立 ext 单词的 AI 回复及上下文

    Args:
        output: 输出 CSV 文件路径
        limit: 最多导出多少条匹配记录，不指定则导出全部
        context_size: 上下文消息数量（目标消息前后各一半）
    """
    asyncio.run(_main(output, limit, context_size))


async def _main(output: str, limit: Optional[int], context_size: int):
    """异步主函数"""
    async with AsyncSessionLocal() as db:
        count = await export_ext_conversations(db, output, limit, context_size)
        print(f"\n导出完成: {count} 条记录已写入 {output}")


if __name__ == "__main__":
    app()

