import asyncio
import re
import sys
import traceback
from datetime import UTC, datetime

import cyclopts
from loguru import logger
from sqlalchemy import and_, select

from app.core.security import get_password_hash, verify_password
from app.core.uuid import get_new_user_id
from app.db.session import AsyncSessionLocal
from app.models.user import AuthType, User
from app.services.user_service import generate_next_readable_id


async def create_email_password_superuser(
    email: str,
    password: str,
    nickname: str,
    dry_run: bool = False,
    delete_existing: bool = False,
    is_superuser: bool = True,
    auto_confirm: bool = False,
) -> User:
    """
    创建邮箱密码认证用户

    该函数用于在数据库中创建带有邮箱密码认证的测试用户。
    支持幂等操作：如果用户已存在，将返回现有用户信息。

    Parameters
    ----------
    email
        用户邮箱地址（必需）
    password
        用户密码，明文（必需）
    nickname
        用户昵称（可选，如果不提供将自动生成）
    dry_run
        试运行模式：显示将要执行的操作但不实际写入数据库
    delete_existing
        如果为 True，删除现有用户后创建新用户
    is_superuser
        是否创建为超级用户
    auto_confirm
        是否自动确认所有交互提示（用于非交互环境）

    Returns
    -------
    User
        创建或已存在的用户对象
    """
    async with AsyncSessionLocal() as db:
        logger.debug(f"Checking if user with email {email} already exists")

        # 检查邮箱是否已存在
        stmt = select(User).where(
            and_(User.email == email, User.deleted_at == None)
        )
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            if delete_existing:
                if dry_run:
                    logger.info(
                        f"DRY-RUN: Would delete existing user {existing_user.id} "
                        f"with email {email}"
                    )
                else:
                    existing_user.deleted_at = datetime.now(UTC)
                    existing_user.deletion_reason = (
                        "Deleted by create_email_password_superuser script"
                    )
                    await db.commit()
                    logger.info(
                        f"Deleted existing user {existing_user.id} with email {email}"
                    )
                # 删除后继续创建新用户，不返回现有用户
            else:
                logger.debug(
                    f"User with email {email} already exists: {existing_user.id}"
                )

                # 检查现有用户的认证类型
                if existing_user.auth_type != AuthType.EMAIL:
                    logger.warning(
                        f"User {existing_user.id} exists but auth_type is {existing_user.auth_type}, "
                        f"not {AuthType.EMAIL}"
                    )
                    return existing_user

                # 验证现有密码是否匹配
                if existing_user.password:
                    password_matches = verify_password(
                        password, existing_user.password
                    )
                    if password_matches:
                        logger.info(
                            f"User already exists with matching password: {existing_user.id}"
                        )
                    else:
                        logger.warning(
                            f"User already exists but password does not match. "
                            f"User ID: {existing_user.id}"
                        )
                        # 如果不是 dry-run 模式，询问是否更新密码
                        if not dry_run:
                            if auto_confirm or confirm_action(
                                f"Password does not match. Do you want to update the password for user {existing_user.id}?"
                            ):
                                hashed_password = get_password_hash(password)
                                existing_user.password = hashed_password
                                await db.commit()
                                await db.refresh(existing_user)
                                logger.info(
                                    f"Password updated successfully for user {existing_user.id}"
                                )
                            else:
                                logger.info("Password update cancelled by user")
                        else:
                            logger.info(
                                "DRY-RUN: Would update password for existing user"
                            )
                else:
                    logger.warning(
                        f"User already exists but has no password set. "
                        f"User ID: {existing_user.id}"
                    )
                    # 如果不是 dry-run 模式，询问是否设置密码
                    if not dry_run:
                        if auto_confirm or confirm_action(
                            f"User has no password set. Do you want to set the password for user {existing_user.id}?"
                        ):
                            hashed_password = get_password_hash(password)
                            existing_user.password = hashed_password
                            await db.commit()
                            await db.refresh(existing_user)
                            logger.info(
                                f"Password set successfully for user {existing_user.id}"
                            )
                        else:
                            logger.info("Password setting cancelled by user")
                    else:
                        logger.info(
                            "DRY-RUN: Would set password for existing user"
                        )

                return existing_user

        user_id = get_new_user_id()
        readable_id = await generate_next_readable_id(db)

        logger.debug(f"Generated user_id: {user_id}")
        logger.debug(f"Generated readable_id: {readable_id}")

        # 哈希密码
        hashed_password = get_password_hash(password)
        logger.debug("Password hashed successfully")

        # 创建用户对象
        user = User(
            id=user_id,
            readable_id=readable_id,
            auth_type=AuthType.EMAIL,
            email=email,
            password=hashed_password,
            nickname=nickname or f"User {user_id[:8]}",
            is_superuser=is_superuser,
        )

        if dry_run:
            logger.info(
                "DRY-RUN: Would create user with the following details:"
            )
            logger.info(f"  User ID: {user.id}")
            logger.info(f"  Readable ID: {user.readable_id}")
            logger.info(f"  Email: {user.email}")
            logger.info(f"  Nickname: {user.nickname}")
            logger.info(f"  Auth Type: {user.auth_type}")
            logger.info(f"  System Language: {user.system_language}")
            logger.info(f"  Is Superuser: {user.is_superuser}")
            return user

        # 保存到数据库
        logger.debug("Adding user to database session")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"Created user successfully:")
        logger.info(f"  User ID: {user.id}")
        logger.info(f"  Readable ID: {user.readable_id}")
        logger.info(f"  Email: {user.email}")
        logger.info(f"  Nickname: {user.nickname}")
        logger.info(f"  Is Superuser: {user.is_superuser}")
        return user


def confirm_action(message: str) -> bool:
    """
    确认用户操作

    Parameters
    ----------
    message
        确认提示信息

    Returns
    -------
    bool
        True 如果用户确认，False 否则
    """
    response = input(f"{message} (yes/no): ").strip().lower()
    return response in ("yes", "y")


async def main(
    email: str,
    password: str,
    nickname: str = "Test User",
    dry_run: bool = False,
    delete_existing: bool = False,
    is_superuser: bool = True,
    yes: bool = False,
):
    """
    创建邮箱密码认证用户

    该脚本用于在数据库中创建带有邮箱密码认证的用户（可选超级权限）。
    支持幂等操作：如果用户已存在，将返回现有用户信息。

    注意：除非使用 --dry-run 或 --yes 模式，否则始终要求用户确认操作。

    Parameters
    ----------
    email
        用户邮箱地址（必需）
    password
        用户密码，明文（必需）
    nickname
        用户昵称（可选，如果不提供将自动生成）
    dry_run
        试运行模式：显示将要执行的操作但不实际写入数据库，且不要求确认
    delete_existing
        如果为 True，删除现有用户（如现有用户存在）用于删除一个已有账户
    is_superuser
        是否创建为超级用户，默认 True
    yes
        自动确认所有提示（非交互模式）

    Examples
    --------
    # 创建超级用户（会要求确认）
    python tools/scripts/create_email_password_superuser.py --email test@gmail.com --password a_password

    # 试运行模式（不实际写入数据库，不要求确认）
    python tools/scripts/create_email_password_superuser.py --email test@gmail.com --password a_password --dry-run

    # 删除现有用户后创建新用户（会要求确认）
    python tools/scripts/create_email_password_superuser.py --email test@gmail.com --password a_password --delete-existing

    # 创建用户并指定昵称（会要求确认）
    python tools/scripts/create_email_password_superuser.py --email test@gmail.com --password a_password --nickname "Test User"

    # 非交互创建普通用户（不需要手动输入 yes/no）
    python tools/scripts/create_email_password_superuser.py --email test@gmail.com --password a_password --is-superuser=false --yes
    """
    # 验证邮箱格式
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        logger.error(f"Invalid email format: {email}")
        sys.exit(1)

    # 验证密码不为空
    if not password:
        logger.error("Password cannot be empty")
        sys.exit(1)

    # 如果不是 dry-run 模式，且未指定自动确认，始终要求确认
    if not dry_run and not yes:
        if not confirm_action(
            f"Are you sure you want to create a user with email {email}?"
        ):
            logger.info("Operation cancelled by user")
            sys.exit(0)

    user = await create_email_password_superuser(
        email=email,
        password=password,
        nickname=nickname,
        dry_run=dry_run,
        delete_existing=delete_existing,
        is_superuser=is_superuser,
        auto_confirm=yes,
    )

    if not dry_run:
        logger.info("User creation completed successfully")
    else:
        logger.info("Dry-run completed. No changes were made to the database.")


if __name__ == "__main__":
    cyclopts.run(main)
