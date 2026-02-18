"""
Predefined generation content configurations for Gemini APIs.
"""
from google.genai import types


DEFAULT_9_16_1K_IMAGE_CONFIG = types.ImageConfig(
    aspect_ratio="9:16",
    image_size="1K",
    # NOTE: 下面两个参数在 Gemini APIs 中不支持。
    # 保留用于支持 ImageGen 系列模型。
    output_mime_type="image/jpeg",
    output_compression_quality=70,
)
