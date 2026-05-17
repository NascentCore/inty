"""
Voice related API endpoints
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from app.api.tags import INTY_EVAL_TAG, WEB_APP_TAG
from app.api.utils.logger_route import LoggerRoute
from app.services.voice_service import voice_service

router = APIRouter(prefix="/text-to-speech", route_class=LoggerRoute)


@router.get(
    "/list-voices",
    summary="获取音色列表",
    description="获取可用音色列表（包含 Gemini TTS 和 ElevenLabs），支持搜索和过滤功能",
    response_model=List[Dict[str, Any]],
    tags=["voice", INTY_EVAL_TAG, WEB_APP_TAG],
)
async def list_voices(
    search: Optional[str] = Query(None, description="搜索音色名称关键词"),
    page_size: Optional[int] = Query(
        None,
        ge=1,
        le=1000,
        description="每页返回结果数，默认返回所有音色，最大1000",
    ),
    voice_type: Optional[str] = Query(
        None, description="音色类型过滤 (如: personal, preset)"
    ),
    category: Optional[str] = Query(
        None, description="音色分类过滤 (如: prebuilt, premade, cloned)"
    ),
    provider: Optional[str] = Query(
        None,
        description='TTS 服务提供商过滤 ("gemini" 或 "elevenlabs"，不传则返回所有)',
    ),
) -> List[Dict[str, Any]]:
    """
    获取可用音色列表

    支持以下功能：
    - 🔍 按名称搜索音色
    - 📄 分页控制 (page_size)
    - 🏷️ 按类型、分类和 provider 过滤
    - 📊 返回完整音色元数据

    返回的每个音色包含：
    - voice_id: 音色唯一标识
    - name: 音色名称
    - provider: TTS 服务提供商 ("gemini" 或 "elevenlabs")
    - category: 音色分类
    - source: 音色来源 (preset, regular, shared 等)
    - settings: 音色设置参数（仅 ElevenLabs）
    - samples: 音色样本信息（仅 ElevenLabs）
    - gender: 音色性别（仅 Gemini）
    - description: 音色描述（仅 Gemini）

    Gemini TTS 预置音色列表（30种）：
    Zephyr, Puck, Charon, Kore, Fenrir, Aoede, Orus, Leda, Elf, Orbit,
    Altair, Cove, Birch, Maple, Vale, Breeze, Juniper, Solaris, Vega, Nova,
    Stella, Eclipse, Dawn, Ember, Shade, Cosmos, Saga, Aurora, Summit, Meadow
    """
    return await voice_service.get_available_voices(
        search=search,
        page_size=page_size,
        voice_type=voice_type,
        category=category,
        include_shared=False,  # 只返回用户个人音色，不包含共享市场音色
        provider=provider,
    )
