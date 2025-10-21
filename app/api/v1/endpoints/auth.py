import logging
import traceback
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api.utils.logger_route import LoggerRoute
from app.core.config import API_V1_PREFIX, global_config_loaded_from_config_yaml
from app.core.security import create_access_token
from app.core.uuid import get_new_user_id
from app.db.session import get_async_db
from app.models import User
from app.models.user import AuthType
from app.schemas.auth import GuestResponse, LoginResponse, LoginUserResponse
from app.schemas.response import APIResponse
from app.services.global_services import subscription_service
from app.services.user_service import create_guest_user, generate_next_readable_id

router = APIRouter(prefix="/auth", route_class=LoggerRoute)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_V1_PREFIX}/auth/login")


@router.post("/guest", response_model=APIResponse[GuestResponse])
async def create_guest(
    *,
    db: AsyncSession = Depends(get_async_db),
    guest_in: schemas.GuestRequest,
) -> Any:
    """
    创建游客账号
    """
    try:
        user = await create_guest_user(
            db,
            device_id=guest_in.device_id,
            system_language=guest_in.system_language,
            age_group=guest_in.age_group,
        )
        access_token = create_access_token(user.id)
        return APIResponse.success(
            data=GuestResponse(guest_id=user.id, token=access_token, is_new_guest=True)
        )
    except Exception as e:
        logger.error(f"create guest user error: {str(e)}")
        traceback.print_exc()
        return APIResponse.error(message=str(e))


@router.post("/google/login", response_model=APIResponse[LoginResponse])
async def google_login(
    *,
    db: AsyncSession = Depends(get_async_db),
    login_in: schemas.GoogleAuthRequest,
) -> Any:
    """Google登录"""
    try:
        # 验证 Google ID Token
        idinfo = id_token.verify_oauth2_token(
            login_in.id_token,
            google_requests.Request(),
            global_config_loaded_from_config_yaml.google_oauth.client_id,
        )

        logger.info(f"Google login idinfo: {idinfo}")

        # 验证发行者
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            logger.error(f"invalid google token issuer: {idinfo['iss']}")
            return APIResponse.error(message="invalid google token issuer")

        # 检查用户是否已存在
        stmt = select(User).where(
            and_(User.google_id == idinfo["sub"], User.deleted_at == None)
        )
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user and not existing_user.deleted_at:
            logger.debug(f"Google login user already exists: {existing_user.id}")

            # 尝试恢复孤立的订阅记录
            try:
                recovered_count = (
                    await subscription_service.recover_orphaned_subscriptions(
                        db, existing_user.id, idinfo.get("email"), idinfo["sub"]
                    )
                )
                if recovered_count > 0:
                    logger.info(
                        f"用户 {existing_user.id} 登录时恢复了 {recovered_count} 个订阅"
                    )
            except Exception as e:
                logger.error(f"用户 {existing_user.id} 恢复订阅失败: {str(e)}")
                # 订阅恢复失败不影响登录流程

            # 如果用户已存在且未被删除，直接返回 token
            access_token = create_access_token(existing_user.id)
            return APIResponse.success(
                data=LoginResponse(
                    token=access_token,
                    user=LoginUserResponse(
                        id=existing_user.id,
                        nickname=existing_user.nickname,
                        avatar=existing_user.avatar,
                        email=existing_user.email,
                        phone=existing_user.phone,
                        auth_type=existing_user.auth_type,
                        gender=existing_user.gender,
                        age_group=existing_user.age_group,
                        system_language=existing_user.system_language,
                        is_new_user=False,
                    ),
                )
            )

        # 检查是否已有用户使用相同的邮箱，由于没有 email unique 限制，因此需要检查 email 是否被另一个活跃账户使用
        if idinfo.get("email"):
            logger.debug(
                f"Checking if email is used by another active account: {idinfo['email']}"
            )
            email_stmt = select(User).where(
                and_(User.email == idinfo["email"], User.deleted_at == None)
            )
            email_result = await db.execute(email_stmt)
            existing_email_users = email_result.scalars().all()

            if existing_email_users:
                # 如果邮箱已被使用，返回错误
                return APIResponse.error(
                    message="Email already used by another account"
                )

        # 如果用户不存在或者已被删除，创建新用户
        # 删除的用户重新登录时会创建新的账户

        # 创建新用户
        user_id = get_new_user_id()
        readable_id = await generate_next_readable_id(db)
        new_user = User(
            id=user_id,
            readable_id=readable_id,
            auth_type=AuthType.GOOGLE,
            google_id=idinfo["sub"],
            nickname=idinfo.get("name", f"User_{user_id[:8]}"),
            avatar=idinfo.get("picture"),
            email=idinfo.get("email"),
            system_language=(
                login_in.user_info.system_language if login_in.user_info else "en"
            ),
            is_active=True,
        )

        if login_in.user_info:
            new_user.gender = login_in.user_info.gender
            new_user.age_group = login_in.user_info.age_group

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # 尝试恢复孤立的订阅记录（新用户也可能需要恢复之前的订阅）
        try:
            recovered_count = await subscription_service.recover_orphaned_subscriptions(
                db, new_user.id, idinfo.get("email"), idinfo["sub"]
            )
            if recovered_count > 0:
                logger.info(f"新用户 {new_user.id} 恢复了 {recovered_count} 个历史订阅")
        except Exception as e:
            logger.error(f"新用户 {new_user.id} 恢复订阅失败: {str(e)}")
            # 订阅恢复失败不影响注册流程

        # 生成 token
        access_token = create_access_token(new_user.id)
        return APIResponse.success(
            data=LoginResponse(
                token=access_token,
                user=LoginUserResponse(
                    id=new_user.id,
                    nickname=new_user.nickname,
                    avatar=new_user.avatar,
                    email=new_user.email,
                    phone=new_user.phone,
                    auth_type=new_user.auth_type,
                    gender=new_user.gender,
                    age_group=new_user.age_group,
                    system_language=new_user.system_language,
                    is_new_user=True,
                ),
            )
        )
    except ValueError as e:
        logger.error(f"Google login error: {str(e)}")
        return APIResponse.error(message="Invalid Google ID token")
    except Exception as e:
        logger.error(f"Google login error: {str(e)}")
        return APIResponse.error(message=str(e))
