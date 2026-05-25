"""
FCM Token 注册脚本

用于测试时手动注册 FCM token 到指定用户。

使用方法:
    # 为指定用户注册 token
    python tools/scripts/fcm/register_fcm_token.py \
      --token "FCM_TOKEN_HERE" \
      --user-id "USER_ID_HERE"

    # 验证 token 格式后注册
    python tools/scripts/fcm/register_fcm_token.py \
      --token "FCM_TOKEN_HERE" \
      --user-id "USER_ID_HERE" \
      --validate-token
"""

import asyncio
import argparse
import sys
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import load_config, init_logger
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services import user_service


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


async def check_user_exists(db: AsyncSession, user_id: str) -> bool:
    """
    检查用户是否存在

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        用户是否存在
    """
    try:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        return user is not None
    except Exception as e:
        logger.error(f"检查用户存在性失败: {str(e)}")
        return False


async def register_token(
    token: str, user_id: str, validate_token: bool = False
) -> bool:
    """
    注册 FCM token 到指定用户

    Args:
        token: FCM token
        user_id: 目标用户 ID
        validate_token: 是否验证 token 格式

    Returns:
        是否注册成功
    """
    try:
        # 验证 token 格式（如果启用）
        if validate_token:
            if not validate_fcm_token(token):
                logger.error("Token 格式验证失败")
                return False
            logger.info("Token 格式验证通过")

        # 连接数据库并验证用户
        async with AsyncSessionLocal() as db:
            # 检查用户是否存在
            user_exists = await check_user_exists(db, user_id)
            if not user_exists:
                logger.error(f"用户不存在: {user_id}")
                return False

            logger.info(f"用户存在: {user_id}")

            # 注册 token
            device_token = await user_service.register_device_token(
                db=db, token=token, user_id=user_id
            )

            logger.success(
                f"Token 注册成功: user_id={user_id}, "
                f"device_token_id={device_token.id}, "
                f"token_prefix={token[:20]}..."
            )
            return True

    except Exception as e:
        logger.error(f"注册 token 失败: {type(e).__name__}: {str(e)}")
        import traceback

        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="FCM Token 注册工具")
    parser.add_argument(
        "--token",
        type=str,
        required=True,
        help="FCM device token（必需）",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        required=True,
        help="目标用户 ID（必需）",
    )
    parser.add_argument(
        "--validate-token",
        action="store_true",
        help="验证 token 格式后再注册",
    )

    args = parser.parse_args()

    # 初始化日志
    init_logger()

    logger.info("=" * 60)
    logger.info("FCM Token 注册工具")
    logger.info("=" * 60)
    logger.info(f"Token: {args.token[:20]}... (长度: {len(args.token)})")
    logger.info(f"用户 ID: {args.user_id}")
    logger.info(f"验证 Token 格式: {args.validate_token}")

    # 加载配置
    # TODO(INTY_CONFIG_YAML): load_config(resolve_inty_config_yaml_path()) from app.utils.config
    config_path = project_root / "config.yaml"
    try:
        load_config(config_path)
        logger.info("配置加载成功")
    except Exception as e:
        logger.error(f"配置加载失败: {str(e)}")
        logger.error("请确保 config.yaml 文件存在且配置正确")
        sys.exit(1)

    # 注册 token
    success = await register_token(
        token=args.token,
        user_id=args.user_id,
        validate_token=args.validate_token,
    )

    if success:
        logger.success("=" * 60)
        logger.success("Token 注册完成！")
        logger.success("=" * 60)
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("Token 注册失败！")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
