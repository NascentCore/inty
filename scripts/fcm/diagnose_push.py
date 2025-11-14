"""
推送诊断脚本

用于诊断推送条件，检查为什么推送未触发。

使用方法:
    # 诊断聊天推送
    python scripts/fcm/diagnose_push.py --chat-id CHAT_ID
    python scripts/fcm/diagnose_push.py --chat-id CHAT_ID --stage 10min

    # 诊断用户推送（无聊天或最近聊天）
    python scripts/fcm/diagnose_push.py --user-id USER_ID
    python scripts/fcm/diagnose_push.py --user-id USER_ID --push-type no_chat
"""

import argparse
import datetime
import sys
from pathlib import Path

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import global_config_loaded_from_config_yaml
from app.core.logging import init_logger
from app.db.session import AsyncSessionLocal
from app.models import Chat, PushNotificationHistory
from app.models.agent import Agent
from app.models.user import DeviceToken, User
from app.services import push_notification_service
from app.services.chat_service import generate_session_id


async def diagnose_chat_push(db: AsyncSession, chat_id: str, stage: str = None) -> dict:
    """
    诊断聊天推送条件

    Args:
        db: 数据库会话
        chat_id: 聊天ID
        stage: 推送阶段（可选，如果提供则只检查该阶段）

    Returns:
        诊断结果字典
    """
    result = {
        "chat_id": chat_id,
        "stage": stage,
        "chat_exists": False,
        "chat_is_active": None,
        "agent_exists": False,
        "agent_deleted": None,
        "user_exists": False,
        "user_deleted": None,
        "has_user_messages": False,
        "last_user_message_time": None,
        "threshold_time": None,
        "time_meets_threshold": None,
        "push_history": {},
        "diagnosis": [],
    }

    try:
        # 1. 检查聊天是否存在
        stmt = select(Chat).where(Chat.id == chat_id)
        query_result = await db.execute(stmt)
        chat = query_result.scalar_one_or_none()

        if not chat:
            result["diagnosis"].append("❌ 聊天不存在")
            return result

        result["chat_exists"] = True
        result["chat_is_active"] = chat.is_active
        result["user_id"] = chat.user_id  # 保存 user_id 供后续使用

        # 2. 检查 Agent 是否存在且未被删除
        agent_stmt = select(Agent).where(Agent.id == chat.agent_id)
        agent_result = await db.execute(agent_stmt)
        agent = agent_result.scalar_one_or_none()

        result["agent_exists"] = agent is not None
        result["agent_deleted"] = agent.deleted_at is not None if agent else None

        # 3. 检查 User 是否存在且未被删除
        user_stmt = select(User).where(User.id == chat.user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        result["user_exists"] = user is not None
        result["user_deleted"] = user.deleted_at is not None if user else None

        # 4. 检查基本条件
        if not chat.is_active:
            result["diagnosis"].append("❌ Chat.is_active 为 False")

        if not agent:
            result["diagnosis"].append("❌ Agent 不存在")
        elif agent.deleted_at:
            result["diagnosis"].append("❌ Agent 已被删除")

        if not user:
            result["diagnosis"].append("❌ User 不存在")
        elif user.deleted_at:
            result["diagnosis"].append("❌ User 已被删除")

        # 5. 获取配置
        config = global_config_loaded_from_config_yaml.push_notification
        # 支持所有阶段（10min, 30min, 2h, 24h, 48h）
        all_stages = list(config.intervals.keys()) if config.intervals else []
        if config.no_chat_intervals:
            all_stages.extend(config.no_chat_intervals.keys())
        stages_to_check = [stage] if stage else all_stages

        # 6. 获取会话ID
        session_id = generate_session_id(chat.id)

        # 7. 检查用户消息
        last_user_message_time = (
            await push_notification_service.get_last_user_message_time(session_id)
        )

        if not last_user_message_time:
            result["diagnosis"].append("❌ 没有用户消息（只有AI消息或开场白）")
            return result

        result["has_user_messages"] = True
        result["last_user_message_time"] = last_user_message_time.isoformat()

        # 8. 检查每个阶段的推送条件
        for check_stage in stages_to_check:
            # 检查阶段配置（支持 minutes 和 hours）
            time_delta_minutes = (
                config.intervals.get(check_stage) if config.intervals else None
            )
            time_delta_hours = None
            if not time_delta_minutes and config.no_chat_intervals:
                time_delta_hours = config.no_chat_intervals.get(check_stage)

            if not time_delta_minutes and not time_delta_hours:
                continue

            # 计算时间阈值
            if time_delta_minutes:
                threshold_time = datetime.datetime.now(
                    datetime.timezone.utc
                ) - datetime.timedelta(minutes=time_delta_minutes)
            else:
                threshold_time = datetime.datetime.now(
                    datetime.timezone.utc
                ) - datetime.timedelta(hours=time_delta_hours)

            # 检查是否已发送过推送（需要传递 last_message_time）
            has_sent = await push_notification_service.has_sent_push_for_stage(
                db, chat_id, check_stage, "recent_chat", last_user_message_time
            )

            # 检查时间是否匹配
            time_meets_threshold = last_user_message_time <= threshold_time

            # 查询推送历史
            stmt = select(PushNotificationHistory).where(
                and_(
                    PushNotificationHistory.chat_id == chat_id,
                    PushNotificationHistory.stage == check_stage,
                )
            )
            history_result = await db.execute(stmt)
            history = history_result.scalar_one_or_none()

            stage_result = {
                "stage": check_stage,
                "time_delta_minutes": time_delta_minutes,
                "time_delta_hours": time_delta_hours,
                "threshold_time": threshold_time.isoformat(),
                "time_meets_threshold": time_meets_threshold,
                "has_sent_push": has_sent,
                "push_history": None,
            }

            if history:
                stage_result["push_history"] = {
                    "id": history.id,
                    "sent_at": history.sent_at.isoformat(),
                    "message_content": (
                        history.message_content[:100] + "..."
                        if history.message_content
                        and len(history.message_content) > 100
                        else history.message_content
                    ),
                }

            result["push_history"][check_stage] = stage_result

            # 诊断该阶段
            if has_sent:
                result["diagnosis"].append(
                    f"⚠️  阶段 {check_stage}: 已发送过推送（{history.sent_at.isoformat() if history else '未知'}）"
                )
            elif not time_meets_threshold:
                time_diff = (
                    threshold_time - last_user_message_time
                ).total_seconds() / 60
                result["diagnosis"].append(
                    f"⏳ 阶段 {check_stage}: 时间未达到阈值（还需等待约 {abs(time_diff):.1f} 分钟）"
                )
            else:
                result["diagnosis"].append(
                    f"✅ 阶段 {check_stage}: 满足推送条件（但可能不在 batch_size 范围内）"
                )

        # 9. 检查用户是否会被查询到（使用与实际查询逻辑相同的方式）
        # 实际查询逻辑：分页查询用户，然后获取每个用户的最近聊天
        user_id = result.get("user_id") or chat.user_id

        if user_id:
            # 检查用户是否有 device_token（实际查询会 join DeviceToken）
            device_token_stmt = select(DeviceToken).where(
                DeviceToken.user_id == user_id
            )
            device_token_result = await db.execute(device_token_stmt)
            has_device_token = device_token_result.scalar_one_or_none() is not None

            if not has_device_token:
                result["diagnosis"].append(
                    "❌ 用户没有 device_token，不会被查询到（实际查询会 join DeviceToken）"
                )
            else:
                # 检查这个聊天是否是用户的最近聊天
                recent_chat_data = await push_notification_service.get_user_recent_chat(
                    db, user_id
                )
                if recent_chat_data:
                    recent_chat, _ = recent_chat_data
                    if recent_chat.id == chat_id:
                        result["diagnosis"].append("✅ 这是用户的最近聊天，会被查询到")
                    else:
                        result["diagnosis"].append(
                            f"⚠️  这不是用户的最近聊天（最近聊天ID: {recent_chat.id}），不会被推送"
                        )
                else:
                    result["diagnosis"].append("⚠️  无法获取用户的最近聊天信息")
        else:
            result["diagnosis"].append("⚠️  无法获取用户ID，无法检查是否会被查询到")

        if not result["diagnosis"]:
            result["diagnosis"].append("✅ 所有检查项通过，应该可以触发推送")

    except Exception as e:
        logger.error(f"诊断失败: {str(e)}")
        result["error"] = str(e)
        result["diagnosis"].append(f"❌ 诊断过程出错: {str(e)}")

    return result


async def diagnose_user_push(
    db: AsyncSession, user_id: str, push_type: str = None
) -> dict:
    """
    诊断用户推送条件（无聊天或最近聊天）

    Args:
        db: 数据库会话
        user_id: 用户ID
        push_type: 推送类型（可选，"no_chat" 或 "recent_chat"）

    Returns:
        诊断结果字典
    """
    result = {
        "user_id": user_id,
        "push_type": push_type,
        "user_exists": False,
        "has_device_token": False,
        "has_active_chats": False,
        "recent_chat": None,
        "popular_agent": None,
        "no_chat_push_history": {},
        "recent_chat_push_history": {},
        "diagnosis": [],
    }

    try:
        # 1. 检查用户是否存在
        stmt = select(User).where(User.id == user_id)
        query_result = await db.execute(stmt)
        user = query_result.scalar_one_or_none()

        if not user:
            result["diagnosis"].append("❌ 用户不存在")
            return result

        result["user_exists"] = True

        # 2. 检查是否有 device_token
        device_token_stmt = select(DeviceToken).where(DeviceToken.user_id == user_id)
        device_token_result = await db.execute(device_token_stmt)
        device_token = device_token_result.scalar_one_or_none()
        result["has_device_token"] = device_token is not None

        if not result["has_device_token"]:
            result["diagnosis"].append("❌ 用户没有注册 device_token，无法接收推送")

        # 3. 检查是否有活跃聊天
        chat_stmt = (
            select(Chat)
            .join(Agent, Chat.agent_id == Agent.id)
            .where(
                and_(
                    Chat.user_id == user_id,
                    Chat.is_active == True,
                    Agent.deleted_at.is_(None),
                )
            )
        )
        chat_result = await db.execute(chat_stmt)
        chats = chat_result.scalars().all()
        result["has_active_chats"] = len(chats) > 0

        # 4. 获取最近聊天（如果有）
        if result["has_active_chats"]:
            recent_chat_data = await push_notification_service.get_user_recent_chat(
                db, user_id
            )
            if recent_chat_data:
                chat, last_message_time = recent_chat_data
                result["recent_chat"] = {
                    "chat_id": chat.id,
                    "agent_id": chat.agent_id,
                    "last_message_time": last_message_time.isoformat(),
                }

        # 5. 获取热门角色（用于无聊天推送）
        popular_agent = await push_notification_service.get_popular_agent(db, limit=1)
        if popular_agent:
            result["popular_agent"] = {
                "agent_id": popular_agent.id,
                "name": popular_agent.name,
            }

        # 6. 检查推送历史
        config = global_config_loaded_from_config_yaml.push_notification

        # 检查无聊天推送历史
        if not push_type or push_type == "no_chat":
            if config.no_chat_intervals:
                for stage, hours in config.no_chat_intervals.items():
                    has_sent = (
                        await push_notification_service.has_sent_push_for_user_stage(
                            db, user_id, stage, "no_chat"
                        )
                    )
                    result["no_chat_push_history"][stage] = {
                        "stage": stage,
                        "time_delta_hours": hours,
                        "has_sent_push": has_sent,
                    }

        # 检查最近聊天推送历史
        if not push_type or push_type == "recent_chat":
            if result["recent_chat"]:
                # 重新获取最近聊天数据以获取 datetime 对象
                recent_chat_data = await push_notification_service.get_user_recent_chat(
                    db, user_id
                )
                if recent_chat_data:
                    chat, last_message_time = recent_chat_data
                    # 检查所有阶段（10min, 30min, 2h, 24h, 48h）
                    all_stages = (
                        list(config.intervals.keys()) if config.intervals else []
                    )
                    if config.no_chat_intervals:
                        all_stages.extend(config.no_chat_intervals.keys())
                    for stage in all_stages:
                        has_sent = (
                            await push_notification_service.has_sent_push_for_stage(
                                db, chat.id, stage, "recent_chat", last_message_time
                            )
                        )
                        result["recent_chat_push_history"][stage] = {
                            "stage": stage,
                            "has_sent_push": has_sent,
                        }

        # 7. 诊断结论
        if not result["has_device_token"]:
            result["diagnosis"].append("❌ 用户没有 device_token，无法接收推送")

        if push_type == "no_chat" or not push_type:
            if result["has_active_chats"]:
                result["diagnosis"].append("⚠️  用户有活跃聊天，不会触发无聊天推送")
            elif not result["popular_agent"]:
                result["diagnosis"].append("❌ 没有找到热门角色，无法进行无聊天推送")
            else:
                for stage, history in result["no_chat_push_history"].items():
                    if history["has_sent_push"]:
                        result["diagnosis"].append(f"⚠️  无聊天推送 {stage}: 已发送过")
                    else:
                        result["diagnosis"].append(f"✅ 无聊天推送 {stage}: 满足条件")

        if push_type == "recent_chat" or not push_type:
            if not result["has_active_chats"]:
                result["diagnosis"].append("⚠️  用户没有活跃聊天，不会触发最近聊天推送")
            elif not result["recent_chat"]:
                result["diagnosis"].append("⚠️  用户有聊天但没有用户消息，不会触发推送")
            else:
                for stage, history in result["recent_chat_push_history"].items():
                    if history["has_sent_push"]:
                        result["diagnosis"].append(f"⚠️  最近聊天推送 {stage}: 已发送过")
                    else:
                        result["diagnosis"].append(f"✅ 最近聊天推送 {stage}: 满足条件")

        if not result["diagnosis"]:
            result["diagnosis"].append("✅ 所有检查项通过")

    except Exception as e:
        logger.error(f"诊断失败: {str(e)}")
        result["error"] = str(e)
        result["diagnosis"].append(f"❌ 诊断过程出错: {str(e)}")

    return result


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="推送诊断工具")
    parser.add_argument(
        "--chat-id",
        type=str,
        help="聊天ID（与 --user-id 二选一）",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="用户ID（与 --chat-id 二选一）",
    )
    parser.add_argument(
        "--stage",
        type=str,
        choices=["10min", "30min", "2h", "24h", "48h"],
        help="推送阶段（可选）",
    )
    parser.add_argument(
        "--push-type",
        type=str,
        choices=["no_chat", "recent_chat"],
        help="推送类型（可选，仅用于 --user-id）",
    )

    args = parser.parse_args()

    if not args.chat_id and not args.user_id:
        parser.error("请提供 --chat-id 或 --user-id")

    if args.chat_id and args.user_id:
        parser.error("不能同时提供 --chat-id 和 --user-id")

    # 初始化日志
    init_logger()

    try:
        async with AsyncSessionLocal() as db:
            if args.chat_id:
                result = await diagnose_chat_push(db, args.chat_id, args.stage)

                # 输出诊断结果
                logger.info("=" * 60)
                logger.info("推送诊断结果（聊天推送）")
                logger.info("=" * 60)
                logger.info(f"聊天ID: {result['chat_id']}")
                logger.info(f"阶段: {result['stage'] or '全部'}")
                logger.info("")

                logger.info("基本信息:")
                logger.info(f"  聊天存在: {result['chat_exists']}")
                logger.info(f"  Chat.is_active: {result['chat_is_active']}")
                logger.info(f"  Agent存在: {result['agent_exists']}")
                logger.info(f"  Agent已删除: {result['agent_deleted']}")
                logger.info(f"  User存在: {result['user_exists']}")
                logger.info(f"  User已删除: {result['user_deleted']}")
                logger.info("")

                if result["has_user_messages"]:
                    logger.info("用户消息:")
                    logger.info(
                        f"  最后用户消息时间: {result['last_user_message_time']}"
                    )
                    logger.info("")

                if result["push_history"]:
                    logger.info("推送阶段检查:")
                    for stage, stage_result in result["push_history"].items():
                        logger.info(f"  阶段 {stage}:")
                        logger.info(
                            f"    时间阈值（分钟）: {stage_result['time_delta_minutes']}"
                        )
                        logger.info(f"    阈值时间: {stage_result['threshold_time']}")
                        logger.info(
                            f"    时间是否满足: {stage_result['time_meets_threshold']}"
                        )
                        logger.info(f"    已发送推送: {stage_result['has_sent_push']}")
                        if stage_result["push_history"]:
                            logger.info(
                                f"    推送历史: {stage_result['push_history']['sent_at']}"
                            )
                        logger.info("")

                logger.info("诊断结论:")
                for diagnosis in result["diagnosis"]:
                    logger.info(f"  {diagnosis}")

                logger.info("=" * 60)

                return 0

            elif args.user_id:
                result = await diagnose_user_push(db, args.user_id, args.push_type)

                # 输出诊断结果
                logger.info("=" * 60)
                logger.info("推送诊断结果（用户推送）")
                logger.info("=" * 60)
                logger.info(f"用户ID: {result['user_id']}")
                logger.info(f"推送类型: {result['push_type'] or '全部'}")
                logger.info("")

                logger.info("基本信息:")
                logger.info(f"  用户存在: {result['user_exists']}")
                logger.info(f"  有 device_token: {result['has_device_token']}")
                logger.info(f"  有活跃聊天: {result['has_active_chats']}")
                logger.info("")

                if result["recent_chat"]:
                    logger.info("最近聊天:")
                    logger.info(f"  聊天ID: {result['recent_chat']['chat_id']}")
                    logger.info(f"  Agent ID: {result['recent_chat']['agent_id']}")
                    logger.info(
                        f"  最后消息时间: {result['recent_chat']['last_message_time']}"
                    )
                    logger.info("")

                if result["popular_agent"]:
                    logger.info("热门角色:")
                    logger.info(f"  Agent ID: {result['popular_agent']['agent_id']}")
                    logger.info(f"  名称: {result['popular_agent']['name']}")
                    logger.info("")

                if result["no_chat_push_history"]:
                    logger.info("无聊天推送历史:")
                    for stage, history in result["no_chat_push_history"].items():
                        logger.info(f"  {stage}:")
                        logger.info(
                            f"    时间阈值（小时）: {history['time_delta_hours']}"
                        )
                        logger.info(f"    已发送推送: {history['has_sent_push']}")
                    logger.info("")

                if result["recent_chat_push_history"]:
                    logger.info("最近聊天推送历史:")
                    for stage, history in result["recent_chat_push_history"].items():
                        logger.info(f"  {stage}:")
                        logger.info(f"    已发送推送: {history['has_sent_push']}")
                    logger.info("")

                logger.info("诊断结论:")
                for diagnosis in result["diagnosis"]:
                    logger.info(f"  {diagnosis}")

                logger.info("=" * 60)

                return 0

    except KeyboardInterrupt:
        logger.info("用户中断")
        return 1
    except Exception as e:
        logger.error(f"诊断失败: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    import asyncio

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
