"""Fal z-image-turbo：文生图（text-to-image）与图生图（image-to-image）复用 app.core.images.fal。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fal_client

from app.core.images.fal import (
    ZImageTurboImageToImageInput,
    z_image_turbo,
    z_image_turbo_image_to_image,
)

from .env_util import env_flag_enabled

# 与 app/api/v1/endpoints/agents.py _generate_with_fal_z_image_turbo 对齐的默认推理参数
_DEFAULT_IMAGE_SIZE = "portrait_4_3"
# 单次调用张数上限（模型应按对话自行决定 1..N，省略则 1）
MAX_NUM_IMAGES_PER_CALL = 4


async def _reset_fal_async_client_after_short_lived_loop() -> None:
    """
    fal 模块级 `async_client` 的 httpx 实例绑定创建它的 event loop。
    在 `asyncio.run(run_turn(...))` 每轮用户输入都会关闭 loop 时，须在 loop 仍存活时拆掉缓存并 aclose，
    否则下一次短生命周期 loop 内调用 Fal 会报 Event loop is closed。
    """
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
    """
    将 workspace 内图片上传到 GCS，返回公网 HTTPS URL，供 Fal image-to-image 的 image_url 入参。
    """
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
    suffix = (
        datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        + "_"
        + uuid.uuid4().hex[:10]
    )
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
        local = _maybe_write_local_copy(root, item)
        if local is not None:
            parts.append(f"local_path={local.resolve()}")


async def run_generate_image_z_image_turbo(
    root: Path,
    *,
    prompt: str,
    image_size: str | None = None,
    num_inference_steps: int | None = None,
    num_images: int | None = None,
) -> str:
    """
    调用 Fal z-image-turbo；默认经 app.core.images.fal 上传 GCS。
    `INTY_V2_PROTO_Z_IMAGE_SKIP_GCS` 为真时跳过结果上传（仅本地像素与 generated_images/）。
    失败时以 ERROR: 开头。
    """
    from .client import load_prototype_dotenv

    load_prototype_dotenv()

    z_in = _build_z_input(
        prompt=prompt,
        image_size=image_size,
        num_inference_steps=num_inference_steps,
        num_images=num_images,
    )
    gcs_base = _gcs_uri_base_for_workspace(root)
    skip_gcs = env_flag_enabled("INTY_V2_PROTO_Z_IMAGE_SKIP_GCS")
    results = await z_image_turbo(z_in, gcs_base, skip_gcs_upload=skip_gcs)

    if not results:
        return "ERROR: Fal z-image-turbo returned no images."

    n = len(results)
    parts: list[str] = [
        "generate_image: OK (fal z-image-turbo).",
        f"requested={num_images if num_images is not None else 1}",
        f"returned={n}",
    ]
    for i, item in enumerate(results):
        _append_one_image_summary(parts, root, item, index=i + 1, total=n)

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
) -> str:
    """
    Fal z-image-turbo **image-to-image**：基于已有图按提示修改；与文生图 `z_image_turbo` 区分。
    source 二选一：workspace 内文件（先上传 GCS 得 URL）或已是 https 的参考图 URL。
    """
    from app.utils.image import ImageFormat

    from .client import load_prototype_dotenv

    load_prototype_dotenv()

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
    if has_path:
        assert source_path is not None
        image_url_for_fal = _upload_local_image_file_to_gcs_for_fal(
            source_path, gcs_base
        )
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
    z_in = ZImageTurboImageToImageInput(**kwargs)
    skip_gcs = env_flag_enabled("INTY_V2_PROTO_Z_IMAGE_SKIP_GCS")
    result = await z_image_turbo_image_to_image(
        z_in, gcs_base, skip_gcs_upload=skip_gcs
    )

    parts: list[str] = [
        "modify_image: OK (fal z-image-turbo image-to-image).",
        "returned=1",
    ]
    _append_one_image_summary(parts, root, result, index=1, total=1)
    return " ".join(parts)
