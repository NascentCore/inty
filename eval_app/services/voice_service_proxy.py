# CREATED_BY_AGENT
"""
Voice 服务代理 - 直接调用主应用的服务层
"""

from typing import Any, Dict, List, Optional

from app.services.voice_service import voice_service


async def get_available_voices(
    search: Optional[str] = None,
    page_size: Optional[int] = None,
    voice_type: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """获取可用音色列表"""
    return await voice_service.get_available_voices(
        search=search,
        page_size=page_size,
        voice_type=voice_type,
        category=category,
        include_shared=False,
    )

