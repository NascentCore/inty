"""
依赖注入：为 FastAPI 接口处理函数注入依赖数据。
"""

from typing import Any, Dict, Generator, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.db.base import SessionLocal
from app.db.session import get_async_db, get_async_replica_db
from app.models.user import User
from app.services.cache_service import cache_service
from app.services.global_services import subscription_service
from app.services.subscription_service import SubscriptionService
from app.services.voice_service import VoiceService, voice_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
USER_AUTH_SNAPSHOT_TTL_SECONDS = 60


def get_db() -> Generator:
    """获取数据库会话（同步版本，另有 async 版本）"""
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_subscription_service() -> SubscriptionService:
    return subscription_service


def get_voice_service() -> VoiceService:
    return voice_service


def _build_user_auth_snapshot(user: User) -> Dict[str, Any]:
    return {
        column.name: getattr(user, column.name) for column in User.__table__.columns
    }


def _cache_user_auth_snapshot(user: User) -> None:
    try:
        cache_service.set_user_auth_snapshot(
            user.id,
            _build_user_auth_snapshot(user),
            ttl=USER_AUTH_SNAPSHOT_TTL_SECONDS,
        )
    except Exception as cache_error:
        logger.warning(f"写入用户鉴权快照缓存失败: {cache_error}")


def _get_user_from_auth_snapshot(
    user_id: str, credentials_exception: HTTPException
) -> User | None:
    # 关键步骤：先查 user_auth_snapshot；命中则直接恢复 User，miss 再回源数据库。
    cached_snapshot = cache_service.get_user_auth_snapshot(user_id)
    if cached_snapshot is None:
        return None
    if cached_snapshot.get("deleted_at"):
        logger.error(f"缓存中用户已删除: {user_id}")
        raise credentials_exception
    try:
        return User(**cached_snapshot)
    except Exception as cache_error:
        logger.warning(
            f"恢复用户鉴权快照失败，回源数据库: user_id={user_id}, error={cache_error}"
        )
        cache_service.invalidate_user_auth_snapshot(user_id)
        return None


def _get_user_from_auth_snapshot_for_websocket_token(user_id: str) -> User | None:
    """
    WebSocket token 鉴权用快照：与 HTTP 路径不同，不得在已 accept 的 WS 上抛 HTTPException，
    否则 Starlette 无法把 401 当作 HTTP 响应写出，会升级为 ASGI 异常（prod 日志已见）。
    缓存标记已删除时返回 None，由路由层 websocket.close 处理。
    """
    cached_snapshot = cache_service.get_user_auth_snapshot(user_id)
    if cached_snapshot is None:
        return None
    if cached_snapshot.get("deleted_at"):
        logger.warning(
            "WebSocket token auth: user marked deleted in auth snapshot cache "
            f"user_id={user_id}"
        )
        return None
    try:
        return User(**cached_snapshot)
    except Exception as cache_error:
        logger.warning(
            "WebSocket token auth: failed to restore user from snapshot "
            f"user_id={user_id} error={cache_error}"
        )
        cache_service.invalidate_user_auth_snapshot(user_id)
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_async_db)
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            global_config_loaded_from_config_yaml.security.secret_key,
            algorithms=[global_config_loaded_from_config_yaml.security.algorithm],
        )

        user_id: str = payload.get("sub")

        if user_id is None:
            logger.error("payload中没有找到sub字段")
            raise credentials_exception

    except JWTError as jwt_error:
        if isinstance(jwt_error, ExpiredSignatureError):
            logger.warning(
                f"JWT已过期: {str(jwt_error)} (类型: {type(jwt_error).__name__})"
            )
        else:
            logger.error(f"JWT解码失败: {str(jwt_error)}")
            logger.error(f"JWT错误类型: {type(jwt_error).__name__}")
        raise credentials_exception
    except ValidationError as validation_error:
        logger.error(f"Token验证失败: {str(validation_error)}")
        logger.error(f"验证错误类型: {type(validation_error).__name__}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Token验证过程中发生未知错误: {str(e)}")
        logger.error(f"错误类型: {type(e).__name__}")
        import traceback

        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise credentials_exception

    try:
        cached_user = _get_user_from_auth_snapshot(user_id, credentials_exception)
        if cached_user is not None:
            return cached_user

        user = await db.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()

        if not user:
            logger.error(f"数据库中未找到用户: {user_id}")
            raise credentials_exception

        _cache_user_auth_snapshot(user)
        return user

    except Exception as db_error:
        logger.error(f"数据库查询失败: {str(db_error)}")
        logger.error(f"数据库错误类型: {type(db_error).__name__}")
        import traceback

        logger.error(f"数据库错误堆栈: {traceback.format_exc()}")
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户"""
    # 检查用户是否已被删除
    if current_user.deleted_at:
        logger.error(
            f"用户已被删除: {current_user.id}, 删除时间: {current_user.deleted_at}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account has been deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"用户活跃状态检查通过: {current_user.id}")
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """要求当前用户为超级用户，否则抛出 403。"""
    if db is None:
        # 测试场景下可能通过 dependency override 注入 None；保持向后兼容。
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can access this endpoint",
            )
        return current_user

    # 关键步骤：超级用户权限属于安全敏感检查，这里始终以数据库最新值为准，避免缓存短暂陈旧。
    result = await db.execute(select(User).where(User.id == current_user.id))
    latest_user = result.scalar_one_or_none()

    if latest_user is None or latest_user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account has been deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _cache_user_auth_snapshot(latest_user)

    if not latest_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can access this endpoint",
        )
    return latest_user


async def get_effective_user_for_eval(
    current_user: User = Depends(get_current_active_user),
    x_assume_user_id: Optional[str] = Header(None, alias="X-Assume-User-Id"),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    For evaluation: return the user to act as.
    If X-Assume-User-Id is set and current user is superuser, load and return that user;
    otherwise return current_user. Used so chat/voice in evaluation can load another user's history.
    """
    if not x_assume_user_id or not x_assume_user_id.strip():
        return current_user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can assume another user identity",
        )
    user_id = x_assume_user_id.strip()
    row = await db.execute(select(User).where(User.id == user_id))
    user = row.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {user_id}",
        )
    if user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User has been deleted",
        )
    return user


async def get_user_from_token(token: str, db: AsyncSession) -> User | None:
    """
    从 token 获取用户（供 WebSocket 使用）

    与 get_current_user 类似，但接受 token 字符串而非依赖注入。
    鉴权失败返回 None（不抛 HTTPException），避免在 WebSocket 已 accept 后
    触发 Starlette 将 401 当作 HTTP 响应写入 WS 连接而导致 RuntimeError。
    """
    try:
        payload = jwt.decode(
            token,
            global_config_loaded_from_config_yaml.security.secret_key,
            algorithms=[global_config_loaded_from_config_yaml.security.algorithm],
        )

        user_id: str = payload.get("sub")
        if user_id is None:
            return None

    except JWTError as jwt_error:
        if isinstance(jwt_error, ExpiredSignatureError):
            logger.warning(
                f"JWT已过期(WebSocket token): {jwt_error} (类型: {type(jwt_error).__name__})"
            )
        else:
            logger.warning(
                f"JWT解码失败(WebSocket token): {jwt_error} (类型: {type(jwt_error).__name__})"
            )
        return None

    cached_user = _get_user_from_auth_snapshot_for_websocket_token(user_id)
    if cached_user is not None:
        return cached_user

    user = await db.execute(select(User).where(User.id == user_id))
    user = user.scalar_one_or_none()

    if not user:
        return None

    if user.deleted_at:
        return None

    _cache_user_auth_snapshot(user)
    return user
