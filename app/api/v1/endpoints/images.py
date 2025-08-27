"""
Images endpoints for general image upload functionality.
"""

import traceback
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from loguru import logger

from app import schemas
from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.schemas.response import APIResponse
from app.schemas.images import ImageUploadRequest
from app.utils.image_upload import process_image_upload

router = APIRouter(prefix="/images", route_class=LoggerRoute)


@router.post(
    "",
    response_model=APIResponse[dict],
    description="Upload image file with validation, compression, and GCS storage",
    summary="Upload image and get the URL of the image",
)
async def upload_image(
    request: ImageUploadRequest = Depends(),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> APIResponse[dict]:
    """
    Upload image file with validation, compression, and GCS storage.
    This endpoint reuses the same logic as the agent avatar upload endpoint.

    Args:
        request: The image upload request containing file and options
        current_user: Current authenticated user

    Returns:
        APIResponse with success/error status and image data
    """
    try:
        # Use helper function to process image upload
        return await process_image_upload(
            file=request.file,
            user_id=current_user.id,
            base_path="images/uploads",
            enable_cropping=request.enable_cropping,  # Use the request parameter
        )
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
