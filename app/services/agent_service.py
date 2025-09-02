import math
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.schemas.agent import AgentSortOption
from app.core.agent.agent import agent_manager
from app.core.config import global_config_loaded_from_config_yaml
from app.models.agent import AgentVisibility
from app.models.agent import AgentVisibility
from app.models.associations import agent_followers
from app.services.cache_service import cache_service
from app.utils.crop_avatar import crop_avatar
from app.utils.gcs import (
    append_filename_suffix,
    download_from_gcs,
    get_bucket_and_path_from_gcs_url,
    upload_to_gcs,
)
from app.utils.image import (
    ImageFormat,
    get_jpg_bytes_from_pil_image,
)
from app.utils.crop_avatar import crop_avatar
from app.utils.gcs import get_bucket_and_path_from_gcs_url


from loguru import logger


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
            models.Agent.avatar,
            models.Agent.opening,
            models.Agent.voice_id,
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
            "settings": row[2],
            "main_prompt": row[3] or "",
            "mode_prompt": row[4] or "",
            "personality": row[5] or "",
            "scenario": row[6] or "",
            "message_example": row[7] or "",
            "creator_notes": row[8] or "",
            "tags": row[9] or [],
            "character_version": row[10] or "1.0",
            "extensions": row[11] or {},
            "avatar": row[12],
            "opening": row[13],
            "voice_id": row[14],
            "created_at": row[15],
            "updated_at": row[16],
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
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user_id: Optional[str] = None,
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
                    models.Agent.creator_id == user_id,
                    models.Agent.deleted_at.is_(None),
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


async def get_recommended_agents_paginated(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    sort_by: Optional[AgentSortOption] = None,
    current_user_id: Optional[str] = None,
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

        # 计算偏移量
        skip = (page - 1) * page_size

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

        # 确定排序方式
        sort_order = None
        if sort_by == AgentSortOption.CREATED_ASC:
            sort_order = models.Agent.created_at.asc()
        elif sort_by == AgentSortOption.RANDOM:
            sort_order = func.random()  # PostgreSQL/SQLite random function
        else:  # 默认为 CREATED_DESC
            sort_order = desc(models.Agent.created_at)

        # 获取分页数据包含关注者数量
        data_query = (
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
            .limit(page_size)
            .order_by(sort_order)
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

        # 获取Agent数据
        agent_data = agent_in.dict()
        logger.debug(f"原始Agent数据: {agent_data}")

        # 处理 llm_config 字段
        if "llm_config" in agent_data:
            # 将 llm_config 移动到 settings 中
            if "settings" not in agent_data or agent_data["settings"] is None:
                agent_data["settings"] = {}
            agent_data["settings"]["llm_config"] = agent_data.pop("llm_config")
            logger.debug(f"处理llm_config后的数据: {agent_data}")

        # 处理图片URL：验证、复制临时文件到永久路径、删除临时文件
        try:
            processed_agent_data = process_agent_image_urls(
                agent_data, agent_id, user_id
            )
            # 确保返回值不为空
            if processed_agent_data is None:
                logger.warning(f"图片处理返回None，使用原始数据 - Agent ID: {agent_id}")
                processed_agent_data = agent_data
            else:
                logger.debug(f"成功处理Agent图片URL - Agent ID: {agent_id}")
        except Exception as e:
            logger.error(
                f"处理Agent图片URL失败 - Agent ID: {agent_id}, Error: {str(e)}"
            )
            # 图片处理失败不应该阻止Agent创建，使用原始数据
            processed_agent_data = agent_data

        # 如果avatar为空但有background，则从background中裁剪出avatar
        if (
            not processed_agent_data.get("avatar")
            or not processed_agent_data["avatar"].strip()
        ) and processed_agent_data.get("background"):
            logger.debug(
                f"Agent avatar为空，尝试从background裁剪avatar - Agent ID: {agent_id}"
            )
            try:
                cropped_avatar_url = await _crop_avatar_from_background(
                    processed_agent_data["background"], agent_id, user_id
                )
                if cropped_avatar_url:
                    processed_agent_data["avatar"] = cropped_avatar_url
                    logger.info(
                        f"成功从background裁剪avatar - Agent ID: {agent_id}, Avatar URL: {cropped_avatar_url}"
                    )
                else:
                    logger.warning(
                        f"从background裁剪avatar失败，使用默认头像 - Agent ID: {agent_id}"
                    )
            except Exception as e:
                logger.error(
                    f"从background裁剪avatar时发生异常 - Agent ID: {agent_id}, Error: {str(e)}"
                )
                # 裁剪失败不影响Agent创建，继续使用原始数据

        # 确保processed_agent_data是有效的字典
        if not isinstance(processed_agent_data, dict):
            logger.error(
                f"processed_agent_data不是字典类型: {type(processed_agent_data)}, 值: {processed_agent_data}"
            )
            processed_agent_data = agent_data

        logger.debug(f"最终处理后的Agent数据: {processed_agent_data}")

        try:
            db_agent = models.Agent(
                id=agent_id,
                readable_id=readable_id,
                **processed_agent_data,
                creator_id=user_id,
            )
        except Exception as e:
            logger.error(f"创建Agent模型实例失败: {str(e)}")
            logger.error(f"Agent数据: {processed_agent_data}")
            raise

        db.add(db_agent)
        await db.commit()
        await db.refresh(db_agent)

        # 重新查询以加载关系数据
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


async def _crop_avatar_from_background(background_url: str) -> Optional[str]:
    """
    从 background 图片中裁剪出 avatar

    Args:
        background_url: 背景图片的URL
        agent_id: 智能体ID
        user_id: 用户ID

    Returns:
        裁剪后的avatar URL，如果失败则返回None
    """
    # 下载背景图片
    background_data = download_from_gcs(background_url)
    if not background_data:
        logger.warning(f"无法下载background图片: {background_url}")
        raise RuntimeError(f"无法下载background图片: {background_url}")

    cropped_avatar = crop_avatar(background_data)
    avatar_data = get_jpg_bytes_from_pil_image(cropped_avatar, 90)

    bucket, background_gcs_path = get_bucket_and_path_from_gcs_url(background_url)
    avatar_gcs_path = append_filename_suffix(background_gcs_path, "-cropped-avatar")

    # 上传裁剪后的avatar到GCS
    avatar_url = upload_to_gcs(avatar_data, ImageFormat.JPEG, bucket, avatar_gcs_path)
    return avatar_url


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

    # 如果既没有角色卡信息也没有prompt，抛出错误
    if not has_character_card and not has_prompt:
        raise HTTPException(
            status_code=400,
            detail="请提供角色设定信息：建议使用personality(性格)和scenario(背景)字段，或使用prompt字段",
        )


async def update_agent(
    db: AsyncSession, db_agent: models.Agent, agent_in: schemas.AgentUpdate
) -> models.Agent:
    """
    更新AI角色
    """
    try:
        if not db_agent:
            raise HTTPException(status_code=404, detail="角色不存在")

        # 验证更新数据
        update_data = agent_in.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided for update")

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
                # 确保 settings 字段存在
                if db_agent.settings is None:
                    db_agent.settings = {}
                elif not isinstance(db_agent.settings, dict):
                    db_agent.settings = {}

                # 更新 settings 中的 llm_config
                db_agent.settings = {**db_agent.settings, "llm_config": llm_config}

        # 更新其他字段
        for field, value in update_data.items():
            setattr(db_agent, field, value)

        await db.commit()
        await db.refresh(db_agent)

        # 重新查询以加载关系数据
        result = await db.execute(
            select(models.Agent)
            .options(selectinload(models.Agent.creator))
            .where(models.Agent.id == db_agent.id)
        )
        updated_agent = result.scalar_one()

        # 重新加载Agent实例到AgentManager缓存中
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
        from datetime import datetime

        db_agent.deleted_at = datetime.utcnow()

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


def generate_agent_avatar_path(agent_id: str, filename: str) -> str:
    """生成agent头像的存储路径"""
    ext = filename.split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        raise ValueError(f"Unsupported file type: {ext}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"agents/{agent_id}/avatar-{timestamp}-{unique_id}.{ext}"


def generate_agent_background_path(agent_id: str, filename: str) -> str:
    """生成agent背景图的存储路径"""
    ext = filename.split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        raise ValueError(f"Unsupported file type: {ext}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"agents/{agent_id}/background-{timestamp}-{unique_id}.{ext}"


# TODO：这个过于复杂，应该直接往数据库插入数据而非拷贝 gcs 文件。
def process_agent_image_urls(agent_data: dict, agent_id: str, user_id: str) -> dict:
    """
    处理Agent创建时的图片URL，将临时路径的图片复制到永久路径

    Args:
        agent_data: Agent数据字典
        agent_id: Agent ID
        user_id: 用户ID

    Returns:
        处理后的agent_data，包含更新的图片URL
    """
    from app.utils.gcs import (
        copy_gcs_file,
        delete_from_gcs,
        is_temp_gcs_path,
        is_valid_gcs_url,
    )

    processed_data = agent_data.copy()
    temp_files_to_delete = []

    # 处理头像
    if agent_data.get("avatar"):
        avatar_url = agent_data["avatar"]
        if is_valid_gcs_url(avatar_url):
            if is_temp_gcs_path(avatar_url, user_id):
                try:
                    # 生成永久路径
                    # 从临时URL中提取文件扩展名
                    _, temp_path = get_bucket_and_path_from_gcs_url(avatar_url)
                    file_ext = temp_path.split(".")[-1] if "." in temp_path else "png"
                    permanent_path = generate_agent_avatar_path(
                        agent_id, f"avatar.{file_ext}"
                    )

                    # 复制到永久路径
                    new_avatar_url = copy_gcs_file(
                        avatar_url,
                        permanent_path,
                        global_config_loaded_from_config_yaml.gcs.bucket,
                    )
                    processed_data["avatar"] = new_avatar_url

                    # 标记临时文件待删除
                    temp_files_to_delete.append(avatar_url)

                    logger.debug(
                        f"复制头像从临时路径到永久路径: {avatar_url} -> {new_avatar_url}"
                    )
                except FileNotFoundError as e:
                    logger.warning(f"临时头像文件不存在，跳过复制: {avatar_url}")
                    processed_data["avatar"] = None
                except Exception as e:
                    logger.error(f"复制头像失败: {str(e)}")
                    processed_data["avatar"] = None
        else:
            logger.warning(f"无效的头像URL: {avatar_url}")
            processed_data["avatar"] = None

    # 处理背景图
    if agent_data.get("background"):
        background_url = agent_data["background"]
        if is_valid_gcs_url(background_url):
            if is_temp_gcs_path(background_url, user_id):
                try:
                    # 生成永久路径
                    _, temp_path = get_bucket_and_path_from_gcs_url(background_url)
                    file_ext = temp_path.split(".")[-1] if "." in temp_path else "png"
                    permanent_path = generate_agent_background_path(
                        agent_id, f"background.{file_ext}"
                    )

                    # 复制到永久路径
                    new_background_url = copy_gcs_file(
                        background_url,
                        permanent_path,
                        global_config_loaded_from_config_yaml.gcs.bucket,
                    )
                    processed_data["background"] = new_background_url

                    # 标记临时文件待删除
                    temp_files_to_delete.append(background_url)

                    logger.debug(
                        f"复制背景图从临时路径到永久路径: {background_url} -> {new_background_url}"
                    )
                except FileNotFoundError as e:
                    logger.warning(f"临时背景图文件不存在，跳过复制: {background_url}")
                    processed_data["background"] = None
                except Exception as e:
                    logger.error(f"复制背景图失败: {str(e)}")
                    processed_data["background"] = None
        else:
            logger.warning(f"无效的背景图URL: {background_url}")
            processed_data["background"] = None

    # 处理相册图片
    if agent_data.get("background_images") and isinstance(
        agent_data["background_images"], list
    ):
        processed_photos = []
        for i, photo_url in enumerate(agent_data["background_images"]):
            if is_valid_gcs_url(photo_url):
                if is_temp_gcs_path(photo_url, user_id):
                    try:
                        # 生成永久路径
                        _, temp_path = get_bucket_and_path_from_gcs_url(photo_url)
                        file_ext = (
                            temp_path.split(".")[-1] if "." in temp_path else "png"
                        )
                        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                        unique_id = uuid.uuid4().hex[:8]
                        permanent_path = f"agents/{agent_id}/photos/photo-{i+1}-{timestamp}-{unique_id}.{file_ext}"

                        # 复制到永久路径
                        new_photo_url = copy_gcs_file(
                            photo_url,
                            permanent_path,
                            global_config_loaded_from_config_yaml.gcs.bucket,
                        )
                        processed_photos.append(new_photo_url)

                        # 标记临时文件待删除
                        temp_files_to_delete.append(photo_url)

                        logger.debug(
                            f"复制相册图片从临时路径到永久路径: {photo_url} -> {new_photo_url}"
                        )
                    except FileNotFoundError as e:
                        logger.warning(f"临时相册图片文件不存在，跳过: {photo_url}")
                        continue
                    except Exception as e:
                        logger.error(f"复制相册图片失败: {str(e)}")
                        # 如果复制失败，跳过这张图片
                        continue
                else:
                    # 非临时路径，直接保留
                    processed_photos.append(photo_url)
            else:
                logger.warning(f"无效的相册图片URL: {photo_url}")
                # 无效URL，跳过
                continue

        processed_data["background_images"] = processed_photos

    # 删除临时文件（在后台异步执行）
    if temp_files_to_delete:
        # TODO: 这个太复杂了，建议删除；应该是 AI 自动生成的复杂代码。
        def cleanup_temp_files():
            for temp_url in temp_files_to_delete:
                try:
                    bucket_name, temp_path = get_bucket_and_path_from_gcs_url(temp_url)
                    if temp_path:
                        deleted = delete_from_gcs(bucket_name, temp_path)
                        if deleted:
                            logger.debug(f"删除临时文件: {temp_url}")
                        else:
                            logger.debug(f"临时文件不存在，跳过删除: {temp_url}")
                    else:
                        logger.warning(f"无法解析临时文件路径: {temp_url}")
                except Exception as e:
                    logger.error(f"删除临时文件失败 {temp_url}: {str(e)}")

        # 在后台线程中执行清理
        import threading

        cleanup_thread = threading.Thread(target=cleanup_temp_files)
        cleanup_thread.daemon = True
        cleanup_thread.start()

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
            .where(
                and_(
                    agent_followers.c.user_id == user_id,
                    models.Agent.deleted_at.is_(None),
                )
            )
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # 获取分页数据
        # 首先获取用户关注的未删除agent IDs
        followed_agents_query = (
            select(agent_followers.c.agent_id)
            .select_from(
                agent_followers.join(
                    models.Agent, agent_followers.c.agent_id == models.Agent.id
                )
            )
            .where(
                and_(
                    agent_followers.c.user_id == user_id,
                    models.Agent.deleted_at.is_(None),
                )
            )
            .offset(skip)
            .limit(page_size)
        )
        followed_result = await db.execute(followed_agents_query)
        followed_agent_ids = [row[0] for row in followed_result]

        if not followed_agent_ids:
            agents = []
        else:
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
                .where(
                    and_(
                        models.Agent.id.in_(followed_agent_ids),
                        models.Agent.deleted_at.is_(None),
                    )
                )
                .group_by(models.Agent.id)
                .order_by(desc(models.Agent.created_at))
            )

            result = await db.execute(data_query)
            rows = result.all()

            agents = []
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
    keyword: str,
    page: int = 1,
    page_size: int = 10,
    current_user_id: Optional[str] = None,
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
