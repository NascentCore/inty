"""
将数据库中的 agent 记录转换为面向客户端端 agent 数据对象。
"""

import math
import uuid
from dataclasses import dataclass
from typing import List, Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import Integer, and_, desc, func, or_, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing_extensions import deprecated

from app import models, schemas
from app.core.agent.agent import agent_manager
from app.core.agent.prompt_template import (
    has_template_variable,
    render_prompt_jinja2_template,
)
from app.external_services.gcs import (
    append_filename_suffix,
    download_from_gcs,
    get_bucket_and_path_from_gcs_url,
    is_valid_gcs_url,
    upload_to_gcs,
)
from app.models.agent import AgentVisibility
from app.models.associations import agent_followers
from app.schemas.agent import AgentSortOption
from app.schemas.exclude_fields import EXCLUDE_FIELDS
from app.services.cache_service import cache_service
from app.services.image_transform_service import image_transform_service
from app.services.resource_service import async_create_image_resource
from app.services.voice_service import GENDER_VOICE_MAPPING, VoiceService
from app.utils.crop_avatar import CROPPED_AVATAR_FILENAME_SUFFIX, crop_avatar
from app.utils.image import ImageFormat, ImageSize, get_jpg_bytes_from_pil_image


async def _populate_agent_image_sizes(db: AsyncSession, agent: models.Agent) -> None:
    """
    从 resources 表填充 agent 的 avatar_size 和 background_size
    """
    # 查询 avatar 和 background 对应的资源信息
    resource_urls = []
    if agent.avatar:
        resource_urls.append(agent.avatar)
    if agent.background:
        resource_urls.append(agent.background)

    if not resource_urls:
        return
    logger.debug(f"Agent {agent.id} Resource URLs: {resource_urls}")
    # 查询 resources 表获取图片尺寸信息
    query = select(models.Resource).where(models.Resource.url.in_(resource_urls))

    result = await db.execute(query)
    resources = result.scalars().all()
    logger.debug(f"Agent {agent.id} Image resources: {resources}")

    # 创建 URL 到资源的映射
    resource_map = {resource.url: resource for resource in resources}

    # 填充 avatar_size
    if agent.avatar in resource_map:
        resource = resource_map[agent.avatar]
        size_data = resource.resource_metadata["size"]
        agent.avatar_size = ImageSize(
            width=size_data["width"], height=size_data["height"]
        )

    # 填充 background_size
    if agent.background in resource_map:
        resource = resource_map[agent.background]
        size_data = resource.resource_metadata["size"]
        agent.background_size = ImageSize(
            width=size_data["width"], height=size_data["height"]
        )


async def generate_agent_opening_voice(
    agent: models.Agent, db: AsyncSession
) -> Optional[str]:
    """
    为Agent生成开场白语音并返回音频URL
    """
    try:
        if not agent.opening or not agent.opening.strip():
            logger.debug(f"Agent {agent.id} 没有开场白文本，跳过语音生成")
            return None

        opening = agent.opening
        if has_template_variable(opening):
            # 将角色名字替换为实际字符，user 则替换为 you（假设英文）。
            opening = render_prompt_jinja2_template(
                opening, char=agent.name, user="you"
            )

        # 确定使用的voice_id：优先使用agent的voice_id，否则根据性别使用默认值
        voice_id_to_use = agent.voice_id
        if not voice_id_to_use:
            # 根据性别选择默认音色ID
            voice_id_to_use = GENDER_VOICE_MAPPING.get(agent.gender.value)
            if not voice_id_to_use:
                logger.debug(
                    f"Agent {agent.id} 性别 {agent.gender.value} 没有对应的默认音色ID，跳过语音生成"
                )
                return None

        logger.debug(
            f"Agent {agent.id} 使用voice_id: {voice_id_to_use} (来源: {'Agent' if agent.voice_id else '性别默认值'})"
        )

        voice_service = VoiceService()

        # 生成开场白语音
        voice_result = await voice_service.generate_voice(
            text=opening, voice_id=voice_id_to_use
        )

        if not voice_result:
            logger.warning(f"Agent {agent.id} 开场白语音生成失败，未返回URL")
            return None

        audio_url, audio_duration = voice_result
        # 更新 agent 的 opening_audio_url字段
        agent.opening_audio_url = audio_url
        await db.commit()
        logger.debug(
            f"成功为Agent {agent.id} 生成开场白语音: {audio_url}, 时长: {audio_duration:.2f}秒"
        )
        return audio_url

    except Exception as e:
        logger.error(f"为Agent {agent.id} 生成开场白语音失败: {str(e)}")
        return None


@deprecated("app 不在显示 readable_id 字段，请使用 id 字段")
async def generate_next_readable_id(db: AsyncSession) -> str:
    """
    Generate next readable ID for agent, starting from 10000000
    """
    try:
        # Get the maximum readable_id from the database
        result = await db.execute(
            text(
                "SELECT MAX(CAST(readable_id AS INTEGER)) FROM agents WHERE readable_id ~ '^[0-9]+$'"
            )
        )
        max_id = result.scalar()

        if max_id is None or max_id < 10000000:
            next_id = 10000000
        else:
            next_id = max_id + 1

        return str(next_id).zfill(8)
    except Exception as e:
        logger.error(f"Error generating readable ID: {str(e)}")
        # Fallback to a random 8-digit number starting from 10000000
        import random

        return str(random.randint(10000000, 99999999))


async def get_agent(
    db: AsyncSession, agent_id: str, current_user_id: Optional[str] = None
) -> Optional[models.Agent]:
    """
    Get AI agent by ID
    """
    try:
        # Get agent's basic information, follower count and connector count
        query = (
            select(
                models.Agent,
                func.count(agent_followers.c.user_id).label("follower_count"),
                func.count(func.distinct(models.Chat.user_id)).label("connector_count"),
            )
            .outerjoin(agent_followers, models.Agent.id == agent_followers.c.agent_id)
            .outerjoin(
                models.Chat,
                and_(
                    models.Agent.id == models.Chat.agent_id,
                    models.Chat.is_active == True,
                ),
            )
            .options(selectinload(models.Agent.creator))
            .where(and_(models.Agent.id == agent_id, models.Agent.deleted_at.is_(None)))
            .group_by(models.Agent.id)
        )

        result = await db.execute(query)
        row = result.first()

        if not row:
            return None

        agent = row[0]
        follower_count = row[1] or 0
        connector_count = row[2] or 0

        # Set follower_count and connector_count attributes
        agent.follower_count = follower_count
        agent.connector_count = connector_count

        # Check if current user follows this agent
        if current_user_id:
            follow_query = select(agent_followers).where(
                and_(
                    agent_followers.c.user_id == current_user_id,
                    agent_followers.c.agent_id == agent_id,
                )
            )
            follow_result = await db.execute(follow_query)
            agent.is_followed = follow_result.first() is not None
        else:
            agent.is_followed = False

        # Get creator's statistics
        if agent.creator_id and agent.creator:
            creator_stats = await get_creator_agent_stats(db, agent.creator_id)
            agent.creator.public_agents_count = creator_stats.public_agents_count
            agent.creator.total_public_agents_follows = (
                creator_stats.total_public_agents_follows
            )

        # Get image sizes from resources table
        await _populate_agent_image_sizes(db, agent)

        return agent
    except SQLAlchemyError as e:
        logger.error(f"Database query error - get agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unknown error - get agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_agent_for_chat(db: AsyncSession, agent_id: str) -> Optional[dict]:
    """
    获取聊天专用的轻量级Agent数据（高性能版本）
    只查询聊天必需的字段，避免复杂的联表查询

    Returns:
        包含聊天所需Agent信息的字典，如果不存在则返回None
    """
    try:
        # 1. 优先从缓存获取完整Agent数据
        cached_agent_data = cache_service.get_agent_config(agent_id)
        if cached_agent_data and cached_agent_data.get("_complete_data"):
            logger.debug(f"从缓存获取完整Agent数据: {agent_id}")
            return cached_agent_data

        # 2. 缓存未命中，执行轻量级数据库查询（仅查询聊天必需字段）
        query = select(
            models.Agent.id,
            models.Agent.name,
            models.Agent.gender,
            models.Agent.settings,
            models.Agent.main_prompt,
            models.Agent.mode_prompt,
            models.Agent.personality,
            models.Agent.scenario,
            models.Agent.message_example,
            models.Agent.creator_notes,
            models.Agent.tags,
            models.Agent.character_version,
            models.Agent.extensions,
            models.Agent.intro,
            models.Agent.avatar,
            models.Agent.background,
            models.Agent.opening,
            models.Agent.voice_id,
            models.Agent.opening_audio_url,
            models.Agent.created_at,
            models.Agent.updated_at,
        ).where(and_(models.Agent.id == agent_id, models.Agent.deleted_at.is_(None)))

        result = await db.execute(query)
        row = result.first()

        if not row:
            logger.debug(f"Agent不存在: {agent_id}")
            return None

        # 3. 构建agent_data字典
        agent_data = {
            "id": row[0],
            "name": row[1] or f"Agent_{row[0][:8]}",
            "gender": row[2].value if row[2] else None,
            "settings": row[3],
            "main_prompt": row[4] or "",
            "mode_prompt": row[5] or "",
            "personality": row[6] or "",
            "scenario": row[7] or "",
            "message_example": row[8] or "",
            "creator_notes": row[9] or "",
            "tags": row[10] or [],
            "character_version": row[11] or "1.0",
            "extensions": row[12] or {},
            "intro": row[13] or "",
            "avatar": row[14],
            "background": row[15],
            "opening": row[16],
            "voice_id": row[17],
            "opening_audio_url": row[18],
            "created_at": row[19],
            "updated_at": row[20],
            "_complete_data": True,  # 标记为完整数据
        }

        # 4. 缓存完整的Agent数据（30分钟过期）
        cache_service.set_agent_config(agent_id, agent_data, ttl=1800)

        logger.debug(f"获取并缓存Agent聊天数据: {agent_data['name']}")
        return agent_data

    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误 - 获取聊天Agent数据 {agent_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"未知错误 - 获取聊天Agent数据 {agent_id}: {str(e)}")
        return None


async def get_user_agents(
    db: AsyncSession,
    current_user: schemas.User,
    skip: int = 0,
    limit: int = 100,
) -> List[models.Agent]:
    """
    Get user's created AI agents list
    """
    try:
        # Validate parameters
        if skip < 0:
            raise HTTPException(
                status_code=400, detail="Skip parameter cannot be negative"
            )
        if limit <= 0 or limit > 1000:
            raise HTTPException(
                status_code=400, detail="Limit parameter must be between 1-1000"
            )

        # 获取agents和关注者数量
        query = (
            select(
                models.Agent,
                func.count(agent_followers.c.user_id).label("follower_count"),
            )
            .outerjoin(agent_followers, models.Agent.id == agent_followers.c.agent_id)
            .options(selectinload(models.Agent.creator))
            .where(
                and_(
                    models.Agent.creator_id == current_user.id,
                    models.Agent.deleted_at.is_(None),
                )
            )
            # 获取每个agent的follower数量
            .group_by(models.Agent.id)
            .offset(skip)
            .limit(limit)
            .order_by(desc(models.Agent.created_at))
        )

        result = await db.execute(query)
        rows = result.all()

        agents = []
        agent_ids = []

        for row in rows:
            agent = row[0]
            follower_count = row[1] or 0
            agent.follower_count = follower_count
            agent.is_followed = False  # 默认值
            # 设置用户名字，用于模板变量替换
            agent.user = current_user.nickname if current_user.nickname else "you"
            agents.append(agent)
            agent_ids.append(agent.id)

        # 批量检查当前用户是否关注了这些agents
        if current_user and current_user.id and agent_ids:
            follow_query = select(agent_followers.c.agent_id).where(
                and_(
                    agent_followers.c.user_id == current_user.id,
                    agent_followers.c.agent_id.in_(agent_ids),
                )
            )
            follow_result = await db.execute(follow_query)
            followed_agent_ids = {row[0] for row in follow_result}

            for agent in agents:
                agent.is_followed = agent.id in followed_agent_ids

        # 批量填充图片尺寸信息
        for agent in agents:
            logger.debug(f"Populating image sizes for agent {agent.id}")
            await _populate_agent_image_sizes(db, agent)

        return agents
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database query error - get user agents list: {str(e)}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unknown error - get user agents list: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_recommended_agents(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    current_user_id: Optional[str] = None,
) -> List[models.Agent]:
    """
    Get recommended AI agents list (public and approved agents, ordered by creation time desc)
    """
    try:
        # Validate parameters
        if skip < 0:
            raise HTTPException(
                status_code=400, detail="Skip parameter cannot be negative"
            )
        if limit <= 0 or limit > 1000:
            raise HTTPException(
                status_code=400, detail="Limit parameter must be between 1-1000"
            )

        # 获取agents和关注者数量
        query = (
            select(
                models.Agent,
                func.count(agent_followers.c.user_id).label("follower_count"),
            )
            .outerjoin(agent_followers, models.Agent.id == agent_followers.c.agent_id)
            .options(selectinload(models.Agent.creator))
            .where(
                and_(
                    models.Agent.visibility == AgentVisibility.PUBLIC,
                    models.Agent.deleted_at.is_(None),
                    # models.Agent.status == AgentStatus.APPROVED
                )
            )
            .group_by(models.Agent.id)
            .offset(skip)
            .limit(limit)
            .order_by(desc(models.Agent.created_at))
        )

        result = await db.execute(query)
        rows = result.all()

        agents = []
        agent_ids = []

        for row in rows:
            agent = row[0]
            follower_count = row[1] or 0
            agent.follower_count = follower_count
            agent.is_followed = False  # 默认值
            agents.append(agent)
            agent_ids.append(agent.id)

        # 批量检查当前用户是否关注了这些agents
        if current_user_id and agent_ids:
            follow_query = select(agent_followers.c.agent_id).where(
                and_(
                    agent_followers.c.user_id == current_user_id,
                    agent_followers.c.agent_id.in_(agent_ids),
                )
            )
            follow_result = await db.execute(follow_query)
            followed_agent_ids = {row[0] for row in follow_result}

            for agent in agents:
                agent.is_followed = agent.id in followed_agent_ids

        return agents
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database query error - get recommended agents list: {str(e)}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.error(f"Unknown error - get recommended agents list: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


def get_deterministic_random_order(sort_seed: str):
    """
    生成基于sort_seed的确定性随机排序表达式
    """
    if not sort_seed:
        return func.random()

    # 使用MD5(concat(id, sort_seed))来实现确定性排序
    return func.md5(func.concat(models.Agent.id, sort_seed))


def _select_agents_with_sizes() -> select:
    avatar_resource = models.Resource.__table__.alias("avatar_resource")
    background_resource = models.Resource.__table__.alias("background_resource")
    return (
        select(
            models.Agent,
            avatar_resource.c.resource_metadata.label("avatar_metadata"),
            background_resource.c.resource_metadata.label("background_metadata"),
        )
        # eager loading optimization that tells SQLAlchemy to load the related creator data in a separate, efficient query.
        # 1. Prevents N+1 queries: Without this, if you access agent.creator for each agent,
        #    SQLAlchemy would make a separate database query for each one
        # 2. Loads all creator data upfront: It performs one additional query to load all the creator information for all agents at once
        # 3. Makes the relationship immediately available: You can access agent.creator without triggering additional database hits
        .options(selectinload(models.Agent.creator))
        .outerjoin(
            avatar_resource,
            avatar_resource.c.url == models.Agent.avatar,
        )
        .outerjoin(
            background_resource,
            background_resource.c.url == models.Agent.background,
        )
        .where(
            # Public ones, users can create private agents
            models.Agent.visibility == AgentVisibility.PUBLIC,
            # Not deleted
            models.Agent.deleted_at.is_(None),
        )
    )


def _fill_agent_image_sizes(
    agent: models.Agent, avatar_metadata: dict, bg_metadata: dict
) -> models.Agent:
    if avatar_metadata:
        agent.avatar_size = ImageSize.model_validate(avatar_metadata["size"])
    if bg_metadata:
        agent.background_size = ImageSize.model_validate(bg_metadata["size"])
    return agent


async def get_balanced_score_based_agents(
    db: AsyncSession,
    page: int,
    page_size: int,
    sort_seed: str = "",
    current_user_id: Optional[str] = None,  # pylint: disable=unused-argument
) -> List[models.Agent]:
    """
    简化的平衡权重排序：score * 2 + random(0-100)
    既保持高分优先，又确保各页面有多样性
    """
    offset = (page - 1) * page_size

    # 平衡权重排序查询，同时获取头像和背景图的尺寸信息
    query = (
        _select_agents_with_sizes()
        .order_by(
            (
                # score * 2 + random(0-100)
                func.coalesce(
                    models.Agent.meta_data.op("->>")(text("'score'")).cast(Integer), 0
                )
                * 2
                + func.abs(func.hashtext(func.concat(models.Agent.id, sort_seed))) % 100
            ).desc(),
            # 添加agent.id作为第二排序字段，确保排序稳定性，避免分页重复
            models.Agent.id.asc(),
        )
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    query_results = result.all()

    # 处理查询结果，提取agent和metadata信息
    return [_fill_agent_image_sizes(row[0], row[1], row[2]) for row in query_results]


async def get_recommended_agents_paginated(
    db: AsyncSession,
    current_user: schemas.User,
    page: int = 1,
    page_size: int = 10,
    sort_by: Optional[AgentSortOption] = None,
    sort_seed: str = "",
) -> schemas.PaginationData[schemas.Agent]:
    """
    获取推荐的AI角色列表（分页版本）
    """
    try:
        # 验证参数
        if page <= 0:
            raise HTTPException(
                status_code=400, detail="Page parameter must be greater than 0"
            )
        if page_size <= 0 or page_size > 100:
            raise HTTPException(
                status_code=400, detail="Page size parameter must be between 1-100"
            )

        # 构建基础查询条件
        base_query = select(models.Agent).where(
            and_(
                models.Agent.visibility == AgentVisibility.PUBLIC,
                models.Agent.deleted_at.is_(None),
                # models.Agent.status == AgentStatus.APPROVED
            )
        )

        # 获取总数
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # 基于评分的推荐算法：使用简化的平衡权重排序
        if sort_by == AgentSortOption.SCORE_BASED_RANDOM:
            # 使用新的平衡权重排序算法
            agents_list = await get_balanced_score_based_agents(
                db, page, page_size, sort_seed, current_user.id
            )
            # 保持使用原来的总数计算（基于基础查询条件）
        else:
            # 传统分页逻辑
            skip = (page - 1) * page_size

            # 确定排序方式
            sort_order = None
            if sort_by == AgentSortOption.CREATED_ASC:
                sort_order = models.Agent.created_at.asc()
            elif sort_by == AgentSortOption.RANDOM:
                sort_order = get_deterministic_random_order(sort_seed)
            else:  # 默认为 CREATED_DESC
                sort_order = desc(models.Agent.created_at)

            # 获取分页数据，同时获取头像和背景图的尺寸信息
            data_query = (
                _select_agents_with_sizes()
                .offset(skip)
                .limit(page_size)
                .order_by(sort_order)
            )

            result = await db.execute(data_query)
            query_results = result.all()

            # 处理查询结果，提取agent和metadata信息
            agents_list = [
                _fill_agent_image_sizes(row[0], row[1], row[2]) for row in query_results
            ]

        # 为所有agents添加关注者数量和关注状态
        agents = []
        agent_ids = []

        for agent in agents_list:
            # 临时禁用关注者数量查询以提高测试性能
            agent.follower_count = 0
            agent.is_followed = False  # 默认值
            # 设置用户名字，用于模板变量替换
            agent.user = current_user.nickname if current_user.nickname else "you"
            agents.append(agent)
            agent_ids.append(agent.id)

        # 批量检查当前用户是否关注了这些agents
        if agent_ids:
            follow_query = select(agent_followers.c.agent_id).where(
                and_(
                    agent_followers.c.user_id == current_user.id,
                    agent_followers.c.agent_id.in_(agent_ids),
                )
            )
            follow_result = await db.execute(follow_query)
            followed_agent_ids = {row[0] for row in follow_result}

            for agent in agents:
                agent.is_followed = agent.id in followed_agent_ids

        # 计算总页数
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return schemas.PaginationData[schemas.Agent](
            list=agents,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误 - 获取推荐角色分页列表: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")
    except Exception as e:
        logger.error(f"未知错误 - 获取推荐角色分页列表: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


async def create_agent(
    db: AsyncSession, agent_in: schemas.AgentCreate, user_id: str
) -> models.Agent:
    """
    创建新的AI角色
    如果 agent_in 没有 avatar，则自动为用户扣一个 avatar，crop_avatar()
    """
    try:
        # 验证必填字段
        if not agent_in.name or not agent_in.name.strip():
            raise HTTPException(status_code=400, detail="Agent name cannot be empty")

        # 处理prompt到personality的转换（向后兼容）
        if (
            agent_in.prompt
            and agent_in.prompt.strip()
            and not (agent_in.personality and agent_in.personality.strip())
        ):
            logger.debug(f"将prompt转换为personality以保持向后兼容")
            agent_in.personality = agent_in.prompt

        # 角色卡字段优先级验证和建议
        _validate_character_card_fields(agent_in)

        # 生成唯一ID
        agent_id = str(uuid.uuid4())

        # 生成可读ID
        readable_id = await generate_next_readable_id(db)

        # 排除数据库模型中不存在的字段
        agent_data = agent_in.model_dump(exclude=EXCLUDE_FIELDS)
        logger.debug(f"原始Agent数据: {agent_data}")

        # 处理 llm_config 字段
        if "llm_config" in agent_data:
            # 将 llm_config 移动到 settings 中
            if "settings" not in agent_data or agent_data["settings"] is None:
                agent_data["settings"] = {}
            agent_data["settings"]["llm_config"] = agent_data.pop("llm_config")
            logger.debug(f"处理llm_config后的数据: {agent_data}")

        # 处理 meta_data 字段
        if "meta_data" in agent_data and agent_data["meta_data"] is not None:
            # 如果meta_data是AgentMetaData对象，转换为dict
            if hasattr(agent_data["meta_data"], "model_dump"):
                agent_data["meta_data"] = agent_data["meta_data"].model_dump()
            logger.debug(f"处理meta_data后的数据: {agent_data}")

        # 处理图片URL：验证、复制临时文件到永久路径、删除临时文件
        processed_agent_data = process_agent_image_urls(agent_data)

        need_to_crop_avatar = not processed_agent_data.get(
            "avatar", None
        ) and processed_agent_data.get("background", None)
        if need_to_crop_avatar:
            logger.debug(
                f"Agent avatar为空，尝试从background裁剪avatar - Agent ID: {agent_id}"
            )
            background_url = processed_agent_data["background"]
            crop_avatar_result = await _crop_avatar_from_background(background_url)
            cropped_avatar_url = crop_avatar_result.avatar_url
            processed_agent_data["avatar"] = cropped_avatar_url
            logger.debug(
                f"成功从background裁剪avatar - Agent ID: {agent_id}, Avatar URL: {cropped_avatar_url}"
            )
            processed_agent_data["background_images"].append(cropped_avatar_url)
            await async_create_image_resource(
                db,
                user_id,
                cropped_avatar_url,
                crop_avatar_result.avatar_size,
                crop_avatar_result.format,
                crop_avatar_result.byte_size,
            )

        db_agent = models.Agent(
            id=agent_id,
            readable_id=readable_id,
            **processed_agent_data,
            creator_id=user_id,
        )

        db.add(db_agent)
        await db.commit()
        await db.refresh(db_agent)

        # 异步生成开场白语音（不阻塞Agent创建）
        try:
            # TODO：https://github.com/NascentCore/inty/issues/542
            # 生成的开场语音中是包含变量名，这种场景下只能替换 agent 名字
            # 比如 “你好，我是 {{ char }}，很高兴认识你”
            # 如果出现了用户的名字，则无法静态生成。
            # TODO：考虑在用户打开时再进行生成，这样用户看到的信息是不同的。
            await generate_agent_opening_voice(db_agent, db)
        except Exception as e:
            logger.warning(
                f"Agent {db_agent.id} 创建后语音生成失败，将在后续使用时生成: {str(e)}"
            )

        result = await db.execute(
            select(models.Agent)
            .options(selectinload(models.Agent.creator))
            .where(models.Agent.id == db_agent.id)
        )
        return result.scalar_one()

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"数据完整性错误 - 创建角色: {str(e)}")
        if "creator_id" in str(e):
            raise HTTPException(status_code=400, detail="无效的创建者ID")
        else:
            raise HTTPException(status_code=400, detail="数据完整性约束违反")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 创建角色: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 创建角色: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@dataclass
class CropAvatarFromGCSUrlResult:
    avatar_url: str
    avatar_size: ImageSize
    format: ImageFormat
    byte_size: int


async def _crop_avatar_from_background(
    background_url: str,
) -> CropAvatarFromGCSUrlResult:
    """
    从 background 图片中裁剪出 avatar
    Args:
        background_url: 背景图片的URL
    Returns:
        裁剪后的avatar URL
    """
    # 下载背景图片
    background_data = download_from_gcs(background_url)
    if not background_data:
        logger.warning(f"无法下载background图片: {background_url}")
        raise RuntimeError(f"无法下载background图片: {background_url}")

    crop_avatar_result = crop_avatar(background_data)
    cropped_avatar = crop_avatar_result.image
    avatar_data = get_jpg_bytes_from_pil_image(cropped_avatar)
    avatar_byte_size = len(avatar_data)

    bucket, background_gcs_path = get_bucket_and_path_from_gcs_url(background_url)
    avatar_gcs_path = append_filename_suffix(
        background_gcs_path, CROPPED_AVATAR_FILENAME_SUFFIX
    )

    avatar_url = upload_to_gcs(avatar_data, ImageFormat.JPEG, bucket, avatar_gcs_path)
    return CropAvatarFromGCSUrlResult(
        avatar_url, crop_avatar_result.size, ImageFormat.JPEG, avatar_byte_size
    )


def _validate_character_card_fields(agent_in: schemas.AgentCreate):
    """
    验证并建议使用角色卡字段

    Args:
        agent_in: Agent创建数据
    """
    # 检查是否提供了角色卡字段或prompt字段
    has_character_card = bool(
        (agent_in.personality and agent_in.personality.strip())
        or (agent_in.scenario and agent_in.scenario.strip())
    )
    has_prompt = bool(agent_in.prompt and agent_in.prompt.strip())

    logger.debug(
        f"创建Agent字段使用情况 - character_card: {has_character_card}, prompt: {has_prompt}"
    )


def _update_agent_in_db(update_data: dict, db_agent: models.Agent):
    # 验证更新数据
    # 验证名称不为空（如果提供了名称）
    if "name" in update_data and (
        not update_data["name"] or not update_data["name"].strip()
    ):
        raise HTTPException(status_code=400, detail="Agent name cannot be empty")

    # 处理prompt到personality的转换（向后兼容）
    if (
        "prompt" in update_data
        and update_data["prompt"]
        and update_data["prompt"].strip()
    ):
        # 如果没有提供personality或personality为空，则使用prompt的值
        if "personality" not in update_data or not (
            update_data.get("personality") and update_data["personality"].strip()
        ):
            logger.debug(f"将prompt转换为personality以保持向后兼容")
            update_data["personality"] = update_data["prompt"]

    # 处理 llm_config 字段 - 将其移动到 settings 中
    if "llm_config" in update_data:
        llm_config = update_data.pop("llm_config")
        if llm_config is not None:
            logger.debug(f"llm_config不为空，更新settings中的llm_config")
            # 确保 settings 字段存在
            if db_agent.settings is None:
                db_agent.settings = {}
            elif not isinstance(db_agent.settings, dict):
                db_agent.settings = {}

            # 更新 settings 中的 llm_config
            db_agent.settings = {**db_agent.settings, "llm_config": llm_config}
        else:
            if db_agent.settings and "llm_config" in db_agent.settings:
                db_agent.settings.pop("llm_config")

    # 处理 meta_data 字段
    if "meta_data" in update_data:
        meta_data = update_data.pop("meta_data")
        if meta_data is not None:
            logger.debug(f"meta_data不为空，更新meta_data字段")
            # 如果meta_data是AgentMetaData对象，转换为dict
            if hasattr(meta_data, "model_dump"):
                meta_data = meta_data.model_dump()
            db_agent.meta_data = meta_data
        else:
            # 如果meta_data为None，清空该字段
            db_agent.meta_data = None

    if "background_images" in update_data:
        images = update_data.pop("background_images")
        existing_images = []
        if db_agent.background_images:
            existing_images = db_agent.background_images.copy()
        for image in images:
            if image not in existing_images:
                existing_images.append(image)
        db_agent.background_images = existing_images

    # 更新其他字段
    for field, value in update_data.items():
        setattr(db_agent, field, value)


async def update_agent(
    db: AsyncSession, db_agent: models.Agent, agent_in: schemas.AgentUpdate
) -> models.Agent:
    """
    更新AI角色
    """
    try:
        if not db_agent:
            raise HTTPException(status_code=404, detail="角色不存在")

        # 检查是否需要重新生成开场白语音
        update_data = agent_in.model_dump(exclude_unset=True)
        should_regenerate_voice = "opening" in update_data or "voice_id" in update_data

        update_data = process_agent_image_urls(update_data)

        _update_agent_in_db(update_data, db_agent)

        # 确保在异步上下文中调用 flag_modified
        # 在 _update_agent_in_db() 调用 flag_modified 会报 MissingGreenlet 错误
        # 这里的两个数据强制更新，实际上并不一定需要。
        # TODO：使用正确的差异检测函数来避免修改没有更改的值。
        from sqlalchemy.orm.attributes import flag_modified

        if hasattr(db_agent, "settings") and db_agent.settings is not None:
            flag_modified(db_agent, "settings")
        if (
            hasattr(db_agent, "background_images")
            and db_agent.background_images is not None
        ):
            flag_modified(db_agent, "background_images")
        if hasattr(db_agent, "meta_data") and db_agent.meta_data is not None:
            flag_modified(db_agent, "meta_data")

        await db.commit()
        await db.refresh(db_agent)

        # 如果开场白文本或语音ID发生变化，重新生成语音
        if should_regenerate_voice:
            try:
                # TODO：https://github.com/NascentCore/inty/issues/542
                # 生成的开场语音中是包含变量名，这种场景下只能替换 agent 名字
                # 比如 “你好，我是 {{ char }}，很高兴认识你”
                # 如果出现了用户的名字，则无法静态生成。
                await generate_agent_opening_voice(db_agent, db)
            except Exception as e:
                logger.warning(f"Agent {db_agent.id} 更新后语音重新生成失败: {str(e)}")

        # 重新查询以加载关系数据
        result = await db.execute(
            select(models.Agent)
            .options(selectinload(models.Agent.creator))
            .where(models.Agent.id == db_agent.id)
        )
        updated_agent = result.scalar_one()

        # 清除相关缓存，确保更新立即生效
        try:
            from app.services.cache_service import cache_service

            # 清除 agent 配置缓存
            cache_service.invalidate_agent_config(updated_agent.id)
            logger.debug(f"已清除Agent {updated_agent.id} 的配置缓存")

            # 清除可能相关的会话缓存（包含 agent 信息的会话）
            # 这里我们无法直接清除特定 agent 的会话缓存，但会话缓存 TTL 较短（5分钟），影响有限

        except Exception as e:
            logger.error(f"清除Agent缓存时发生错误 {updated_agent.id}: {str(e)}")
            # 注意：这里不抛出异常，因为数据库更新已经成功了

        # 重新加载Agent实例到AgentManager缓存中，AgentManager 仅用于提供聊天所需的提示词，
        # 因此，不需要加载图片等数据。
        try:
            agent_data = {
                "id": updated_agent.id,
                "name": updated_agent.name,
                "description": "",
                "settings": updated_agent.settings or {},
                "main_prompt": updated_agent.main_prompt or "",
                "mode_prompt": updated_agent.mode_prompt or "",
                "personality": updated_agent.personality or "",
                "scenario": updated_agent.scenario or "",
                "message_example": updated_agent.message_example or "",
                "creator_notes": updated_agent.creator_notes or "",
                "tags": updated_agent.tags or [],
                "voice_id": updated_agent.voice_id or "",
                "character_version": updated_agent.character_version or "",
                "extensions": updated_agent.extensions or {},
            }

            reload_success = await agent_manager.reload_agent(
                updated_agent.id, agent_data
            )
            if reload_success:
                logger.debug(f"Agent {updated_agent.id} 缓存重载成功")
            else:
                logger.warning(f"Agent {updated_agent.id} 缓存重载失败")

        except Exception as e:
            logger.error(f"重载Agent缓存时发生错误 {updated_agent.id}: {str(e)}")
            # 注意：这里不抛出异常，因为数据库更新已经成功了

        return updated_agent

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(
            f"数据完整性错误 - 更新角色 {db_agent.id if db_agent else 'unknown'}: {str(e)}"
        )
        raise HTTPException(status_code=400, detail="数据完整性约束违反")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            f"数据库错误 - 更新角色 {db_agent.id if db_agent else 'unknown'}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(
            f"未知错误 - 更新角色 {db_agent.id if db_agent else 'unknown'}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="服务器内部错误")


async def delete_agent(db: AsyncSession, db_agent: models.Agent) -> models.Agent:
    """
    逻辑删除AI角色
    设置deleted_at字段，不删除相关资源
    """
    try:
        if not db_agent:
            raise HTTPException(status_code=404, detail="角色不存在")

        # 检查是否已经被删除
        if db_agent.deleted_at:
            raise HTTPException(status_code=400, detail="角色已被删除")

        agent_id = db_agent.id
        logger.info(f"开始逻辑删除agent {agent_id}")

        # 设置删除时间戳
        from datetime import datetime, timezone

        db_agent.deleted_at = datetime.now(timezone.utc)

        # TODO: soft delete all chats and chat_settings associated with this agent
        # 这个 agent 关联的所有数据都标记成 deleted_at 不为空
        # TODO: query 要过滤掉 deleted_at 不为空的记录

        # 提交更改
        await db.commit()
        await db.refresh(db_agent)

        logger.info(f"成功逻辑删除agent {agent_id}")
        return db_agent

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            f"数据库错误 - 逻辑删除角色 {db_agent.id if db_agent else 'unknown'}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(
            f"未知错误 - 逻辑删除角色 {db_agent.id if db_agent else 'unknown'}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="服务器内部错误")


def process_agent_image_urls(agent_data: dict) -> dict:
    """
    验证Agent创建时的图片URL，确保URL有效性
    现在的实现非常简洁：只验证URL的有效性，不进行任何文件操作。
    返回所有有效的图片URL，包括头像、背景图和相册图片。
    同时将CDN URL转换为GCS URL用于存储。
    """
    logger.debug(
        f"开始处理Agent图片URLs - 原始数据: avatar={agent_data.get('avatar')}, background={agent_data.get('background')}, background_images={agent_data.get('background_images')}"
    )

    # 先将CDN URL转换为GCS URL用于存储
    processed_data = image_transform_service.batch_normalize_urls_for_storage(
        agent_data
    )

    logger.debug(
        f"URL转换完成 - 转换后数据: avatar={processed_data.get('avatar')}, background={processed_data.get('background')}, background_images={processed_data.get('background_images')}"
    )
    images_urls = []

    def add_image_url(image_url):
        if image_url not in images_urls:
            images_urls.append(image_url)

    # 验证头像URL
    if processed_data.get("avatar"):
        avatar_url = processed_data["avatar"]
        if is_valid_gcs_url(avatar_url):
            logger.debug(
                f"头像URL验证通过: {avatar_url} (原始: {agent_data.get('avatar')})"
            )
            add_image_url(avatar_url)
        else:
            logger.warning(
                f"无效的头像URL: {avatar_url} (原始: {agent_data.get('avatar')})"
            )
            processed_data["avatar"] = None

    # 验证背景图URL
    if processed_data.get("background"):
        background_url = processed_data["background"]
        if is_valid_gcs_url(background_url):
            logger.debug(
                f"背景图URL验证通过: {background_url} (原始: {agent_data.get('background')})"
            )
            add_image_url(background_url)
        else:
            logger.warning(
                f"无效的背景图URL: {background_url} (原始: {agent_data.get('background')})"
            )
            processed_data["background"] = None

    # 验证相册图片URLs，但不添加到images_urls（避免重复）
    valid_bg_images = []
    if processed_data.get("background_images") and isinstance(
        processed_data["background_images"], list
    ):
        for photo_url in processed_data["background_images"]:
            if is_valid_gcs_url(photo_url):
                valid_bg_images.append(photo_url)
            else:
                logger.warning(f"无效的相册图片URL: {photo_url}")

    # 构建最终的background_images列表，顺序：avatar -> background -> background_images
    final_images = []
    for url in images_urls:  # images_urls已经包含了avatar和background（按添加顺序）
        final_images.append(url)
    for url in valid_bg_images:  # 添加原始的background_images
        if url not in final_images:  # 避免重复
            final_images.append(url)

    processed_data["background_images"] = final_images if final_images else []

    return processed_data


async def follow_agent(db: AsyncSession, agent_id: str, user_id: str) -> bool:
    """
    用户关注AI角色
    """
    try:
        # 检查agent是否存在
        agent = await get_agent(db, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="AI agent not found")

        # 检查是否已经关注
        follow_query = select(agent_followers).where(
            and_(
                agent_followers.c.user_id == user_id,
                agent_followers.c.agent_id == agent_id,
            )
        )
        result = await db.execute(follow_query)
        if result.first():
            raise HTTPException(status_code=400, detail="已经关注了这个AI角色")

        # 插入关注记录
        insert_query = agent_followers.insert().values(
            user_id=user_id, agent_id=agent_id
        )
        await db.execute(insert_query)
        await db.commit()

        return True
    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"数据完整性错误 - 关注角色: {str(e)}")
        if "user_id" in str(e) or "agent_id" in str(e):
            raise HTTPException(status_code=400, detail="用户或AI角色不存在")
        else:
            raise HTTPException(status_code=400, detail="已经关注了这个AI角色")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 关注角色: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 关注角色: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


async def unfollow_agent(db: AsyncSession, agent_id: str, user_id: str) -> bool:
    """
    用户取消关注AI角色
    """
    try:
        # 检查是否已经关注
        follow_query = select(agent_followers).where(
            and_(
                agent_followers.c.user_id == user_id,
                agent_followers.c.agent_id == agent_id,
            )
        )
        result = await db.execute(follow_query)
        if not result.first():
            raise HTTPException(
                status_code=400, detail="Not following this AI agent yet"
            )

        # 删除关注记录
        delete_query = agent_followers.delete().where(
            and_(
                agent_followers.c.user_id == user_id,
                agent_followers.c.agent_id == agent_id,
            )
        )
        await db.execute(delete_query)
        await db.commit()

        return True
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 取消关注角色: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 取消关注角色: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


async def get_user_followed_agents(
    db: AsyncSession, user_id: str, page: int = 1, page_size: int = 10
) -> schemas.PaginationData[schemas.Agent]:
    """
    获取用户关注的AI角色列表（分页）
    """
    try:
        # 验证参数
        if page <= 0:
            raise HTTPException(status_code=400, detail="page参数必须大于0")
        if page_size <= 0 or page_size > 100:
            raise HTTPException(status_code=400, detail="page_size参数必须在1-100之间")

        # 计算偏移量
        skip = (page - 1) * page_size

        # 获取总数（只计算未删除的agents）
        count_query = (
            select(func.count())
            .select_from(
                agent_followers.join(
                    models.Agent, agent_followers.c.agent_id == models.Agent.id
                )
            )
            .where(agent_followers.c.user_id == user_id)
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        logger.debug(f"total agents followed by user {user_id}: {total}")

        # 获取分页数据
        # 首先获取用户关注的未删除agent IDs
        followed_agents_query = (
            select(agent_followers.c.agent_id)
            .select_from(
                agent_followers.join(
                    models.Agent, agent_followers.c.agent_id == models.Agent.id
                )
            )
            .where(agent_followers.c.user_id == user_id)
            .offset(skip)
            .limit(page_size)
        )
        followed_result = await db.execute(followed_agents_query)
        followed_agent_ids = [row[0] for row in followed_result]

        logger.debug(f"followed agent ids: {followed_agent_ids}")

        agents = []

        if followed_agent_ids:
            # 然后获取这些agents的详细信息和follower数量
            data_query = (
                select(
                    models.Agent,
                    func.count(agent_followers.c.user_id).label("follower_count"),
                )
                .outerjoin(
                    agent_followers, models.Agent.id == agent_followers.c.agent_id
                )
                .options(selectinload(models.Agent.creator))
                .where(models.Agent.id.in_(followed_agent_ids))
                .group_by(models.Agent.id)
                .order_by(desc(models.Agent.created_at))
            )

            result = await db.execute(data_query)
            rows = result.all()

            for row in rows:
                agent = row[0]
                follower_count = row[1] or 0
                agent.follower_count = follower_count
                agent.is_followed = True  # 这些都是用户关注的
                agents.append(agent)

        # 计算总页数
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return schemas.PaginationData[schemas.Agent](
            list=agents,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误 - 获取用户关注列表: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")
    except Exception as e:
        logger.error(f"未知错误 - 获取用户关注列表: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


async def search_agents(
    db: AsyncSession,
    current_user: schemas.User,
    keyword: str,
    page: int = 1,
    page_size: int = 10,
) -> schemas.PaginationData[schemas.Agent]:
    """
    搜索公开的AI角色（分页版本）
    支持按名称、介绍、分类进行模糊查询
    """
    try:
        # 验证参数
        if page <= 0:
            raise HTTPException(status_code=400, detail="page参数必须大于0")
        if page_size <= 0 or page_size > 100:
            raise HTTPException(status_code=400, detail="page_size参数必须在1-100之间")
        if not keyword or not keyword.strip():
            raise HTTPException(
                status_code=400, detail="Search keyword cannot be empty"
            )

        # 计算偏移量
        skip = (page - 1) * page_size
        keyword = keyword.strip()

        # 构建搜索条件 - 在name, intro, category字段中进行模糊搜索
        search_conditions = []
        if keyword:
            search_pattern = f"%{keyword}%"
            search_conditions = [
                models.Agent.name.ilike(search_pattern),
                models.Agent.intro.ilike(search_pattern),
                models.Agent.category.ilike(search_pattern),
            ]

        # 构建基础查询条件 - 只搜索公开且未删除的agent
        base_conditions = [
            models.Agent.visibility == AgentVisibility.PUBLIC,
            models.Agent.deleted_at.is_(None),
            # models.Agent.status == AgentStatus.APPROVED  # 如果需要只搜索已审核的
        ]

        # 如果有搜索条件，添加OR条件
        if search_conditions:
            base_conditions.append(or_(*search_conditions))

        # 构建基础查询
        base_query = select(models.Agent).where(*base_conditions)

        # 获取总数
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # 获取分页数据包含关注者数量
        data_query = (
            select(
                models.Agent,
                func.count(agent_followers.c.user_id).label("follower_count"),
            )
            .outerjoin(agent_followers, models.Agent.id == agent_followers.c.agent_id)
            .options(selectinload(models.Agent.creator))
            .where(*base_conditions)
            .group_by(models.Agent.id)
            .offset(skip)
            .limit(page_size)
            .order_by(desc(models.Agent.created_at))  # 按创建时间倒序排列
        )

        result = await db.execute(data_query)
        rows = result.all()

        agents = []
        agent_ids = []

        for row in rows:
            agent = row[0]
            follower_count = row[1] or 0
            agent.follower_count = follower_count
            agent.is_followed = False  # 默认值
            # 设置用户名字，用于模板变量替换
            agent.user = current_user.nickname if current_user.nickname else "you"
            agents.append(agent)
            agent_ids.append(agent.id)

        # 批量检查当前用户是否关注了这些agents
        if current_user and current_user.id and agent_ids:
            follow_query = select(agent_followers.c.agent_id).where(
                and_(
                    agent_followers.c.user_id == current_user.id,
                    agent_followers.c.agent_id.in_(agent_ids),
                )
            )
            follow_result = await db.execute(follow_query)
            followed_agent_ids = {row[0] for row in follow_result}

            for agent in agents:
                agent.is_followed = agent.id in followed_agent_ids

        # 计算总页数
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return schemas.PaginationData[schemas.Agent](
            list=agents,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误 - 搜索角色: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")
    except Exception as e:
        logger.error(f"未知错误 - 搜索角色: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


async def get_creator_agent_stats(
    db: AsyncSession, creator_id: str
) -> schemas.CreatorAgentStats:
    """
    获取创建者的公共角色统计信息
    """
    try:
        # 获取创建者创建的公共角色数量
        public_agents_count_query = select(func.count(models.Agent.id)).where(
            and_(
                models.Agent.creator_id == creator_id,
                models.Agent.visibility == AgentVisibility.PUBLIC,
                models.Agent.deleted_at.is_(None),
            )
        )

        public_agents_count_result = await db.execute(public_agents_count_query)
        public_agents_count = public_agents_count_result.scalar() or 0

        # 获取创建者的所有公共角色的总关注数
        total_follows_query = (
            select(func.count(agent_followers.c.user_id))
            .select_from(
                agent_followers.join(
                    models.Agent, agent_followers.c.agent_id == models.Agent.id
                )
            )
            .where(
                and_(
                    models.Agent.creator_id == creator_id,
                    models.Agent.visibility == AgentVisibility.PUBLIC,
                    models.Agent.deleted_at.is_(None),
                )
            )
        )

        total_follows_result = await db.execute(total_follows_query)
        total_follows = total_follows_result.scalar() or 0

        return schemas.CreatorAgentStats(
            creator_id=creator_id,
            public_agents_count=public_agents_count,
            total_public_agents_follows=total_follows,
        )

    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误 - 获取创建者角色统计: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")
    except Exception as e:
        logger.error(f"未知错误 - 获取创建者角色统计: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")
