"""
Voice related API endpoints
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from app.api.utils.logger_route import LoggerRoute
from app.services.voice_service import voice_service

router = APIRouter(prefix="/text-to-speech", route_class=LoggerRoute)


@router.get(
    "/list-voices",
    summary="获取音色列表",
    description="获取 ElevenLabs 可用音色列表，支持搜索和过滤功能",
    response_model=List[Dict[str, Any]],
    tags=["voice"],
)
async def list_voices(
    search: Optional[str] = Query(None, description="搜索音色名称关键词"),
    page_size: Optional[int] = Query(
        None, ge=1, le=1000, description="每页返回结果数，默认返回所有音色，最大1000"
    ),
    voice_type: Optional[str] = Query(
        None, description="音色类型过滤 (如: personal, community)"
    ),
    category: Optional[str] = Query(
        None, description="音色分类过滤 (如: premade, cloned)"
    ),
) -> List[Dict[str, Any]]:
    """
    获取 ElevenLabs 音色列表

    支持以下功能：
    - 🔍 按名称搜索音色
    - 📄 分页控制 (page_size)
    - 🏷️ 按类型和分类过滤
    - 📊 返回完整音色元数据

    返回的每个音色包含：
    - voice_id: 音色唯一标识
    - name: 音色名称
    - category: 音色分类
    - settings: 音色设置参数
    - samples: 音色样本信息
    """
    return await voice_service.get_available_voices(
        search=search,
        page_size=page_size,
        voice_type=voice_type,
        category=category,
        include_shared=False,  # 只返回用户个人音色，不包含共享市场音色
    )
