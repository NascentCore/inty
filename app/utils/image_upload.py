"""
Image upload utility functions for processing and uploading images to GCS.
"""

import io
import uuid
from datetime import datetime
from typing import Optional

from fastapi import UploadFile
from loguru import logger
from pydantic import BaseModel

from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.response import APIResponse
from app.utils.crop_avatar import CROPPED_AVATAR_FILENAME_SUFFIX, crop_avatar
from app.utils.gcs import append_filename_suffix, upload_to_gcs
from app.utils.image import (
    compress_png_to_jpeg,
    ImageFormat,
    get_jpg_bytes_from_pil_image,
)


class ImageUploadResponse(BaseModel):
    """Image upload response"""
    # Uploaded compressed image
    url: str
    # Uploaded original image
    original_url: Optional[str] = None
    # Uploaded avatar image
    avatar_url: Optional[str] = None


async def process_image_upload(
    file: UploadFile,
    user_id: str,
    base_path: str = "uploads/images",
    cropping_avatar: bool = False,
    max_size_mb: int = global_config_loaded_from_config_yaml.app.limits.max_image_size_mb,
) -> APIResponse[ImageUploadResponse]:
    """
    Helper function to process image upload with validation, compression, and GCS upload.

    Args:
        file: The uploaded file
        user_id: User ID for creating unique file paths
        base_path: Base path for file storage (e.g., "avatars/tmp", "uploads/images")
        cropping_avatar: Whether to enable avatar cropping (requires crop_avatar utility)
        max_size_mb: Maximum file size in MB (overrides config if provided)

    Returns:
        APIResponse with success/error status and data
    """
    # Validate file content type
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
            }
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
            }
        )

    # Store original file data before compression
    original_file_data = file_data
    original_file_ext = file_ext
    original_content_type = file.content_type

    # Compress PNG and large files
    # Always compress PNG, and also compress if file is > 500KB.
    # We might adjust the threshold value of 500KB in the future.
    # The rationale is that on a smart phone, 500KB JPEG should be sufficient.
    # PNG is a lossless format, so we can compress it to JPEG to save space.
    # TODO: Explicitly add parameter compress_image in request body to control this.
    # Not always compress png files.
    compression_threshold_size_bytes = global_config_loaded_from_config_yaml.app.limits.image_compression_threshold_size_kb * 1024
    was_compressed = False
    if file_ext == ImageFormat.PNG or len(file_data) > compression_threshold_size_bytes:
        file_data = compress_png_to_jpeg(file_data)
        file_ext = ImageFormat.JPEG
        was_compressed = True
        logger.debug(
            f"Compressed PNG ({file_size} bytes) to JPEG ({len(file_data)} bytes)"
        )

    # Generate unique file paths
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    file_gcs_path = f"{base_path}/{user_id}/{timestamp}-{unique_id}.{file_ext}"

    url = upload_to_gcs(
        file_data,
        file.content_type,
        global_config_loaded_from_config_yaml.gcs.bucket,
        file_gcs_path,
    )
    result = ImageUploadResponse(url=url)
    logger.debug(f"图片 上传 GCS 成功，返回URL: {url}")

    # If image was compressed and it's not an avatar, also upload uncompressed version
    if was_compressed:
        # Generate path for uncompressed image
        uncompressed_file_gcs_path = f"{base_path}/{user_id}/{timestamp}-{unique_id}-original.{original_file_ext}"

        # Upload uncompressed file to GCS
        uncompressed_url = upload_to_gcs(
            original_file_data,
            original_content_type,
            global_config_loaded_from_config_yaml.gcs.bucket,
            uncompressed_file_gcs_path,
        )
        logger.debug(f"Uploaded original image: {uncompressed_url}")
        result.original_url = uncompressed_url

    # Handle cropping if enabled
    if cropping_avatar:
        cropped_avatar = crop_avatar(file_data)

        # Convert PIL Image to bytes for GCS upload
        jpg_data = get_jpg_bytes_from_pil_image(cropped_avatar)

        cropped_file_gcs_path = append_filename_suffix(
            file_gcs_path, CROPPED_AVATAR_FILENAME_SUFFIX
        )

        cropped_avatar_url = upload_to_gcs(
            jpg_data,
            f"image/{ImageFormat.JPEG}",  # Cropped image is always JPEG
            global_config_loaded_from_config_yaml.gcs.bucket,
            cropped_file_gcs_path,
        )
        logger.debug(f"扣脸图片上传 GCS 成功,返回URL: {cropped_avatar_url}")
        result.avatar_url = cropped_avatar_url

    return APIResponse.success(data=result)
