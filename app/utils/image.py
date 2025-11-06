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
