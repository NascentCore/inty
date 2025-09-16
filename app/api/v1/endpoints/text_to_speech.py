"""
Voice related API endpoints
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from app.api.utils.logger_route import LoggerRoute
from app.schemas.response import APIResponse, PaginationData
from app.services.voice_service import voice_service

router = APIRouter(prefix="/text-to-speech", route_class=LoggerRoute)


@router.get(
    "/list-voices",
    summary="获取音色列表",
    description="获取 ElevenLabs 可用音色列表，支持搜索和过滤功能",
    response_model=APIResponse[PaginationData[Dict[str, Any]]],
    tags=["voice"],
)
async def list_voices(
    search: Optional[str] = Query(None, description="搜索音色名称关键词"),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="每页返回结果数，默认20，最大100（ElevenLabs限制）",
    ),
    voice_type: Optional[str] = Query(
        None, description="音色类型过滤 (如: personal, community)"
    ),
    category: Optional[str] = Query(
        None, description="音色分类过滤 (如: premade, cloned)"
    ),
) -> APIResponse[PaginationData[Dict[str, Any]]]:
    """
    获取 ElevenLabs 音色列表

    支持以下功能：
    - 🔍 按名称搜索音色
    - 📄 分页控制 (page, page_size)
    - 🏷️ 按类型和分类过滤
    - 📊 返回完整音色元数据

    返回的每个音色包含：
    - voice_id: 音色唯一标识
    - name: 音色名称
    - category: 音色分类
    - settings: 音色设置参数
    - samples: 音色样本信息
    """
    # 计算skip和limit
    skip = (page - 1) * page_size

    voices = await voice_service.get_available_voices(
        search=search, page_size=page_size, voice_type=voice_type, category=category
    )

    # 这里假设voices是一个列表，实际可能需要从service获取总数
    total = len(voices)  # 这里应该是实际的总数，可能需要额外查询
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1

    # 构建分页数据
    pagination_data = PaginationData(
        items=voices,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )

    return APIResponse.success(data=pagination_data)
