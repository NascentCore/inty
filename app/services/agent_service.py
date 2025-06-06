from typing import List, Optional
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
import logging
import uuid
import math

from app import models, schemas
from app.models.agent import AgentVisibility, AgentStatus

logger = logging.getLogger(__name__)

async def get_agent(db: AsyncSession, agent_id: str) -> Optional[models.Agent]:
    """
    通过ID获取AI角色
    """
    try:
        result = await db.execute(
            select(models.Agent)
            .options(selectinload(models.Agent.creator))
            .where(models.Agent.id == agent_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误 - 获取角色 {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")
    except Exception as e:
        logger.error(f"未知错误 - 获取角色 {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

async def get_user_agents(db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100) -> List[models.Agent]:
    """
    获取用户创建的AI角色列表
    """
    try:
        # 验证参数
        if skip < 0:
            raise HTTPException(status_code=400, detail="skip参数不能为负数")
        if limit <= 0 or limit > 1000:
            raise HTTPException(status_code=400, detail="limit参数必须在1-1000之间")
            
        result = await db.execute(
            select(models.Agent)
            .options(selectinload(models.Agent.creator))
            .where(models.Agent.creator_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(desc(models.Agent.created_at))
        )
        return result.scalars().all()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误 - 获取用户角色列表: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")
    except Exception as e:
        logger.error(f"未知错误 - 获取用户角色列表: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

async def get_recommended_agents(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[models.Agent]:
    """
    获取推荐的AI角色列表（公开且已审核的角色，按创建时间倒序）
    """
    try:
        # 验证参数
        if skip < 0:
            raise HTTPException(status_code=400, detail="skip参数不能为负数")
        if limit <= 0 or limit > 1000:
            raise HTTPException(status_code=400, detail="limit参数必须在1-1000之间")
            
        result = await db.execute(
            select(models.Agent)
            .options(selectinload(models.Agent.creator))
            .where(
                models.Agent.visibility == AgentVisibility.PUBLIC,
                # models.Agent.status == AgentStatus.APPROVED
            )
            .offset(skip)
            .limit(limit)
            .order_by(desc(models.Agent.created_at))
        )
        return result.scalars().all()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误 - 获取推荐角色列表: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")
    except Exception as e:
        logger.error(f"未知错误 - 获取推荐角色列表: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

async def get_recommended_agents_paginated(db: AsyncSession, page: int = 1, page_size: int = 10) -> schemas.PaginationData[schemas.Agent]:
    """
    获取推荐的AI角色列表（分页版本）
    """
    try:
        # 验证参数
        if page <= 0:
            raise HTTPException(status_code=400, detail="page参数必须大于0")
        if page_size <= 0 or page_size > 100:
            raise HTTPException(status_code=400, detail="page_size参数必须在1-100之间")
            
        # 计算偏移量
        skip = (page - 1) * page_size
        
        # 构建基础查询条件
        base_query = select(models.Agent).where(
            models.Agent.visibility == AgentVisibility.PUBLIC,
            # models.Agent.status == AgentStatus.APPROVED
        )
        
        # 获取总数
        count_query = select(func.count()).select_from(
            base_query.subquery()
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # 获取分页数据
        data_query = (
            base_query
            .options(selectinload(models.Agent.creator))
            .offset(skip)
            .limit(page_size)
            .order_by(desc(models.Agent.created_at))
        )
        
        result = await db.execute(data_query)
        agents = result.scalars().all()
        
        # 计算总页数
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        
        return schemas.PaginationData[schemas.Agent](
            list=agents,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误 - 获取推荐角色分页列表: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库查询失败")
    except Exception as e:
        logger.error(f"未知错误 - 获取推荐角色分页列表: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

async def create_agent(db: AsyncSession, agent_in: schemas.AgentCreate, user_id: str) -> models.Agent:
    """
    创建新的AI角色
    """
    try:
        # 验证必填字段
        if not agent_in.name or not agent_in.name.strip():
            raise HTTPException(status_code=400, detail="角色名称不能为空")
        
        # 生成唯一ID
        agent_id = str(uuid.uuid4())
        
        # 获取Agent数据
        agent_data = agent_in.dict()
        
        db_agent = models.Agent(
            id=agent_id,
            **agent_data,
            creator_id=user_id
        )
        
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

async def update_agent(db: AsyncSession, db_agent: models.Agent, agent_in: schemas.AgentUpdate) -> models.Agent:
    """
    更新AI角色
    """
    try:
        if not db_agent:
            raise HTTPException(status_code=404, detail="角色不存在")
            
        # 验证更新数据
        update_data = agent_in.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的数据")
            
        # 验证名称不为空（如果提供了名称）
        if 'name' in update_data and (not update_data['name'] or not update_data['name'].strip()):
            raise HTTPException(status_code=400, detail="角色名称不能为空")
        
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
        return result.scalar_one()
        
    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"数据完整性错误 - 更新角色 {db_agent.id if db_agent else 'unknown'}: {str(e)}")
        raise HTTPException(status_code=400, detail="数据完整性约束违反")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 更新角色 {db_agent.id if db_agent else 'unknown'}: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 更新角色 {db_agent.id if db_agent else 'unknown'}: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

async def delete_agent(db: AsyncSession, db_agent: models.Agent) -> models.Agent:
    """
    删除AI角色
    """
    try:
        if not db_agent:
            raise HTTPException(status_code=404, detail="角色不存在")
            
        await db.delete(db_agent)
        await db.commit()
        return db_agent
        
    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"数据完整性错误 - 删除角色 {db_agent.id if db_agent else 'unknown'}: {str(e)}")
        raise HTTPException(status_code=400, detail="无法删除角色，存在关联数据")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"数据库错误 - 删除角色 {db_agent.id if db_agent else 'unknown'}: {str(e)}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        await db.rollback()
        logger.error(f"未知错误 - 删除角色 {db_agent.id if db_agent else 'unknown'}: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误") 