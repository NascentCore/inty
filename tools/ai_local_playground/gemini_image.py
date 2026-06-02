"""
Gemini / Nano Banana image generation for the local playground.

CREATED_BY_AGENT
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass

from google.genai import types as gemini_types

from app.core.google_genai.predefined_configs import GEN_CONTENT_CONFIG_IMAGE_9_16_1K
from app.core.google_genai.utils import get_jpeg_url_and_text_mixed_parts, get_text_parts
from app.core.google_genai.wrapped_client import (
    _process_image_part_to_generated_image,
    _process_one_candidate,
    _validate_gemini_image_response,
    get_wrapped_client,
)
from app.core.images.types import GeneratedImageProcessResult
from app.utils.gemini import get_genai_client, get_newapi_gemini_client
from app.utils.langsmith import attach_provider_response_to_langsmith_run
from app.utils.models_catalog import (
    NANO_BANANA,
    NANO_BANANA_2,
    NANO_BANANA_PRO,
    NEWAPI_NANO_BANANA_2,
)
from tools.ai_local_playground.catalog import WRAPPED_GEMINI_IMAGE_IDS


@dataclass(frozen=True)
class GeminiPlaygroundImageInput:
    model_id: str
    prompt: str
    reference_image_urls: tuple[str, ...]
    system_instruction: str
    gcs_uri_base: str
    count: int


async def generate_gemini_playground_image(
    inp: GeminiPlaygroundImageInput,
) -> list[GeneratedImageProcessResult]:
    assert inp.model_id
    assert inp.prompt
    assert inp.gcs_uri_base
    assert inp.count >= 1

    contents: list[str] = list(inp.reference_image_urls)
    contents.append(inp.prompt)
    system_instructions: list[str] | None = None
    if inp.system_instruction:
        system_instructions = [inp.system_instruction]

    if inp.model_id in WRAPPED_GEMINI_IMAGE_IDS:
        client = get_wrapped_client()
        return await client.async_generate_images(
            model=inp.model_id,  # type: ignore[arg-type]
            contents=contents,
            gcs_uri_base=inp.gcs_uri_base,
            system_instructions=system_instructions,
            count=inp.count,
        )

    if inp.model_id == NANO_BANANA_2.id_on_provider:
        return await _generate_nano_banana_2(
            contents=contents,
            gcs_uri_base=inp.gcs_uri_base,
            system_instructions=system_instructions,
            count=inp.count,
        )

    allowed = sorted(WRAPPED_GEMINI_IMAGE_IDS | {NANO_BANANA_2.id_on_provider})
    raise ValueError(
        f"Gemini playground model {inp.model_id!r} not supported; allowed: {allowed}"
    )


async def _generate_nano_banana_2(
    *,
    contents: list[str],
    gcs_uri_base: str,
    system_instructions: list[str] | None,
    count: int,
) -> list[GeneratedImageProcessResult]:
    """Nano Banana 2 uses generate_content; WrappedClient literal omits this id."""
    gen_client = get_genai_client()
    config = copy.copy(GEN_CONTENT_CONFIG_IMAGE_9_16_1K)
    config.candidate_count = count
    if system_instructions is not None:
        config.system_instruction = get_text_parts(system_instructions)

    contents_parts = get_jpeg_url_and_text_mixed_parts(contents)
    response = await gen_client.aio.models.generate_content(
        model=NANO_BANANA_2.id_on_provider,
        contents=[
            gemini_types.Content(role="user", parts=contents_parts),
        ],
        config=config,
    )
    attach_provider_response_to_langsmith_run(response)
    _validate_gemini_image_response(response)
    results: list[GeneratedImageProcessResult] = []
    for candidate in response.candidates:
        part = _process_one_candidate(candidate)
        result = _process_image_part_to_generated_image(part, gcs_uri_base)
        results.append(result)
    return results


def playground_gcs_uri_base() -> str:
    return f"model-playground/{uuid.uuid4().hex}"
