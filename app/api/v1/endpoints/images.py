"""
Images endpoints for general image upload functionality.
"""

import traceback

from fastapi import APIRouter, Depends, File, UploadFile, Form

from app import schemas
from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.schemas.response import APIResponse
from app.utils.image_upload import process_image_upload

from loguru import logger
router = APIRouter(
    prefix="/images",
    route_class=LoggerRoute,
    tags=["images"],
    summary="For general image upload functionality",
    description="Use these APIs to upload images, and get the URL of the image",
)


@router.post(
    "",
    response_model=APIResponse[dict],
    description="Upload image file with validation, compression, and GCS storage",
    summary="Upload image and get the URL of the image",
)
async def upload_image(
    file: UploadFile = File(...),
    cropping_avatar: bool = Form(False),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
        base_path = f"avatars/{current_user.id}" if cropping_avatar else "images/uploads"
        result = await process_image_upload(
            file=file,
            user_id=current_user.id,
            base_path=base_path,
            cropping_avatar=cropping_avatar,  # Use the direct parameter
        )
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
