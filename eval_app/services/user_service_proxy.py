# CREATED_BY_AGENT
"""
User 服务代理 - 直接调用主应用的服务层
"""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.services import user_service


async def search_users(
    db: AsyncSession,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> schemas.PaginationData[schemas.User]:
    """搜索用户列表"""
    return await user_service.search_users(
        db, search=search, skip=skip, limit=limit
    )

