from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import traceback
import uuid
import vertexai

from app import schemas
from app.api import deps
from app.services import agent_service
from app.utils.gcs import upload_to_gcs, delete_from_gcs
from app.core.config import settings
from app.schemas.response import APIResponse
from app.core.agent.avater import generate_background_image_to_gcs

router = APIRouter()

@router.get("/", response_model=List[schemas.Agent])
async def list_agents(
    db: AsyncSession = Depends(deps.get_async_db),
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取当前用户创建的AI角色列表
    """
    agents = await agent_service.get_user_agents(db, user_id=current_user.id, skip=skip, limit=limit)
    return agents

@router.get("/recommend", response_model=schemas.APIResponse[schemas.PaginationData[schemas.Agent]])
async def recommend_agents(
    db: AsyncSession = Depends(deps.get_async_db),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量，最大100"),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取推荐的AI角色列表（公开且已审核的角色，按创建时间倒序）
    """
    pagination_data = await agent_service.get_recommended_agents_paginated(db, page=page, page_size=page_size)
    return schemas.APIResponse.success(data=pagination_data)

@router.post("/", response_model=schemas.Agent)
async def create_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_in: schemas.AgentCreate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新的AI角色
    """
    agent = await agent_service.create_agent(db, agent_in=agent_in, user_id=current_user.id)
    return agent

@router.get("/{agent_id}", response_model=schemas.Agent)
async def get_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    通过ID获取AI角色
    """
    agent = await agent_service.get_agent(db, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.put("/{agent_id}", response_model=schemas.Agent)
async def update_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    agent_in: schemas.AgentUpdate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新AI角色
    """
    agent = await agent_service.get_agent(db, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = await agent_service.update_agent(db, db_agent=agent, agent_in=agent_in)
    return agent

@router.delete("/{agent_id}", response_model=schemas.Agent)
async def delete_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除AI角色
    """
    agent = await agent_service.get_agent(db, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = await agent_service.delete_agent(db, db_agent=agent)
    return agent

@router.post("/generate_background", response_model=APIResponse[dict])
async def generate_background(
    prompt: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user)
):
    """
    根据prompt生成背景图片，直接保存到GCS，返回图片URL
    """
    try:
        # 构造GCS路径
        gcs_path = f"backgrounds/tmp/{current_user.id}/{uuid.uuid4().hex}.png"
        gcs_uri = f"gs://{settings.gcs.bucket}/{gcs_path}"
        
        # 生成图片并获取实际的GCS路径
        actual_gcs_uri = generate_background_image_to_gcs(prompt, gcs_uri, aspect_ratio="16:9")
        
        # 将gs://bucket/path格式转换为https://storage.googleapis.com/bucket/path格式
        if actual_gcs_uri.startswith("gs://"):
            # 去掉gs://前缀，构建HTTPS URL
            gcs_path_actual = actual_gcs_uri[5:]  # 去掉"gs://"
            url = f"https://storage.googleapis.com/{gcs_path_actual}"
        else:
            # 备用方案：使用原始路径
            url = f"https://storage.googleapis.com/{settings.gcs.bucket}/{gcs_path}"
        
        return APIResponse.success(data={"url": url, "format": "png"})
    except Exception as e:
        logger.error(f"背景图生成失败: {str(e)}")
        return APIResponse.error(message="背景图生成失败")

@router.post("/{agent_id}/avatar", response_model=APIResponse[schemas.Agent])
async def upload_agent_avatar(
    agent_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user)
):
    """
    上传AI角色头像
    """
    try:
        # 验证agent是否存在且用户有权限修改
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # 检查用户是否是该agent的创建者
        if agent.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # 读取文件数据
        file_data = await file.read()
        
        # 生成存储路径
        avatar_path = agent_service.generate_agent_avatar_path(agent_id, file.filename)
        
        # 上传到GCS
        url = upload_to_gcs(file_data, file.content_type, settings.gcs.bucket, avatar_path)
        
        # 删除旧头像
        if agent.avatar:
            old_path = agent_service.get_path_from_gcs_url(agent.avatar)
            if old_path:
                delete_from_gcs(settings.gcs.bucket, old_path)
        
        # 更新数据库
        updated_agent = await agent_service.update_agent(
            db, 
            db_agent=agent, 
            agent_in=schemas.AgentUpdate(avatar=url)
        )
        
        return APIResponse.success(data=updated_agent)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"文件类型错误: {str(e)}")
        return APIResponse.error(message=str(e))
    except Exception as e:
        logger.error(f"头像上传失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(message="头像上传失败")

@router.post("/{agent_id}/background", response_model=APIResponse[schemas.Agent])
async def upload_agent_background(
    agent_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user)
):
    """
    上传AI角色背景图
    """
    try:
        # 验证agent是否存在且用户有权限修改
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # 检查用户是否是该agent的创建者
        if agent.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # 读取文件数据
        file_data = await file.read()
        
        # 生成存储路径
        background_path = agent_service.generate_agent_background_path(agent_id, file.filename)
        
        # 上传到GCS
        url = upload_to_gcs(file_data, file.content_type, settings.gcs.bucket, background_path)
        
        # 删除旧背景图
        if agent.background:
            old_path = agent_service.get_path_from_gcs_url(agent.background)
            if old_path:
                delete_from_gcs(settings.gcs.bucket, old_path)
        
        # 更新数据库
        updated_agent = await agent_service.update_agent(
            db, 
            db_agent=agent, 
            agent_in=schemas.AgentUpdate(background=url)
        )
        
        return APIResponse.success(data=updated_agent)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"文件类型错误: {str(e)}")
        return APIResponse.error(message=str(e))
    except Exception as e:
        logger.error(f"背景图上传失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(message="背景图上传失败") 