"""
推送流程测试脚本

用于手动触发推送测试，支持指定 chat_id 或 user_id。

使用方法:
    # Dry run 模式（推荐，不会实际发送）
    python scripts/fcm/test_push_flow.py --chat-id CHAT_ID --stage 10min --dry-run

    # 真实发送模式
    python scripts/fcm/test_push_flow.py --chat-id CHAT_ID --stage 10min

    # 通过 user_id 测试（会测试该用户的所有活跃聊天）
    python scripts/fcm/test_push_flow.py --user-id USER_ID --stage 10min --dry-run

    # 测试所有阶段
    python scripts/fcm/test_push_flow.py --chat-id CHAT_ID --dry-run
"""

import argparse
import datetime
import sys
from pathlib import Path
from typing import List, Optional

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import global_config_loaded_from_config_yaml
from app.core.logging import init_logger
from app.db.session import AsyncSessionLocal
from app.external_services.firebase import init_firebase
from app.models import Chat
from app.models.agent import Agent
from app.models.user import User
from app.services import agent_service, push_notification_service
from app.services.chat_service import generate_session_id
from app.services.push_notification_service import get_last_user_message_time


async def test_push_for_chat(
    db: AsyncSession,
    chat_id: str,
    stage: str,
    dry_run: bool = True,
) -> dict:
    """
    测试单个聊天的推送流程

    Args:
        db: 数据库会话
        chat_id: 聊天ID
        stage: 推送阶段
        dry_run: 是否为测试模式

    Returns:
        测试结果字典
    """
    result = {
        "chat_id": chat_id,
        "stage": stage,
        "dry_run": dry_run,
        "success": False,
        "error": None,
        "steps": [],
    }

    try:
        # 1. 检查聊天是否存在
        stmt = select(Chat).where(Chat.id == chat_id)
        query_result = await db.execute(stmt)
        chat = query_result.scalar_one_or_none()

        if not chat:
            result["error"] = "聊天不存在"
            result["steps"].append("❌ 聊天不存在")
            return result

        result["steps"].append("✅ 聊天存在")

        # 2. 检查基本条件
        if not chat.is_active:
            result["error"] = "Chat.is_active 为 False"
            result["steps"].append("❌ Chat.is_active 为 False")
            return result

        result["steps"].append("✅ Chat.is_active 为 True")

        # 3. 获取配置
        config = global_config_loaded_from_config_yaml.push_notification

        # 检查阶段配置（支持 minutes 和 hours）
        time_delta_minutes = config.intervals.get(stage)
        time_delta_hours = None
        if not time_delta_minutes and config.no_chat_intervals:
            time_delta_hours = config.no_chat_intervals.get(stage)

        if not time_delta_minutes and not time_delta_hours:
            result["error"] = f"无效的推送阶段: {stage}"
            result["steps"].append(f"❌ 无效的推送阶段: {stage}")
            return result

        if time_delta_minutes:
            result["steps"].append(
                f"✅ 推送阶段配置: {stage} ({time_delta_minutes} 分钟)"
            )
        else:
            result["steps"].append(
                f"✅ 推送阶段配置: {stage} ({time_delta_hours} 小时)"
            )

        # 4. 获取最后消息时间
        session_id = generate_session_id(chat_id)
        last_message_time = await get_last_user_message_time(session_id)

        if not last_message_time:
            result["error"] = "没有用户消息"
            result["steps"].append("❌ 没有用户消息")
            return result

        result["steps"].append(f"✅ 最后消息时间: {last_message_time.isoformat()}")

        # 5. 检查是否已发送过推送
        has_sent = await push_notification_service.has_sent_push_for_stage(
            db, chat_id, stage, "recent_chat", last_message_time
        )

        if has_sent and not dry_run:
            result["error"] = f"已发送过 {stage} 阶段的推送"
            result["steps"].append(f"⚠️  已发送过 {stage} 阶段的推送")
            if not dry_run:
                return result

        if not has_sent:
            result["steps"].append(f"✅ 未发送过 {stage} 阶段的推送")
        else:
            result["steps"].append(f"⚠️  已发送过推送（dry-run 模式下继续）")

        # 6. 获取 Agent 数据
        agent_data = await agent_service.get_agent_for_chat(db, agent_id=chat.agent_id)
        if not agent_data:
            result["error"] = "Agent数据未找到"
            result["steps"].append("❌ Agent数据未找到")
            return result

        result["steps"].append(
            f"✅ Agent数据获取成功: {agent_data.get('name', '未知')}"
        )

        # 7. 生成 Agent 消息
        message_content = await push_notification_service.generate_agent_message(
            db=db,
            user_id=chat.user_id,
            agent_id=chat.agent_id,
            stage=stage,
            push_type="recent_chat",
            agent_data=agent_data,
            chat_id=chat.id,
        )

        if not message_content:
            result["error"] = "生成消息失败"
            result["steps"].append("❌ 生成消息失败")
            return result

        result["steps"].append(f"✅ 消息生成成功: {message_content[:50]}...")
        result["message_content"] = message_content

        # 8. 获取 Agent 名称和头像
        agent_name = agent_data.get("name") or "角色"
        agent_avatar_url = await push_notification_service.get_agent_avatar_url(
            agent_data
        )

        result["steps"].append(f"✅ Agent信息: {agent_name}")
        if agent_avatar_url:
            result["steps"].append(f"✅ Agent头像: {agent_avatar_url[:50]}...")

        # 9. 发送推送（如果是 dry_run，只模拟）
        if dry_run:
            result["steps"].append("🔍 [DRY RUN] 模拟发送推送...")
            result["steps"].append(
                f"  - 标题: {agent_name}",
            )
            result["steps"].append(
                f"  - 内容: {message_content[:100]}...",
            )
            result["steps"].append(
                f"  - 数据: chat_id={chat.id}, agent_id={chat.agent_id}, stage={stage}",
            )
            if agent_avatar_url:
                result["steps"].append(f"  - 图片: {agent_avatar_url[:50]}...")
            result["steps"].append("✅ [DRY RUN] 推送模拟成功")
            result["success"] = True
        else:
            # 实际发送推送
            sent_at = datetime.datetime.now(datetime.timezone.utc)
            success = await push_notification_service.send_push_notification(
                db=db,
                user_id=chat.user_id,
                agent_id=chat.agent_id,
                agent_name=agent_name,
                message_content=message_content,
                stage=stage,
                agent_avatar_url=agent_avatar_url,
                chat_id=chat.id,
            )

            if success:
                # 记录推送历史
                await push_notification_service.record_push_history(
                    db=db,
                    user_id=chat.user_id,
                    agent_id=chat.agent_id,
                    stage=stage,
                    push_type="recent_chat",
                    message_content=message_content,
                    sent_at=sent_at,
                    chat_id=chat.id,
                )
                result["steps"].append("✅ 推送发送成功")
                result["steps"].append(f"✅ 推送历史已记录: {sent_at.isoformat()}")
                result["success"] = True
            else:
                result["error"] = "推送发送失败"
                result["steps"].append("❌ 推送发送失败")

    except Exception as e:
        logger.error(f"测试推送流程失败: {str(e)}")
        result["error"] = str(e)
        result["steps"].append(f"❌ 错误: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())

    return result


async def test_push_for_user(
    db: AsyncSession,
    user_id: str,
    stage: str,
    dry_run: bool = True,
) -> dict:
    """
    测试用户的最近聊天推送流程（以用户为维度，选择最新对话的角色）

    Args:
        db: 数据库会话
        user_id: 用户ID
        stage: 推送阶段
        dry_run: 是否为测试模式

    Returns:
        测试结果字典
    """
    result = {
        "user_id": user_id,
        "stage": stage,
        "dry_run": dry_run,
        "has_recent_chat": False,
        "recent_chat_id": None,
        "success": False,
        "error": None,
        "steps": [],
    }

    try:
        # 1. 检查用户是否存在
        user_stmt = select(User).where(User.id == user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            result["error"] = f"用户 {user_id} 不存在"
            result["steps"].append("❌ 用户不存在")
            return result

        result["steps"].append("✅ 用户存在")

        # 2. 获取用户的最近聊天（与实际推送逻辑一致）
        recent_chat_data = await push_notification_service.get_user_recent_chat(
            db, user_id
        )

        if not recent_chat_data:
            result["error"] = f"用户 {user_id} 没有最近聊天（没有用户消息）"
            result["steps"].append("❌ 用户没有最近聊天（没有用户消息）")
            return result

        chat, last_message_time = recent_chat_data
        result["has_recent_chat"] = True
        result["recent_chat_id"] = chat.id

        result["steps"].append(
            f"✅ 找到最近聊天: {chat.id} (最后消息时间: {last_message_time.isoformat()})"
        )

        # 3. 测试最近聊天的推送流程
        logger.info(f"测试用户 {user_id} 的最近聊天: {chat.id}")
        chat_result = await test_push_for_chat(db, chat.id, stage, dry_run)

        # 合并结果
        result["steps"].extend(chat_result.get("steps", []))
        result["success"] = chat_result.get("success", False)
        result["error"] = chat_result.get("error")
        result["message_content"] = chat_result.get("message_content")

    except Exception as e:
        logger.error(f"测试用户推送流程失败: {str(e)}")
        result["error"] = str(e)
        result["steps"].append(f"❌ 错误: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())

    return result


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="推送流程测试工具")
    parser.add_argument(
        "--chat-id",
        type=str,
        help="聊天ID（与 --user-id 二选一）",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="用户ID（与 --chat-id 二选一，会测试该用户的所有活跃聊天）",
    )
    parser.add_argument(
        "--stage",
        type=str,
        choices=["10min", "30min", "2h", "24h", "48h"],
        default="10min",
        help="推送阶段（默认: 10min）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry run 模式（默认启用，不会实际发送）",
    )
    parser.add_argument(
        "--real",
        action="store_true",
        help="真实发送模式（会实际发送消息）",
    )

    args = parser.parse_args()

    # 初始化日志
    init_logger()

    # 初始化 Firebase
    try:
        init_firebase()
        logger.info("Firebase 初始化成功")
    except Exception as e:
        logger.error(f"Firebase 初始化失败: {str(e)}")
        return 1

    # 确定是否使用 dry_run
    dry_run = not args.real if args.real else args.dry_run

    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN 模式：仅模拟推送流程，不会实际发送")
        logger.info("=" * 60)
    else:
        logger.warning("=" * 60)
        logger.warning("真实发送模式：消息将被实际发送到设备")
        logger.warning("=" * 60)

    if not args.chat_id and not args.user_id:
        logger.error("请提供 --chat-id 或 --user-id")
        parser.print_help()
        return 1

    try:
        async with AsyncSessionLocal() as db:
            if args.chat_id:
                # 测试单个聊天
                result = await test_push_for_chat(db, args.chat_id, args.stage, dry_run)

                logger.info("=" * 60)
                logger.info("推送流程测试结果")
                logger.info("=" * 60)
                logger.info(f"聊天ID: {result['chat_id']}")
                logger.info(f"阶段: {result['stage']}")
                logger.info(f"模式: {'DRY RUN' if result['dry_run'] else 'REAL'}")
                logger.info("")

                logger.info("执行步骤:")
                for step in result["steps"]:
                    logger.info(f"  {step}")

                logger.info("")
                if result["success"]:
                    logger.success("✅ 测试成功")
                else:
                    logger.error(f"❌ 测试失败: {result.get('error', '未知错误')}")

                logger.info("=" * 60)

                return 0 if result["success"] else 1

            elif args.user_id:
                # 测试用户的最近聊天推送（以用户为维度）
                result = await test_push_for_user(db, args.user_id, args.stage, dry_run)

                logger.info("=" * 60)
                logger.info("推送流程测试结果（用户维度）")
                logger.info("=" * 60)
                logger.info(f"用户ID: {result['user_id']}")
                logger.info(f"阶段: {result['stage']}")
                logger.info(f"模式: {'DRY RUN' if result['dry_run'] else 'REAL'}")
                logger.info("")

                if result.get("recent_chat_id"):
                    logger.info(f"最近聊天ID: {result['recent_chat_id']}")
                    logger.info("")

                logger.info("执行步骤:")
                for step in result.get("steps", []):
                    logger.info(f"  {step}")

                logger.info("")
                if result["success"]:
                    logger.success("✅ 测试成功")
                else:
                    logger.error(f"❌ 测试失败: {result.get('error', '未知错误')}")

                logger.info("=" * 60)

                return 0 if result["success"] else 1

    except KeyboardInterrupt:
        logger.info("用户中断")
        return 1
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    import asyncio

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
