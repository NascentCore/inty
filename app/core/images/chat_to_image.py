"""
聚合多个提供商的图片生成 API，提供一个统一的接口给聊天生图。
"""

from app.core.google_genai.wrapped_client import WrappedClient
from app.core.images.fal import z_image_turbo_image_to_image


WrappedClient(client=get_genai_client())
