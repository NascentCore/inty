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

    # Uploaded compressed image
    url: str
    size: ImageSize
    # Uploaded original image
    original_url: Optional[str] = None
    # Uploaded avatar image
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

    # Validate filename
    if not file.filename:
        logger.error("Filename is required")
        return APIResponse.error(message="Filename is required")

    if "." not in file.filename:
        logger.error(f"文件名格式错误，缺少扩展名: {file.filename}")
        return APIResponse.error(message="Invalid filename")

    # Validate file extension
    file_ext = file.filename.split(".")[-1].lower()
    logger.debug(f"文件扩展名: {file_ext}")
    allowed_extensions = [
        ImageFormat.JPG,
        ImageFormat.JPEG,
        ImageFormat.PNG,
        ImageFormat.WEBP,
        ImageFormat.GIF,
        ImageFormat.AVIF,
    ]
    if file_ext not in allowed_extensions:
        logger.error(
            f"不支持的文件扩展名: {file_ext}，支持的格式: {allowed_extensions}"
        )
        return APIResponse.error(
            message="Unsupported file type, only jpg, jpeg, png, webp, gif, avif formats are supported",
            data={
                "error_code": "UNSUPPORTED_FILE_TYPE",
                "supported_formats": allowed_extensions,
                "received_format": file_ext,
                "filename": file.filename,
            },
        )

    # Store original file data before compression
    original_file_data = file_data
    original_file_ext = file_ext
    original_content_type = f"image/{file_ext}"

    # Animated formats (GIF and AVIF) should not be compressed
    is_animated_format = file_ext in (ImageFormat.GIF, ImageFormat.AVIF)

    # Compress PNG and large files
    # Always compress PNG, and also compress if file is > 500KB.
    # We might adjust the threshold value of 500KB in the future.
    # The rationale is that on a smart phone, 500KB JPEG should be sufficient.
    # PNG is a lossless format, so we can compress it to JPEG to save space.
    # TODO: Explicitly add parameter compress_image in request body to control this.
    # Not always compress png files.
    was_compressed = False
    if not is_animated_format:
        compression_threshold_size_bytes = (
            global_config_loaded_from_config_yaml.app.limits.image_compression_threshold_size_kb
            * 1024
        )
        if (
            file_ext == ImageFormat.PNG
            or len(file_data) > compression_threshold_size_bytes
        ):
            file_data = compress_png_to_jpeg(file_data)
            file_ext = ImageFormat.JPEG
            was_compressed = True
            logger.debug(
                f"Compressed PNG ({file_size} bytes) to JPEG ({len(file_data)} bytes)"
            )

    # Get image size - for GIF, use first frame if animated
    img = Image.open(io.BytesIO(original_file_data))
    if (
        file_ext == ImageFormat.GIF
        and hasattr(img, "is_animated")
        and img.is_animated
    ):
        # For animated GIF, get size from first frame
        img.seek(0)
    size = ImageSize(width=img.width, height=img.height)
    logger.debug(f"图片大小: {size}")

    # Generate unique file paths
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    file_gcs_path = f"{base_path}/{user_id}/{timestamp}-{unique_id}.{file_ext}"
    content_type = f"image/{file_ext}"

    gcs_url = upload_to_gcs(
        file_data,
        content_type,
        global_config_loaded_from_config_yaml.gcs.bucket,
        file_gcs_path,
    )

    # Convert GCS URL to CDN URL
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

    # If image was compressed and it's not an avatar, also upload uncompressed version
    if was_compressed:
        # Generate path for uncompressed image
        uncompressed_file_gcs_path = f"{base_path}/{user_id}/{timestamp}-{unique_id}-original.{original_file_ext}"

        # Upload uncompressed file to GCS
        uncompressed_gcs_url = upload_to_gcs(
            original_file_data,
            original_content_type,
            global_config_loaded_from_config_yaml.gcs.bucket,
            uncompressed_file_gcs_path,
        )

        # Convert uncompressed GCS URL to CDN URL
        try:
            uncompressed_url = image_transform_service.transform_mobile(
                uncompressed_gcs_url
            )
            logger.debug(
                f"Uploaded original image, CDN URL: {uncompressed_url}"
            )
        except Exception as transform_error:
            logger.warning(
                f"Failed to transform original URL to CDN: {uncompressed_gcs_url}, error: {str(transform_error)}"
            )
            uncompressed_url = (
                uncompressed_gcs_url  # Fallback to original GCS URL
            )

        result.original_url = uncompressed_url

        # Only store CDN URL, save GCS URL in metadata
        await async_create_image_resource(
            async_db=async_db,
            user_id=user_id,
            url=uncompressed_url,
            size=size,
            format=ImageFormat(original_file_ext),
            byte_size=len(original_file_data),
            gcs_url=uncompressed_gcs_url,  # Store GCS URL in metadata
        )

    # Create resource record for the compressed image
    # Only store CDN URL, save GCS URL in metadata
    await async_create_image_resource(
        async_db=async_db,
        user_id=user_id,
        url=url,
        size=size,
        format=ImageFormat(file_ext),
        byte_size=len(file_data),
        gcs_url=gcs_url,  # Store GCS URL in metadata
    )

    # Handle cropping if enabled
    if cropping_avatar:
        crop_avatar_result = crop_avatar(file_data)
        cropped_avatar = crop_avatar_result.image
        result.avatar_size = crop_avatar_result.size

        # Convert PIL Image to bytes for GCS upload
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

        # Convert cropped avatar GCS URL to CDN URL
        try:
            cropped_avatar_url = image_transform_service.transform_mobile(
                cropped_avatar_gcs_url
            )
            logger.debug(
                f"扣脸图片上传 GCS 成功, CDN URL: {cropped_avatar_url}"
            )
        except Exception as transform_error:
            logger.warning(
                f"Failed to transform avatar URL to CDN: {cropped_avatar_gcs_url}, error: {str(transform_error)}"
            )
            cropped_avatar_url = (
                cropped_avatar_gcs_url  # Fallback to original GCS URL
            )

        result.avatar_url = cropped_avatar_url

        # Write the metadata of the uploaded image, which might be compressed.
        # Only store CDN URL, save GCS URL in metadata
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
