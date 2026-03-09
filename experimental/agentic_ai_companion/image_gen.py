# 根据聊天上下文调用 Gemini API Imagen 生成图片，不依赖 app 内接口。
# 参考: https://ai.google.dev/gemini-api/docs/imagen

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from langsmith.run_helpers import traceable

if TYPE_CHECKING:
    from google.genai import Client

IMAGEN_4_FAST_MODEL = "imagen-4.0-fast-generate-001"
RECENT_MESSAGES_LIMIT = 10


from loguru import logger


def _prompt_from_messages(messages: list[dict[str, Any]]) -> str:
    """
    策略 A：使用最后一条 role="user" 的 content 作为 Imagen 的 prompt。
    Imagen 仅接受单条文本且约 480 token 上限；若无 user 消息则退回默认描述。
    """
    logger.debug(f"Generating image from messages: {messages}")
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if msg.get("role") == "user":
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()[:2000]
            break
    return "A scene inspired by the conversation."


def _trace_output_image(data: bytes | None) -> dict:
    """process_outputs：避免将原始图片字节写入 trace，仅记录摘要。异常时 data 可能为 None。"""
    if data is None:
        return {"status": "error", "image_bytes": 0}
    return {"image_bytes": len(data), "status": "success"}


# [tracing] LangSmith 中对应 role_play_minimal 的「generate_image」工具调用；输出摘要由 process_outputs 记录
@traceable(
    name="generate_image",
    run_type="tool",
    process_outputs=_trace_output_image,
)
def generate_image_from_messages(
    client: "Client",
    prompt: str,
    model: str = IMAGEN_4_FAST_MODEL,
) -> bytes:
    """
    使用 prompt 调用 Gemini API Imagen 生成一张图并返回图片字节。
    client 由调用方传入（通常为 LangSmith wrapped 的 genai.Client）。
    """
    from google.genai import types

    prompt = (prompt or "").strip() or "A scene inspired by the conversation."
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
