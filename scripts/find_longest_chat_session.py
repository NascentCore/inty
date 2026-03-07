#!/usr/bin/env python3
"""
CREATED_BY_AGENT

查找最长会话脚本：统计所有会话的用户消息数（轮数），找出最长的会话

使用方法：
    # 显示最长的 10 个会话（默认）
    python scripts/find_longest_chat_session.py

    # 显示最长的 N 个会话
    python scripts/find_longest_chat_session.py --limit 20

    # 显示所有会话统计
    python scripts/find_longest_chat_session.py --limit 0
"""

import asyncio
import uuid
from dataclasses import dataclass
from typing import List, Optional

import cyclopts
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal


def generate_session_id(chat_id: str) -> str:
    """
    根据 chat_id 生成 session_id

    与 app/services/chat_service.py 中的 generate_session_id 保持一致
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))


@dataclass
class ChatSessionStats:
    """会话统计数据"""

    chat_id: str
    user_id: str
    user_name: Optional[str]
    agent_id: str
    agent_name: Optional[str]
    session_id: str
    user_message_count: int
    total_message_count: int
    created_at: str


@dataclass
class SummaryStats:
    """统计摘要"""

    total_chats: int
    chats_with_messages: int
    total_user_messages: int
    avg_user_messages: float
    max_user_messages: int


async def get_all_chats(db: AsyncSession) -> List[dict]:
    """获取所有会话记录"""
    query = text(
        """
        SELECT 
            c.id as chat_id,
            c.user_id,
            u.nickname as user_name,
            c.agent_id,
            a.name as agent_name,
            c.created_at
        FROM chats c
        LEFT JOIN agents a ON c.agent_id = a.id
        LEFT JOIN users u ON c.user_id = u.id
        ORDER BY c.created_at DESC
    """
    )
    result = await db.execute(query)
    rows = result.fetchall()

    return [
        {
            "chat_id": row[0],
            "user_id": row[1],
            "user_name": row[2],
            "agent_id": row[3],
            "agent_name": row[4],
            "created_at": str(row[5]) if row[5] else None,
        }
        for row in rows
    ]


BATCH_SIZE = 1000


async def get_message_counts_by_sessions(
    db: AsyncSession, session_ids: List[str]
) -> dict:
    """
    批量获取每个 session 的消息统计（分批处理以避免参数过多）

    Returns:
        session_id -> {"user_count": int, "total_count": int}
    """
    if not session_ids:
        return {}

    result_dict = {}
    total_batches = (len(session_ids) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(total_batches):
        start = batch_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(session_ids))
        batch_ids = session_ids[start:end]

        if batch_idx % 10 == 0:
            logger.debug(f"处理批次 {batch_idx + 1}/{total_batches}...")

        placeholders = ",".join([f":sid_{i}" for i in range(len(batch_ids))])
        params = {f"sid_{i}": sid for i, sid in enumerate(batch_ids)}

        query = text(
            f"""
            SELECT 
                session_id::text as session_id,
                COUNT(*) FILTER (
                    WHERE message->>'type' IN ('human', 'HumanMessage')
                    AND (meta_data IS NULL OR meta_data->>'isOpening' IS NULL OR meta_data->>'isOpening' != 'true')
                ) as user_message_count,
                COUNT(*) as total_message_count
            FROM chat_history
            WHERE session_id::text IN ({placeholders})
            GROUP BY session_id
        """
        )

        result = await db.execute(query, params)
        rows = result.fetchall()

        for row in rows:
            result_dict[row[0]] = {"user_count": row[1], "total_count": row[2]}

    return result_dict


async def find_longest_sessions(
    db: AsyncSession, limit: int = 10
) -> tuple[List[ChatSessionStats], SummaryStats]:
    """
    查找最长的会话

    Args:
        db: 数据库会话
        limit: 返回的会话数量，0 表示返回所有

    Returns:
        (会话统计列表, 统计摘要)
    """
    logger.info("正在获取所有会话...")
    chats = await get_all_chats(db)
    total_chats = len(chats)
    logger.info(f"共找到 {total_chats} 个会话")

    if not chats:
        return [], SummaryStats(
            total_chats=0,
            chats_with_messages=0,
            total_user_messages=0,
            avg_user_messages=0,
            max_user_messages=0,
        )

    chat_id_to_info = {chat["chat_id"]: chat for chat in chats}
    session_id_to_chat_id = {
        generate_session_id(chat["chat_id"]): chat["chat_id"] for chat in chats
    }
    session_ids = list(session_id_to_chat_id.keys())

    logger.info("正在统计消息数量...")
    message_counts = await get_message_counts_by_sessions(db, session_ids)

    session_stats_list = []
    for session_id, chat_id in session_id_to_chat_id.items():
        chat_info = chat_id_to_info[chat_id]
        counts = message_counts.get(session_id, {"user_count": 0, "total_count": 0})

        session_stats_list.append(
            ChatSessionStats(
                chat_id=chat_id,
                user_id=chat_info["user_id"],
                user_name=chat_info["user_name"],
                agent_id=chat_info["agent_id"],
                agent_name=chat_info["agent_name"],
                session_id=session_id,
                user_message_count=counts["user_count"],
                total_message_count=counts["total_count"],
                created_at=chat_info["created_at"],
            )
        )

    session_stats_list.sort(key=lambda x: x.user_message_count, reverse=True)

    chats_with_messages = sum(1 for s in session_stats_list if s.user_message_count > 0)
    total_user_messages = sum(s.user_message_count for s in session_stats_list)
    max_user_messages = (
        session_stats_list[0].user_message_count if session_stats_list else 0
    )
    avg_user_messages = (
        total_user_messages / chats_with_messages if chats_with_messages > 0 else 0
    )

    summary = SummaryStats(
        total_chats=total_chats,
        chats_with_messages=chats_with_messages,
        total_user_messages=total_user_messages,
        avg_user_messages=avg_user_messages,
        max_user_messages=max_user_messages,
    )

    if limit > 0:
        session_stats_list = session_stats_list[:limit]

    return session_stats_list, summary


def print_results(sessions: List[ChatSessionStats], summary: SummaryStats, limit: int):
    """打印结果"""
    print("\n" + "=" * 80)
    print("会话统计摘要")
    print("=" * 80)
    print(f"总会话数: {summary.total_chats}")
    print(f"有用户消息的会话数: {summary.chats_with_messages}")
    print(f"总用户消息数: {summary.total_user_messages}")
    print(f"平均每会话用户消息数: {summary.avg_user_messages:.2f}")
    print(f"最长会话用户消息数: {summary.max_user_messages}")

    if not sessions:
        print("\n没有找到任何会话")
        return

    title = f"最长的 {len(sessions)} 个会话" if limit > 0 else "所有会话"
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    for i, session in enumerate(sessions, 1):
        print(f"\n--- 第 {i} 名 ---")
        print(f"  Chat ID: {session.chat_id}")
        print(f"  User ID: {session.user_id}")
        print(f"  User Name: {session.user_name or '(未知)'}")
        print(f"  Agent ID: {session.agent_id}")
        print(f"  Agent Name: {session.agent_name or '(未知)'}")
        print(f"  用户消息数（轮数）: {session.user_message_count}")
        print(f"  总消息数: {session.total_message_count}")
        print(f"  创建时间: {session.created_at or '(未知)'}")


app = cyclopts.App(
    help="查找最长会话脚本：统计所有会话的用户消息数（轮数），找出最长的会话"
)


@app.default
def main(limit: int = 10):
    """
    查找最长的会话

    Args:
        limit: 显示最长的 N 个会话，0 表示显示所有
    """
    asyncio.run(_main(limit))


async def _main(limit: int):
    """异步主函数"""
    async with AsyncSessionLocal() as db:
        sessions, summary = await find_longest_sessions(db, limit)
        print_results(sessions, summary, limit)


if __name__ == "__main__":
    app()
