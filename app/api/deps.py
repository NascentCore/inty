"""
依赖注入：为 FastAPI 接口处理函数注入依赖数据。
"""

from typing import Generator, Optional

from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.db.base import SessionLocal
from app.db.session import get_async_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _get_bearer_token_from_authorization_header(
    authorization: Optional[str],
) -> Optional[str]:
    if not authorization:
        return None

    prefix = "bearer "
    if authorization.lower().startswith(prefix):
        token = authorization[len(prefix) :].strip()
        return token or None

    return None


async def get_current_user_from_token(token: str, db: AsyncSession) -> User:
    """从 token 获取当前用户（可复用在 WebSocket/HTTP 场景）。"""
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
        user = await db.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()

        if not user:
            logger.error(f"数据库中未找到用户: {user_id}")
            raise credentials_exception

        return user

    except Exception as db_error:
        logger.error(f"数据库查询失败: {str(db_error)}")
        logger.error(f"数据库错误类型: {type(db_error).__name__}")
        import traceback

        logger.error(f"数据库错误堆栈: {traceback.format_exc()}")
        raise credentials_exception


def get_db() -> Generator:
    """获取数据库会话（同步版本，另有 async 版本）"""
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_async_db)
) -> User:
    """获取当前用户"""
    return await get_current_user_from_token(token, db)


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


async def get_current_active_user_ws(
    websocket: WebSocket, db: AsyncSession = Depends(get_async_db)
) -> User:
    """
    WebSocket 鉴权：优先取 `Authorization: Bearer <token>`，其次取查询参数 `token`。
    """
    authorization = websocket.headers.get("authorization")
    token = _get_bearer_token_from_authorization_header(authorization)

    if not token:
        token = websocket.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_current_user_from_token(token, db)
    # 复用 active 检查逻辑
    if user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account has been deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
