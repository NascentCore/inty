"""
Predefined generation content configurations for Gemini APIs.
"""

from google.genai import types

from app.core.agent.prompts import R_RATED_ROMANCE_DIRECTOR_SYSTEM_INSTRUCTION_PROMPT
from app.core.google_genai.utils import get_text_part

IMAGE_CONFIG_9_16_1K = types.ImageConfig(
    aspect_ratio="9:16",
    image_size="1K",
    # NOTE: 下面两个参数在 Gemini APIs 中不支持。
    # 保留用于支持 ImageGen 系列模型。
    output_mime_type="image/jpeg",
    output_compression_quality=70,
)

TEXT_PART_SYSTEM_INSTRUCTION = get_text_part(
    R_RATED_ROMANCE_DIRECTOR_SYSTEM_INSTRUCTION_PROMPT
)


GEN_CONTENT_CONFIG_IMAGE_9_16_1K_R_RATED_ROMANCE_DIRECTOR = types.GenerateContentConfig(
    temperature=1.0,
    top_p=0.95,
    max_output_tokens=8192,
    response_modalities=["IMAGE"],
    system_instruction=[TEXT_PART_SYSTEM_INSTRUCTION],
    image_config=IMAGE_CONFIG_9_16_1K,
)
