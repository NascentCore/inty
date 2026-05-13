import traceback
import uuid
from datetime import UTC, datetime
from typing import Optional

from loguru import logger
from sqlalchemy import and_, func, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from typing_extensions import deprecated

from app.core.config import global_config_loaded_from_config_yaml
from app.core.uuid import get_new_user_id
from app.models.user import User
from app.models.chat import Chat
from app.models.subscription import SubscriptionStatus, UserSubscription
from app.models.user import AuthType, DeviceToken
from app.schemas.user import UserUpdate
from app.services.cache_service import cache_service
from app.services.subscription_service import SubscriptionService


def _invalidate_user_related_cache(user_id: str) -> None:
    cache_service.invalidate_user_info(user_id)
    cache_service.invalidate_user_auth_snapshot(user_id)


@deprecated("app 不在显示 readable_id 字段，请使用 id 字段")
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

        user_id = get_new_user_id()
        readable_id = await generate_next_readable_id(db)

        user = User(
            id=user_id,
            readable_id=readable_id,
            auth_type=AuthType.GUEST,
            device_id=device_id,
            nickname=f"Guest_{user_id[-8:]}",
            system_language=system_language or "en",
            age_group=age_group,
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

        # 处理头像URL：如果是CDN URL则转换为GCS URL用于存储
        if "avatar" in update_data and update_data["avatar"]:
            from app.services.image_transform_service import image_transform_service

            update_data["avatar"] = (
                image_transform_service.normalize_image_url_for_storage(
                    update_data["avatar"]
                )
            )

        # 处理用户自拍照片URL：同样转换为GCS URL用于存储
        if "user_photo" in update_data and update_data["user_photo"]:
            from app.services.image_transform_service import image_transform_service

            update_data["user_photo"] = (
                image_transform_service.normalize_image_url_for_storage(
                    update_data["user_photo"]
                )
            )

        # 过滤掉不应该被用户更新的字段
        excluded_fields = {
            "readable_id",
            "id",
            "auth_type",
            "is_superuser",
            "created_at",
            "updated_at",
        }
        update_data = {k: v for k, v in update_data.items() if k not in excluded_fields}

        # 过滤掉值为 None 或空字符串的字段，防止误清空数据库中的有效数据
        # 这样可以保护已有数据不被客户端误传的 None 值覆盖
        update_data = {
            k: v for k, v in update_data.items() if v is not None and v != ""
        }

        user_photo_changed = (
            "user_photo" in update_data and update_data["user_photo"] != user.user_photo
        )
        selfie_persona_feature_enabled = (
            global_config_loaded_from_config_yaml.app.features.enable_selfie_persona_summary
        )

        for field, value in update_data.items():
            setattr(user, field, value)

        if user_photo_changed:
            # 自拍更新后先清空旧结论，避免出现与当前自拍不一致的旧画像结论。
            user.selfie_persona_summary = None

        await db.commit()
        await db.refresh(user)

        # 关键步骤：资料更新后同时失效 user_info 与 user_auth_snapshot，避免读到旧鉴权状态/资料。
        _invalidate_user_related_cache(user_id)
        logger.debug(f"已清除用户 {user_id} 的缓存信息与鉴权快照")

        if selfie_persona_feature_enabled and user_photo_changed and user.user_photo:
            from app.services.selfie_persona_service import selfie_persona_service

            selfie_persona_service.enqueue_selfie_persona_inference(
                user_id=user_id,
                user_photo_url=user.user_photo,
            )

        return user
    except Exception as e:
        logger.error(f"Failed to update user information: {str(e)}")
        logger.error(f"Error stack: {traceback.format_exc()}")
        raise e


async def update_user_last_android_app_version_code(
    db: AsyncSession, user_id: str, version_code: int
) -> None:
    """Update the user's last reported Android app version code. Used for push-worker feature gating."""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(last_android_app_version_code=version_code)
    )
    await db.commit()


def generate_avatar_path(user_id: str, filename: str) -> str:
    ext = filename.split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        raise ValueError(f"Unsupported file type: {ext}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"avatars/{user_id}/avatar-{timestamp}-{unique_id}.{ext}"


GENDER_DISPLAY_MAP = {"MALE": "Male", "FEMALE": "Female", "OTHER": "Other"}


async def get_user_display_name_for_prompt(db: AsyncSession, user_id: str) -> str:
    """
    获取用于提示词渲染的用户显示名（如 personality/scenario 中的 {{ user }}）。
    用于图片生成等需要与 char 一起渲染 Jinja2 模板的场景。
    """
    if not user_id:
        return "the user"
    try:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        if user and user.nickname and user.nickname.strip():
            return user.nickname.strip()
    except SQLAlchemyError as e:
        logger.debug(
            "get_user_display_name_for_prompt: user_id={}, error={}", user_id, e
        )
    return "the user"


async def build_user_info_prompt_block(db: AsyncSession, user_id: str) -> str:
    """
    构建用户信息文本块，用于图片生成提示词。
    优先从缓存读取基础块，未命中时查询数据库并写回缓存；再追加 ##User Memory（不缓存）。
    """
    from app.services.memory_service import get_user_memory_for_prompt_async

    selfie_persona_feature_enabled = (
        global_config_loaded_from_config_yaml.app.features.enable_selfie_persona_summary
    )
    cached = cache_service.get_user_info(user_id)
    if cached is not None:
        user_info_text = cached
    else:
        user_info_text = ""
        try:
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalars().first()

            if not user:
                cache_service.set_user_info(user_id, "", ttl=60)
            else:
                parts = []
                if user.nickname:
                    parts.append(f"Name: {user.nickname}")
                if user.gender:
                    parts.append(
                        f"Gender: {GENDER_DISPLAY_MAP.get(user.gender.value, user.gender.value)}"
                    )
                if user.age_group:
                    parts.append(f"Age: {user.age_group}")
                if user.description:
                    parts.append(f"Description: {user.description}")
                if selfie_persona_feature_enabled and user.selfie_persona_summary:
                    parts.append(f"Selfie Persona: {user.selfie_persona_summary}")
                user_info_text = (
                    "##User Information\n" + "\n".join(parts) if parts else ""
                )
                cache_service.set_user_info(user_id, user_info_text)

        except Exception as e:
            logger.error(f"构建用户信息块失败: user_id={user_id}, error={e}")
            cache_service.set_user_info(user_id, "", ttl=30)

    memory_text = await get_user_memory_for_prompt_async(db, user_id)
    if memory_text:
        user_info_text = (user_info_text or "") + "\n\n##User Memory\n" + memory_text
    return user_info_text


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

        # 清除用户的无效 token 标记（如果存在）
        # 因为用户注册了新 token，说明现在有有效 token 了
        user_stmt = (
            update(User)
            .where(User.id == user_id)
            .where(User.fcm_token_invalid_at.isnot(None))
            .values(fcm_token_invalid_at=None)
        )
        await db.execute(user_stmt)

        await db.commit()
        await db.refresh(device_token)

        # 记录日志
        logger.debug(
            f"用户注册新 device token，已清除无效标记: user_id={user_id}, token={token[:20]}..."
        )

        return device_token

    except Exception as e:
        raise e


async def get_users_device_tokens(db: AsyncSession, user_ids: list[str]) -> list[str]:
    """Get the latest device token for each user

    Args:
        db: Database session
        user_ids: List of user IDs

    Returns:
        list[str]: List of device tokens (one per user, the latest one), returns empty list if no records found
    """
    try:
        # 使用窗口函数获取每个用户最新的 token（按 updated_at 降序排序）
        # 为每个用户的 token 按 updated_at 降序编号，然后选择编号为 1 的（即最新的）
        row_number = (
            func.row_number()
            .over(
                partition_by=DeviceToken.user_id, order_by=DeviceToken.updated_at.desc()
            )
            .label("rn")
        )

        subquery = (
            select(DeviceToken.token, DeviceToken.user_id, row_number).where(
                DeviceToken.user_id.in_(user_ids)
            )
        ).subquery()

        stmt = select(subquery.c.token).where(subquery.c.rn == 1)
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
    subscription_service: SubscriptionService,
    deletion_reason: str = "用户主动删除",
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

        # 提交用户数据更改
        await db.commit()
        await db.refresh(user)
        _invalidate_user_related_cache(user_id)

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
