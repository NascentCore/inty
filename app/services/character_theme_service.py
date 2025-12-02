"""角色主题专区服务"""

import uuid
from typing import List, Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models
from app.schemas import character_theme as character_theme_schemas


async def create_theme(
    db: AsyncSession, theme_in: character_theme_schemas.CharacterThemeCreate
) -> models.CharacterTheme:
    """创建角色主题专区"""
    theme = models.CharacterTheme(
        id=str(uuid.uuid4()),
        name=theme_in.name,
        description=theme_in.description,
        background_image_url=theme_in.background_image_url,
    )
    db.add(theme)
    await db.commit()
    await db.refresh(theme)

    # 重新加载 theme 对象，确保 agents 关系被正确加载（即使是空列表）
    stmt = (
        select(models.CharacterTheme)
        .where(models.CharacterTheme.id == theme.id)
        .options(
            selectinload(models.CharacterTheme.agents)
            .selectinload(models.CharacterThemeAgent.agent)
            .selectinload(models.Agent.creator)
        )
    )
    result = await db.execute(stmt)
    theme = result.scalar_one()

    logger.info(f"创建角色主题专区: {theme.id} - {theme.name}")
    return theme


async def get_theme(db: AsyncSession, theme_id: str) -> Optional[models.CharacterTheme]:
    """获取角色主题专区详情（包含角色列表，按 order_index 排序）"""
    stmt = (
        select(models.CharacterTheme)
        .where(models.CharacterTheme.id == theme_id)
        .options(
            selectinload(models.CharacterTheme.agents)
            .selectinload(models.CharacterThemeAgent.agent)
            .selectinload(models.Agent.creator)
        )
    )
    result = await db.execute(stmt)
    theme = result.scalar_one_or_none()
    return theme


async def list_themes(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[models.CharacterTheme]:
    """获取角色主题专区列表"""
    stmt = (
        select(models.CharacterTheme)
        .offset(skip)
        .limit(limit)
        .options(
            selectinload(models.CharacterTheme.agents)
            .selectinload(models.CharacterThemeAgent.agent)
            .selectinload(models.Agent.creator)
        )
    )
    result = await db.execute(stmt)
    themes = result.scalars().all()

    # 显式访问所有关系，确保它们被加载到内存中
    for theme in themes:
        for theme_agent in theme.agents:
            # 访问 agent 关系，确保它被加载
            _ = theme_agent.agent

    return list(themes)


async def update_theme(
    db: AsyncSession,
    theme_id: str,
    theme_in: character_theme_schemas.CharacterThemeUpdate,
) -> Optional[models.CharacterTheme]:
    """更新角色主题专区信息"""
    theme = await get_theme(db, theme_id)
    if not theme:
        return None

    update_data = theme_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(theme, field, value)

    await db.commit()
    await db.refresh(theme)

    # 重新加载 theme 对象，确保 agents 关系被正确加载
    stmt = (
        select(models.CharacterTheme)
        .where(models.CharacterTheme.id == theme.id)
        .options(
            selectinload(models.CharacterTheme.agents)
            .selectinload(models.CharacterThemeAgent.agent)
            .selectinload(models.Agent.creator)
        )
    )
    result = await db.execute(stmt)
    theme = result.scalar_one()

    logger.info(f"更新角色主题专区: {theme.id} - {theme.name}")
    return theme


async def delete_theme(db: AsyncSession, theme_id: str) -> bool:
    """删除角色主题专区"""
    theme = await get_theme(db, theme_id)
    if not theme:
        return False

    await db.delete(theme)
    await db.commit()
    logger.info(f"删除角色主题专区: {theme_id}")
    return True


async def add_agent_to_theme(
    db: AsyncSession, theme_id: str, agent_id: str
) -> models.CharacterThemeAgent:
    """向专区添加角色"""
    # 检查专区是否存在
    theme = await get_theme(db, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="专区不存在")

    # 检查角色是否存在
    agent_stmt = select(models.Agent).where(models.Agent.id == agent_id)
    agent_result = await db.execute(agent_stmt)
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 检查角色是否已在专区中
    existing_stmt = select(models.CharacterThemeAgent).where(
        models.CharacterThemeAgent.theme_id == theme_id,
        models.CharacterThemeAgent.agent_id == agent_id,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="角色已在该专区中")

    # 获取当前最大 order_index
    from sqlalchemy import func

    max_order_stmt = select(func.max(models.CharacterThemeAgent.order_index)).where(
        models.CharacterThemeAgent.theme_id == theme_id
    )
    max_order_result = await db.execute(max_order_stmt)
    max_order = max_order_result.scalar()
    next_order = (max_order + 1) if max_order is not None else 0

    # 创建关联记录
    theme_agent = models.CharacterThemeAgent(
        theme_id=theme_id,
        agent_id=agent_id,
        order_index=next_order,
    )
    db.add(theme_agent)
    await db.commit()
    await db.refresh(theme_agent)

    # 重新加载 theme_agent 对象，确保 agent 关系被正确加载
    stmt = (
        select(models.CharacterThemeAgent)
        .where(
            models.CharacterThemeAgent.theme_id == theme_id,
            models.CharacterThemeAgent.agent_id == agent_id,
        )
        .options(
            selectinload(models.CharacterThemeAgent.agent).selectinload(
                models.Agent.creator
            )
        )
    )
    result = await db.execute(stmt)
    theme_agent = result.scalar_one()

    logger.info(f"向专区 {theme_id} 添加角色 {agent_id}，顺序: {next_order}")
    return theme_agent


async def remove_agent_from_theme(
    db: AsyncSession, theme_id: str, agent_id: str
) -> bool:
    """从专区移除角色"""
    stmt = select(models.CharacterThemeAgent).where(
        models.CharacterThemeAgent.theme_id == theme_id,
        models.CharacterThemeAgent.agent_id == agent_id,
    )
    result = await db.execute(stmt)
    theme_agent = result.scalar_one_or_none()
    if not theme_agent:
        return False

    await db.delete(theme_agent)
    await db.commit()
    logger.info(f"从专区 {theme_id} 移除角色 {agent_id}")
    return True


async def reorder_agents(db: AsyncSession, theme_id: str, agent_ids: List[str]) -> bool:
    """调整角色顺序"""
    # 检查专区是否存在
    theme = await get_theme(db, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="专区不存在")

    # 获取专区中所有角色关联记录
    stmt = select(models.CharacterThemeAgent).where(
        models.CharacterThemeAgent.theme_id == theme_id
    )
    result = await db.execute(stmt)
    theme_agents = result.scalars().all()

    # 验证 agent_ids 是否与专区中的角色匹配
    existing_agent_ids = {ta.agent_id for ta in theme_agents}
    if set(agent_ids) != existing_agent_ids:
        raise HTTPException(
            status_code=400,
            detail="角色ID列表与专区中的角色不匹配",
        )

    # 创建 agent_id 到 theme_agent 的映射
    agent_map = {ta.agent_id: ta for ta in theme_agents}

    # 更新顺序
    for order_index, agent_id in enumerate(agent_ids):
        theme_agent = agent_map[agent_id]
        theme_agent.order_index = order_index

    await db.commit()
    logger.info(f"调整专区 {theme_id} 的角色顺序")
    return True
