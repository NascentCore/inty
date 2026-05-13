"""
FCM 推送测试脚本

用于在 app 开发未就绪时，测试 FCM 推送功能。

使用方法:
    # Dry run 模式（推荐，不会实际发送）
    python tools/scripts/fcm/test_fcm_push.py --dry-run --token YOUR_FCM_TOKEN

    # 真实发送模式
    python tools/scripts/fcm/test_fcm_push.py --token YOUR_FCM_TOKEN

    # 测试用户 ID（从数据库获取 token）
    python tools/scripts/fcm/test_fcm_push.py --user-id USER_ID --dry-run

    # 测试推送通知服务
    python tools/scripts/fcm/test_fcm_push.py --test-push-service --user-id USER_ID --dry-run
"""

import asyncio
import argparse
import sys
from typing import Optional

from firebase_admin import messaging
from firebase_admin.exceptions import InvalidArgumentError
from loguru import logger

# 添加项目根目录到路径
from pathlib import Path

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


async def test_fcm_single_token(
    token: str,
    title: str = "测试推送",
    body: str = "这是一条测试消息",
    data: Optional[dict] = None,
    image_url: Optional[str] = None,
    dry_run: bool = True,
) -> dict:
    """
    测试向单个 token 发送 FCM 消息

    Args:
        token: FCM device token
        title: 通知标题
        body: 通知内容
        data: 数据字段（可选）
        image_url: 图片 URL（可选）
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

        # 构建消息
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(
                title=title, body=body, image=image_url
            ),
            data=data or {},
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="default",
                    sound="default",
                ),
            ),
        )

        # 发送消息
        mode = "[DRY RUN]" if dry_run else "[REAL]"
        logger.info(f"{mode} 开始发送 FCM 消息到 token: {token[:20]}...")

        message_id = messaging.send(message, dry_run=dry_run)

        result["success"] = True
        result["message_id"] = message_id

        if dry_run:
            logger.success(
                f"[DRY RUN] 消息验证成功！message_id={message_id}, "
                f"title={title}, body={body[:50]}..."
            )
        else:
            logger.success(
                f"[REAL] 消息发送成功！message_id={message_id}, "
                f"title={title}, body={body[:50]}..."
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


async def test_fcm_by_user_id(
    user_id: str,
    title: str = "测试推送",
    body: str = "这是一条测试消息",
    data: Optional[dict] = None,
    image_url: Optional[str] = None,
    dry_run: bool = True,
) -> dict:
    """
    通过用户 ID 测试 FCM 推送

    Args:
        user_id: 用户 ID
        title: 通知标题
        body: 通知内容
        data: 数据字段（可选）
        image_url: 图片 URL（可选）
        dry_run: 是否为测试模式

    Returns:
        测试结果字典
    """
    result = {
        "user_id": user_id,
        "dry_run": dry_run,
        "success": False,
        "tokens_found": 0,
        "results": [],
    }

    try:
        async with AsyncSessionLocal() as db:
            # 获取用户的 device tokens
            tokens = await user_service.get_users_device_tokens(db, [user_id])

            if not tokens:
                result["error"] = f"用户 {user_id} 没有注册的 device token"
                logger.warning(result["error"])
                return result

            result["tokens_found"] = len(tokens)
            logger.info(f"找到 {len(tokens)} 个 device token 用于用户 {user_id}")

            # 测试每个 token
            for token in tokens:
                token_result = await test_fcm_single_token(
                    token=token,
                    title=title,
                    body=body,
                    data=data,
                    image_url=image_url,
                    dry_run=dry_run,
                )
                result["results"].append(token_result)

            # 统计结果
            success_count = sum(1 for r in result["results"] if r["success"])
            result["success"] = success_count > 0
            result["success_count"] = success_count
            result["fail_count"] = len(result["results"]) - success_count

            mode = "[DRY RUN]" if dry_run else "[REAL]"
            logger.info(
                f"{mode} 用户 {user_id} 测试完成: "
                f"成功={success_count}, 失败={result['fail_count']}, 总计={len(tokens)}"
            )

    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
        logger.error(f"测试失败: {type(e).__name__}: {str(e)}")

    return result


async def test_push_service(
    user_id: str,
    title: str = "测试推送服务",
    body: str = "这是一条通过推送服务发送的测试消息",
    data: Optional[dict] = None,
    image_url: Optional[str] = None,
    dry_run: bool = True,
) -> dict:
    """
    测试推送通知服务

    Args:
        user_id: 用户 ID
        title: 通知标题
        body: 通知内容
        data: 数据字段（可选）
        image_url: 图片 URL（可选）
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
            logger.info(f"{mode} 测试推送通知服务，用户 ID: {user_id}")

            success = await notification_service.send_fcm_multicast(
                db=db,
                user_ids=[user_id],
                title=title,
                body=body,
                data=data,
                image_url=image_url,
                dry_run=dry_run,
            )

            result["success"] = success

            if success:
                logger.success(f"{mode} 推送服务测试成功！")
            else:
                logger.error(f"{mode} 推送服务测试失败")

    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
        logger.error(f"推送服务测试失败: {type(e).__name__}: {str(e)}")

    return result


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="FCM 推送测试工具")
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
        "--test-push-service",
        action="store_true",
        help="测试推送通知服务（使用 send_fcm_multicast）",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="测试推送",
        help="通知标题（默认: 测试推送）",
    )
    parser.add_argument(
        "--body",
        type=str,
        default="这是一条测试消息",
        help="通知内容（默认: 这是一条测试消息）",
    )
    parser.add_argument(
        "--image-url",
        type=str,
        default="https://images.sxwl.dev/inty-static/avatars/user-01JWZ34Y4D1C92GD86A5R6EWYJ/user-01JWZ34Y4D1C92GD86A5R6EWYJ/20251105-143155-da43ea7b-cropped-avatar.jpeg",
        help="图片 URL（可选）",
    )
    parser.add_argument(
        "--data",
        type=str,
        help='数据字段（JSON 格式，例如: \'{"key":"value"}\'）',
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

    # 解析 data 参数
    data = None
    if args.data:
        try:
            import json

            data = json.loads(args.data)
        except json.JSONDecodeError as e:
            logger.error(f"数据字段 JSON 解析失败: {str(e)}")
            return 1

    try:
        if args.test_push_service:
            # 测试推送服务
            if not args.user_id:
                logger.error("测试推送服务需要提供 --user-id")
                return 1

            result = await test_push_service(
                user_id=args.user_id,
                title=args.title,
                body=args.body,
                data=data,
                image_url=args.image_url,
                dry_run=dry_run,
            )

        elif args.user_id:
            # 通过用户 ID 测试
            result = await test_fcm_by_user_id(
                user_id=args.user_id,
                title=args.title,
                body=args.body,
                data=data,
                image_url=args.image_url,
                dry_run=dry_run,
            )

        elif args.token:
            # 直接测试 token
            result = await test_fcm_single_token(
                token=args.token,
                title=args.title,
                body=args.body,
                data=data,
                image_url=args.image_url,
                dry_run=dry_run,
            )

        else:
            logger.error("请提供 --token、--user-id 或 --test-push-service")
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
