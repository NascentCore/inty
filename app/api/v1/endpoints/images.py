"""
Images endpoints for general image upload functionality.
"""

import traceback

from fastapi import APIRouter, Depends, File, Form, UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.api import deps
from app.api.tags import (
    ANDROID_APP_TAG,
    INTY_EVAL_TAG,
    WEB_APP_TAG,
    NOT_USED_TAG,
)
from app.api.utils.logger_route import LoggerRoute
from app.schemas.response import APIResponse
from app.utils.image_upload import process_image_upload
from app.schemas.user import User as UserSchema

router = APIRouter(prefix="/images", route_class=LoggerRoute)


@router.post(
    "",
    response_model=APIResponse[dict],
    description="Upload image file with validation, compression, and GCS storage",
    summary="Upload image and get the URL of the image",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG, NOT_USED_TAG],
)
async def upload_image(
    file: UploadFile = File(...),
    cropping_avatar: bool = Form(False),
    current_user: UserSchema = Depends(deps.get_current_active_user),
    # 更新图片元数据
    async_db: AsyncSession = Depends(deps.get_async_db),
) -> APIResponse[dict]:
    """
    Upload image file with validation, compression, and GCS storage.
    This endpoint reuses the same logic as the agent avatar upload endpoint.

    Args:
        file: The uploaded image file
        cropping_avatar: Whether to enable avatar cropping (default: False)
        current_user: Current authenticated user

    Returns:
        APIResponse with success/error status and image data
    """
    try:
        # Use helper function to process image upload
        # Use avatars directory for unified storage, similar to backgrounds
        base_path = (
            f"avatars/{current_user.id}"
            if cropping_avatar
            else "images/uploads"
        )
        result = await process_image_upload(
            file=file,
            user_id=current_user.id,
            async_db=async_db,
            base_path=base_path,
            cropping_avatar=cropping_avatar,  # Use the direct parameter
        )
        if result.data:
            # 如果返回的是错误，则 data == None，就无需转换数据
            result.data = result.data.model_dump()
        return result
    except ValueError as e:
        logger.error(f"文件验证错误: {str(e)}")
        logger.error(f"验证错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(message=str(e))
    except Exception as e:
        logger.error(f"图片上传失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return APIResponse.error(message="Image upload failed")
    finally:
        logger.debug("=== 图片上传请求处理完成 ===")
