"""
Unified text-to-image API wrapper for multiple providers.

Supported providers:
- Google Vertex AI Imagen via `google.genai` (model name uses `google/` prefix)
- fal.ai model APIs via `fal_client`

This module is intentionally NOT integrated into Inty backend flows yet.

CREATED_BY_AGENT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from types import SimpleNamespace
from typing import Any, Optional

from app.external_services.fal_ai import FalAIClient


GOOGLE_MODEL_PREFIX = "google/"
DEFAULT_GOOGLE_MIME_TYPE = "image/jpeg"
DEFAULT_FAL_IMAGE_SIZE = "landscape_4_3"
DEFAULT_FAL_OUTPUT_FORMAT = "png"

logger = logging.getLogger(__name__)


class TextToImageProvider(StrEnum):
    GOOGLE = "google"
    FALAI = "falai"


@dataclass(frozen=True, slots=True)
class TextToImageGeneratedImage:
    provider: TextToImageProvider
    model: str
    prompt: str

    # One of the below may be set depending on provider & config.
    gcs_uri: str | None = None
    public_url: str | None = None
    url: str | None = None
    image_bytes: bytes | None = None
    mime_type: str | None = None

    width: int | None = None
    height: int | None = None

    # Google Imagen specific
    rai_filtered_reason: str | None = None
    enhanced_prompt: str | None = None


@dataclass(frozen=True, slots=True)
class TextToImageGenerationResult:
    provider: TextToImageProvider
    model: str
    images: list[TextToImageGeneratedImage]
    raw: Any


@dataclass(slots=True)
class TextToImageGenerationRequest:
    """
    A provider-agnostic request.

    Provider routing is based on `model`:
    - `google/<imagen-model-name>` routes to Google Imagen.
    - Otherwise routes to fal.ai.

    Use `provider_args` for provider-specific parameters.
    """

    model: str
    prompt: str
    num_images: int = 1
    negative_prompt: str | None = None
    seed: int | None = None
    provider_args: dict[str, Any] = field(default_factory=dict)


def generate_text_to_image(request: TextToImageGenerationRequest) -> TextToImageGenerationResult:
    provider, provider_model = _resolve_provider_and_model(request.model)
    if provider == TextToImageProvider.GOOGLE:
        return _generate_google_imagen(provider_model=provider_model, request=request)
    return _generate_fal_text_to_image(provider_model=provider_model, request=request)


def _resolve_provider_and_model(model: str) -> tuple[TextToImageProvider, str]:
    if model.startswith(GOOGLE_MODEL_PREFIX):
        stripped = model[len(GOOGLE_MODEL_PREFIX) :].strip()
        if not stripped:
            raise ValueError("google/ prefix provided but model name is empty")
        return TextToImageProvider.GOOGLE, stripped

    # Backward-compatible heuristic for Imagen model names without prefix.
    if model.startswith("imagen-"):
        logger.warning(
            "Text-to-image model name '%s' is missing the 'google/' prefix; "
            "treating it as a Google Imagen model for compatibility.",
            model,
        )
        return TextToImageProvider.GOOGLE, model

    return TextToImageProvider.FALAI, model


def _generate_google_imagen(
    *,
    provider_model: str,
    request: TextToImageGenerationRequest,
) -> TextToImageGenerationResult:
    client = request.provider_args.get("client") or _get_google_genai_client()

    aspect_ratio = request.provider_args.get("aspect_ratio")
    output_gcs_uri = request.provider_args.get("output_gcs_uri")
    output_mime_type = request.provider_args.get("output_mime_type") or DEFAULT_GOOGLE_MIME_TYPE
    enhance_prompt = bool(request.provider_args.get("enhance_prompt", False))

    config = _build_google_generate_images_config(
        num_images=int(request.num_images),
        negative_prompt=request.negative_prompt,
        aspect_ratio=aspect_ratio,
        output_gcs_uri=output_gcs_uri,
        output_mime_type=output_mime_type,
        enhance_prompt=enhance_prompt,
        safety_filter_level=request.provider_args.get("safety_filter_level"),
        person_generation=request.provider_args.get("person_generation"),
    )

    response = client.models.generate_images(
        model=provider_model,
        prompt=request.prompt,
        config=config,
    )

    images: list[TextToImageGeneratedImage] = []
    for generated in getattr(response, "generated_images", []) or []:
        image_obj = getattr(generated, "image", None)
        gcs_uri = getattr(image_obj, "gcs_uri", None) if image_obj else None
        image_bytes = getattr(image_obj, "image_bytes", None) if image_obj else None

        public_url = _gcs_uri_to_public_url(gcs_uri) if isinstance(gcs_uri, str) else None
        images.append(
            TextToImageGeneratedImage(
                provider=TextToImageProvider.GOOGLE,
                model=f"{GOOGLE_MODEL_PREFIX}{provider_model}",
                prompt=request.prompt,
                gcs_uri=gcs_uri,
                public_url=public_url,
                image_bytes=image_bytes if isinstance(image_bytes, (bytes, bytearray)) else None,
                mime_type=output_mime_type if isinstance(output_mime_type, str) else None,
                rai_filtered_reason=getattr(generated, "rai_filtered_reason", None),
                enhanced_prompt=getattr(generated, "enhanced_prompt", None),
            )
        )

    return TextToImageGenerationResult(
        provider=TextToImageProvider.GOOGLE,
        model=f"{GOOGLE_MODEL_PREFIX}{provider_model}",
        images=images,
        raw=response,
    )


def _generate_fal_text_to_image(
    *,
    provider_model: str,
    request: TextToImageGenerationRequest,
) -> TextToImageGenerationResult:
    api_key = request.provider_args.get("api_key")
    client = FalAIClient(api_key=api_key if isinstance(api_key, str) else None)

    arguments: dict[str, Any] = dict(request.provider_args.get("arguments") or {})
    arguments.setdefault("prompt", request.prompt)
    arguments.setdefault("num_images", int(request.num_images))
    arguments.setdefault("image_size", request.provider_args.get("image_size") or DEFAULT_FAL_IMAGE_SIZE)
    arguments.setdefault(
        "output_format", request.provider_args.get("output_format") or DEFAULT_FAL_OUTPUT_FORMAT
    )

    if request.negative_prompt:
        arguments.setdefault("negative_prompt", request.negative_prompt)
    if request.seed is not None:
        arguments.setdefault("seed", int(request.seed))

    result = client.text_to_image(model=provider_model, arguments=arguments, with_logs=False)

    images: list[TextToImageGeneratedImage] = []
    for img in result.images:
        images.append(
            TextToImageGeneratedImage(
                provider=TextToImageProvider.FALAI,
                model=provider_model,
                prompt=request.prompt,
                url=img.url,
                width=img.width if isinstance(img.width, int) else None,
                height=img.height if isinstance(img.height, int) else None,
                mime_type=img.content_type,
            )
        )

    return TextToImageGenerationResult(
        provider=TextToImageProvider.FALAI,
        model=provider_model,
        images=images,
        raw=result.raw,
    )


def _gcs_uri_to_public_url(gcs_uri: Optional[str]) -> Optional[str]:
    if not gcs_uri:
        return None
    if gcs_uri.startswith("gs://"):
        return f"https://storage.googleapis.com/{gcs_uri[5:]}"
    return gcs_uri


def _get_google_genai_client():
    # Lazy import to avoid importing Inty config on module import.
    from app.utils.gemini import get_genai_client

    return get_genai_client()


def _build_google_generate_images_config(
    *,
    num_images: int,
    negative_prompt: Optional[str],
    aspect_ratio: Any,
    output_gcs_uri: Any,
    output_mime_type: Any,
    enhance_prompt: bool,
    safety_filter_level: Any,
    person_generation: Any,
):
    """
    Build `google.genai.types.GenerateImagesConfig` if available, otherwise fall back
    to a lightweight attribute container (useful for unit tests).
    """

    try:
        from google.genai import types as genai_types  # type: ignore
    except Exception:  # pragma: no cover - only used when dependency is absent
        genai_types = None

    if genai_types is None:
        return SimpleNamespace(
            number_of_images=num_images,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            output_gcs_uri=output_gcs_uri,
            include_rai_reason=True,
            output_mime_type=output_mime_type,
            enhance_prompt=enhance_prompt,
            safety_filter_level=safety_filter_level,
            person_generation=person_generation,
        )

    resolved_safety_filter_level = safety_filter_level or genai_types.SafetyFilterLevel.BLOCK_LOW_AND_ABOVE
    resolved_person_generation = person_generation or genai_types.PersonGeneration.ALLOW_ADULT

    return genai_types.GenerateImagesConfig(
        number_of_images=num_images,
        negative_prompt=negative_prompt,
        aspect_ratio=aspect_ratio,
        output_gcs_uri=output_gcs_uri,
        include_rai_reason=True,
        output_mime_type=output_mime_type,
        enhance_prompt=enhance_prompt,
        safety_filter_level=resolved_safety_filter_level,
        person_generation=resolved_person_generation,
    )


__all__ = [
    "GOOGLE_MODEL_PREFIX",
    "TextToImageGeneratedImage",
    "TextToImageGenerationRequest",
    "TextToImageGenerationResult",
    "TextToImageProvider",
    "generate_text_to_image",
]

