# CREATED_BY_AGENT: cursor-gpt-5.2 (2025-12-23)

from __future__ import annotations

import base64
import io
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Optional

import PIL.Image

_ORG_SEPARATOR = "/"
_ORG_GOOGLE = "google"
_ORG_OPENAI = "openai"

_OUTPUT_BYTES: Literal["bytes"] = "bytes"
_OUTPUT_GCS: Literal["gcs"] = "gcs"
_OUTPUT_BOTH: Literal["both"] = "both"

_DEFAULT_GCS_BASE_DIR = "tmp/image_generation_wrapper"
_DEFAULT_ASPECT_RATIO = "9:16"
_FORMAT_JPEG = "jpeg"
_FORMAT_PNG = "png"


class ImageProvider(StrEnum):
    GOOGLE = _ORG_GOOGLE
    OPENAI = _ORG_OPENAI


@dataclass(frozen=True)
class ResolvedImageModel:
    provider: ImageProvider
    # Provider-native model id (e.g. "imagen-4.0-fast-generate-001")
    provider_model: str
    # Original user-facing model id with org prefix (e.g. "google/imagen-4...")
    model: str


@dataclass(frozen=True)
class UnifiedGeneratedImage:
    provider: ImageProvider
    model: str
    prompt: str
    format: str
    size: Optional["UnifiedImageSize"]
    image_bytes: Optional[bytes]
    gcs_uri: Optional[str]
    rai_filtered_reason: Optional[str] = None


@dataclass(frozen=True)
class UnifiedImageSize:
    width: int
    height: int


def resolve_image_model(model: str) -> ResolvedImageModel:
    """
    Resolve a user-facing model id with org prefix to a provider + provider model id.

    Supported formats:
    - google/<imagen_model_id>
    - openai/<image_model_id>
    """
    if not model or _ORG_SEPARATOR not in model:
        raise ValueError(f"Invalid model id: {model!r}. Expect '<org>/<model>' format.")

    org, rest = model.split(_ORG_SEPARATOR, 1)
    org = org.strip().lower()
    rest = rest.strip()
    if not rest:
        raise ValueError(f"Invalid model id: {model!r}. Missing model part.")

    if org == _ORG_GOOGLE:
        return ResolvedImageModel(
            provider=ImageProvider.GOOGLE,
            provider_model=rest,
            model=model,
        )
    if org == _ORG_OPENAI:
        return ResolvedImageModel(
            provider=ImageProvider.OPENAI,
            # OpenAI / OpenRouter generally expects the org-prefixed model id.
            provider_model=model,
            model=model,
        )

    raise ValueError(f"Unsupported image model org prefix: {org!r} (model={model!r})")


def generate_images(
    *,
    model: str,
    prompt: str,
    negative_prompt: Optional[str] = None,
    count: int = 1,
    aspect_ratio: str = _DEFAULT_ASPECT_RATIO,
    output: Literal["bytes", "gcs", "both"] = _OUTPUT_BYTES,
    gcs_uri_base: Optional[str] = None,
    enhance_prompt: bool = False,
    gender: str = "",
    openai_client=None,
) -> list[UnifiedGeneratedImage]:
    """
    Unified wrapper for image generation.

    Notes:
    - This is an INTERNAL API and is NOT wired into any FastAPI endpoint yet.
    - Model ids MUST include an org prefix, e.g. "google/..." or "openai/...".
    """
    resolved = resolve_image_model(model)
    if resolved.provider == ImageProvider.GOOGLE:
        return _generate_with_google_imagen(
            resolved=resolved,
            prompt=prompt,
            negative_prompt=negative_prompt or "",
            count=count,
            aspect_ratio=aspect_ratio,
            output=output,
            gcs_uri_base=gcs_uri_base,
            enhance_prompt=enhance_prompt,
            gender=gender,
        )

    return _generate_with_openai_gpt_image(
        resolved=resolved,
        prompt=prompt,
        negative_prompt=negative_prompt,
        count=count,
        output=output,
        gcs_uri_base=gcs_uri_base,
        openai_client=openai_client,
    )


def _generate_with_google_imagen(
    *,
    resolved: ResolvedImageModel,
    prompt: str,
    negative_prompt: str,
    count: int,
    aspect_ratio: str,
    output: Literal["bytes", "gcs", "both"],
    gcs_uri_base: Optional[str],
    enhance_prompt: bool,
    gender: str,
) -> list[UnifiedGeneratedImage]:
    if output in (_OUTPUT_GCS, _OUTPUT_BOTH) and not gcs_uri_base:
        gcs_uri_base = _default_gcs_uri_base()

    from app.utils.gemini import text_to_image

    generated = text_to_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        enhanced_prompt=enhance_prompt,
        gender=gender,
        aspect_ratio=aspect_ratio,
        gcs_uri_base=gcs_uri_base or _default_gcs_uri_base(),
        count=count,
        model=resolved.provider_model,
    )

    results: list[UnifiedGeneratedImage] = []
    for img in generated:
        img_bytes: Optional[bytes] = None
        if output in (_OUTPUT_BYTES, _OUTPUT_BOTH) and img.gcs_uri:
            # Prefer not downloading by default; only download when requested.
            from app.external_services.gcs import download_from_gcs

            img_bytes = download_from_gcs(img.gcs_uri)

        results.append(
            UnifiedGeneratedImage(
                provider=resolved.provider,
                model=resolved.model,
                prompt=prompt,
                format=(img.format.value if getattr(img.format, "value", None) else (img.format or _FORMAT_JPEG)),
                size=(
                    UnifiedImageSize(width=img.size.width, height=img.size.height)
                    if img.size
                    else None
                ),
                image_bytes=img_bytes,
                gcs_uri=img.gcs_uri if output in (_OUTPUT_GCS, _OUTPUT_BOTH) else None,
                rai_filtered_reason=img.rai_filtered_reason,
            )
        )
    return results


def _generate_with_openai_gpt_image(
    *,
    resolved: ResolvedImageModel,
    prompt: str,
    negative_prompt: Optional[str],
    count: int,
    output: Literal["bytes", "gcs", "both"],
    gcs_uri_base: Optional[str],
    openai_client,
) -> list[UnifiedGeneratedImage]:
    if openai_client is None:
        from app.utils.openai_client import get_base_openai_client

        client = get_base_openai_client()
    else:
        client = openai_client

    # OpenAI image generation does not have a single universal negative prompt field.
    # We append it to prompt for now; real integration can refine this mapping.
    full_prompt = _merge_negative_prompt(prompt, negative_prompt)

    response = client.images.generate(
        model=resolved.provider_model,
        prompt=full_prompt,
        n=count,
        response_format="b64_json",
    )

    results: list[UnifiedGeneratedImage] = []
    for item in getattr(response, "data", []) or []:
        b64_json = getattr(item, "b64_json", None)
        if not b64_json:
            continue
        image_bytes = base64.b64decode(b64_json)
        size = _infer_image_size(image_bytes)

        gcs_uri: Optional[str] = None
        if output in (_OUTPUT_GCS, _OUTPUT_BOTH):
            gcs_uri = _upload_openai_image_to_gcs(
                image_bytes=image_bytes, gcs_uri_base=gcs_uri_base
            )

        results.append(
            UnifiedGeneratedImage(
                provider=resolved.provider,
                model=resolved.model,
                prompt=prompt,
                format=_FORMAT_PNG,
                size=size,
                image_bytes=image_bytes if output in (_OUTPUT_BYTES, _OUTPUT_BOTH) else None,
                gcs_uri=gcs_uri,
            )
        )
    return results


def _default_gcs_uri_base() -> str:
    from app.core.config import global_config_loaded_from_config_yaml

    bucket = global_config_loaded_from_config_yaml.gcs.bucket
    uid = uuid.uuid4().hex
    return f"gs://{bucket}/{_DEFAULT_GCS_BASE_DIR}/{uid}"


def _upload_openai_image_to_gcs(*, image_bytes: bytes, gcs_uri_base: Optional[str]) -> str:
    from app.core.config import global_config_loaded_from_config_yaml
    from app.external_services.gcs import upload_to_gcs

    bucket = global_config_loaded_from_config_yaml.gcs.bucket
    if gcs_uri_base and gcs_uri_base.startswith("gs://"):
        stripped = gcs_uri_base.removeprefix("gs://")
        base_bucket, base_path = stripped.split("/", 1)
        bucket = base_bucket or bucket
        base_dir = base_path.rstrip("/")
    else:
        base_dir = f"{_DEFAULT_GCS_BASE_DIR}/{uuid.uuid4().hex}"

    path = f"{base_dir}/openai_{uuid.uuid4().hex}.png"
    upload_to_gcs(
        file_data=image_bytes,
        content_type="image/png",
        bucket_name=bucket,
        path=path,
    )
    return f"gs://{bucket}/{path}"


def _infer_image_size(image_bytes: bytes) -> Optional[UnifiedImageSize]:
    try:
        pil_image = PIL.Image.open(io.BytesIO(image_bytes))
        return UnifiedImageSize(width=pil_image.width, height=pil_image.height)
    except Exception:
        return None


def _merge_negative_prompt(prompt: str, negative_prompt: Optional[str]) -> str:
    if not negative_prompt:
        return prompt
    return f"{prompt}\n\nAvoid: {negative_prompt}"

