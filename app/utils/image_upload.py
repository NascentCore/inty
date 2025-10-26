"""
Image upload utility functions for processing and uploading images to GCS.
"""

import io
import uuid
from datetime import datetime
from typing import Optional

from fastapi import UploadFile
from loguru import logger
from PIL import Image
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.gcs import append_filename_suffix, upload_to_gcs
from app.schemas.response import APIResponse
from app.services.resource_service import async_create_image_resource
from app.utils.crop_avatar import CROPPED_AVATAR_FILENAME_SUFFIX, crop_avatar
from app.utils.image import (
    ImageFormat,
    ImageSize,
    compress_png_to_jpeg,
    get_jpg_bytes_from_pil_image,
)


class ImageUploadResponse(BaseModel):
    """Image upload response"""
# 上传compressed图片
    url: str
    size: ImageSize
# 上传原图
    original_url: Optional[str] = None
# 上传头像图片
    avatar_url: Optional[str] = None
    avatar_size: Optional[ImageSize] = None


async def process_image_upload(
    file: UploadFile,
    user_id: str,
    async_db: AsyncSession,
    base_path: str = "uploads/images",
    cropping_avatar: bool = False,
    max_size_mb: int = global_config_loaded_from_config_yaml.app.limits.max_image_size_mb,
) -> APIResponse[ImageUploadResponse]:
    """
    Helper function to process image upload with validation, compression, and GCS upload.

    Args:
        file: The uploaded file
        user_id: User ID for creating unique file paths
        db: Database session for creating resource records
        base_path: Base path for file storage (e.g., "avatars/tmp", "uploads/images")
        cropping_avatar: Whether to enable avatar cropping (requires crop_avatar utility)
        max_size_mb: Maximum file size in MB (overrides config if provided)

    Returns:
        APIResponse with success/error status and data
    """
# 验证文件内容类型
    if not file.content_type:
        logger.error("File content type is required")
        return APIResponse.error(
            message="File content type is required",
            data={
                "error_code": "FILE_CONTENT_TYPE_REQUIRED",
                "error_message": "File content type is required",
            },
        )

    if not file.content_type.startswith("image/"):
        logger.error(f"不支持的文件类型: {file.content_type}")
        return APIResponse.error(message="Only image files are allowed")

    max_size_bytes = max_size_mb * 1024 * 1024

    file_data = await file.read()
    file_size = len(file_data)
    logger.debug(f"文件实际大小: {file_size} bytes")

    if file_size > max_size_bytes:
        logger.error(f"文件大小超出限制: {file_size} > {max_size_bytes}")
        return APIResponse.error(
            message=f"File size exceeds {max_size_mb}MB limit",
            data={
                "error_code": "FILE_SIZE_EXCEEDED",
                "max_size_mb": max_size_mb,
                "actual_size_bytes": file_size,
            },
        )
# 验证文件名
    if not file.filename:
        logger.error("Filename is required")
        return APIResponse.error(message="Filename is required")

    if "." not in file.filename:
        logger.error(f"文件名格式错误，缺少扩展名: {file.filename}")
        return APIResponse.error(message="Invalid filename")
# 验证文件扩展名
    file_ext = file.filename.split(".")[-1].lower()
    logger.debug(f"文件扩展名: {file_ext}")
    allowed_extensions = [
        ImageFormat.JPG,
        ImageFormat.JPEG,
        ImageFormat.PNG,
        ImageFormat.WEBP,
    ]
    if file_ext not in allowed_extensions:
        logger.error(
            f"不支持的文件扩展名: {file_ext}，支持的格式: {allowed_extensions}"
        )
        return APIResponse.error(
            message="Unsupported file type, only jpg, jpeg, png, webp formats are supported",
            data={
                "error_code": "UNSUPPORTED_FILE_TYPE",
                "supported_formats": allowed_extensions,
                "received_format": file_ext,
            },
        )
# compression 存储原始文件数据之前
    original_file_data = file_data
    original_file_ext = file_ext
    original_content_type = file.content_type
# Compress PNG 和大文件
# 始终为 compress PNG，如果文件 > 500KB，则也为 compress。
# 未来我们可能会调整500KB的阈值。
#理由是在智能手机上，500KB JPEG应该足够了。
# PNG 是无损格式，因此我们可以将其 compress 转换为 JPEG 以节省空间。
# TODO：在请求体中显式添加参数compress_image来控制。
# 并不总是 compress png 文件。
    compression_threshold_size_bytes = (
        global_config_loaded_from_config_yaml.app.limits.image_compression_threshold_size_kb
        * 1024
    )
    was_compressed = False
    if file_ext == ImageFormat.PNG or len(file_data) > compression_threshold_size_bytes:
        file_data = compress_png_to_jpeg(file_data)
        file_ext = ImageFormat.JPEG
        was_compressed = True
        logger.debug(
            f"Compressed PNG ({file_size} bytes) to JPEG ({len(file_data)} bytes)"
        )

    img = Image.open(io.BytesIO(original_file_data))
    size = ImageSize(width=img.width, height=img.height)
    logger.debug(f"图片大小: {size}")
#唯一生成的文件路径
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    file_gcs_path = f"{base_path}/{user_id}/{timestamp}-{unique_id}.{file_ext}"

    gcs_url = upload_to_gcs(
        file_data,
        file.content_type,
        global_config_loaded_from_config_yaml.gcs.bucket,
        file_gcs_path,
    )
# 将 GCS URL 转换为 CDN URL
    from app.services.image_transform_service import image_transform_service

    try:
        url = image_transform_service.transform_mobile(gcs_url)
        logger.debug(f"图片 上传 GCS 成功，CDN URL: {url}")
    except Exception as transform_error:
        logger.warning(
            f"Failed to transform URL to CDN: {gcs_url}, error: {str(transform_error)}"
        )
        url = gcs_url  # Fallback to original GCS URL

    result = ImageUploadResponse(url=url, size=size)
    logger.debug(f"图片 上传 GCS 成功，返回URL: {url}")
# 如果图片是 compressed 并且不是头像，还上传 uncompressed 版本
    if was_compressed:
# 生成uncompressed图像的路径
        uncompressed_file_gcs_path = f"{base_path}/{user_id}/{timestamp}-{unique_id}-original.{original_file_ext}"
# 将uncompressed文件上传到GCS
        uncompressed_gcs_url = upload_to_gcs(
            original_file_data,
            original_content_type,
            global_config_loaded_from_config_yaml.gcs.bucket,
            uncompressed_file_gcs_path,
        )
# 将 uncompressed GCS URL 转换为 CDN URL
        try:
            uncompressed_url = image_transform_service.transform_mobile(
                uncompressed_gcs_url
            )
            logger.debug(f"Uploaded original image, CDN URL: {uncompressed_url}")
        except Exception as transform_error:
            logger.warning(
                f"Failed to transform original URL to CDN: {uncompressed_gcs_url}, error: {str(transform_error)}"
            )
            uncompressed_url = uncompressed_gcs_url  # Fallback to original GCS URL

        result.original_url = uncompressed_url
# 只存储CDN URL，将GCS URL保存在元数据中
        await async_create_image_resource(
            async_db=async_db,
            user_id=user_id,
            url=uncompressed_url,
            size=size,
            format=ImageFormat(original_file_ext),
            byte_size=len(original_file_data),
            gcs_url=uncompressed_gcs_url,  # Store GCS URL in metadata
        )
# 为compressed镜像创建资源记录
# 只存储CDN URL，将GCS URL保存在元数据中
    await async_create_image_resource(
        async_db=async_db,
        user_id=user_id,
        url=url,
        size=size,
        format=ImageFormat(file_ext),
        byte_size=len(file_data),
        gcs_url=gcs_url,  # Store GCS URL in metadata
    )
# 如果启用则处理
    if cropping_avatar:
        crop_avatar_result = crop_avatar(file_data)
        cropped_avatar = crop_avatar_result.image
        result.avatar_size = crop_avatar_result.size
# 将 PIL 图像转换为字节以供 GCS 上传
        jpg_data = get_jpg_bytes_from_pil_image(cropped_avatar)

        cropped_file_gcs_path = append_filename_suffix(
            file_gcs_path, CROPPED_AVATAR_FILENAME_SUFFIX
        )

        cropped_avatar_gcs_url = upload_to_gcs(
            jpg_data,
            f"image/{ImageFormat.JPEG}",  # Cropped image is always JPEG
            global_config_loaded_from_config_yaml.gcs.bucket,
            cropped_file_gcs_path,
        )
# 将修剪后的头像 GCS URL 转换为 CDN URL
        try:
            cropped_avatar_url = image_transform_service.transform_mobile(
                cropped_avatar_gcs_url
            )
            logger.debug(f"扣脸图片上传 GCS 成功, CDN URL: {cropped_avatar_url}")
        except Exception as transform_error:
            logger.warning(
                f"Failed to transform avatar URL to CDN: {cropped_avatar_gcs_url}, error: {str(transform_error)}"
            )
            cropped_avatar_url = cropped_avatar_gcs_url  # Fallback to original GCS URL

        result.avatar_url = cropped_avatar_url
# 写入上传图片的元数据，可能是compressed。
#只存储CDN URL，在元数据中保存GCS URL
        await async_create_image_resource(
            async_db=async_db,
            user_id=user_id,
            url=cropped_avatar_url,
            size=crop_avatar_result.size,
            format=ImageFormat.JPEG,
            byte_size=len(jpg_data),
            cropped=True,
            uncropped_image_url=result.url,
            gcs_url=cropped_avatar_gcs_url,  # Store GCS URL in metadata
        )

    return APIResponse.success(data=result)
