#！/usr/bin/env python3
"""
Script to initialize an admin user in the database.
This script creates a superuser with admin privileges.
"""
import argparse
import random
import sys
from pathlib import Path
# 将目录父添加到Python路径中，方便我们可以导入应用程序
script_dir = Path(__file__).parent
parent_dir = script_dir.parent
sys.path.insert(0, str(parent_dir))

from loguru import logger
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.base import SessionLocal
from app.models.user import AuthType, Gender, User

DEFAULT_ADMIN_USER_ID = "user-01JWZ34Y4D1C92GD86A5R6EWYJ"


def generate_readable_id() -> str:
    """Generate a random 8-digit readable_id (0-9)."""
    return "".join(str(random.randint(0, 9)) for _ in range(8))


def create_user(
    user_id: str = DEFAULT_ADMIN_USER_ID,
    is_superuser: bool = True,
):
    """Create an admin user in the database."""
    logger.info("Starting admin user creation...")
# 创建数据库会话
    db: Session = SessionLocal()
# 检查admin用户是否已经存在
    existing_user = db.query(User).filter(User.id == user_id).first()

    if existing_user:
        logger.warning(f"Admin user already exists with ID: {user_id}")
        created_user = existing_user
    else:
# 创建新的管理员用户
        created_user = User(
            id=user_id,
            nickname="admin",
            email="admin@sxwl.ai",
            gender=Gender.MALE,
            age_group="18-24",
            description="An admin user",
            is_active=True,
            is_superuser=is_superuser,
            auth_type=AuthType.GOOGLE,
            readable_id=generate_readable_id(),
        )
#添加到数据库
        db.add(created_user)
        db.commit()
# 为创建的用户生成不记名令牌
    access_token = create_access_token(created_user.id)

    logger.info("Admin user created successfully!")
    logger.info(f"User ID: {created_user.id}")
    logger.info(f"Email: {created_user.email}")
    logger.info(f"Readable ID: {created_user.readable_id}")
    logger.info(f"🔑 Bearer Token: {access_token}")


def parse_args():
    parser = argparse.ArgumentParser(description="Create an user")
    parser.add_argument("--user-id", type=str, default=DEFAULT_ADMIN_USER_ID)
    parser.add_argument("--is-superuser", type=bool, default=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    create_user(user_id=args.user_id, is_superuser=args.is_superuser)
