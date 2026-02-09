import io
from enum import StrEnum

from loguru import logger
from PIL import Image
from pydantic import BaseModel


class ImageSize(BaseModel):
    """Image size"""

    width: int
    height: int


class ImageFormat(StrEnum):
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    GIF = "gif"
    AVIF = "avif"


class AspectRatio(StrEnum):
    PORTRAIT = "9:16"


def compress_png_to_jpeg(image_data: bytes, quality: int = 80) -> bytes:
    image = Image.open(io.BytesIO(image_data))

    if image.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "P":
            image = image.convert("RGBA")
        background.paste(
            image, mask=image.split()[-1] if image.mode == "RGBA" else None
        )
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")

    output_buffer = io.BytesIO()
    image.save(output_buffer, format="JPEG", quality=quality, optimize=True)
    jpeg_data = output_buffer.getvalue()

    logger.debug(f"Compressed PNG to JPEG: {len(image_data)} -> {len(jpeg_data)} bytes")
    return jpeg_data


def get_jpg_bytes_from_pil_image(pil_image: Image.Image, quality: int = 80) -> bytes:
    """Get JPEG bytes from PIL image"""
    output_buffer = io.BytesIO()
    pil_image.save(output_buffer, format="JPEG", quality=quality, optimize=True)
    return output_buffer.getvalue()


def check_aspect_ratio_9_16(image_or_size) -> bool:
    """
    检查图片是否为 9:16 比例

    Args:
        image_or_size: PIL Image 对象或 (width, height) 元组

    Returns:
        bool: True 表示是 9:16 比例（允许 0.01 的误差）
    """
    if isinstance(image_or_size, Image.Image):
        width, height = image_or_size.size
    elif isinstance(image_or_size, tuple) and len(image_or_size) == 2:
        width, height = image_or_size
    else:
        raise ValueError(
            "Parameter must be a PIL Image object or a (width, height) tuple"
        )

    target_aspect_ratio = 9 / 16  # 0.5625
    current_aspect_ratio = width / height

    return abs(current_aspect_ratio - target_aspect_ratio) < 0.01


def crop_image_to_9_16(image: Image.Image) -> Image.Image:
    """
    将图片裁剪到 9:16 比例（居中裁剪）

    Args:
        image: PIL Image 对象

    Returns:
        裁剪后的 PIL Image 对象
    """
    width, height = image.size
    target_aspect_ratio = 9 / 16  # 0.5625
    current_aspect_ratio = width / height

    # 如果已经是 9:16 比例（允许小误差），直接返回
    if abs(current_aspect_ratio - target_aspect_ratio) < 0.01:
        logger.debug(f"图片已经是 9:16 比例 ({width}x{height})，无需裁剪")
        return image

    # 计算裁剪尺寸
    if current_aspect_ratio > target_aspect_ratio:
        # 图片更宽，需要裁剪左右
        # 保持高度不变，裁剪宽度
        new_width = int(height * target_aspect_ratio)
        left = (width - new_width) // 2
        top = 0
        right = left + new_width
        bottom = height
    else:
        # 图片更高，需要裁剪上下
        # 保持宽度不变，裁剪高度
        new_height = int(width / target_aspect_ratio)
        left = 0
        top = (height - new_height) // 2
        right = width
        bottom = top + new_height

    logger.debug(
        f"裁剪图片: {width}x{height} -> {right-left}x{bottom-top} "
        f"(裁剪区域: left={left}, top={top}, right={right}, bottom={bottom})"
    )

    cropped_image = image.crop((left, top, right, bottom))
    return cropped_image
