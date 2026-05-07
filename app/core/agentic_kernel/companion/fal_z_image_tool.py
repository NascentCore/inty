"""Fal z-image-turbo text-to-image and image-to-image via app.core.images.fal."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fal_client

from .env_flags import env_flag_enabled
from .image_gate import (
    append_image_asset_record,
    find_latest_asset_by_local_relative_path,
    relative_path_under_workspace,
)
from .utc import utc_iso_ts

_DEFAULT_IMAGE_SIZE = "portrait_4_3"
MAX_NUM_IMAGES_PER_CALL = 4


def _load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def _z_image_turbo_call(
    z_input: Any,
    gcs_base: str,
    *,
    skip_gcs_upload: bool,
) -> Any:
    from app.core.images.fal import z_image_turbo

    return z_image_turbo(z_input, gcs_base, skip_gcs_upload=skip_gcs_upload)


def _z_image_turbo_i2i_call(
    z_input: Any,
    gcs_base: str,
    *,
    skip_gcs_upload: bool,
) -> Any:
    from app.core.images.fal import z_image_turbo_image_to_image

    return z_image_turbo_image_to_image(
        z_input, gcs_base, skip_gcs_upload=skip_gcs_upload
    )


async def reset_fal_async_client_after_short_lived_loop() -> None:
    inst = fal_client.async_client
    old = inst.__dict__.pop("_client", None)
    inst.__dict__.pop("_token_manager", None)
    if old is not None:
        await old.aclose()


def _gcs_uri_base_for_workspace(root: Path) -> str:
    return f"inty_v2_proto_chat_images/{root.resolve().name}"


_SOURCE_IMAGE_EXT_TO_UPLOAD: dict[str, tuple[str, str]] = {
    ".jpg": ("image/jpeg", "jpeg"),
    ".jpeg": ("image/jpeg", "jpeg"),
    ".png": ("image/png", "png"),
    ".webp": ("image/webp", "webp"),
    ".gif": ("image/gif", "gif"),
}


def _upload_local_image_file_to_gcs_for_fal(image_path: Path, gcs_uri_base: str) -> str:
    from app.core.config import global_config_loaded_from_config_yaml as global_config
    from app.external_services.gcs import upload_to_gcs

    suffix = image_path.suffix.lower()
    if suffix not in _SOURCE_IMAGE_EXT_TO_UPLOAD:
        raise ValueError(
            "source image extension must be one of: "
            + ", ".join(sorted(_SOURCE_IMAGE_EXT_TO_UPLOAD.keys()))
        )
    content_type, ext_value = _SOURCE_IMAGE_EXT_TO_UPLOAD[suffix]
    file_data = image_path.read_bytes()
    if len(file_data) == 0:
        raise ValueError("source image file is empty")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    gcs_path = f"{gcs_uri_base}/i2i_src_{timestamp}_{uuid.uuid4().hex[:8]}.{ext_value}"
    return upload_to_gcs(
        file_data=file_data,
        content_type=content_type,
        bucket_name=global_config.gcs.bucket,
        path=gcs_path,
    )


def _build_z_input(
    *,
    prompt: str,
    image_size: str | None,
    num_inference_steps: int | None,
    num_images: int | None,
) -> Any:
    from app.core.images.fal import ZImageTurboInput
    from app.utils.image import ImageFormat

    kwargs: dict[str, Any] = {
        "prompt": prompt,
        "image_size": image_size or _DEFAULT_IMAGE_SIZE,
        "num_images": num_images if num_images is not None else 1,
        "output_format": ImageFormat.PNG,
    }
    if num_inference_steps is not None:
        kwargs["num_inference_steps"] = num_inference_steps
    return ZImageTurboInput(**kwargs)


def _build_image_to_image_input(kwargs: dict[str, Any]) -> Any:
    from app.core.images.fal import ZImageTurboImageToImageInput

    return ZImageTurboImageToImageInput(**kwargs)


def _append_one_image_summary(
    parts: list[str],
    root: Path,
    item: Any,
    *,
    index: int,
    total: int,
    tool_name: str,
    persona_revision_id: str,
    source_asset_id: str | None = None,
    source_persona_revision_id: str | None = None,
    source_image_relative_path: str | None = None,
    source_image_url: str | None = None,
) -> None:
    if total > 1:
        parts.append(f"#{index}:")
    url = getattr(item, "gcs_http_url", "") or ""
    gcs_uri = str(getattr(item, "gcs_uri", "") or "").strip()
    parts.append(f"gcs_http_url={url}" if url else "gcs_http_url=(none)")
    w = getattr(getattr(item, "size", None), "width", None)
    h = getattr(getattr(item, "size", None), "height", None)
    if w is not None and h is not None:
        parts.append(f"size={w}x{h}")
    local_rel: str | None = None

    asset_id = str(uuid.uuid4())
    parts.append(f"asset_id={asset_id}")
    parts.append(f"persona_revision_id={persona_revision_id}")
    append_image_asset_record(
        root,
        {
            "asset_id": asset_id,
            "tool_name": tool_name,
            "image_mode": "regenerate" if tool_name == "generate_image" else "modify",
            "persona_revision_id": persona_revision_id,
            "source_asset_id": source_asset_id,
            "source_persona_revision_id": source_persona_revision_id,
            "source_image_relative_path": source_image_relative_path,
            "source_image_url": source_image_url,
            "local_path_relative": local_rel,
            "local_path_absolute": None,
            "gcs_uri": gcs_uri if gcs_uri else None,
            "gcs_http_url": url if url else None,
            "width": int(w) if w is not None else None,
            "height": int(h) if h is not None else None,
            "created_at": utc_iso_ts(),
        },
    )
    if source_asset_id:
        parts.append(f"source_asset_id={source_asset_id}")
    if source_persona_revision_id:
        parts.append(f"source_persona_revision_id={source_persona_revision_id}")


async def run_generate_image_z_image_turbo(
    root: Path,
    *,
    prompt: str,
    image_size: str | None = None,
    num_inference_steps: int | None = None,
    num_images: int | None = None,
    persona_revision_id: str,
) -> str:
    _load_dotenv_if_present()

    z_in = _build_z_input(
        prompt=prompt,
        image_size=image_size,
        num_inference_steps=num_inference_steps,
        num_images=num_images,
    )
    gcs_base = _gcs_uri_base_for_workspace(root)
    skip_gcs = env_flag_enabled("INTY_V2_PROTO_Z_IMAGE_SKIP_GCS")
    maybe_results = _z_image_turbo_call(z_in, gcs_base, skip_gcs_upload=skip_gcs)
    if asyncio.iscoroutine(maybe_results):
        results = await maybe_results
    else:
        results = maybe_results

    if not results:
        return "ERROR: Fal z-image-turbo returned no images."

    n = len(results)
    parts: list[str] = [
        "generate_image: OK (fal z-image-turbo).",
        f"requested={num_images if num_images is not None else 1}",
        f"returned={n}",
        f"persona_revision_id={persona_revision_id}",
    ]
    for i, item in enumerate(results):
        _append_one_image_summary(
            parts,
            root,
            item,
            index=i + 1,
            total=n,
            tool_name="generate_image",
            persona_revision_id=persona_revision_id,
        )

    return " ".join(parts)


async def run_modify_image_z_image_turbo(
    root: Path,
    *,
    prompt: str,
    source_path: Path | None,
    source_image_url: str | None,
    image_size: str | None = None,
    num_inference_steps: int | None = None,
    strength: float | None = None,
    persona_revision_id: str,
) -> str:
    from app.utils.image import ImageFormat

    _load_dotenv_if_present()

    has_path = source_path is not None
    has_url = source_image_url is not None and source_image_url.strip() != ""
    if has_path and has_url:
        return "ERROR: use only one of source_image_relative_path or source_image_url, not both"
    if not has_path and not has_url:
        return (
            "ERROR: modify_image requires source_image_relative_path (workspace image file) "
            "or source_image_url (https)"
        )

    gcs_base = _gcs_uri_base_for_workspace(root)
    source_asset_id: str | None = None
    source_persona_revision_id: str | None = None
    source_rel_for_index: str | None = None
    if has_path:
        path = source_path
        if path is None:
            raise ValueError("source_path is required when has_path is true")
        source_rel_for_index = relative_path_under_workspace(root, path)
        source_asset = find_latest_asset_by_local_relative_path(
            root, source_rel_for_index
        )
        if source_asset is not None:
            source_asset_id = str(source_asset.get("asset_id") or "") or None
            source_persona_revision_id = (
                str(source_asset.get("persona_revision_id") or "") or None
            )
        image_url_for_fal = _upload_local_image_file_to_gcs_for_fal(path, gcs_base)
    else:
        u = source_image_url.strip()
        if not (u.startswith("https://") or u.startswith("http://")):
            return "ERROR: source_image_url must be an http(s) URL"
        image_url_for_fal = u

    size_kw: Any = (
        image_size.strip()
        if isinstance(image_size, str) and image_size.strip()
        else _DEFAULT_IMAGE_SIZE
    )
    steps = num_inference_steps if num_inference_steps is not None else 8
    kwargs: dict[str, Any] = {
        "prompt": prompt,
        "image_url": image_url_for_fal,
        "image_size": size_kw,
        "num_inference_steps": steps,
        "output_format": ImageFormat.PNG,
        "num_images": 1,
    }
    if strength is not None:
        kwargs["strength"] = strength

    z_in = _build_image_to_image_input(kwargs)
    skip_gcs = env_flag_enabled("INTY_V2_PROTO_Z_IMAGE_SKIP_GCS")
    maybe_result = _z_image_turbo_i2i_call(z_in, gcs_base, skip_gcs_upload=skip_gcs)
    if asyncio.iscoroutine(maybe_result):
        result = await maybe_result
    else:
        result = maybe_result

    parts: list[str] = [
        "modify_image: OK (fal z-image-turbo image-to-image).",
        "returned=1",
        f"persona_revision_id={persona_revision_id}",
    ]
    _append_one_image_summary(
        parts,
        root,
        result,
        index=1,
        total=1,
        tool_name="modify_image",
        persona_revision_id=persona_revision_id,
        source_asset_id=source_asset_id,
        source_persona_revision_id=source_persona_revision_id,
        source_image_relative_path=source_rel_for_index,
        source_image_url=source_image_url,
    )
    return " ".join(parts)
