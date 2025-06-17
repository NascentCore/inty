from typing import List, Optional
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
import logging
import uuid
import math
from datetime import datetime

from app import models, schemas
from app.models.agent import AgentVisibility, AgentStatus
from app.core.config import settings

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
        
        # 处理图片URL：验证、复制临时文件到永久路径、删除临时文件
        try:
            processed_agent_data = process_agent_image_urls(agent_data, agent_id, user_id)
            logger.info(f"成功处理Agent图片URL - Agent ID: {agent_id}")
        except Exception as e:
            logger.error(f"处理Agent图片URL失败 - Agent ID: {agent_id}, Error: {str(e)}")
            # 图片处理失败不应该阻止Agent创建，使用原始数据
            processed_agent_data = agent_data
        
        db_agent = models.Agent(
            id=agent_id,
            **processed_agent_data,
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

def generate_agent_avatar_path(agent_id: str, filename: str) -> str:
    """生成agent头像的存储路径"""
    ext = filename.split('.')[-1].lower()
    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
        raise ValueError(f"Unsupported file type: {ext}")
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"agents/{agent_id}/avatar-{timestamp}-{unique_id}.{ext}"

def generate_agent_background_path(agent_id: str, filename: str) -> str:
    """生成agent背景图的存储路径"""
    ext = filename.split('.')[-1].lower()
    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
        raise ValueError(f"Unsupported file type: {ext}")
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"agents/{agent_id}/background-{timestamp}-{unique_id}.{ext}"

def get_path_from_gcs_url(url: str) -> str:
    """从GCS URL中提取文件路径"""
    if not url:
        return ""
    parts = url.split(".com/")
    if len(parts) < 2:
        return ""
    path = parts[1]
    # 去掉bucket名前缀
    bucket = settings.gcs.bucket
    if path.startswith(bucket + "/"):
        path = path[len(bucket) + 1 :]
    return path

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
    from app.utils.gcs import is_valid_gcs_url, is_temp_gcs_path, copy_gcs_file, delete_from_gcs
    
    processed_data = agent_data.copy()
    temp_files_to_delete = []
    
    # 处理头像
    if agent_data.get('avatar'):
        avatar_url = agent_data['avatar']
        if is_valid_gcs_url(avatar_url):
            if is_temp_gcs_path(avatar_url, user_id):
                try:
                    # 生成永久路径
                    # 从临时URL中提取文件扩展名
                    temp_path = get_path_from_gcs_url(avatar_url)
                    file_ext = temp_path.split('.')[-1] if '.' in temp_path else 'png'
                    permanent_path = generate_agent_avatar_path(agent_id, f"avatar.{file_ext}")
                    
                    # 复制到永久路径
                    new_avatar_url = copy_gcs_file(avatar_url, permanent_path, settings.gcs.bucket)
                    processed_data['avatar'] = new_avatar_url
                    
                    # 标记临时文件待删除
                    temp_files_to_delete.append(avatar_url)
                    
                    logger.info(f"复制头像从临时路径到永久路径: {avatar_url} -> {new_avatar_url}")
                except Exception as e:
                    logger.error(f"复制头像失败: {str(e)}")
                    # 如果复制失败，保持原URL
        else:
            logger.warning(f"无效的头像URL: {avatar_url}")
            processed_data['avatar'] = None
    
    # 处理背景图
    if agent_data.get('background'):
        background_url = agent_data['background']
        if is_valid_gcs_url(background_url):
            if is_temp_gcs_path(background_url, user_id):
                try:
                    # 生成永久路径
                    temp_path = get_path_from_gcs_url(background_url)
                    file_ext = temp_path.split('.')[-1] if '.' in temp_path else 'png'
                    permanent_path = generate_agent_background_path(agent_id, f"background.{file_ext}")
                    
                    # 复制到永久路径
                    new_background_url = copy_gcs_file(background_url, permanent_path, settings.gcs.bucket)
                    processed_data['background'] = new_background_url
                    
                    # 标记临时文件待删除
                    temp_files_to_delete.append(background_url)
                    
                    logger.info(f"复制背景图从临时路径到永久路径: {background_url} -> {new_background_url}")
                except Exception as e:
                    logger.error(f"复制背景图失败: {str(e)}")
                    # 如果复制失败，保持原URL
        else:
            logger.warning(f"无效的背景图URL: {background_url}")
            processed_data['background'] = None
    
    # 处理相册图片
    if agent_data.get('photos') and isinstance(agent_data['photos'], list):
        processed_photos = []
        for i, photo_url in enumerate(agent_data['photos']):
            if is_valid_gcs_url(photo_url):
                if is_temp_gcs_path(photo_url, user_id):
                    try:
                        # 生成永久路径
                        temp_path = get_path_from_gcs_url(photo_url)
                        file_ext = temp_path.split('.')[-1] if '.' in temp_path else 'png'
                        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                        unique_id = uuid.uuid4().hex[:8]
                        permanent_path = f"agents/{agent_id}/photos/photo-{i+1}-{timestamp}-{unique_id}.{file_ext}"
                        
                        # 复制到永久路径
                        new_photo_url = copy_gcs_file(photo_url, permanent_path, settings.gcs.bucket)
                        processed_photos.append(new_photo_url)
                        
                        # 标记临时文件待删除
                        temp_files_to_delete.append(photo_url)
                        
                        logger.info(f"复制相册图片从临时路径到永久路径: {photo_url} -> {new_photo_url}")
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
        
        processed_data['photos'] = processed_photos
    
    # 删除临时文件（在后台异步执行）
    if temp_files_to_delete:
        def cleanup_temp_files():
            for temp_url in temp_files_to_delete:
                try:
                    temp_path = get_path_from_gcs_url(temp_url)
                    if temp_path:
                        delete_from_gcs(settings.gcs.bucket, temp_path)
                        logger.info(f"删除临时文件: {temp_url}")
                except Exception as e:
                    logger.error(f"删除临时文件失败 {temp_url}: {str(e)}")
        
        # 在后台线程中执行清理
        import threading
        cleanup_thread = threading.Thread(target=cleanup_temp_files)
        cleanup_thread.daemon = True
        cleanup_thread.start()
    
    return processed_data 