"""
Feedback 推送测试脚本

用于手动向用户发送 feedback 推送通知，用于测试 feedback 推送功能。

使用方法:
    # Dry run 模式（推荐，不会实际发送）
    python scripts/fcm/test_feedback_push.py --user-id USER_ID --dry-run

    # 真实发送模式
    python scripts/fcm/test_feedback_push.py --user-id USER_ID --real

    # 直接通过 token 发送（dry run）
    python scripts/fcm/test_feedback_push.py --token FCM_TOKEN --dry-run
"""

import argparse
import asyncio
import sys
from pathlib import Path

from firebase_admin import messaging
from firebase_admin.exceptions import InvalidArgumentError
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import global_config_loaded_from_config_yaml
from app.core.logging import init_logger
from app.db.session import AsyncSessionLocal
from app.external_services.firebase import init_firebase
from app.services import notification_service, user_service


def validate_fcm_token(token: str) -> bool:
    """
    验证 FCM token 格式

    Args:
        token: FCM token 字符串

    Returns:
        是否为有效格式
    """
    if not token:
        return False

    # FCM token 通常是长字符串，长度通常在 100-200 字符之间
    if len(token) < 50 or len(token) > 500:
        logger.warning(f"Token 长度异常: {len(token)} 字符")
        return False

    return True


async def test_feedback_push_by_token(
    token: str,
    dry_run: bool = True,
) -> dict:
    """
    通过 token 测试 feedback 推送

    Args:
        token: FCM device token
        dry_run: 是否为测试模式

    Returns:
        测试结果字典
    """
    result = {
        "token": token[:20] + "..." if len(token) > 20 else token,
        "dry_run": dry_run,
        "success": False,
        "message_id": None,
        "error": None,
        "error_type": None,
    }

    try:
        # 验证 token 格式
        if not validate_fcm_token(token):
            result["error"] = "Token 格式无效"
            result["error_type"] = "ValidationError"
            return result

        # 构建数据消息（纯 data，无 notification）
        data = {"type": "feedback_request"}
        data_str = {k: str(v) for k, v in data.items()}

        message = messaging.Message(
            token=token,
            data=data_str,
            android=messaging.AndroidConfig(priority="high"),
        )

        # 发送消息
        mode = "[DRY RUN]" if dry_run else "[REAL]"
        logger.info(f"{mode} 开始发送 Feedback 推送到 token: {token[:20]}...")

        message_id = messaging.send(message, dry_run=dry_run)

        result["success"] = True
        result["message_id"] = message_id

        if dry_run:
            logger.success(
                f"[DRY RUN] Feedback 推送验证成功！message_id={message_id}, data={data}"
            )
        else:
            logger.success(
                f"[REAL] Feedback 推送发送成功！message_id={message_id}, data={data}"
            )

    except InvalidArgumentError as e:
        result["error"] = str(e)
        result["error_type"] = "InvalidArgumentError"
        logger.error(f"FCM 参数错误: {str(e)}")
    except messaging.UnregisteredError:
        result["error"] = "Token 未注册或已失效"
        result["error_type"] = "UnregisteredError"
        logger.warning(f"Token 未注册: {token[:20]}...")
    except messaging.SenderIdMismatchError:
        result["error"] = "Sender ID 不匹配"
        result["error_type"] = "SenderIdMismatchError"
        logger.error("Sender ID 不匹配，请检查 Firebase 配置")
    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
        logger.error(f"FCM 发送失败: {type(e).__name__}: {str(e)}")

    return result


async def test_feedback_push_by_user_id(
    user_id: str,
    dry_run: bool = True,
) -> dict:
    """
    通过用户 ID 测试 feedback 推送

    Args:
        user_id: 用户 ID
        dry_run: 是否为测试模式

    Returns:
        测试结果字典
    """
    result = {
        "user_id": user_id,
        "dry_run": dry_run,
        "success": False,
        "error": None,
    }

    try:
        async with AsyncSessionLocal() as db:
            mode = "[DRY RUN]" if dry_run else "[REAL]"
            logger.info(f"{mode} 测试 Feedback 推送，用户 ID: {user_id}")

            # 使用 send_fcm_data_only 发送纯数据消息
            data = {"type": "feedback_request"}
            success = await notification_service.send_fcm_data_only(
                db=db,
                user_ids=[user_id],
                data=data,
                dry_run=dry_run,
            )

            result["success"] = success

            if success:
                logger.success(f"{mode} Feedback 推送测试成功！")
            else:
                logger.error(f"{mode} Feedback 推送测试失败")
                result["error"] = "发送失败，请检查日志"

    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
        logger.error(f"Feedback 推送测试失败: {type(e).__name__}: {str(e)}")

    return result


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Feedback 推送测试工具")
    parser.add_argument(
        "--token",
        type=str,
        help="FCM device token（直接测试单个 token）",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="用户 ID（从数据库获取 token 测试）",
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
        logger.info("DRY RUN 模式：仅验证消息格式，不会实际发送")
        logger.info("=" * 60)
    else:
        logger.warning("=" * 60)
        logger.warning("真实发送模式：消息将被实际发送到设备")
        logger.warning("=" * 60)

    try:
        if args.user_id:
            # 通过用户 ID 测试
            result = await test_feedback_push_by_user_id(
                user_id=args.user_id,
                dry_run=dry_run,
            )

        elif args.token:
            # 直接测试 token
            result = await test_feedback_push_by_token(
                token=args.token,
                dry_run=dry_run,
            )

        else:
            logger.error("请提供 --user-id 或 --token")
            parser.print_help()
            return 1

        # 输出结果
        logger.info("=" * 60)
        logger.info("测试结果:")
        logger.info("=" * 60)
        import json

        print(json.dumps(result, indent=2, ensure_ascii=False))

        return 0 if result.get("success", False) else 1

    except KeyboardInterrupt:
        logger.info("用户中断")
        return 1
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
