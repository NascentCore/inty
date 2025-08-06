"""
Agents endpoints for accessing agents for interactions.
"""

import traceback
import uuid
from datetime import datetime
from typing import Any, List

import vertexai
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.core.agent.agent import agent_manager
from app.core.agent.avatar import generate_background_image_to_gcs
from app.core.config import settings
from app.schemas.character_card import (
    CharacterCardExportRequest,
    CharacterCardImportRequest,
    CharacterCardImportResponse,
    CharacterCardValidationResponse,
)

# 移除未使用的导入
from app.schemas.response import (
    APIResponse,
    BusinessErrorCode,
    create_business_error_response,
)
from app.services import agent_service
from app.services.character_card_service import character_card_service
from app.services.subscription_service import SubscriptionService
from app.utils.gcs import delete_from_gcs, is_user_gcs_file, upload_to_gcs

router = APIRouter()

# 创建订阅服务实例
subscription_service = SubscriptionService()


@router.get("/", response_model=schemas.APIResponse[List[schemas.Agent]])
async def list_agents(
    db: AsyncSession = Depends(deps.get_async_db),
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user's created AI agents list
    """
    agents = await agent_service.get_user_agents(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        current_user_id=current_user.id,
    )
    return schemas.APIResponse.success(data=agents)


@router.get(
    "/search", response_model=schemas.APIResponse[schemas.PaginationData[schemas.Agent]]
)
async def search_agents(
    q: str = Query(..., description="Search keyword"),
    page: int = Query(1, ge=1, description="Page number, starting from 1"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page, maximum 100"),
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Search public AI agents
    Support fuzzy search by name, description, category
    """
    pagination_data = await agent_service.search_agents(
        db, keyword=q, page=page, page_size=page_size, current_user_id=current_user.id
    )
    return schemas.APIResponse.success(data=pagination_data)


@router.get(
    "/recommend",
    response_model=schemas.APIResponse[schemas.PaginationData[schemas.Agent]],
)
async def recommend_agents(
    db: AsyncSession = Depends(deps.get_async_db),
    page: int = Query(1, ge=1, description="Page number, starting from 1"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page, maximum 100"),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get recommended AI agents list (public and approved agents, ordered by creation time desc)
    """
    pagination_data = await agent_service.get_recommended_agents_paginated(
        db, page=page, page_size=page_size, current_user_id=current_user.id
    )
    return schemas.APIResponse.success(data=pagination_data)


@router.get(
    "/following",
    response_model=schemas.APIResponse[schemas.PaginationData[schemas.Agent]],
)
async def get_following_agents(
    db: AsyncSession = Depends(deps.get_async_db),
    page: int = Query(1, ge=1, description="Page number, starting from 1"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page, maximum 100"),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user's followed AI agents list
    """
    pagination_data = await agent_service.get_user_followed_agents(
        db, user_id=current_user.id, page=page, page_size=page_size
    )
    return schemas.APIResponse.success(data=pagination_data)


@router.post("/", response_model=schemas.APIResponse[schemas.Agent])
async def create_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_in: schemas.AgentCreate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new AI agent

    推荐使用角色卡字段构建AI角色：
    - personality: 角色性格特点 (推荐)
    - scenario: 背景设定 (推荐)
    - first_message: 开场白
    - message_example: 对话示例

    兼容性说明：
    - 仍支持legacy的prompt字段
    - 如果同时提供prompt和角色卡字段，将优先使用角色卡字段
    - 建议新创建的角色使用角色卡字段以获得更好的效果
    """
    # 检查数量限制：系统管理员不限制，普通用户限制6个
    if not current_user.is_superuser:
        # 查询用户已创建的agent数量（不包括已删除的）
        user_agents = await agent_service.get_user_agents(
            db, user_id=current_user.id, skip=0, limit=1000
        )
        if len(user_agents) >= 6:
            raise HTTPException(
                status_code=400,
                detail="普通用户最多只能创建6个Agent，如需创建更多请联系管理员",
            )

    agent = await agent_service.create_agent(
        db, agent_in=agent_in, user_id=current_user.id
    )
    return schemas.APIResponse.success(data=agent)


@router.get("/{agent_id}", response_model=schemas.Agent)
async def get_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get AI agent by ID
    """
    agent = await agent_service.get_agent(
        db, agent_id=agent_id, current_user_id=current_user.id
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/{agent_id}/follow", response_model=schemas.APIResponse[dict])
async def follow_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Follow AI agent
    """
    try:
        await agent_service.follow_agent(db, agent_id=agent_id, user_id=current_user.id)
        return schemas.APIResponse.success(data={"message": "Successfully followed"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to follow AI agent: {str(e)}")
        return schemas.APIResponse.error(message="Failed to follow")


@router.delete("/{agent_id}/follow", response_model=schemas.APIResponse[dict])
async def unfollow_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Unfollow AI agent
    """
    try:
        await agent_service.unfollow_agent(
            db, agent_id=agent_id, user_id=current_user.id
        )
        return schemas.APIResponse.success(data={"message": "Successfully unfollowed"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unfollow AI agent: {str(e)}")
        return schemas.APIResponse.error(message="Failed to unfollow")


@router.put("/{agent_id}", response_model=schemas.Agent)
async def update_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    agent_in: schemas.AgentUpdate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update AI agent
    """
    agent = await agent_service.get_agent(db, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = await agent_service.update_agent(db, db_agent=agent, agent_in=agent_in)
    return agent


@router.delete("/{agent_id}", response_model=schemas.APIResponse[schemas.Agent])
async def delete_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete AI agent
    """
    agent = await agent_service.get_agent(db, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check permission: only creator can delete
    if agent.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    deleted_agent = await agent_service.delete_agent(db, db_agent=agent)
    return schemas.APIResponse.success(data=deleted_agent)


@router.post("/generate_background", response_model=APIResponse[dict])
async def generate_background(
    request: schemas.BackgroundGenerateRequest,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Generate background images based on prompt, save directly to GCS, return image URLs
    """
    try:
        # Validate count parameter
        if request.count < 1 or request.count > 4:
            return APIResponse.error(message="Count must be between 1 and 4")

        # 检查背景图生成限制
        is_allowed, used_count, limit = (
            await subscription_service.check_background_generation_limit(
                db, current_user.id
            )
        )

        if not is_allowed:
            # 超级管理员不受限制
            if not current_user.is_superuser:
                # 返回统一的订阅错误响应
                return create_business_error_response(
                    error_info=BusinessErrorCode.SUBSCRIPTION_REQUIRED,
                    extra_data={
                        "used_count": used_count,
                        "limit": limit,
                        "feature": "background_generation",
                    },
                )

        # Construct GCS base path
        gcs_base_path = f"backgrounds/tmp/{current_user.id}/{uuid.uuid4().hex}"
        gcs_uri_base = f"gs://{settings.gcs.bucket}/{gcs_base_path}"

        # 获取用户性别信息并转换为相应格式
        user_gender = None
        if current_user.gender:
            # 将数据库中的Gender枚举转换为字符串格式
            gender_mapping = {"MALE": "male", "FEMALE": "female", "OTHER": "non-binary"}
            user_gender = gender_mapping.get(current_user.gender.value, "non-binary")

        logger.info(
            f"Starting background generation for user {current_user.id}, prompt: {request.prompt}, count: {request.count}, gender: {user_gender}"
        )

        # Generate images and get actual GCS URLs with RAI reason support
        result = generate_background_image_to_gcs(
            request.prompt,
            gcs_uri_base,
            count=request.count,
            aspect_ratio="9:16",
            gender=user_gender,
            include_rai_reason=True,
        )

        # Handle both new format (with RAI reasons) and old format (just URLs)
        if isinstance(result, dict) and "image_uris" in result:
            gcs_urls = result["image_uris"]
            rai_reasons = result.get("rai_reasons", [])
            if rai_reasons:
                logger.warning(f"Some images were filtered by RAI: {rai_reasons}")
        else:
            # Backward compatibility: if result is still a list
            gcs_urls = result
            rai_reasons = []

        logger.info(f"Successfully generated {len(gcs_urls)} background images")

        # 记录背景图生成使用次数
        try:
            await subscription_service.record_usage(
                db, current_user.id, "background_generation", request.count
            )
            logger.info(
                f"Recorded background generation usage for user {current_user.id}: {request.count} images"
            )
        except Exception as usage_error:
            logger.error(f"Failed to record usage: {str(usage_error)}")
            # 使用记录失败不影响主要功能，继续返回结果

        response_data = {
            "urls": gcs_urls,
            "count": len(gcs_urls),
            "format": "png",
            "remaining_usage": {
                "used_count": used_count + request.count,
                "limit": limit,
            },
        }

        # Include RAI information if available (for debugging/transparency)
        if rai_reasons:
            response_data["rai_filtered_count"] = len(rai_reasons)
            response_data["rai_reasons"] = rai_reasons

        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"Background image generation failed: {str(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")

        # Check if the error message contains RAI filtering information
        error_message = str(e)
        if (
            "RAI filtering reasons:" in error_message
            or "prohibited content" in error_message
        ):
            # Extract RAI-specific error information for better user experience
            return APIResponse.error(
                message="Image generation was blocked due to content policy restrictions. Please modify your prompt and try again.",
                data={
                    "error_type": "RAI_FILTERED",
                    "original_error": error_message,
                    "suggestion": "Try using different descriptions or avoiding potentially sensitive content.",
                },
            )
        else:
            # Generic error handling for other types of failures
            return APIResponse.error(
                message=f"Background image generation failed: {error_message}"
            )


@router.post("/upload-avatar", response_model=APIResponse[dict])
async def upload_avatar_preview(
    file: UploadFile = File(...),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    上传头像文件，返回URL供创建agent时使用
    """
    logger.info(f"=== 开始处理头像上传请求 ===")
    logger.info(f"用户ID: {current_user.id}")
    logger.info(f"用户昵称: {current_user.nickname}")
    logger.info(
        f"文件信息: filename={file.filename}, content_type={file.content_type}, size={file.size if hasattr(file, 'size') else 'unknown'}"
    )

    try:
        # 验证文件类型
        logger.info(f"验证文件类型: content_type={file.content_type}")
        if not file.content_type:
            logger.error("文件content_type为空")
            return APIResponse.error(
                message="File content type is required",
                data={
                    "error_code": "FILE_CONTENT_TYPE_REQUIRED",
                    "error_message": "File content type is required",
                },
            )

        if not file.content_type.startswith("image/"):
            logger.error(f"不支持的文件类型: {file.content_type}")
            return APIResponse.error(message="Only image files are allowed")

        # 验证文件大小 (最大 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        logger.info(f"开始读取文件数据，最大允许大小: {max_size} bytes")
        file_data = await file.read()
        file_size = len(file_data)
        logger.info(f"文件实际大小: {file_size} bytes")

        if file_size > max_size:
            logger.error(f"文件大小超出限制: {file_size} > {max_size}")
            return APIResponse.error(message="File size exceeds 10MB limit")

        # 验证文件扩展名
        logger.info(f"验证文件扩展名: filename={file.filename}")
        if not file.filename:
            logger.error("文件名为空")
            return APIResponse.error(message="Filename is required")

        if "." not in file.filename:
            logger.error(f"文件名格式错误，缺少扩展名: {file.filename}")
            return APIResponse.error(message="Invalid filename")

        file_ext = file.filename.split(".")[-1].lower()
        logger.info(f"文件扩展名: {file_ext}")
        allowed_extensions = ["jpg", "jpeg", "png", "webp"]
        if file_ext not in allowed_extensions:
            logger.error(
                f"不支持的文件扩展名: {file_ext}，支持的格式: {allowed_extensions}"
            )
            return APIResponse.error(
                message="Unsupported file type, only jpg, jpeg, png, webp formats are supported"
            )

        # 生成存储路径
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        avatar_path = (
            f"avatars/tmp/{current_user.id}/{timestamp}-{unique_id}.{file_ext}"
        )
        logger.info(f"生成的存储路径: {avatar_path}")

        # 验证GCS配置
        logger.info(f"GCS配置: bucket={settings.gcs.bucket}")
        if not settings.gcs.bucket:
            logger.error("GCS bucket未配置")
            return APIResponse.error(message="GCS bucket not configured")

        # 上传到GCS
        logger.info("开始上传文件到GCS")
        try:
            url = upload_to_gcs(
                file_data, file.content_type, settings.gcs.bucket, avatar_path
            )
            logger.info(f"GCS上传成功，返回URL: {url}")
        except Exception as gcs_error:
            logger.error(f"GCS上传失败: {str(gcs_error)}")
            logger.error(f"GCS错误堆栈: {traceback.format_exc()}")
            return APIResponse.error(
                message=f"Failed to upload to GCS: {str(gcs_error)}"
            )

        logger.info(f"头像上传成功: {url}")
        response_data = {
            "url": url,
            "filename": file.filename,
            "size": file_size,
            "content_type": file.content_type,
        }
        logger.info(f"返回响应数据: {response_data}")
        return APIResponse.success(data=response_data)

    except ValueError as e:
        logger.error(f"文件验证错误: {str(e)}")
        logger.error(f"验证错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(message=str(e))
    except Exception as e:
        logger.error(f"头像上传失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(message="Avatar upload failed")
    finally:
        logger.info("=== 头像上传请求处理完成 ===")


@router.post("/{agent_id}/avatar", response_model=APIResponse[schemas.Agent])
async def upload_agent_avatar(
    agent_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
        url = upload_to_gcs(
            file_data, file.content_type, settings.gcs.bucket, avatar_path
        )

        # 删除旧头像，但只有当它确实是存储在用户GCS bucket中的文件时才删除
        if agent.avatar and is_user_gcs_file(agent.avatar, settings.gcs.bucket):
            old_path = agent_service.get_path_from_gcs_url(agent.avatar)
            if old_path:
                delete_from_gcs(settings.gcs.bucket, old_path)
                logger.info(f"已删除旧头像: {agent.avatar}")
        elif agent.avatar:
            logger.info(f"跳过删除非GCS头像: {agent.avatar}")

        # 更新数据库
        updated_agent = await agent_service.update_agent(
            db, db_agent=agent, agent_in=schemas.AgentUpdate(avatar=url)
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
        return APIResponse.error(message="Avatar upload failed")


@router.post("/{agent_id}/background", response_model=APIResponse[schemas.Agent])
async def upload_agent_background(
    agent_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
        background_path = agent_service.generate_agent_background_path(
            agent_id, file.filename
        )

        # 上传到GCS
        url = upload_to_gcs(
            file_data, file.content_type, settings.gcs.bucket, background_path
        )

        # 删除旧背景图，但只有当它确实是存储在用户GCS bucket中的文件时才删除
        if agent.background and is_user_gcs_file(agent.background, settings.gcs.bucket):
            old_path = agent_service.get_path_from_gcs_url(agent.background)
            if old_path:
                delete_from_gcs(settings.gcs.bucket, old_path)
                logger.info(f"已删除旧背景图: {agent.background}")
        elif agent.background:
            logger.info(f"跳过删除非GCS背景图: {agent.background}")

        # 更新数据库
        updated_agent = await agent_service.update_agent(
            db, db_agent=agent, agent_in=schemas.AgentUpdate(background=url)
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
        return APIResponse.error(message="Background image upload failed")


@router.post("/{agent_id}/set-background", response_model=APIResponse[schemas.Agent])
async def set_current_background(
    agent_id: str,
    background_url: str = Query(
        ..., description="Background image URL to set as current"
    ),
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Set current background image from background images list
    """
    try:
        # 验证agent是否存在且用户有权限修改
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 检查用户是否是该agent的创建者
        if agent.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

        # 检查背景图URL是否在background_images列表中
        if not agent.background_images or background_url not in agent.background_images:
            return APIResponse.error(
                message="Background image not found in agent's background images list"
            )

        # 更新当前背景图
        updated_agent = await agent_service.update_agent(
            db, db_agent=agent, agent_in=schemas.AgentUpdate(background=background_url)
        )

        return APIResponse.success(data=updated_agent)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Set current background failed: {str(e)}")
        return APIResponse.error(message="Failed to set current background")


@router.post("/{agent_id}/save-backgrounds", response_model=APIResponse[schemas.Agent])
async def save_background_images(
    agent_id: str,
    background_urls: List[str] = Query(
        ..., description="List of background image URLs to save"
    ),
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Save generated background images to agent's background images list
    """
    try:
        # 验证agent是否存在且用户有权限修改
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 检查用户是否是该agent的创建者
        if agent.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

        # 合并现有背景图和新的背景图
        existing_backgrounds = agent.background_images or []
        updated_backgrounds = list(set(existing_backgrounds + background_urls))  # 去重

        # 更新背景图列表
        updated_agent = await agent_service.update_agent(
            db,
            db_agent=agent,
            agent_in=schemas.AgentUpdate(background_images=updated_backgrounds),
        )

        return APIResponse.success(data=updated_agent)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save background images failed: {str(e)}")
        return APIResponse.error(message="Failed to save background images")


@router.get(
    "/creator/{creator_id}/stats",
    response_model=schemas.APIResponse[schemas.CreatorAgentStats],
)
async def get_creator_agent_stats(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    creator_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取创建者的公共角色统计信息
    返回创建者创建的公共角色数量和所有公共角色的总关注数
    """
    try:
        stats = await agent_service.get_creator_agent_stats(db, creator_id=creator_id)
        return schemas.APIResponse.success(data=stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取创建者角色统计失败: {str(e)}")
        return schemas.APIResponse.error(message="Failed to get statistics")


# TODO: Needs to disable this endpoint in production environment.
# https://github.com/NascentCore/inty-backend/issues/43
@router.get("/{agent_id}/prompt", response_model=schemas.APIResponse[dict])
async def get_agent_prompt(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取Agent的最终提示词
    """
    try:
        # 验证agent是否存在
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 检查用户是否是该agent的创建者（只有创建者才能查看提示词）
        if agent.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

        # 尝试从运行中的Agent实例获取提示词
        final_prompt = agent_manager.get_agent_prompt(agent_id)
        template_info = agent_manager.get_agent_template_info(agent_id)

        if final_prompt is None:
            # 如果Agent实例不存在，临时创建一个来获取提示词
            from app.core.agent.prompt_template import prompt_template_manager

            agent_data = {
                "id": agent_id,
                "name": agent.name,
                "prompt": agent.prompt,
                "description": agent.description or "",
                "template_name": "default",  # 默认模版
            }

            final_prompt = prompt_template_manager.render_prompt(agent_data)
            template_info = {
                "template_name": "default",
                "template_variables": prompt_template_manager.get_template(
                    "default"
                ).get_template_variables(),
                "agent_data": agent_data,
            }

        return schemas.APIResponse.success(
            data={
                "agent_id": agent_id,
                "original_prompt": agent.prompt,
                "final_prompt": final_prompt,
                "template_info": template_info,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Agent提示词失败: {str(e)}")
        return schemas.APIResponse.error(message="Failed to get prompts")


@router.get("/{agent_id}/prompt/preview", response_model=schemas.APIResponse[dict])
async def preview_agent_prompt(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    template_name: str = Query("default", description="Template name to use"),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    预览Agent使用指定模版的提示词
    """
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        # 验证agent是否存在
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 检查用户是否是该agent的创建者
        if agent.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

        # 使用指定模版渲染提示词
        from app.core.agent.prompt_template import prompt_template_manager

        agent_data = {
            "id": agent_id,
            "name": agent.name,
            "prompt": agent.prompt,
            "description": agent.description or "",
            "template_name": template_name,
        }

        # 验证模版是否存在
        available_templates = prompt_template_manager.list_templates()
        if template_name not in available_templates:
            return schemas.APIResponse.error(
                message=f"Template '{template_name}' not found. Available templates: {', '.join(available_templates)}"
            )

        final_prompt = prompt_template_manager.render_prompt(agent_data, template_name)
        template = prompt_template_manager.get_template(template_name)

        return schemas.APIResponse.success(
            data={
                "agent_id": agent_id,
                "template_name": template_name,
                "template_variables": template.get_template_variables(),
                "original_prompt": agent.prompt,
                "final_prompt": final_prompt,
                "available_templates": available_templates,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览Agent提示词失败: {str(e)}")
        return schemas.APIResponse.error(message="Failed to preview prompt")


@router.get("/templates", response_model=schemas.APIResponse[dict])
async def list_prompt_templates(
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取所有可用的提示词模版
    """
    try:
        from app.core.agent.prompt_template import prompt_template_manager

        templates = prompt_template_manager.list_templates()
        template_info = {}

        for template_name in templates:
            template = prompt_template_manager.get_template(template_name)
            template_info[template_name] = {
                "name": template_name,
                "variables": template.get_template_variables(),
                "is_valid": template.validate_template(),
            }

        return schemas.APIResponse.success(
            data={"templates": template_info, "total_count": len(templates)}
        )

    except Exception as e:
        logger.error(f"获取提示词模版列表失败: {str(e)}")
        return schemas.APIResponse.error(message="Failed to get template list")


# ==================== 角色卡相关API端点 ====================


@router.post(
    "/import-character-card", response_model=APIResponse[CharacterCardImportResponse]
)
async def import_character_card(
    request: CharacterCardImportRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_async_db),
):
    """
    从JSON数据导入角色卡
    """
    try:
        result = await character_card_service.import_character_card(
            request=request, user_id=current_user.id, db=db
        )

        if result.success:
            return APIResponse.success(data=result)
        else:
            return APIResponse.error(message=result.message, data=result)

    except Exception as e:
        logger.error(f"导入角色卡失败: {str(e)}")
        return APIResponse.error(message=f"Failed to import character card: {str(e)}")


@router.post(
    "/import-character-card-file",
    response_model=APIResponse[CharacterCardImportResponse],
)
async def import_character_card_file(
    file: UploadFile = File(...),
    override_existing: bool = Query(False, description="是否覆盖现有同名角色"),
    import_character_book: bool = Query(True, description="是否导入角色书"),
    import_alternate_greetings: bool = Query(True, description="是否导入替代问候语"),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_async_db),
):
    """
    从文件导入角色卡（支持JSON和PNG文件）
    """
    try:
        # 验证文件大小 (最大10MB)
        if file.size and file.size > 10 * 1024 * 1024:
            return APIResponse.error(message="File size cannot exceed 10MB")

        result = await character_card_service.import_character_card_from_file(
            file=file,
            user_id=current_user.id,
            db=db,
            override_existing=override_existing,
            import_character_book=import_character_book,
            import_alternate_greetings=import_alternate_greetings,
        )

        if result.success:
            return APIResponse.success(data=result)
        else:
            return APIResponse.error(message=result.message, data=result)

    except Exception as e:
        logger.error(f"从文件导入角色卡失败: {str(e)}")
        return APIResponse.error(
            message=f"Failed to import character card from file: {str(e)}"
        )


@router.post("/export-character-card", response_model=APIResponse[dict])
async def export_character_card(
    request: CharacterCardExportRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_async_db),
):
    """
    导出Agent为角色卡格式
    """
    try:
        card_data = await character_card_service.export_agent_to_character_card(
            agent_id=request.agent_id,
            user_id=current_user.id,
            db=db,
            include_character_book=request.include_character_book,
            include_alternate_greetings=request.include_alternate_greetings,
            include_extensions=request.include_extensions,
        )

        return APIResponse.success(data=card_data.dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出角色卡失败: {str(e)}")
        return APIResponse.error(message=f"Failed to export character card: {str(e)}")


@router.get("/{agent_id}/character-card", response_model=APIResponse[dict])
async def get_agent_character_card(
    agent_id: str,
    include_character_book: bool = Query(True, description="是否包含角色书"),
    include_alternate_greetings: bool = Query(True, description="是否包含替代问候语"),
    include_extensions: bool = Query(True, description="是否包含扩展数据"),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_async_db),
):
    """
    获取Agent的角色卡数据
    """
    try:
        card_data = await character_card_service.export_agent_to_character_card(
            agent_id=agent_id,
            user_id=current_user.id,
            db=db,
            include_character_book=include_character_book,
            include_alternate_greetings=include_alternate_greetings,
            include_extensions=include_extensions,
        )

        return APIResponse.success(data=card_data.dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取角色卡数据失败: {str(e)}")
        return APIResponse.error(message=f"Failed to get character card data: {str(e)}")


@router.post(
    "/validate-character-card",
    response_model=APIResponse[CharacterCardValidationResponse],
)
async def validate_character_card(
    card_data: dict, current_user: schemas.User = Depends(deps.get_current_active_user)
):
    """
    验证角色卡数据格式
    """
    try:
        result = await character_card_service.validate_character_card(card_data)
        return APIResponse.success(data=result)

    except Exception as e:
        logger.error(f"验证角色卡失败: {str(e)}")
        return APIResponse.error(message=f"Failed to validate character card: {str(e)}")


@router.get("/character-card/features", response_model=APIResponse[dict])
async def get_character_card_features(
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    获取支持的角色卡功能列表
    """
    try:
        from app.services.character_card_mapper import CharacterCardMapper

        mapper = CharacterCardMapper()
        features = mapper.get_supported_features()

        return APIResponse.success(
            data={
                "supported_features": features,
                "spec_version": "chara_card_v2",
                "spec_version_number": "2.0",
            }
        )

    except Exception as e:
        logger.error(f"获取角色卡功能列表失败: {str(e)}")
        return APIResponse.error(
            message=f"Failed to get character card features: {str(e)}"
        )


@router.get("/models/openrouter", response_model=schemas.APIResponse[List[dict]])
async def get_openrouter_models(
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    获取OpenRouter模型列表
    """
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        from app.services.scoring_service import ScoringService

        scoring_service = ScoringService()
        models = await scoring_service._fetch_openrouter_models()

        if models is None:
            # 如果获取失败，返回默认模型列表
            models = [
                {
                    "id": "openai/gpt-4o",
                    "name": "GPT-4o",
                    "description": "OpenAI最新的多模态模型，支持文本、图像、音频和视频处理",
                },
                {
                    "id": "openai/gpt-4o-mini",
                    "name": "GPT-4o Mini",
                    "description": "OpenAI的轻量级多模态模型，快速且经济",
                },
                {
                    "id": "anthropic/claude-3.5-sonnet",
                    "name": "Claude 3.5 Sonnet",
                    "description": "Anthropic的最新Claude模型，擅长分析、写作和推理",
                },
                {
                    "id": "anthropic/claude-3.5-haiku",
                    "name": "Claude 3.5 Haiku",
                    "description": "Anthropic的快速模型，适合实时对话",
                },
                {
                    "id": "google/gemini-pro-1.5",
                    "name": "Gemini Pro 1.5",
                    "description": "Google的Gemini模型，支持长上下文和多模态",
                },
                {
                    "id": "meta-llama/llama-3.1-405b-instruct",
                    "name": "Llama 3.1 405B Instruct",
                    "description": "Meta最大的开源语言模型，顶级性能",
                },
            ]

        return schemas.APIResponse.success(data=models)

    except Exception as e:
        logger.error(f"获取OpenRouter模型失败: {str(e)}")
        return schemas.APIResponse.error(message=f"获取OpenRouter模型失败: {str(e)}")
