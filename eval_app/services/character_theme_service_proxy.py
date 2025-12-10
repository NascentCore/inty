# CREATED_BY_AGENT
"""
Character Theme 服务代理 - 直接调用主应用的服务层
"""

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.services import character_theme_service


async def list_themes(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    include_hidden: bool = False,
) -> List[schemas.character_theme.CharacterTheme]:
    """获取角色主题列表"""
    themes = await character_theme_service.list_themes(
        db, skip=skip, limit=limit, include_hidden=include_hidden
    )
    return [
        schemas.character_theme.CharacterTheme.model_validate(theme)
        for theme in themes
    ]


async def get_theme(
    db: AsyncSession, theme_id: str
) -> schemas.character_theme.CharacterTheme:
    """获取角色主题详情"""
    theme = await character_theme_service.get_theme(db, theme_id=theme_id)
    return schemas.character_theme.CharacterTheme.model_validate(theme)


async def create_theme(
    db: AsyncSession,
    theme_in: schemas.character_theme.CharacterThemeCreate,
) -> schemas.character_theme.CharacterTheme:
    """创建角色主题"""
    theme = await character_theme_service.create_theme(db, theme_in)
    return schemas.character_theme.CharacterTheme.model_validate(theme)


async def update_theme(
    db: AsyncSession,
    theme_id: str,
    theme_in: schemas.character_theme.CharacterThemeUpdate,
) -> schemas.character_theme.CharacterTheme:
    """更新角色主题"""
    theme = await character_theme_service.update_theme(
        db, theme_id=theme_id, theme_in=theme_in
    )
    return schemas.character_theme.CharacterTheme.model_validate(theme)


async def delete_theme(db: AsyncSession, theme_id: str) -> None:
    """删除角色主题"""
    await character_theme_service.delete_theme(db, theme_id=theme_id)

