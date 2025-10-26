#!/usr/bin/env python3
"""
激活用户账户的脚本

使用方法:
python scripts/activate_user.py --user-id user_123
python scripts/activate_user.py --readable-id 10000001
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_async_db
from app.models.user import User
from sqlalchemy import select, update


async def activate_user(user_id: str = None, readable_id: str = None):
    """激活用户账户"""

    try:
        async for db in get_async_db():
            # 查找用户
            if user_id:
                stmt = select(User).where(User.id == user_id)
            elif readable_id:
                stmt = select(User).where(User.readable_id == readable_id)
            else:
                raise ValueError("必须提供用户ID或readable_id")

            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                print("❌ 未找到用户")
                sys.exit(1)

            # 显示用户信息
            print("=== 用户信息 ===")
            print(f"用户ID: {user.id}")
            print(f"昵称: {user.nickname}")
            print(f"Readable ID: {user.readable_id}")
            print(f"当前状态: {'活跃' if user.is_active else '不活跃'}")
            print(f"删除状态: {'已删除' if user.deleted_at else '正常'}")

            if user.is_active and not user.deleted_at:
                print("✅ 用户已经是活跃状态，无需操作")
                return

            if user.deleted_at:
                print("⚠️  警告: 这是一个已删除的用户，激活可能不安全")
                confirm = input("是否继续激活？(y/N): ")
                if confirm.lower() != "y":
                    print("已取消操作")
                    return

            # 激活用户
            await db.execute(
                update(User).where(User.id == user.id).values(is_active=True)
            )
            await db.commit()

            print("✅ 用户已激活")
            break

    except Exception as e:
        print(f"❌ 激活用户失败: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="激活用户账户")

    # 用户查找参数（互斥）
    user_group = parser.add_mutually_exclusive_group(required=True)
    user_group.add_argument("--user-id", help="用户ID")
    user_group.add_argument("--readable-id", help="用户可读ID")

    args = parser.parse_args()

    # 激活用户
    print("🔄 正在激活用户...")
    asyncio.run(activate_user(user_id=args.user_id, readable_id=args.readable_id))


if __name__ == "__main__":
    main()
