"""
Unified text-to-image API wrapper for multiple providers.

Supported providers:
- Google Vertex AI Imagen via `google.genai` (model name uses `google/` prefix)
- OpenAI image generation via OpenAI client (model name uses `openai/` prefix)
- fal.ai image generation via `fal_client` (model name uses `fal-ai/` prefix)

This module is intentionally NOT integrated into Inty backend flows yet.

CREATED_BY_AGENT
"""

from __future__ import annotations

import base64
import io
import os
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from enum import StrEnum
from types import SimpleNamespace
from typing import Any, Optional

import PIL.Image

from app.utils.models_catalog import (
    ModelNameFamily,
    detect_model_name_family,
    normalize_model_name,
)

GOOGLE_MODEL_PREFIX = "google/"
OPENAI_MODEL_PREFIX = "openai/"
FALAI_MODEL_PREFIX = "fal-ai/"
DEFAULT_GOOGLE_MIME_TYPE = "image/jpeg"
DEFAULT_GCS_BASE_DIR = "tmp/image_generation_wrapper"
FORMAT_JPEG = "jpeg"
FORMAT_PNG = "png"

from loguru import logger


class TextToImageProvider(StrEnum):
    GOOGLE = "google"
    OPENAI = "openai"
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
    format: str | None = None

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
    - `openai/<image-model-name>` routes to OpenAI image generation.

    Use `provider_args` for provider-specific parameters.
    """

    model: str
    prompt: str
    num_images: int = 1
    negative_prompt: str | None = None
    seed: int | None = None
    provider_args: dict[str, Any] = field(default_factory=dict)


def generate_text_to_image(
    request: TextToImageGenerationRequest,
) -> TextToImageGenerationResult:
    provider, provider_model = _resolve_provider_and_model(request.model)
    if provider == TextToImageProvider.GOOGLE:
        return _generate_google_imagen(
            provider_model=provider_model, request=request
        )
    if provider == TextToImageProvider.OPENAI:
        return _generate_openai_image(
            provider_model=provider_model, request=request
        )
    if provider == TextToImageProvider.FALAI:
        return _generate_falai_image(
            provider_model=provider_model, request=request
        )
    raise ValueError(f"Unsupported provider: {provider}")


def _resolve_provider_and_model(model: str) -> tuple[TextToImageProvider, str]:
    if not model:
        raise ValueError(
            f"Invalid model id: {model!r}. Expect '<org>/<model>' format or imagen-* model name."
        )

    normalized_model = normalize_model_name(model)
    model_family = detect_model_name_family(model)

    if normalized_model.startswith(GOOGLE_MODEL_PREFIX):
        stripped = normalized_model[len(GOOGLE_MODEL_PREFIX) :].strip()
        if not stripped:
            raise ValueError("google/ prefix provided but model name is empty")
        return TextToImageProvider.GOOGLE, stripped

    if normalized_model.startswith(OPENAI_MODEL_PREFIX):
        stripped = normalized_model[len(OPENAI_MODEL_PREFIX) :].strip()
        if not stripped:
            raise ValueError("openai/ prefix provided but model name is empty")
        # OpenAI / OpenRouter generally expects the org-prefixed model id.
        return TextToImageProvider.OPENAI, normalized_model

    if model_family == ModelNameFamily.FAL:
        stripped = normalized_model[len(FALAI_MODEL_PREFIX) :].strip()
        if not stripped:
            raise ValueError("fal-ai/ prefix provided but model name is empty")
        return TextToImageProvider.FALAI, f"{FALAI_MODEL_PREFIX}{stripped}"

    # Backward-compatible heuristic for Imagen model names without prefix.
    if normalized_model.startswith("imagen-"):
        logger.warning(
            "Text-to-image model name '%s' is missing the 'google/' prefix; "
            "treating it as a Google Imagen model for compatibility.",
            normalized_model,
        )
        return TextToImageProvider.GOOGLE, normalized_model

    # If model has org prefix, only google/openai/fal-ai are supported.
    if "/" in normalized_model:
        org = normalized_model.split("/", 1)[0].strip().lower()
        raise ValueError(
            f"Unsupported image model org prefix: {org!r} (model={model!r})"
        )

    # No org prefix and not imagen-*: require explicit provider prefix.
    raise ValueError(
        f"Unsupported image model: {model!r}. "
        "Model id must use google/, openai/, or fal-ai/ prefix "
        "(e.g. google/imagen-4.0-fast-generate-001)."
    )


def _generate_google_imagen(
    *,
    provider_model: str,
    request: TextToImageGenerationRequest,
) -> TextToImageGenerationResult:
    """
    Google Imagen via client.models.generate_images.

    GCS: When output_gcs_uri is set in config, the SDK uploads generated images
    to GCS; response contains gcs_uri per image. No app-side upload.
    GenerateImagesConfig also supports output_compression_quality (0-100) for JPEG
    if we need to control quality; not passed in _build_google_generate_images_config.
    """
    client = request.provider_args.get("client") or _get_google_genai_client()

    aspect_ratio = request.provider_args.get("aspect_ratio")
    output_gcs_uri = request.provider_args.get("output_gcs_uri")
    output_mime_type = (
        request.provider_args.get("output_mime_type")
        or DEFAULT_GOOGLE_MIME_TYPE
    )
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
        image_bytes = (
            getattr(image_obj, "image_bytes", None) if image_obj else None
        )

        public_url = (
            _gcs_uri_to_public_url(gcs_uri)
            if isinstance(gcs_uri, str)
            else None
        )
        images.append(
            TextToImageGeneratedImage(
                provider=TextToImageProvider.GOOGLE,
                model=f"{GOOGLE_MODEL_PREFIX}{provider_model}",
                prompt=request.prompt,
                gcs_uri=gcs_uri,
                public_url=public_url,
                image_bytes=(
                    image_bytes
                    if isinstance(image_bytes, (bytes, bytearray))
                    else None
                ),
                mime_type=(
                    output_mime_type
                    if isinstance(output_mime_type, str)
                    else None
                ),
                rai_filtered_reason=getattr(
                    generated, "rai_filtered_reason", None
                ),
                enhanced_prompt=getattr(generated, "enhanced_prompt", None),
            )
        )

    return TextToImageGenerationResult(
        provider=TextToImageProvider.GOOGLE,
        model=f"{GOOGLE_MODEL_PREFIX}{provider_model}",
        images=images,
        raw=response,
    )


def _generate_openai_image(
    *,
    provider_model: str,
    request: TextToImageGenerationRequest,
) -> TextToImageGenerationResult:
    openai_client = request.provider_args.get("openai_client")
    if openai_client is None:
        from app.core.llms.openai_client import get_base_openai_client

        client = get_base_openai_client()
    else:
        client = openai_client

    # OpenAI image generation does not have a single universal negative prompt field.
    # We append it to prompt for now; real integration can refine this mapping.
    full_prompt = _merge_negative_prompt(
        request.prompt, request.negative_prompt
    )

    output = request.provider_args.get("output", "bytes")
    gcs_uri_base = request.provider_args.get("gcs_uri_base")

    response = client.images.generate(
        model=provider_model,
        prompt=full_prompt,
        n=int(request.num_images),
        response_format="b64_json",
    )

    images: list[TextToImageGeneratedImage] = []
    for item in getattr(response, "data", []) or []:
        b64_json = getattr(item, "b64_json", None)
        if not b64_json:
            continue
        image_bytes = base64.b64decode(b64_json)
        size = _infer_image_size(image_bytes)

        gcs_uri: Optional[str] = None
        if output in ("gcs", "both"):
            gcs_uri = _upload_openai_image_to_gcs(
                image_bytes=image_bytes, gcs_uri_base=gcs_uri_base
            )

        images.append(
            TextToImageGeneratedImage(
                provider=TextToImageProvider.OPENAI,
                model=provider_model,
                prompt=request.prompt,
                format=FORMAT_PNG,
                image_bytes=(
                    image_bytes if output in ("bytes", "both") else None
                ),
                gcs_uri=gcs_uri,
                mime_type="image/png",
                width=size["width"] if size else None,
                height=size["height"] if size else None,
            )
        )

    return TextToImageGenerationResult(
        provider=TextToImageProvider.OPENAI,
        model=provider_model,
        images=images,
        raw=response,
    )


def _generate_falai_image(
    *,
    provider_model: str,
    request: TextToImageGenerationRequest,
) -> TextToImageGenerationResult:
    fal_image_client = request.provider_args.get("fal_client")
    if fal_image_client is None:
        import fal_client as fal_image_client  # type: ignore

    api_key = request.provider_args.get("api_key")
    if isinstance(api_key, str) and api_key:
        os.environ["FAL_KEY"] = api_key

    arguments = _build_falai_arguments(
        provider_model=provider_model, request=request
    )
    with_logs = bool(request.provider_args.get("with_logs", False))
    response = fal_image_client.subscribe(
        provider_model, arguments=arguments, with_logs=with_logs
    )
    if not isinstance(response, dict):
        raise TypeError(
            f"fal_client.subscribe returned non-dict: {type(response)}"
        )

    output_format = request.provider_args.get("output_format")
    normalized_format = (
        output_format if isinstance(output_format, str) else None
    )

    images: list[TextToImageGeneratedImage] = []
    for item in response.get("images", []) or []:
        if not isinstance(item, dict):
            continue

        url = item.get("url")
        if not isinstance(url, str) or not url:
            continue

        width = item.get("width")
        height = item.get("height")
        width_int = width if isinstance(width, int) else None
        height_int = height if isinstance(height, int) else None

        content_type = item.get("content_type")
        mime_type = (
            content_type
            if isinstance(content_type, str)
            else (
                item.get("mime_type")
                if isinstance(item.get("mime_type"), str)
                else None
            )
        )

        images.append(
            TextToImageGeneratedImage(
                provider=TextToImageProvider.FALAI,
                model=provider_model,
                prompt=request.prompt,
                url=url,
                mime_type=mime_type,
                format=normalized_format,
                width=width_int,
                height=height_int,
            )
        )

    return TextToImageGenerationResult(
        provider=TextToImageProvider.FALAI,
        model=provider_model,
        images=images,
        raw=response,
    )


def _build_falai_arguments(
    *,
    provider_model: str,
    request: TextToImageGenerationRequest,
) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "prompt": request.prompt,
        "num_images": int(request.num_images),
        # For /text-to-image endpoint we download image URL then upload to GCS.
        # sync_mode=False ensures fal returns HTTP URL instead of data URI.
        "sync_mode": bool(request.provider_args.get("sync_mode", False)),
    }

    if request.seed is not None:
        arguments["seed"] = int(request.seed)

    if request.negative_prompt and not _is_fal_z_image_turbo_model(
        provider_model
    ):
        arguments["negative_prompt"] = request.negative_prompt

    passthrough_keys = (
        "image_size",
        "output_format",
        "num_inference_steps",
        "enable_safety_checker",
        "enable_prompt_expansion",
        "acceleration",
        "strength",
        "image_url",
        "image_urls",
    )
    for key in passthrough_keys:
        value = request.provider_args.get(key)
        if value is not None:
            arguments[key] = value

    custom_arguments = request.provider_args.get("fal_arguments")
    if isinstance(custom_arguments, dict):
        arguments.update(custom_arguments)

    return arguments


def _is_fal_z_image_turbo_model(provider_model: str) -> bool:
    normalized = normalize_model_name(provider_model)
    return normalized.startswith("fal-ai/z-image/turbo")


def _gcs_uri_to_public_url(gcs_uri: Optional[str]) -> Optional[str]:
    if not gcs_uri:
        return None
    if gcs_uri.startswith("gs://"):
        from app.core.config import global_config_loaded_from_config_yaml

        rest = gcs_uri[5:]
        cfg = global_config_loaded_from_config_yaml.gcs
        if cfg.use_fake_gcs:
            return (Path(cfg.fake_gcs_base_dir) / rest).resolve().as_uri()
        return f"https://storage.googleapis.com/{rest}"
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

    Optional: GenerateImagesConfig supports output_compression_quality (int 0-100)
    for JPEG; not wired here yet.
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

    resolved_safety_filter_level = (
        safety_filter_level or genai_types.SafetyFilterLevel.BLOCK_LOW_AND_ABOVE
    )
    resolved_person_generation = (
        person_generation or genai_types.PersonGeneration.ALLOW_ADULT
    )

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


def _infer_image_size(image_bytes: bytes) -> Optional[dict[str, int]]:
    """Infer image size from image bytes. Returns dict with 'width' and 'height' keys, or None on error."""
    try:
        pil_image = PIL.Image.open(io.BytesIO(image_bytes))
        return {"width": pil_image.width, "height": pil_image.height}
    except Exception:
        return None


def _merge_negative_prompt(prompt: str, negative_prompt: Optional[str]) -> str:
    """Merge negative prompt into the main prompt for providers that don't support separate negative prompts."""
    if not negative_prompt:
        return prompt
    return f"{prompt}\n\nAvoid: {negative_prompt}"


def _upload_openai_image_to_gcs(
    *, image_bytes: bytes, gcs_uri_base: Optional[str]
) -> str:
    """Upload OpenAI generated image to GCS and return the GCS URI."""
    from app.core.config import global_config_loaded_from_config_yaml
    from app.external_services.gcs import upload_to_gcs

    bucket = global_config_loaded_from_config_yaml.gcs.bucket
    if gcs_uri_base and gcs_uri_base.startswith("gs://"):
        stripped = gcs_uri_base.removeprefix("gs://")
        base_bucket, base_path = stripped.split("/", 1)
        bucket = base_bucket or bucket
        base_dir = base_path.rstrip("/")
    else:
        base_dir = f"{DEFAULT_GCS_BASE_DIR}/{uuid.uuid4().hex}"

    path = f"{base_dir}/openai_{uuid.uuid4().hex}.png"
    upload_to_gcs(
        file_data=image_bytes,
        content_type="image/png",
        bucket_name=bucket,
        path=path,
    )
    return f"gs://{bucket}/{path}"


__all__ = [
    "GOOGLE_MODEL_PREFIX",
    "OPENAI_MODEL_PREFIX",
    "TextToImageGeneratedImage",
    "TextToImageGenerationRequest",
    "TextToImageGenerationResult",
    "TextToImageProvider",
    "generate_text_to_image",
]
