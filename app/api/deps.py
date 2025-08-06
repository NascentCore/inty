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
from app.core.config import settings
from app.db.base import SessionLocal
from app.db.session import get_async_db
from app.models.user import User
from app.schemas.token import TokenPayload

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.app.api_v1_prefix}/auth/login"
)


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
    logger.debug(f"=== 开始验证用户token ===")
    logger.debug(f"Token长度: {len(token) if token else 0}")
    logger.debug(
        f"Token前缀: {token[:20] + '...' if token and len(token) > 20 else token}"
    )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        logger.debug(f"开始解码JWT token")
        logger.debug(
            f"使用密钥: {settings.security.secret_key[:10] + '...' if settings.security.secret_key else 'None'}"
        )
        logger.debug(f"使用算法: {settings.security.algorithm}")

        payload = jwt.decode(
            token,
            settings.security.secret_key,
            algorithms=[settings.security.algorithm],
        )
        logger.debug(f"JWT解码成功，payload: {payload}")

        user_id: str = payload.get("sub")
        logger.debug(f"从payload中提取user_id: {user_id}")

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

    logger.debug(f"开始查询用户: {user_id}")
    try:
        user = await db.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()
        logger.debug(f"用户查询结果: {'找到用户' if user else '用户不存在'}")

        if not user:
            logger.error(f"数据库中未找到用户: {user_id}")
            raise credentials_exception

        logger.debug(
            f"用户验证成功: {user.id}, 昵称: {user.nickname}, 是否激活: {user.is_active}"
        )
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
    logger.debug(f"=== 检查用户活跃状态 ===")
    logger.debug(f"用户ID: {current_user.id}")
    logger.debug(f"用户昵称: {current_user.nickname}")
    logger.debug(f"用户是否激活: {current_user.is_active}")
    logger.debug(f"用户删除时间: {current_user.deleted_at}")

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
