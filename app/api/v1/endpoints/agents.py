"""
Agents endpoints for accessing agents for interactions.
"""

import traceback
import uuid
from typing import Any, Dict, List, Union

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.api.tags import (
    ANDROID_APP_TAG,
    INTERNAL_API_TAG,
    INTY_EVAL_TAG,
    NOT_USED_TAG,
    WEB_APP_TAG,
)
from app.api.utils.logger_route import LoggerRoute
from app.core.agent import prompts as agent_prompts
from app.core.config import global_config_loaded_from_config_yaml
from app.core.model_selection import select_text_to_image_model
from app.core.user_privilege.superuser_check import is_superuser
from app.external_services.fal import is_fal_model
from app.external_services.text_to_image import (
    TextToImageGenerationRequest,
    TextToImageProvider,
    generate_text_to_image,
)
from app.schemas.character_card import (
    CharacterCardExportRequest,
    CharacterCardImportRequest,
    CharacterCardImportResponse,
    CharacterCardValidationResponse,
)
from app.schemas.response import (
    APIResponse,
    BusinessErrorCode,
    create_business_error_response,
)
from app.services import agent_service
from app.services.character_card_service import character_card_service
from app.services.global_services import subscription_service
from app.services import memory_service
from app.services.resource_service import async_create_image_resource
from app.utils.gemini import ImagenGeneratedImage, text_to_image
from app.utils.image import AspectRatio, ImageFormat

router = APIRouter(prefix="/ai/agents", route_class=LoggerRoute)


async def get_current_superuser(
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> schemas.User:
    """验证当前用户是否为超级管理员"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="只有超级用户才能访问此接口",
        )
    return current_user


@router.get(
    "/me",
    response_model=schemas.APIResponse[List[schemas.Agent]],
    summary="Get list of user's created AI characters",
    description="This endpoint is used by an registered user to list their created AI characters (agents as a misnomer)",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
)
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
        current_user=current_user,
        skip=skip,
        limit=limit,
    )
    return schemas.APIResponse.success(data=agents)


@router.get(
    "/admin/list",
    response_model=schemas.APIResponse[List[schemas.Agent]],
    summary="Admin list all AI characters (for evaluation console)",
    description="Superuser-only endpoint to list all AI characters, including those created by non-superusers.",
    tags=[INTY_EVAL_TAG],
)
async def admin_list_all_agents(
    db: AsyncSession = Depends(deps.get_async_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    if not is_superuser(current_user):
        raise HTTPException(status_code=403, detail="只有超级用户才能访问此接口")

    agents = await agent_service.get_all_agents_for_admin(db, skip=skip, limit=limit)
    return schemas.APIResponse.success(data=agents)


@router.get(
    "/search",
    response_model=schemas.APIResponse[schemas.PaginationData[schemas.Agent]],
    summary="Used by inty-eval to list all public AI characters",
    tags=[INTY_EVAL_TAG, WEB_APP_TAG, NOT_USED_TAG],
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
        db, keyword=q, page=page, page_size=page_size, current_user=current_user
    )
    return schemas.APIResponse.success(data=pagination_data)


@router.get(
    "/recommend",
    response_model=schemas.APIResponse[schemas.PaginationData[schemas.Agent]],
    summary="Get recommended AI agents list",
    description=(
        "Get recommended AI agents list (public and approved agents), "
        "sort_seed is required when sort is random, "
        "which is used to ensure deterministic order for the random sort option"
    ),
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
)
async def recommend_agents(
    db: AsyncSession = Depends(deps.get_async_db),
    page: int = Query(1, ge=1, description="Page number, starting from 1"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page, maximum 100"),
    sort: schemas.AgentSortOption = Query(
        schemas.AgentSortOption.CREATED_DESC,
        description="Sort order: created_asc, created_desc, random, score_based_random, energy_points",
    ),
    sort_seed: str = Query(
        "", description="Sort seed for deterministic random ordering"
    ),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get recommended AI agents list (public and approved agents)

    Sorting options (default: created_desc):
    - created_desc: Most recent first
    - created_asc: Oldest first
    - random: Random order (uses sort_seed for deterministic results)
    - score_based_random: Score-based recommendation (6 high-score agents + 4 random agents)
    - energy_points: Sort by energy points in descending order (highest first)

    For score_based_random algorithm:
    - Returns 6 agents with highest scores (5-star first, then 4-star, etc.)
    - Plus 4 randomly selected agents
    - Uses sort_seed for consistent results across pagination requests
    """
    pagination_data = await agent_service.get_recommended_agents_paginated(
        db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        sort_by=sort,
        sort_seed=sort_seed,
    )
    return schemas.APIResponse.success(data=pagination_data)


########################################################
# To test create agent API:
# curl -X POST "http://localhost:8000/api/v1/ai/agents" \
#   -H "Content-Type: application/json" \
#   -H "Authorization: Bearer TOKEN" \
#   -d '{
#     "name": "Test Agent",
#     "gender": "FEMALE",
#     "visibility": "PRIVATE",
#     "intro": "This is a test AI agent",
#     "opening": "Hello! I am your AI assistant.",
#     "main_prompt": "main_prompt",
#     "personality": "personality",
#     "mode_prompt": "mode_prompt",
#     "background": "<background_image_url>"
#   }'
########################################################
@router.post(
    "",
    response_model=schemas.APIResponse[Union[schemas.Agent, Dict[str, Any]]],
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
    summary="Create new AI agent",
    description="Create new AI agent, used by app and inty-eval",
)
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
    is_allowed, agent_count, limit = (
        await subscription_service.check_agent_creation_limit(db, current_user)
    )
    if not is_allowed:
        return create_business_error_response(
            error_info=BusinessErrorCode.AGENT_CREATION_LIMIT_REACHED,
            extra_data={
                "used_count": agent_count,
                "limit": limit,
                "feature": "agent_creation",
            },
        )

    agent = await agent_service.create_agent(
        db, agent_in=agent_in, user_id=current_user.id
    )
    return schemas.APIResponse.success(data=agent)


@router.get(
    "/{agent_id}",
    response_model=schemas.Agent,
    operation_id="get_public_agent_by_id",
    summary="Get public agent by ID",
    description="Get public agent by ID, include pre-generated agents and user-created public agents",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
)
async def get_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get AI agent by ID
    """
    agent_orm = await agent_service.get_agent(
        db, agent_id=agent_id, current_user_id=current_user.id
    )
    if not agent_orm:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent_schema = schemas.Agent.model_validate(agent_orm)
    festival_list = await memory_service.get_festival_memories_for_user_agent(
        db, current_user.id, agent_id
    )
    if festival_list:
        agent_schema.features = schemas.AgentFeatures(
            festival_memories=[
                schemas.FestivalMemoryItem(**item) for item in festival_list
            ]
        )
    return agent_schema


@router.put(
    "/{agent_id}",
    response_model=schemas.Agent,
    summary="更新智能体（AI 角色）",
    description=(
        "更新任何图片，都会将图片全部记录在 background_images 字段中，用于保存历史记录"
        "如果没有提供 avatar，则会自动截取头像，并记录在 avatar 字段中"
    ),
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
)
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


@router.delete(
    "/{agent_id}",
    response_model=schemas.APIResponse[schemas.Agent],
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
)
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


@router.post(
    "/{agent_id}/generate-background-animated",
    response_model=schemas.APIResponse[schemas.Agent],
    summary="生成背景动图（需要 9:16 比例背景图）",
    description="通过 Google Veo3 API 生成视频，然后转换为 webp 动图格式存储。背景图必须是 9:16 比例，否则会返回错误提示。",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def generate_background_animated(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: schemas.GenerateBackgroundAnimatedRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    生成背景动图并更新到 Agent

    通过 Google Veo3 API 生成视频，然后转换为 webp 动图格式存储。
    背景图必须是 9:16 比例，否则会返回错误提示。
    """
    # 验证 Agent 存在且用户有权限
    agent = await agent_service.get_agent(db, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 验证背景图是否存在
    if not agent.background:
        raise HTTPException(status_code=400, detail="请先上传背景图")

    try:
        from app.services.image_transform_service import image_transform_service
        from app.services.video_generation_service import video_generation_service
        from app.utils.gemini import generate_image_description

        # 1. 将背景图 URL 转换为 GCS URI 格式
        background_url = agent.background
        background_gcs_uri = None

        # 如果是 CDN URL，先转换为 GCS URL
        if image_transform_service.is_cloudflare_url(background_url):
            gcs_url = image_transform_service.cloudflare_to_gcs(background_url)
            if gcs_url:
                # 转换为 gs:// 格式
                gcs_path = image_transform_service.extract_gcs_path(gcs_url)
                if gcs_path:
                    background_gcs_uri = f"gs://{gcs_path}"
        elif image_transform_service.is_gcs_url(background_url):
            # 已经是 GCS URL，转换为 gs:// 格式
            gcs_path = image_transform_service.extract_gcs_path(background_url)
            if gcs_path:
                background_gcs_uri = f"gs://{gcs_path}"
        else:
            # 如果无法转换，尝试直接使用（可能是 HTTPS URL）
            background_gcs_uri = background_url

        if not background_gcs_uri:
            logger.warning(
                f"无法将背景图 URL 转换为 GCS URI: {background_url}，将直接使用原 URL"
            )
            background_gcs_uri = background_url

        # 2. 生成默认提示词（如果请求中没有提供）
        prompt = request.prompt
        if not prompt or not prompt.strip():
            try:
                logger.info(f"开始从背景图生成默认提示词: {background_gcs_uri}")
                prompt = generate_image_description(background_gcs_uri)
                logger.info(f"生成的默认提示词: {prompt}")
            except Exception as e:
                logger.error(f"生成默认提示词失败: {str(e)}")
                # 如果生成失败，使用 Agent 的 intro 或 scenario 作为回退
                if agent.intro:
                    prompt = agent.intro
                elif agent.scenario:
                    prompt = agent.scenario
                else:
                    prompt = "一个美丽的场景"
                logger.warning(f"使用回退提示词: {prompt}")

        # 3. 调用 Veo3 生成视频（使用背景图作为输入图片）
        logger.info(
            f"开始为 Agent {agent_id} 生成视频，提示词: {prompt}, "
            f"输入图片: {background_gcs_uri}"
        )
        video_gcs_uri = await video_generation_service.generate_video_with_veo3(
            prompt=prompt,
            duration=4,
            image_uri=background_gcs_uri,
        )

        # 4. 将视频转换为 webp 动图
        logger.info(f"开始将视频转换为 webp 动图: {video_gcs_uri}")
        from app.utils.video_to_animated_image import (
            convert_video_to_animated_image_and_upload,
        )

        # 将 GCS URI 转换为 CDN URL 用于下载
        video_url = image_transform_service.transform_desktop(video_gcs_uri)

        # 转换为 webp 动图并上传
        webp_url = await convert_video_to_animated_image_and_upload(
            video_url=video_url,
            user_id=current_user.id,
            output_format="webp",
            duration=4,
            base_path="uploads/animated_images",
        )

        # 5. 更新 Agent 的 background_animated 字段
        from app.schemas.agent import AgentUpdate

        agent_update = AgentUpdate(background_animated=webp_url)
        updated_agent = await agent_service.update_agent(
            db, db_agent=agent, agent_in=agent_update
        )

        logger.info(f"背景动图生成成功，webp URL: {webp_url}")
        return schemas.APIResponse.success(data=updated_agent)

    except HTTPException:
        raise
    except NotImplementedError as e:
        logger.error(f"Veo3 API 调用失败: {str(e)}")
        raise HTTPException(
            status_code=501,
            detail=f"视频生成功能暂未实现或 API 配置错误: {str(e)}",
        )
    except ValueError as e:
        logger.error(f"参数验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        error_msg = str(e)
        # 检查是否是 ffmpeg 相关错误
        if "ffmpeg" in error_msg.lower():
            logger.error(f"FFmpeg 相关错误: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"视频转换失败: {error_msg}。"
                "请参考文档 backend/docs/FFMPEG_INSTALLATION.md 了解安装方法。",
            )
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        logger.error(f"生成背景动图失败: {str(e)}\n{error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"生成背景动图失败: {str(e)}",
        )


def get_opposite_gender(gender: str) -> str:
    gender_mapping = {
        "male": "female",
        "female": "male",
        "non-binary": "",
        "they/them": "",
        "nb": "",  # non-binary 的简写
        "other": "",
        "": "",
    }
    normalized_gender = gender.lower().strip()
    opposite = gender_mapping.get(normalized_gender, "")
    return opposite


def process_generated_images(generated_images: List[ImagenGeneratedImage]) -> dict:
    """
    Process the generated images and return the HTTPS URL list and RAI filtering reasons.
    """
    generated_uris = []
    rai_reasons = []

    for i, image in enumerate(generated_images):
        if image.rai_filtered_reason:
            rai_reasons.append(image.rai_filtered_reason)
            logger.warning(f"Image {i} filtered by RAI: {image.rai_filtered_reason}")
            continue
        generated_uris.append(image.gcs_uri)

    if not generated_uris:
        raise Exception(f"No images were generated, rai reasons: {rai_reasons}")

    return {"image_uris": generated_uris, "rai_reasons": rai_reasons}


async def _download_and_upload_to_gcs(
    url: str,
    gcs_bucket: str,
    gcs_path: str,
    content_type: str | None = None,
) -> tuple[str, int | None]:
    """
    从 URL 下载图片并上传到 GCS。

    Args:
        url: 图片的源 URL
        gcs_bucket: GCS bucket 名称
        gcs_path: GCS 存储路径（不含 bucket）
        content_type: 图片的 MIME 类型，如果未指定则尝试从 URL 推断

    Returns:
        (gcs_uri, byte_size) 元组
    """
    import httpx

    from app.external_services.gcs import upload_to_gcs

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        image_bytes = response.content

    resolved_content_type = content_type
    if not resolved_content_type:
        if url.lower().endswith(".png"):
            resolved_content_type = "image/png"
        elif url.lower().endswith((".jpg", ".jpeg")):
            resolved_content_type = "image/jpeg"
        elif url.lower().endswith(".webp"):
            resolved_content_type = "image/webp"
        else:
            resolved_content_type = "image/png"

    upload_to_gcs(
        file_data=image_bytes,
        content_type=resolved_content_type,
        bucket_name=gcs_bucket,
        path=gcs_path,
    )

    gcs_uri = f"https://storage.googleapis.com/{gcs_bucket}/{gcs_path}"
    return gcs_uri, len(image_bytes)


async def _generate_with_fal_ai(
    *,
    model: str,
    prompt: str,
    negative_prompt: str | None,
    num_images: int,
    gcs_bucket: str,
    gcs_base_path: str,
) -> tuple[list[ImagenGeneratedImage], list[str], list[str], dict]:
    """
    使用 fal.ai 生成图片，下载并上传到 GCS。

    Returns:
        (generated_images, gcs_urls, rai_reasons, gcs_url_to_img_dict) 元组
    """
    from app.utils.image import ImageSize

    fal_api_key = global_config_loaded_from_config_yaml.fal.api_key

    fal_request = TextToImageGenerationRequest(
        model=model,
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_images=num_images,
        provider_args={
            "api_key": fal_api_key,
            "image_size": "portrait_4_3",
            "output_format": "png",
        },
    )

    logger.debug(f"Calling fal.ai text-to-image with model: {model}")
    fal_result = generate_text_to_image(fal_request)
    logger.debug(f"fal.ai returned {len(fal_result.images)} images")

    generated_images: list[ImagenGeneratedImage] = []
    gcs_urls: list[str] = []
    gcs_url_to_img_dict: dict = {}

    for i, fal_image in enumerate(fal_result.images):
        if not fal_image.url:
            logger.warning(f"fal.ai image {i} has no URL, skipping")
            continue

        file_ext = "png"
        if fal_image.mime_type:
            if "jpeg" in fal_image.mime_type or "jpg" in fal_image.mime_type:
                file_ext = "jpg"
            elif "webp" in fal_image.mime_type:
                file_ext = "webp"

        gcs_path = f"{gcs_base_path}/fal_{uuid.uuid4().hex}.{file_ext}"

        try:
            gcs_uri, byte_size = await _download_and_upload_to_gcs(
                url=fal_image.url,
                gcs_bucket=gcs_bucket,
                gcs_path=gcs_path,
                content_type=fal_image.mime_type,
            )
            logger.debug(f"Uploaded fal.ai image to GCS: {gcs_uri}")

            image_size = None
            if fal_image.width and fal_image.height:
                image_size = ImageSize(width=fal_image.width, height=fal_image.height)

            imagen_image = ImagenGeneratedImage(
                gcs_uri=gcs_uri,
                size=image_size,
                byte_size=byte_size,
                format=ImageFormat.PNG if file_ext == "png" else ImageFormat.JPEG,
                rai_filtered_reason=None,
                enhanced_prompt=prompt,
            )
            generated_images.append(imagen_image)
            gcs_urls.append(gcs_uri)
            gcs_url_to_img_dict[gcs_uri] = imagen_image

        except Exception as e:
            logger.error(f"Failed to download/upload fal.ai image {i}: {e}")
            continue

    if not gcs_urls:
        raise Exception("No images were generated from fal.ai")

    return generated_images, gcs_urls, [], gcs_url_to_img_dict


@router.post(
    "/text-to-image",
    response_model=APIResponse[dict],
    summary="[Deprecated, use /api/v1/images/text-to-image instead] Generate images based on text description",
    deprecated=True,
    include_in_schema=True,
    tags=[INTY_EVAL_TAG],
)
async def generate_background(
    request: schemas.TextToImageRequest,
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

        check_result = await subscription_service.check_image_gen_limit(
            db, current_user
        )

        if not check_result[0]:
            return create_business_error_response(
                error_info=BusinessErrorCode.IMAGE_GENERATION_LIMIT_REACHED,
                extra_data={
                    "used_count": check_result[1],
                    "limit": check_result[2],
                    "feature": "background_generation",
                },
            )

        # Construct GCS base path - use unified directory instead of tmp
        gcs_base_path = f"backgrounds/{current_user.id}/{uuid.uuid4().hex}"
        gcs_uri_base = (
            f"gs://{global_config_loaded_from_config_yaml.gcs.bucket}/{gcs_base_path}"
        )

        # 获取用户性别信息并转换为相应格式
        user_gender = None
        if current_user.gender:
            # 将数据库中的Gender枚举转换为字符串格式
            gender_mapping = {"MALE": "male", "FEMALE": "female", "OTHER": "non-binary"}
            user_gender = gender_mapping.get(current_user.gender.value, "non-binary")

        logger.debug(
            f"Starting background generation for user {current_user.id}, prompt: {request.prompt}, count: {request.count}, gender: {user_gender}"
        )

        opposite_gender = get_opposite_gender(user_gender)

        subscription = await subscription_service.get_user_current_subscription(
            db, current_user.id
        )

        # 优先使用请求指定的模型，否则根据订阅状态自动选择
        image_model = request.model or select_text_to_image_model(
            user=current_user, is_subscribed=bool(subscription)
        )

        gcs_bucket = global_config_loaded_from_config_yaml.gcs.bucket

        # 根据模型类型选择不同的生成流程
        if is_fal_model(image_model):
            # fal.ai 生图流程
            generated_images, gcs_urls, rai_reasons, gcs_url_to_img_dict = (
                await _generate_with_fal_ai(
                    model=image_model,
                    prompt=request.prompt,
                    negative_prompt=request.negative_prompt,
                    num_images=request.count,
                    gcs_bucket=gcs_bucket,
                    gcs_base_path=gcs_base_path,
                )
            )
        else:
            # Google Imagen 生图流程
            generated_images = text_to_image(
                request.prompt,
                request.negative_prompt,
                request.enhance_prompt,
                gender=opposite_gender,
                aspect_ratio=AspectRatio.PORTRAIT,
                gcs_uri_base=gcs_uri_base,
                count=request.count,
                model=image_model,
            )

            result = process_generated_images(generated_images)
            gcs_url_to_img_dict = {}
            for image in generated_images:
                if not image.gcs_uri:
                    continue
                gcs_url_to_img_dict[image.gcs_uri] = image

            gcs_urls = result["image_uris"]
            rai_reasons = result["rai_reasons"]

        # Convert GCS URLs to CDN URLs
        from app.services.image_transform_service import image_transform_service

        cdn_urls = []
        cdn_url_to_img_dict = {}
        for gcs_url in gcs_urls:
            try:
                cdn_url = image_transform_service.transform_desktop(gcs_url)
                logger.debug(f"Transformed GCS URL to CDN URL: {gcs_url} -> {cdn_url}")
                cdn_urls.append(cdn_url)
                cdn_url_to_img_dict[cdn_url] = gcs_url_to_img_dict[gcs_url]
            except Exception as transform_error:
                logger.warning(
                    f"Failed to transform URL to CDN: {gcs_url}, error: {str(transform_error)}"
                )
                cdn_urls.append(gcs_url)  # Fallback to original URL
                cdn_url_to_img_dict[gcs_url] = gcs_url_to_img_dict[gcs_url]

        # Create image resource records for each generated image
        # Only create CDN URL records, store GCS URL in metadata to avoid duplicates
        for i, cdn_url in enumerate(cdn_urls):
            # Get corresponding GCS URL for this CDN URL
            gcs_url = gcs_urls[i] if i < len(gcs_urls) else None

            # Get image info from CDN URL dict
            img_info = cdn_url_to_img_dict[cdn_url]

            await async_create_image_resource(
                async_db=db,
                user_id=current_user.id,
                url=cdn_url,
                size=img_info.size,
                format=img_info.format,
                byte_size=img_info.byte_size,
                compressed=False,  # Generated images are not compressed
                cropped=False,  # Generated images are not cropped
                gcs_url=gcs_url,  # Store GCS URL in metadata
                generation_prompt=request.prompt,
            )
            logger.debug(
                f"Created image resource record for CDN URL: {cdn_url}, GCS URL: {gcs_url}"
            )

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
            "urls": cdn_urls,
            "count": len(cdn_urls),
            "format": ImageFormat.JPEG,
            "remaining_usage": {
                "used_count": check_result[1] + request.count,
                "limit": check_result[2],
            },
        }

        # Include RAI information if available (for debugging/transparency)
        if rai_reasons:
            response_data["rai_filtered_count"] = len(rai_reasons)
            response_data["rai_reasons"] = rai_reasons

        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"Background image generation failed: {str(e)}")
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


# ==================== 角色卡相关API端点 ====================


@router.post(
    "/import-character-card",
    response_model=APIResponse[CharacterCardImportResponse],
    include_in_schema=False,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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
    include_in_schema=False,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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


@router.post(
    "/export-character-card",
    response_model=APIResponse[dict],
    include_in_schema=False,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
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


@router.get(
    "/{agent_id}/character-card",
    response_model=APIResponse[dict],
    include_in_schema=False,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
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
    include_in_schema=False,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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


@router.get(
    "/character-card/features",
    response_model=APIResponse[dict],
    include_in_schema=False,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
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


@router.get(
    "/models/openrouter",
    response_model=schemas.APIResponse[List[dict]],
    include_in_schema=False,
    summary="Get OpenRouter models list",
    description="Get OpenRouter models, used by inty-eval to list all available models, so users can select models for evaluation",
    tags=[INTY_EVAL_TAG],
)
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


@router.get(
    "/image-generation/config",
    response_model=schemas.APIResponse[Dict[str, Any]],
    summary="获取图片生成配置",
    description="获取当前图片生成的提示词模板和默认参数配置",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_image_generation_config(
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """获取图片生成配置"""
    try:
        config = {
            "prompt_template": agent_prompts.IMAGE_GENERATION_PROMPT_TEMPLATE,
            "default_history_count": global_config_loaded_from_config_yaml.agent.image_generation_default_history_count,
            "free_user_chat_image_model": global_config_loaded_from_config_yaml.agent.free_user_chat_image_model,
            "sub_user_chat_image_model": global_config_loaded_from_config_yaml.agent.sub_user_chat_image_model,
            "free_user_chat_image_gemini_model": global_config_loaded_from_config_yaml.agent.free_user_chat_image_gemini_model,
            "sub_user_chat_image_gemini_model": global_config_loaded_from_config_yaml.agent.sub_user_chat_image_gemini_model,
        }

        logger.debug(f"用户 {current_user.id} 获取图片生成配置")
        return schemas.APIResponse.success(data=config)

    except Exception as e:
        logger.error(f"获取图片生成配置失败: {str(e)}")
        return schemas.APIResponse.error(message=f"获取图片生成配置失败: {str(e)}")


@router.get(
    "/prompts/available",
    response_model=schemas.APIResponse[Dict[str, Any]],
    summary="获取可用的 prompt 列表",
    description="获取可用的主提示词和模式提示词列表，以及 force_default_prompts 配置状态",
    tags=[INTY_EVAL_TAG, WEB_APP_TAG, NOT_USED_TAG],
)
async def get_available_prompts(
    include_content: bool = Query(False, description="是否包含完整的 prompt 内容"),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """获取可用的 prompt 列表"""
    try:
        from app.core.agent import prompts as agent_prompts
        from app.core.config import global_config_loaded_from_config_yaml

        main_prompts = [
            {
                "id": prompt.id,
                "name": prompt.name,
                "description": prompt.description,
                **({"content": prompt.content} if include_content else {}),
            }
            for prompt in agent_prompts.AVAILABLE_MAIN_PROMPTS
        ]

        mode_prompts = [
            {
                "id": prompt.id,
                "name": prompt.name,
                "description": prompt.description,
                **({"content": prompt.content} if include_content else {}),
            }
            for prompt in agent_prompts.AVAILABLE_MODE_PROMPTS
        ]

        config = {
            "main_prompts": main_prompts,
            "mode_prompts": mode_prompts,
            "force_default_prompts": global_config_loaded_from_config_yaml.agent.force_default_prompts,
            "default_main_prompt_id": agent_prompts.DEFAULT_MAIN_PROMPT_ID,
            "default_mode_prompt_id": agent_prompts.DEFAULT_MODE_PROMPT_ID,
        }

        logger.debug(f"用户 {current_user.id} 获取可用 prompt 列表")
        return schemas.APIResponse.success(data=config)

    except Exception as e:
        logger.error(f"获取可用 prompt 列表失败: {str(e)}")
        return schemas.APIResponse.error(message=f"获取可用 prompt 列表失败: {str(e)}")


@router.put(
    "/image-generation/config",
    response_model=schemas.APIResponse[Dict[str, Any]],
    summary="更新图片生成配置",
    description="更新图片生成的提示词模板和默认参数配置（仅超级用户）",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def update_image_generation_config(
    config: Dict[str, Any],
    current_user: schemas.User = Depends(get_current_superuser),
) -> Any:
    """
    更新图片生成配置（仅超级用户）

    注意：此接口更新内存中的配置，重启后会恢复到config.yaml中的值。
    如需持久化，请直接修改config.yaml文件。
    """
    try:
        # 更新内存中的配置
        if "prompt_template" in config:
            agent_prompts.IMAGE_GENERATION_PROMPT_TEMPLATE = config["prompt_template"]

        if "default_history_count" in config:
            global_config_loaded_from_config_yaml.agent.image_generation_default_history_count = config[
                "default_history_count"
            ]

        if "free_user_chat_image_model" in config:
            global_config_loaded_from_config_yaml.agent.free_user_chat_image_model = (
                config["free_user_chat_image_model"]
            )

        if "sub_user_chat_image_model" in config:
            global_config_loaded_from_config_yaml.agent.sub_user_chat_image_model = (
                config["sub_user_chat_image_model"]
            )

        if "free_user_chat_image_gemini_model" in config:
            global_config_loaded_from_config_yaml.agent.free_user_chat_image_gemini_model = config[
                "free_user_chat_image_gemini_model"
            ]

        if "sub_user_chat_image_gemini_model" in config:
            global_config_loaded_from_config_yaml.agent.sub_user_chat_image_gemini_model = config[
                "sub_user_chat_image_gemini_model"
            ]

        logger.info(f"超级用户 {current_user.id} 更新了图片生成配置")

        # 返回更新后的配置
        updated_config = {
            "prompt_template": agent_prompts.IMAGE_GENERATION_PROMPT_TEMPLATE,
            "default_history_count": global_config_loaded_from_config_yaml.agent.image_generation_default_history_count,
            "free_user_chat_image_model": global_config_loaded_from_config_yaml.agent.free_user_chat_image_model,
            "sub_user_chat_image_model": global_config_loaded_from_config_yaml.agent.sub_user_chat_image_model,
            "free_user_chat_image_gemini_model": global_config_loaded_from_config_yaml.agent.free_user_chat_image_gemini_model,
            "sub_user_chat_image_gemini_model": global_config_loaded_from_config_yaml.agent.sub_user_chat_image_gemini_model,
        }

        return schemas.APIResponse.success(data=updated_config)

    except Exception as e:
        logger.error(f"更新图片生成配置失败: {str(e)}")
        return schemas.APIResponse.error(message=f"更新图片生成配置失败: {str(e)}")
