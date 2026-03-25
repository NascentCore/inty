"""Fal z-image-turbo 文生图：复用 app.core.images.fal，结果摘要回注 LLM；可选落盘 workspace/generated_images/。"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

# 与 app/api/v1/endpoints/agents.py _generate_with_fal_z_image_turbo 对齐的默认推理参数
_DEFAULT_IMAGE_SIZE = "portrait_4_3"
# 单次调用张数上限（模型应按对话自行决定 1..N，省略则 1）
MAX_NUM_IMAGES_PER_CALL = 4


async def _z_image_turbo_call(args: Any, gcs_uri_base: str) -> list[Any]:
    """可测性钩子：patch 此协程即可避免真实 Fal/GCS。"""
    from app.core.images.fal import z_image_turbo as _impl

    return await _impl(args, gcs_uri_base)


def _gcs_uri_base_for_workspace(root: Path) -> str:
    raw = os.getenv("INTY_V2_PROTO_Z_IMAGE_GCS_BASE", "").strip()
    if raw:
        return raw
    return f"inty_v2_proto_chat_images/{root.resolve().name}"


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


def _maybe_write_local_copy(root: Path, item: Any) -> Path | None:
    raw = getattr(item, "raw_data", None)
    if not isinstance(raw, bytes) or len(raw) == 0:
        return None
    fmt = getattr(item, "format", None)
    ext = getattr(fmt, "value", None) if fmt is not None else None
    if not isinstance(ext, str) or not ext:
        ext = "bin"
    out_dir = root.resolve() / "generated_images"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:10]
    path = out_dir / f"z_image_{suffix}.{ext}"
    path.write_bytes(raw)
    return path


def _append_one_image_summary(
    parts: list[str],
    root: Path,
    item: Any,
    *,
    index: int,
    total: int,
) -> None:
    """单张结果：URL、尺寸、可选本地路径。"""
    if total > 1:
        parts.append(f"#{index}:")
    url = getattr(item, "gcs_http_url", "") or ""
    parts.append(f"gcs_http_url={url}" if url else "gcs_http_url=(none)")
    w = getattr(getattr(item, "size", None), "width", None)
    h = getattr(getattr(item, "size", None), "height", None)
    if w is not None and h is not None:
        parts.append(f"size={w}x{h}")
    try:
        local = _maybe_write_local_copy(root, item)
    except OSError as e:
        parts.append(f"local_path=(write failed: {e!s})")
    else:
        if local is not None:
            parts.append(f"local_path={local.resolve()}")


def run_generate_image_z_image_turbo(
    root: Path,
    *,
    prompt: str,
    image_size: str | None = None,
    num_inference_steps: int | None = None,
    num_images: int | None = None,
) -> str:
    """
    调用 Fal z-image-turbo，上传 GCS（经 app.core.images.fal）；返回单行摘要供 tool 消息。
    失败时以 ERROR: 开头。
    """
    from .client import load_prototype_dotenv

    load_prototype_dotenv()

    p = (prompt or "").strip()
    if not p:
        return "ERROR: prompt is required and must be non-empty."

    if num_images is not None and num_images < 1:
        return "ERROR: num_images must be >= 1."
    if num_images is not None and num_images > MAX_NUM_IMAGES_PER_CALL:
        return (
            f"ERROR: num_images must be <= {MAX_NUM_IMAGES_PER_CALL} "
            "(split into multiple turns if the user needs more)."
        )
    if num_inference_steps is not None and num_inference_steps < 1:
        return "ERROR: num_inference_steps must be >= 1."

    try:
        z_in = _build_z_input(
            prompt=p,
            image_size=image_size,
            num_inference_steps=num_inference_steps,
            num_images=num_images,
        )
        gcs_base = _gcs_uri_base_for_workspace(root)
        results = asyncio.run(_z_image_turbo_call(z_in, gcs_base))
    except ModuleNotFoundError as e:
        return (
            "ERROR: cannot import app (backend) modules. Run from repo root with "
            "`python -m experimental.inty_v2_text_chat_prototype.main` and install root "
            f"requirements. Detail: {e!s}"
        )
    except (ValueError, TypeError, OSError, RuntimeError, ValidationError) as e:
        return f"ERROR: image generation failed: {e!s}"

    if not results:
        return "ERROR: provider returned no images."

    n = len(results)
    parts: list[str] = [
        "generate_image: OK (fal z-image-turbo).",
        f"requested={num_images if num_images is not None else 1}",
        f"returned={n}",
    ]
    for i, item in enumerate(results):
        _append_one_image_summary(parts, root, item, index=i + 1, total=n)

    return " ".join(parts)
