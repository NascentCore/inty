"""
推送历史查询脚本

用于查询特定会话的推送历史，显示所有阶段的推送记录。

使用方法:
    # 查询特定聊天的推送历史
    python scripts/fcm/check_push_history.py --chat-id CHAT_ID

    # 查询特定用户的推送历史
    python scripts/fcm/check_push_history.py --user-id USER_ID

    # 查询特定 Agent 的推送历史
    python scripts/fcm/check_push_history.py --agent-id AGENT_ID

    # 查询特定阶段的推送历史
    python scripts/fcm/check_push_history.py --chat-id CHAT_ID --stage 10min

    # 限制返回数量
    python scripts/fcm/check_push_history.py --chat-id CHAT_ID --limit 10
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from loguru import logger
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.logging import init_logger
from app.db.session import AsyncSessionLocal
from app.models import PushNotificationHistory


async def get_push_history(
    db: AsyncSession,
    chat_id: Optional[str] = None,
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    stage: Optional[str] = None,
    limit: int = 100,
) -> List[PushNotificationHistory]:
    """
    查询推送历史

    Args:
        db: 数据库会话
        chat_id: 聊天ID（可选）
        user_id: 用户ID（可选）
        agent_id: Agent ID（可选）
        stage: 推送阶段（可选）
        limit: 返回数量限制

    Returns:
        推送历史记录列表
    """
    conditions = []

    if chat_id:
        conditions.append(PushNotificationHistory.chat_id == chat_id)
    if user_id:
        conditions.append(PushNotificationHistory.user_id == user_id)
    if agent_id:
        conditions.append(PushNotificationHistory.agent_id == agent_id)
    if stage:
        conditions.append(PushNotificationHistory.stage == stage)

    stmt = (
        select(PushNotificationHistory)
        .where(and_(*conditions) if conditions else True)
        .order_by(desc(PushNotificationHistory.sent_at))
        .limit(limit)
    )

    result = await db.execute(stmt)
    return result.scalars().all()


async def format_push_history(history: PushNotificationHistory) -> dict:
    """
    格式化推送历史记录

    Args:
        history: 推送历史记录

    Returns:
        格式化后的字典
    """
    return {
        "id": history.id,
        "chat_id": history.chat_id,
        "user_id": history.user_id,
        "agent_id": history.agent_id,
        "stage": history.stage,
        "message_content": (
            history.message_content[:200] + "..."
            if history.message_content and len(history.message_content) > 200
            else history.message_content
        ),
        "sent_at": history.sent_at.isoformat() if history.sent_at else None,
        "read_at": history.read_at.isoformat() if history.read_at else None,
        "created_at": history.created_at.isoformat() if history.created_at else None,
    }


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="推送历史查询工具")
    parser.add_argument(
        "--chat-id",
        type=str,
        help="聊天ID",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="用户ID",
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        help="Agent ID",
    )
    parser.add_argument(
        "--stage",
        type=str,
        choices=["10min", "30min", "2h", "24h", "48h"],
        help="推送阶段",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="返回数量限制（默认: 100）",
    )

    args = parser.parse_args()

    # 检查是否至少提供了一个查询条件
    if not args.chat_id and not args.user_id and not args.agent_id:
        logger.error("请至少提供一个查询条件: --chat-id, --user-id 或 --agent-id")
        parser.print_help()
        return 1

    # 初始化日志
    init_logger()

    try:
        async with AsyncSessionLocal() as db:
            history_list = await get_push_history(
                db=db,
                chat_id=args.chat_id,
                user_id=args.user_id,
                agent_id=args.agent_id,
                stage=args.stage,
                limit=args.limit,
            )

            logger.info("=" * 60)
            logger.info("推送历史查询结果")
            logger.info("=" * 60)

            if args.chat_id:
                logger.info(f"聊天ID: {args.chat_id}")
            if args.user_id:
                logger.info(f"用户ID: {args.user_id}")
            if args.agent_id:
                logger.info(f"Agent ID: {args.agent_id}")
            if args.stage:
                logger.info(f"阶段: {args.stage}")

            logger.info(f"找到记录数: {len(history_list)}")
            logger.info("")

            if not history_list:
                logger.info("没有找到推送历史记录")
                logger.info("=" * 60)
                return 0

            # 按阶段分组统计
            stage_stats = {}
            for history in history_list:
                stage = history.stage
                if stage not in stage_stats:
                    stage_stats[stage] = 0
                stage_stats[stage] += 1

            logger.info("阶段统计:")
            for stage, count in sorted(stage_stats.items()):
                logger.info(f"  {stage}: {count} 条")
            logger.info("")

            # 显示详细记录
            logger.info("推送历史记录:")
            for i, history in enumerate(history_list, 1):
                formatted = await format_push_history(history)
                logger.info(f"  [{i}] {formatted['stage']} - {formatted['sent_at']}")
                logger.info(f"      ID: {formatted['id']}")
                logger.info(f"      Chat ID: {formatted['chat_id']}")
                logger.info(f"      User ID: {formatted['user_id']}")
                logger.info(f"      Agent ID: {formatted['agent_id']}")
                logger.info(f"      已读时间: {formatted.get('read_at', '未读')}")
                if formatted["message_content"]:
                    logger.info(
                        f"      消息内容: {formatted['message_content'][:100]}..."
                        if len(formatted["message_content"]) > 100
                        else f"      消息内容: {formatted['message_content']}"
                    )
                logger.info("")

            logger.info("=" * 60)

            return 0

    except KeyboardInterrupt:
        logger.info("用户中断")
        return 1
    except Exception as e:
        logger.error(f"查询失败: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    import asyncio

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
