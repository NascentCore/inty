"""
依赖注入：为 FastAPI 接口处理函数注入依赖数据。
"""

import logging
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import deprecated

from app import models, schemas
from app.core import security
from app.core.config import global_config_loaded_from_config_yaml
from app.db.base import SessionLocal
from app.db.session import get_async_db
from app.models.user import User
from app.schemas.token import TokenPayload

from loguru import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@deprecated("Use app.db.session get_async_db instead")
def get_db() -> Generator:
    """获取数据库会话"""
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


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


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        logger.error(f"用户未激活: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

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
