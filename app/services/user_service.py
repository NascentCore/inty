import logging
import traceback
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import and_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from app.core.config import global_config_loaded_from_config_yaml
from app.core.uuid import uid
from app.models import User
from app.models.chat import Chat
from app.models.subscription import SubscriptionStatus, UserSubscription
from app.models.user import AuthType, DeviceToken
from app.schemas import UserUpdate
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


async def generate_next_readable_id(db: AsyncSession) -> str:
    """
    Generate next readable ID for user using database sequence for thread safety
    """
    try:
        # Use database sequence to generate next readable_id atomically
        result = await db.execute(text("SELECT nextval('user_readable_id_seq')"))
        next_id = result.scalar()
        return str(next_id).zfill(8)
    except Exception as e:
        logger.error(f"Error generating readable ID from sequence: {str(e)}")
        # Fallback to a random 8-digit number starting from 10000000
        import random
        return str(random.randint(10000000, 99999999))


def generate_next_readable_id_sync(db: Session) -> str:
    """
    Generate next readable ID for user using database sequence for thread safety (sync version)
    """
    try:
        # Use database sequence to generate next readable_id atomically
        result = db.execute(text("SELECT nextval('user_readable_id_seq')"))
        next_id = result.scalar()
        return str(next_id).zfill(8)
    except Exception as e:
        logger.error(f"Error generating readable ID from sequence: {str(e)}")
        # Fallback to a random 8-digit number starting from 10000000
        import random
        return str(random.randint(10000000, 99999999))


def register_user(db: Session, user_in) -> User:
    """Register user (phone number etc.)"""
    try:
        user_id = str(uuid.uuid4())
        readable_id = generate_next_readable_id_sync(db)

        user = User(
            id=user_id,
            readable_id=readable_id,
            auth_type=user_in.auth_type,
            system_language=(
                user_in.user_info.system_language if user_in.user_info else "en"
            ),
            is_active=True,
        )
        if user_in.user_info:
            user.gender = user_in.user_info.gender
            user.age_group = user_in.user_info.age_group
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error registering user: {str(e)}")
        # If readable_id conflicts, try again with a new one
        if "readable_id" in str(e):
            return register_user(db, user_in)
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to register user: {str(e)}")
        logger.error(f"Error stack: {traceback.format_exc()}")
        raise e


def get_user_by_phone(db: Session, phone: str) -> Optional[User]:
    """Get user by phone number"""
    return db.query(User).filter(User.phone == phone).first()


async def create_guest_user(
    db: AsyncSession,
    device_id: Optional[str] = None,
    system_language: Optional[str] = None,
    age_group: Optional[str] = None,
) -> User:
    """Create guest user - can create anonymous users without device_id association"""
    try:
        if device_id:
            stmt = select(User).where(
                User.device_id == device_id,
                User.auth_type == AuthType.GUEST,
                User.deleted_at.is_(None),  # 只查找未删除的用户
            )
            result = await db.execute(stmt)
            existing_user = result.scalars().first()
            if existing_user:
                return existing_user

        user_id = uid(prefix="user")
        readable_id = await generate_next_readable_id(db)

        user = User(
            id=user_id,
            readable_id=readable_id,
            auth_type=AuthType.GUEST,
            device_id=device_id,
            nickname=f"Guest_{user_id[-8:]}",
            system_language=system_language or "en",
            age_group=age_group,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error creating guest user: {str(e)}")
        # If readable_id conflicts, try again with a new one
        if "readable_id" in str(e):
            return await create_guest_user(db, device_id, system_language, age_group)
        raise e
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create guest user: {str(e)}")
        logger.error(f"Error stack: {traceback.format_exc()}")
        raise e


async def update_user(db: AsyncSession, user_id: str, user_in: UserUpdate) -> User:
    """Update user information"""
    try:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            raise ValueError(f"User does not exist: {user_id}")

        update_data = user_in.model_dump(exclude_unset=True)

        # 过滤掉不应该被用户更新的字段
        excluded_fields = {
            "readable_id",
            "id",
            "auth_type",
            "is_active",
            "is_superuser",
            "created_at",
            "updated_at",
        }
        update_data = {k: v for k, v in update_data.items() if k not in excluded_fields}

        for field, value in update_data.items():
            setattr(user, field, value)

        await db.commit()
        await db.refresh(user)

        # 清除用户信息缓存，确保Agent系统能获取到最新信息
        cache_service.invalidate_user_info(user_id)
        logger.debug(f"已清除用户 {user_id} 的缓存信息")

        return user
    except Exception as e:
        logger.error(f"Failed to update user information: {str(e)}")
        logger.error(f"Error stack: {traceback.format_exc()}")
        raise e


def generate_avatar_path(user_id: str, filename: str) -> str:
    ext = filename.split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        raise ValueError(f"Unsupported file type: {ext}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"avatars/{user_id}/avatar-{timestamp}-{unique_id}.{ext}"


def get_path_from_gcs_url(url: str) -> str:
    if not url:
        return ""
    parts = url.split(".com/")
    if len(parts) < 2:
        return ""
    path = parts[1]
    # Remove bucket name prefix
    bucket = global_config_loaded_from_config_yaml.gcs.bucket
    if path.startswith(bucket + "/"):
        path = path[len(bucket) + 1 :]
    return path


async def register_device_token(
    db: AsyncSession, token: str, user_id: str
) -> DeviceToken:
    """
    Register or update device token
    """
    try:
        # Check if token already exists
        stmt = select(DeviceToken).where(DeviceToken.token == token)
        result = await db.execute(stmt)
        device_token = result.scalars().first()

        if device_token:
            # If exists, update user_id
            device_token.user_id = user_id
        else:
            # If not exists, create new record
            device_token = DeviceToken(token=token, user_id=user_id)
            db.add(device_token)

        await db.commit()
        await db.refresh(device_token)
        return device_token

    except Exception as e:
        raise e


async def get_users_device_tokens(db: AsyncSession, user_ids: list[str]) -> list[str]:
    """Get all device tokens for multiple users

    Args:
        db: Database session
        user_ids: List of user IDs

    Returns:
        list[str]: List of device tokens, returns empty list if no records found
    """
    try:
        stmt = select(DeviceToken.token).where(DeviceToken.user_id.in_(user_ids))
        result = await db.execute(stmt)
        tokens = result.scalars().all()
        return tokens
    except Exception as e:
        logger.error(f"Failed to get user device tokens: {str(e)}")
        logger.error(f"Error stack: {traceback.format_exc()}")
        raise e


async def check_user_can_delete_account(
    db: AsyncSession, user_id: str
) -> tuple[bool, str]:
    """
    检查用户是否可以删除账户

    Returns:
        tuple[bool, str]: (是否可以删除, 错误信息)
    """
    try:
        # 检查用户是否存在
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            return False, "用户不存在"

        if user.deleted_at:
            return False, "账户已被删除"

        # 检查是否有活跃订阅
        active_subscription_stmt = select(UserSubscription).where(
            and_(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE,
                UserSubscription.end_date > datetime.now(UTC),
            )
        )
        active_subscription_result = await db.execute(active_subscription_stmt)
        active_subscription = active_subscription_result.scalars().first()

        if active_subscription:
            return False, "存在活跃订阅，请先取消订阅后再删除账户"

        return True, ""

    except Exception as e:
        logger.error(f"检查用户删除权限失败: {str(e)}")
        raise e


async def delete_user_account(
    db: AsyncSession,
    user_id: str,
    deletion_reason: str = "用户主动删除",
    processor_id: Optional[str] = None,
) -> dict:
    """
    删除用户账户

    Args:
        db: 数据库会话
        user_id: 用户ID
        deletion_reason: 删除原因
        processor_id: 处理者ID（通常是用户本人）

    Returns:
        dict: 删除结果信息
    """
    try:
        # 检查用户是否可以删除
        can_delete, error_msg = await check_user_can_delete_account(db, user_id)
        if not can_delete:
            return {"success": False, "message": error_msg, "user_id": user_id}

        # 获取用户信息
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            return {"success": False, "message": "用户不存在", "user_id": user_id}

        # 获取用户当前订阅状态
        from app.services.subscription_service import subscription_service

        subscription_status_response = (
            await subscription_service.get_user_subscription_status(db, user_id)
        )

        # 如果用户有活跃订阅，先取消订阅
        cancellation_stats = None
        if subscription_status_response.is_subscribed:
            try:
                cancellation_stats = (
                    await subscription_service.cancel_user_subscriptions_for_deletion(
                        db, user_id
                    )
                )
                logger.debug(f"用户 {user_id} 订阅取消统计: {cancellation_stats}")
            except Exception as e:
                logger.warning(f"取消用户订阅失败，继续删除流程: {str(e)}")

        # 设置删除时间戳
        user.deleted_at = datetime.now(UTC)
        user.deletion_reason = deletion_reason
        user.is_active = False

        # 提交用户数据更改
        await db.commit()
        await db.refresh(user)

        logger.info(f"用户账户删除成功: {user_id}")

        return {
            "success": True,
            "message": "账户删除成功",
            "user_id": user_id,
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"删除用户账户失败: {str(e)}")
        logger.error(f"Error stack: {traceback.format_exc()}")
        raise e


async def get_all_users(
    db: AsyncSession, skip: int = 0, limit: int = 50, search: Optional[str] = None
) -> dict:
    """
    获取所有用户信息，支持分页和关键字搜索

    Args:
        db: 数据库会话
        skip: 跳过记录数
        limit: 限制记录数
        search: 搜索关键字，可匹配昵称和readable_id

    Returns:
        dict: 包含总数和分页数据的字典
    """
    try:
        from sqlalchemy import func, or_

        # 构建基础查询
        base_query = select(User)
        count_query = select(func.count()).select_from(User)

        # 如果有搜索关键字，添加搜索条件
        if search:
            search_condition = or_(
                User.nickname.ilike(f"%{search}%"),
                User.readable_id.ilike(f"%{search}%"),
            )
            base_query = base_query.where(search_condition)
            count_query = count_query.where(search_condition)

        # 获取总数
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # 获取分页数据
        result = await db.execute(
            base_query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        )
        users = result.scalars().all()

        # 转换为字典格式
        items = []
        for user in users:
            items.append(
                {
                    "id": user.id,
                    "readable_id": user.readable_id,
                    "nickname": user.nickname,
                    "avatar": user.avatar,
                    "email": user.email,
                    "phone": user.phone,
                    "gender": user.gender,
                    "age_group": user.age_group,
                    "description": user.description,
                    "auth_type": user.auth_type,
                    "google_id": user.google_id,
                    "device_id": user.device_id,
                    "system_language": user.system_language,
                    "is_active": user.is_active,
                    "is_superuser": user.is_superuser,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at,
                    "deleted_at": user.deleted_at,
                    "anonymized_at": user.anonymized_at,
                    "deletion_reason": user.deletion_reason,
                }
            )

        has_more = total > skip + len(items)

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": items,
            "has_more": has_more,
        }

    except Exception as e:
        logger.error(f"获取所有用户失败: {str(e)}")
        raise e


async def get_user_connector_count(db: AsyncSession, user_id: str) -> int:
    """
    计算用户的对话数量（与多少个不同agent产生过对话）

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        int: 对话数量
    """
    try:
        from sqlalchemy import distinct, func

        # 查询用户与多少个不同的agent有过聊天
        stmt = select(func.count(distinct(Chat.agent_id))).where(
            Chat.user_id == user_id
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0

        return count

    except Exception as e:
        logger.error(f"计算用户对话数量失败: {str(e)}")
        return 0
