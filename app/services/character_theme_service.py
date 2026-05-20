"""角色主题专区服务"""

import uuid
from typing import List, Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent
from app.models.character_theme import CharacterTheme, CharacterThemeAgent
from app.models.character_theme import CharacterThemeVisibility
from app.schemas import character_theme as character_theme_schemas


async def _ensure_visibility_uniqueness(
    db: AsyncSession,
    visibility: CharacterThemeVisibility,
    exclude_theme_id: Optional[str] = None,
) -> None:
    """确保可见性的唯一性约束

    当设置专区为 PRIMARY 或 SECONDARY 时，将其他具有相同可见性的专区改为 HIDDEN

    Args:
        db: 数据库会话
        visibility: 要设置的可见性
        exclude_theme_id: 要排除的专区ID（通常是当前正在更新的专区）
    """
    if visibility == CharacterThemeVisibility.HIDDEN:
        return

    stmt = select(CharacterTheme).where(CharacterTheme.visibility == visibility)
    if exclude_theme_id:
        stmt = stmt.where(CharacterTheme.id != exclude_theme_id)

    result = await db.execute(stmt)
    conflicting_themes = result.scalars().all()

    for theme in conflicting_themes:
        theme.visibility = CharacterThemeVisibility.HIDDEN
        logger.info(
            f"将专区 {theme.id} ({theme.name}) 的可见性从 {visibility} 改为 HIDDEN"
        )


async def create_theme(
    db: AsyncSession, theme_in: character_theme_schemas.CharacterThemeCreate
) -> CharacterTheme:
    """创建角色主题专区"""
    visibility = (
        theme_in.visibility
        if theme_in.visibility is not None
        else CharacterThemeVisibility.HIDDEN
    )

    await _ensure_visibility_uniqueness(db, visibility)

    theme = CharacterTheme(
        id=str(uuid.uuid4()),
        name=theme_in.name,
        description=theme_in.description,
        background_image_url=theme_in.background_image_url,
        visibility=visibility,
    )
    db.add(theme)
    await db.commit()
    await db.refresh(theme)

    # 重新加载 theme 对象，确保 agents 关系被正确加载（即使是空列表）
    stmt = (
        select(CharacterTheme)
        .where(CharacterTheme.id == theme.id)
        .options(
            selectinload(CharacterTheme.agents)
            .selectinload(CharacterThemeAgent.agent)
            .selectinload(Agent.creator)
        )
    )
    result = await db.execute(stmt)
    theme = result.scalar_one()

    logger.info(f"创建角色主题专区: {theme.id} - {theme.name}")
    return theme


async def get_theme(
    db: AsyncSession, theme_id: str
) -> Optional[CharacterTheme]:
    """获取角色主题专区详情（包含角色列表，按 order_index 排序）"""
    stmt = (
        select(CharacterTheme)
        .where(CharacterTheme.id == theme_id)
        .options(
            selectinload(CharacterTheme.agents)
            .selectinload(CharacterThemeAgent.agent)
            .selectinload(Agent.creator)
        )
    )
    result = await db.execute(stmt)
    theme = result.scalar_one_or_none()
    return theme


async def list_themes(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    include_hidden: bool = False,
) -> List[CharacterTheme]:
    """获取角色主题专区列表

    Args:
        db: 数据库会话
        skip: 跳过的记录数
        limit: 返回的记录数
        include_hidden: 是否包含不可见的专区，默认 False（只返回可见专区）
    """
    stmt = select(CharacterTheme)

    if not include_hidden:
        stmt = stmt.where(
            CharacterTheme.visibility.in_(
                [
                    CharacterThemeVisibility.PRIMARY,
                    CharacterThemeVisibility.SECONDARY,
                ]
            )
        )

    stmt = (
        stmt.offset(skip)
        .limit(limit)
        .options(
            selectinload(CharacterTheme.agents)
            .selectinload(CharacterThemeAgent.agent)
            .selectinload(Agent.creator)
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
) -> Optional[CharacterTheme]:
    """更新角色主题专区信息"""
    theme = await get_theme(db, theme_id)
    if not theme:
        return None

    update_data = theme_in.model_dump(exclude_unset=True)

    # 如果更新可见性，需要确保唯一性约束
    if "visibility" in update_data:
        new_visibility = update_data["visibility"]
        if new_visibility is not None:
            await _ensure_visibility_uniqueness(
                db, new_visibility, exclude_theme_id=theme_id
            )

    for field, value in update_data.items():
        setattr(theme, field, value)

    await db.commit()
    await db.refresh(theme)

    # 重新加载 theme 对象，确保 agents 关系被正确加载
    stmt = (
        select(CharacterTheme)
        .where(CharacterTheme.id == theme.id)
        .options(
            selectinload(CharacterTheme.agents)
            .selectinload(CharacterThemeAgent.agent)
            .selectinload(Agent.creator)
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
) -> CharacterThemeAgent:
    """向专区添加角色"""
    # 检查专区是否存在
    theme = await get_theme(db, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme section not found")

    # 检查角色是否存在
    agent_stmt = select(Agent).where(Agent.id == agent_id)
    agent_result = await db.execute(agent_stmt)
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 检查角色是否已在专区中
    existing_stmt = select(CharacterThemeAgent).where(
        CharacterThemeAgent.theme_id == theme_id,
        CharacterThemeAgent.agent_id == agent_id,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400, detail="Agent is already in this theme section"
        )

    # 获取当前最大 order_index
    from sqlalchemy import func

    max_order_stmt = select(func.max(CharacterThemeAgent.order_index)).where(
        CharacterThemeAgent.theme_id == theme_id
    )
    max_order_result = await db.execute(max_order_stmt)
    max_order = max_order_result.scalar()
    next_order = (max_order + 1) if max_order is not None else 0

    # 创建关联记录
    theme_agent = CharacterThemeAgent(
        theme_id=theme_id,
        agent_id=agent_id,
        order_index=next_order,
    )
    db.add(theme_agent)
    await db.commit()
    await db.refresh(theme_agent)

    # 重新加载 theme_agent 对象，确保 agent 关系被正确加载
    stmt = (
        select(CharacterThemeAgent)
        .where(
            CharacterThemeAgent.theme_id == theme_id,
            CharacterThemeAgent.agent_id == agent_id,
        )
        .options(
            selectinload(CharacterThemeAgent.agent).selectinload(Agent.creator)
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
    stmt = select(CharacterThemeAgent).where(
        CharacterThemeAgent.theme_id == theme_id,
        CharacterThemeAgent.agent_id == agent_id,
    )
    result = await db.execute(stmt)
    theme_agent = result.scalar_one_or_none()
    if not theme_agent:
        return False

    await db.delete(theme_agent)
    await db.commit()
    logger.info(f"从专区 {theme_id} 移除角色 {agent_id}")
    return True


async def reorder_agents(
    db: AsyncSession, theme_id: str, agent_ids: List[str]
) -> bool:
    """调整角色顺序"""
    # 检查专区是否存在
    theme = await get_theme(db, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme section not found")

    # 获取专区中所有角色关联记录
    stmt = select(CharacterThemeAgent).where(
        CharacterThemeAgent.theme_id == theme_id
    )
    result = await db.execute(stmt)
    theme_agents = result.scalars().all()

    # 验证 agent_ids 是否与专区中的角色匹配
    existing_agent_ids = {ta.agent_id for ta in theme_agents}
    if set(agent_ids) != existing_agent_ids:
        raise HTTPException(
            status_code=400,
            detail="Agent ID list does not match agents in the theme section",
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
