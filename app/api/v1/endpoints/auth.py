import traceback
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.constants import API_V1_PREFIX
from app.api.tags import ANDROID_APP_TAG, WEB_APP_TAG
from app.api.utils.logger_route import LoggerRoute
from app.core.config import global_config_loaded_from_config_yaml
from app.core.security import create_access_token, verify_password
from app.core.uuid import get_new_user_id
from app.db.session import get_async_db
from app.models.user import User
from app.models.user import AuthType
from app.schemas.auth import GuestResponse, LoginResponse, LoginUserResponse
from app.schemas.response import APIResponse
from app.services.global_services import subscription_service
from app.services.user_service import create_guest_user, generate_next_readable_id
from app.schemas.auth import GoogleAuthRequest
from app.schemas.auth import GuestRequest

router = APIRouter(prefix="/auth", route_class=LoggerRoute)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_V1_PREFIX}/auth/login")


@router.post("/guest", response_model=APIResponse[GuestResponse], tags=[WEB_APP_TAG])
async def create_guest(
    *,
    db: AsyncSession = Depends(get_async_db),
    guest_in: GuestRequest,
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


@router.post(
    "/google/login",
    response_model=APIResponse[LoginResponse],
    tags=[ANDROID_APP_TAG, WEB_APP_TAG],
)
async def google_login(
    *,
    db: AsyncSession = Depends(get_async_db),
    login_in: GoogleAuthRequest,
) -> Any:
    """
    两种登录二选一（请求体在 `GoogleAuthRequest` 中互斥校验）：

    - 仅 `id_token`：Google OAuth
    - 仅 `email` + `password`：邮箱密码（不走 Google 验证）
    """
    if (
        global_config_loaded_from_config_yaml.app.api_endpoints.use_dummy_api_v1_auth_google_login
    ):
        # 你可以这样在 python 代码中访问 API endpoint 的路径：
        # 1. 直接查看 router 的 prefix 和装饰器参数：
        #    此接口路径由 router.prefix + 装饰器 url 拼接得到，即 "/auth" + "/google/login" = "/auth/google/login"
        # 2. 如果你需要在 FastAPI 内部动态获取当前端点的 path，可以在依赖项中通过 fastapi.Request:
        #    示例:
        #    from fastapi import Request
        #    @router.post("/google/login")
        #    async def google_login(..., request: Request):
        #        path = request.url.path
        #        print(path)  # 输出当前请求的完整 path
        logger.info(f"### 使用虚假的 Google 登录接口 {router.prefix}/google/login ###")
        logger.info(f"### 修改下方定义直接改变返回值 ###")
        return APIResponse.success(
            data=LoginResponse(
                token="dummy_token",
                user=LoginUserResponse(
                    id="dummy_user_id",
                    nickname="Dummy User",
                    avatar="dummy_avatar",
                    email="dummy@example.com",
                    phone="dummy_phone",
                    auth_type=AuthType.GOOGLE,
                    gender="male",
                    age_group="adult",
                    system_language="en",
                    description="Dummy User",
                    is_new_user=True,
                ),
            )
        )
    try:
        # 如果提供了 email 和 password，使用 email + password 登录
        if login_in.email and login_in.password:
            return await email_password_login(db, login_in.email, login_in.password)

        # 否则使用 Google ID token 登录（向后兼容）
        if not login_in.id_token:
            return APIResponse.error(
                message="Either id_token or email+password must be provided"
            )

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
                        description=existing_user.description,
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
                    description=new_user.description,
                    is_new_user=True,
                ),
            )
        )
    except ValueError as e:
        logger.error(f"Google login error: {str(e)}")
        return APIResponse.error(message="Invalid Google ID token")
    except ValidationError as e:
        logger.error(f"Google login validation error: {str(e)}")
        logger.error(f"Validation error details: {e.errors()}")
        return APIResponse.error(
            message=f"Invalid response data: {', '.join([err['msg'] for err in e.errors()])}"
        )
    except Exception as e:
        logger.error(f"Google login error: {str(e)}")
        logger.error(f"Error stack: {traceback.format_exc()}")
        return APIResponse.error(message=str(e))


async def email_password_login(
    db: AsyncSession,
    email: str,
    password: str,
) -> APIResponse[LoginResponse]:
    """Email + Password 登录"""
    try:
        # 验证 email 格式
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            logger.error(f"Invalid email format: {email}")
            return APIResponse.error(message="Invalid email format")

        # 查询用户
        stmt = select(User).where(
            and_(
                User.email == email,
                User.deleted_at == None,
                User.auth_type == AuthType.EMAIL,
            )
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User not found with email: {email}")
            return APIResponse.error(message="Invalid Email password combination")

        # 验证密码
        if not user.password:
            logger.error(f"User {user.id} has no password set")
            return APIResponse.error(message="Invalid Email password combination")

        if not verify_password(password, user.password):
            logger.error(f"Invalid password for user: {user.id}")
            return APIResponse.error(message="Invalid Email password combination")

        # 尝试恢复孤立的订阅记录
        try:
            recovered_count = await subscription_service.recover_orphaned_subscriptions(
                db, user.id, email, None
            )
            if recovered_count > 0:
                logger.info(f"用户 {user.id} 登录时恢复了 {recovered_count} 个订阅")
        except Exception as e:
            logger.error(f"用户 {user.id} 恢复订阅失败: {str(e)}")
            # 订阅恢复失败不影响登录流程

        # 生成 token
        access_token = create_access_token(user.id)
        return APIResponse.success(
            data=LoginResponse(
                token=access_token,
                user=LoginUserResponse(
                    id=user.id,
                    nickname=user.nickname,
                    avatar=user.avatar,
                    email=user.email,
                    phone=user.phone,
                    auth_type=user.auth_type,
                    gender=user.gender,
                    age_group=user.age_group,
                    system_language=user.system_language,
                    description=user.description,
                    is_new_user=False,
                ),
            )
        )
    except Exception as e:
        logger.error(f"Email password login error: {str(e)}")
        logger.error(f"Error stack: {traceback.format_exc()}")
        return APIResponse.error(message=str(e))
