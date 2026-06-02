"""
Route playground requests to Inty provider wrappers.

CREATED_BY_AGENT
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.llm.chat_completions import create_chat_completion_sync
from app.core.images.types import GeneratedImageProcessResult
from app.external_services.text_to_image import (
    TextToImageGeneratedImage,
    TextToImageGenerationRequest,
    generate_text_to_image,
)
from app.utils.models_catalog import (
    ModelNameFamily,
    detect_model_name_family,
    resolve_chat_text_model,
)
from app.utils.openai_client import (
    OpenAICompatibleClientOptions,
    get_openai_compatible_sync_client,
)
from tools.ai_local_playground.catalog import FAL_GPT_IMAGE_1_5_EDIT_ID, GEMINI_IMAGE_IDS
from tools.ai_local_playground.gemini_image import (
    GeminiPlaygroundImageInput,
    generate_gemini_playground_image,
    playground_gcs_uri_base,
)


class PlaygroundImageBackend(StrEnum):
    GEMINI = "gemini"
    FAL = "fal"


@dataclass(frozen=True)
class PlaygroundTextInput:
    model_id: str
    user_message: str
    system_message: str


@dataclass(frozen=True)
class PlaygroundImageInput:
    model_id: str
    prompt: str
    reference_image_urls: tuple[str, ...]
    system_instruction: str
    num_images: int
    input_fidelity: str


def resolve_image_backend(model_id: str) -> PlaygroundImageBackend:
    if model_id in GEMINI_IMAGE_IDS:
        return PlaygroundImageBackend.GEMINI
    family = detect_model_name_family(model_id)
    match family:
        case ModelNameFamily.FAL:
            return PlaygroundImageBackend.FAL
        case ModelNameFamily.GEMINI:
            return PlaygroundImageBackend.GEMINI
        case _:
            raise ValueError(
                f"Image model {model_id!r} is not gemini or fal; "
                f"try a catalog id such as {FAL_GPT_IMAGE_1_5_EDIT_ID}"
            )


def run_playground_text(inp: PlaygroundTextInput) -> dict[str, Any]:
    assert inp.model_id
    assert inp.user_message

    llm_config = CompanionLLMConfig.from_openrouter_env()
    if not llm_config.api_key:
        raise ValueError(
            "Set OPENROUTER_API_KEY or OPENAI_API_KEY for text models."
        )

    resolved = resolve_chat_text_model(inp.model_id)
    messages: list[dict[str, str]] = []
    if inp.system_message:
        messages.append({"role": "system", "content": inp.system_message})
    messages.append({"role": "user", "content": inp.user_message})

    client = get_openai_compatible_sync_client(
        OpenAICompatibleClientOptions(
            api_key=llm_config.api_key,
            base_url=llm_config.api_base,
            wrap_langsmith=False,
            chat_name="ai_local_playground_text",
        )
    )
    started = time.perf_counter()
    response = create_chat_completion_sync(
        client,
        model=resolved.id_on_provider,
        messages_payload=messages,
        tools=[],
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    choice = response.choices[0]
    content = choice.message.content or ""
    usage = getattr(response, "usage", None)
    usage_payload: dict[str, Any] | None = None
    if usage is not None:
        usage_payload = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }

    return {
        "model": resolved.id_on_provider,
        "nickname": resolved.nickname,
        "content": content,
        "usage": usage_payload,
        "elapsed_ms": round(elapsed_ms, 1),
    }


async def run_playground_image(inp: PlaygroundImageInput) -> dict[str, Any]:
    assert inp.model_id
    assert inp.prompt
    assert inp.num_images >= 1

    backend = resolve_image_backend(inp.model_id)
    started = time.perf_counter()
    gcs_base = playground_gcs_uri_base()

    match backend:
        case PlaygroundImageBackend.GEMINI:
            gemini_inp = GeminiPlaygroundImageInput(
                model_id=inp.model_id,
                prompt=inp.prompt,
                reference_image_urls=inp.reference_image_urls,
                system_instruction=inp.system_instruction,
                gcs_uri_base=gcs_base,
                count=inp.num_images,
            )
            results = await generate_gemini_playground_image(gemini_inp)
            images = [_serialize_gemini_result(r) for r in results]
        case PlaygroundImageBackend.FAL:
            images = _run_fal_image(inp=inp)
        case _:
            raise ValueError(f"Unsupported image backend: {backend}")

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "model": inp.model_id,
        "backend": backend.value,
        "images": images,
        "elapsed_ms": round(elapsed_ms, 1),
    }


def _run_fal_image(*, inp: PlaygroundImageInput) -> list[dict[str, Any]]:
    provider_args: dict[str, Any] = {}
    if inp.reference_image_urls:
        provider_args["image_urls"] = list(inp.reference_image_urls)
    if inp.model_id == FAL_GPT_IMAGE_1_5_EDIT_ID and inp.input_fidelity:
        provider_args["input_fidelity"] = inp.input_fidelity

    request = TextToImageGenerationRequest(
        model=inp.model_id,
        prompt=inp.prompt,
        num_images=inp.num_images,
        provider_args=provider_args,
    )
    result = generate_text_to_image(request)
    return [_serialize_fal_image(img) for img in result.images]


def _serialize_gemini_result(item: GeneratedImageProcessResult) -> dict[str, Any]:
    fmt = item.format.value if hasattr(item.format, "value") else str(item.format)
    payload: dict[str, Any] = {
        "gcs_uri": item.gcs_uri,
        "url": item.gcs_http_url,
        "width": item.size.width,
        "height": item.size.height,
        "format": fmt,
    }
    raw = item.raw_data
    if isinstance(raw, bytes) and raw:
        payload["data_url"] = (
            f"data:image/{fmt};base64,"
            f"{base64.standard_b64encode(raw).decode('ascii')}"
        )
    return payload


def _serialize_fal_image(item: TextToImageGeneratedImage) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "url": item.url or item.public_url,
        "width": item.width,
        "height": item.height,
        "mime_type": item.mime_type,
        "format": item.format,
    }
    if item.image_bytes:
        mime = item.mime_type or "image/png"
        payload["data_url"] = (
            f"data:{mime};base64,"
            f"{base64.standard_b64encode(item.image_bytes).decode('ascii')}"
        )
    return payload
