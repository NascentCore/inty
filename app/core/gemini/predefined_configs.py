"""
Predefined generation content configurations for Gemini APIs.
"""
from google.genai import types


DEFAULT_9_16_1K_IMAGE_CONFIG = types.ImageConfig(
    aspect_ratio="9:16",
    image_size="1K",
    # NOTE: output_mime_type is not supported on Gemini APIs.
    # output_mime_type="image/jpeg",
)
