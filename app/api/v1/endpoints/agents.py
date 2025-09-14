"""
Agents endpoints for accessing agents for interactions.
"""

import traceback
import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.schemas.agent import AgentSortConfig
from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.core.agent.agent import agent_manager
from app.utils.gemini import ImagenGeneratedImage, text_to_image
from app.core.config import global_config_loaded_from_config_yaml
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
from app.utils.image import ImageFormat, AspectRatio


router = APIRouter(prefix="/ai/agents", route_class=LoggerRoute)


@router.get(
    "/",
    response_model=schemas.APIResponse[List[schemas.Agent]],
    deprecated=True,
    include_in_schema=False,
    summary="[Deprecated, use /me, kept for v1.0.3 compatibility]",
)
@router.get(
    "/me",
    response_model=schemas.APIResponse[List[schemas.Agent]],
    summary="Get list of user's created AI characters",
    description="This endpoint is used by an registered user to list their created AI characters (agents as a misnomer)",
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
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        current_user_id=current_user.id,
    )
    return schemas.APIResponse.success(data=agents)


@router.get(
    "/search",
    response_model=schemas.APIResponse[schemas.PaginationData[schemas.Agent]],
    summary="Used by inty-eval to list all public AI characters",
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


class RecommendAgentsRequest(BaseModel):
    """
    替换掉现有的参数
    """
    
    index: int = Query(1, ge=1, description="0-index, the starting index of the recommended agents list")
    count: int = Query(10, ge=1, le=100, description="count of recommended agents, app should balance between smoothness and loading speed")
    sort_config: AgentSortConfig = Query(AgentSortConfig(), description="sort method and sort seed")


@router.get(
    "/recommend",
    response_model=schemas.APIResponse[schemas.PaginationData[schemas.Agent]],
)
async def recommend_agents(
    db: AsyncSession = Depends(deps.get_async_db),
    page: int = Query(1, ge=1, description="Page number, starting from 1"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page, maximum 100"),
    sort: schemas.AgentSortOption = Query(schemas.AgentSortOption.CREATED_DESC, description="Sort order: created_asc, created_desc, random"),
    # TODO: Fill in the implementation. 目前还没有使用该参数，因为还没有实现推荐算法。
    # 目前不会影响 app 端正常使用。详情查看：https://github.com/NascentCore/inty/issues/484
    # 实现原理：
    # SELECT * FROM (
    # SELECT *, md5(id || 'sort.sort_seed') as hash 
    # FROM agents
    # ) ORDER BY hash;
    # app 需要记录 sort seed，每次请求新的推荐列表时，要提供新的 sort seed；
    # 以下这些场景下，需要生成新的 sort seed：
    # 1. Home 页 featured 列表每次 app 重新启动时
    # 2. Explore 页每次顶部下拉刷新推荐列表
    # 然后每次请求 /recommends 要提供这个 sort seed，否则会返回相同的推荐列表。
    request: RecommendAgentsRequest = Depends(RecommendAgentsRequest),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get recommended AI agents list (public and approved agents)
    
    Sorting options:
    - created_desc: Most recent first (default)
    - created_asc: Oldest first 
    - random: Random order
    """
    pagination_data = await agent_service.get_recommended_agents_paginated(
        db, page=page, page_size=page_size, sort_by=sort, current_user_id=current_user.id
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
    "/",
    response_model=schemas.APIResponse[schemas.Agent],
    deprecated=True,
    include_in_schema=False,
    summary="Deprecated, use /api/v1/ai/agents instead, kept for v1.0.3 compatibility",
    description="Deprecated, use /api/v1/ai/agents instead, kept for v1.0.3 compatibility",
)
@router.post(
    "",
    response_model=schemas.APIResponse[schemas.Agent],
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


@router.post(
    "/generate_background",
    response_model=APIResponse[dict],
    deprecated=True,
    include_in_schema=False,
    summary="Deprecated, use /generate_background instead",
    description="Deprecated, use /generate_background instead",
)
@router.post(
    "/text-to-image",
    response_model=APIResponse[dict],
    summary="[Deprecated, use /api/v1/images/text-to-image instead] Generate images based on text description",
    deprecated=True,
    include_in_schema=False,
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

        # Generate images and get actual GCS URLs with RAI reason support
        generated_images = text_to_image(
            request.prompt,
            request.negative_prompt,
            request.enhance_prompt,
            gender=opposite_gender,
            aspect_ratio=AspectRatio.PORTRAIT,
            gcs_uri_base=gcs_uri_base,
            count=request.count,
        )

        result = process_generated_images(generated_images)

        gcs_urls = result["image_uris"]
        rai_reasons = result["rai_reasons"]

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


@router.get(
    "/creator/{creator_id}/stats",
    # Not used by anyone
    deprecated=True,
    include_in_schema=False,
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


# ==================== 角色卡相关API端点 ====================


@router.post(
    "/import-character-card",
    response_model=APIResponse[CharacterCardImportResponse],
    include_in_schema=False,
    tags=["unknown", "inty-eval"],
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
    tags=["unknown", "inty-eval"],
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
    tags=["unknown", "inty-eval"],
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
    tags=["unknown", "inty-eval"],
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
    tags=["unknown", "inty-eval"],
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
    tags=["unknown", "inty-eval"],
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
    tags=["inty-eval"],
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
