#!/usr/bin/env python3
"""
生成长期有效Token的命令行工具

在仓库根目录执行，并设置 PYTHONPATH:

export PYTHONPATH=.
python tools/scripts/generate_long_term_token.py --user-id user_123 --days 365
python tools/scripts/generate_long_term_token.py --phone 13800138000 --days 365
python tools/scripts/generate_long_term_token.py --email test@example.com --days 365
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Optional

import cyclopts
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_async_db
from app.models.user import User


async def find_user_by_criteria(
    db: AsyncSession,
    user_id: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
) -> User:
    """根据不同条件查找用户"""

    if user_id:
        stmt = select(User).where(User.id == user_id)
    elif phone:
        stmt = select(User).where(User.phone == phone)
    elif email:
        stmt = select(User).where(User.email == email)
    else:
        raise ValueError("必须提供用户ID、手机号或邮箱中的一个")

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise ValueError("未找到用户")

    return user


async def generate_long_term_token(
    user_id: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    days: int = 365,
):
    """生成长期有效的token"""

    try:
        async for db in get_async_db():
            user = await find_user_by_criteria(
                db, user_id=user_id, phone=phone, email=email
            )

            expire_delta = timedelta(days=days)
            token = create_access_token(subject=user.id, expires_delta=expire_delta)
            expire_time = datetime.utcnow() + expire_delta

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

    except ValueError as e:
        print(f"❌ 生成Token失败: {e}")
        sys.exit(1)
    except SQLAlchemyError as e:
        print(f"❌ 数据库错误: {e}")
        sys.exit(1)


def _count_non_empty(values: list[Optional[str]]) -> int:
    return sum(1 for v in values if v is not None and str(v).strip() != "")


def main(
    user_id: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    days: int = 365,
):
    if _count_non_empty([user_id, phone, email]) != 1:
        raise ValueError("必须且只能提供 --user-id、--phone、--email 中的一个")

    if days <= 0:
        print("❌ 错误: 有效期必须大于0天")
        sys.exit(1)

    if days > 3650:  # 10年
        print("⚠️  警告: 有效期超过10年，这可能存在安全风险")
        confirm = input("是否继续？(y/N): ")
        if confirm.lower() != "y":
            print("已取消")
            sys.exit(0)

    print("🔄 正在生成长期Token...")
    asyncio.run(
        generate_long_term_token(
            user_id=user_id,
            phone=phone,
            email=email,
            days=days,
        )
    )


if __name__ == "__main__":
    cyclopts.run(main)
