#!/usr/bin/env python3
"""
生成长期有效Token的命令行工具

使用方法:
python scripts/generate_long_term_token.py --user-id user_123 --days 365
python scripts/generate_long_term_token.py --phone 13800138000 --days 365
python scripts/generate_long_term_token.py --email test@example.com --days 365
python scripts/generate_long_term_token.py --readable-id 10000001 --days 365
"""

import asyncio
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import global_config_loaded_from_config_yaml
from app.core.security import create_access_token
from app.db.session import get_async_db
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def find_user_by_criteria(
    db: AsyncSession,
    user_id: str = None,
    phone: str = None,
    email: str = None,
    readable_id: str = None,
) -> User:
    """根据不同条件查找用户"""

    if user_id:
        stmt = select(User).where(User.id == user_id)
    elif phone:
        stmt = select(User).where(User.phone == phone)
    elif email:
        stmt = select(User).where(User.email == email)
    elif readable_id:
        stmt = select(User).where(User.readable_id == readable_id)
    else:
        raise ValueError("必须提供用户ID、手机号、邮箱或readable_id中的一个")

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise ValueError("未找到用户")

    return user


async def generate_long_term_token(
    user_id: str = None,
    phone: str = None,
    email: str = None,
    readable_id: str = None,
    days: int = 365,
):
    """生成长期有效的token"""

    try:
        # 获取数据库会话
        async for db in get_async_db():
            # 查找用户
            user = await find_user_by_criteria(
                db, user_id=user_id, phone=phone, email=email, readable_id=readable_id
            )

            # 生成长期token
            expire_delta = timedelta(days=days)
            token = create_access_token(subject=user.id, expires_delta=expire_delta)

            # 计算过期时间
            expire_time = datetime.utcnow() + expire_delta

            # 输出结果
            print("=" * 60)
            print("🎉 长期Token生成成功!")
            print("=" * 60)
            print(f"用户ID: {user.id}")
            print(f"用户昵称: {user.nickname}")
            print(f"用户邮箱: {user.email or 'N/A'}")
            print(f"用户手机: {user.phone or 'N/A'}")
            print(f"Readable ID: {user.readable_id}")
            print(f"认证类型: {user.auth_type}")
            print(f"有效期: {days} 天")
            print(f"过期时间: {expire_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print("=" * 60)
            print("🔑 Token:")
            print(token)
            print("=" * 60)
            print("\n💡 使用方法:")
            print("在HTTP请求头中添加: Authorization: Bearer <token>")
            print("或者在Swagger UI中点击Authorize按钮，输入token")
            print("\n⚠️  安全提示:")
            print("- 请妥善保管这个token，不要泄露给他人")
            print("- 如果token泄露，请立即修改security.secret_key")
            print("- 建议定期更换token")

            break

    except Exception as e:
        print(f"❌ 生成Token失败: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="生成长期有效Token")

    # 用户查找参数（互斥）
    user_group = parser.add_mutually_exclusive_group(required=True)
    user_group.add_argument("--user-id", help="用户ID")
    user_group.add_argument("--phone", help="手机号")
    user_group.add_argument("--email", help="邮箱")
    user_group.add_argument("--readable-id", help="用户可读ID")

    # Token有效期参数
    parser.add_argument(
        "--days", type=int, default=365, help="Token有效期（天数），默认365天"
    )

    args = parser.parse_args()

    # 验证参数
    if args.days <= 0:
        print("❌ 错误: 有效期必须大于0天")
        sys.exit(1)

    if args.days > 3650:  # 10年
        print("⚠️  警告: 有效期超过10年，这可能存在安全风险")
        confirm = input("是否继续？(y/N): ")
        if confirm.lower() != "y":
            print("已取消")
            sys.exit(0)

    # 生成token
    print("🔄 正在生成长期Token...")
    asyncio.run(
        generate_long_term_token(
            user_id=args.user_id,
            phone=args.phone,
            email=args.email,
            readable_id=args.readable_id,
            days=args.days,
        )
    )


if __name__ == "__main__":
    main()
