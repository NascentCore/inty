"""
Predefined generation content configurations for Gemini APIs.
"""

from typing import Final

from google.genai import types

ASPECT_RATIO_9_16 = "9:16"


IMAGE_CONFIG_9_16_1K = types.ImageConfig(
    aspect_ratio=ASPECT_RATIO_9_16,
    image_size="1K",
    # NOTE: 下面两个参数在 Gemini generate_content 的 ImageConfig 中可能不被支持，
    # 保留用于与 ImageGen 系列模型一致。Imagen generate_images 使用
    # GenerateImagesConfig，其 output_compression_quality (0-100) 对 JPEG 有效。
    output_mime_type="image/jpeg",
    output_compression_quality=70,
)


GEN_CONTENT_CONFIG_IMAGE_9_16_1K: Final[types.GenerateContentConfig] = (
    types.GenerateContentConfig(
        temperature=1.0,
        top_p=0.95,
        max_output_tokens=8192,
        response_modalities=["IMAGE"],
        image_config=IMAGE_CONFIG_9_16_1K,
    )
)

# NewAPI / Gemini Developer API 不接受 Vertex ImageConfig 里的 output_mime_type 等字段
GEN_CONTENT_CONFIG_IMAGE_9_16_1K_MLDEV: Final[types.GenerateContentConfig] = types.GenerateContentConfig(
    temperature=1.0,
    top_p=0.95,
    max_output_tokens=8192,
    response_modalities=["IMAGE"],
    image_config=types.ImageConfig(aspect_ratio=ASPECT_RATIO_9_16, image_size="1K"),
)
