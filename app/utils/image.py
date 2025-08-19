from PIL import Image
import io
from loguru import logger


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

    logger.info(f"Compressed PNG to JPEG: {len(image_data)} -> {len(jpeg_data)} bytes")
    return jpeg_data
