# CREATED_BY_AGENT
"""
Image 服务代理 - 直接调用主应用的工具函数
"""

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.response import APIResponse
from app.utils.image_upload import process_image_upload


async def upload_image(
    file: UploadFile,
    user_id: str,
    async_db: AsyncSession,
    cropping_avatar: bool = False,
) -> APIResponse[dict]:
    """上传图片"""
    base_path = (
        f"avatars/{user_id}" if cropping_avatar else "images/uploads"
    )
    result = await process_image_upload(
        file=file,
        user_id=user_id,
        async_db=async_db,
        base_path=base_path,
        cropping_avatar=cropping_avatar,
    )
    if result.data:
        result.data = result.data.model_dump()
    return result

