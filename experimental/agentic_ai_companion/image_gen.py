# 根据聊天上下文调用 Gemini API Imagen 生成图片，不依赖 app 内接口。
# 参考: https://ai.google.dev/gemini-api/docs/imagen

from __future__ import annotations

import os
from typing import Any

IMAGEN_4_FAST_MODEL = "imagen-4.0-fast-generate-001"
RECENT_MESSAGES_LIMIT = 10


def _prompt_from_messages(messages: list[dict[str, Any]]) -> str:
    """
    策略 A：使用最后一条 role="user" 的 content 作为 Imagen 的 prompt。
    Imagen 仅接受单条文本且约 480 token 上限；若无 user 消息则退回默认描述。
    """
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if msg.get("role") == "user":
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()[:2000]
            break
    return "A scene inspired by the conversation."


def generate_image_from_messages(
    messages: list[dict[str, Any]],
    model: str = IMAGEN_4_FAST_MODEL,
) -> bytes:
    """
    根据当前 session 的若干条消息推导出 Imagen prompt，调用 Gemini API Imagen 生成一张图并返回图片字节。
    使用 GEMINI_API_KEY（.env），不依赖 GCP/Vertex/GCS。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError("GEMINI_API_KEY 未设置，请在 .env 中配置")

    from google import genai
    from google.genai import types

    prompt = _prompt_from_messages(messages)
    client = genai.Client(api_key=api_key)
    config = types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="1:1",
    )
    response = client.models.generate_images(
        model=model,
        prompt=prompt,
        config=config,
    )
    generated = getattr(response, "generated_images", None) or []
    if not generated:
        raise ValueError("Imagen 未返回任何图片")
    first = generated[0]
    image_obj = getattr(first, "image", None)
    if not image_obj:
        raise ValueError("Imagen 返回结果中无 image 字段")
    image_bytes = getattr(image_obj, "image_bytes", None)
    if isinstance(image_bytes, bytes) and len(image_bytes) > 0:
        return image_bytes
    raise ValueError("Imagen 返回的图片数据为空或格式不可用")
