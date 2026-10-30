"""Generated image index access and chat_history generated_image helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    GENERATED_IMAGES_INDEX_JSONL_REL,
)
from app.core.companion_harness.memory.memory_store_scope import (
    IDENTITY_MD_REL,
    SOUL_MD_REL,
    USER_MD_REL,
)


def _read_profile_doc(store: MemoryStore, relative_path: str) -> str:
    body = store.read_document_if_exists(relative_path)
    if body is not None:
        return body
    return ""


def _core_profile_payload(store: MemoryStore) -> dict[str, str]:
    return {
        IDENTITY_MD_REL: _read_profile_doc(store, IDENTITY_MD_REL),
        SOUL_MD_REL: _read_profile_doc(store, SOUL_MD_REL),
        USER_MD_REL: _read_profile_doc(store, USER_MD_REL),
    }


def compute_persona_revision_id(store: MemoryStore) -> str:
    payload = _core_profile_payload(store)
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def current_persona_revision_id(store: MemoryStore) -> str:
    return compute_persona_revision_id(store)


def append_image_asset_record(
    store: MemoryStore, record: dict[str, Any]
) -> None:
    store.append_jsonl_record(GENERATED_IMAGES_INDEX_JSONL_REL, record)


def list_image_asset_records(store: MemoryStore) -> list[dict[str, Any]]:
    body = store.read_document_if_exists(GENERATED_IMAGES_INDEX_JSONL_REL)
    if body is None or not body.strip():
        return []
    out: list[dict[str, Any]] = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        if isinstance(row, dict):
            out.append(row)
    return out


def _generated_image_dimension_base(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "width": row.get("width"),
        "height": row.get("height"),
        "format": "png",
    }


def _generated_image_meta_with_url(
    image_url: str, base: dict[str, Any]
) -> dict[str, Any]:
    assert image_url
    return {"image_url": image_url, **base}


def _generated_image_meta_for_fake_gcs_row(
    row: dict[str, Any], base: dict[str, Any]
) -> dict[str, Any] | None:
    http_u = str(row.get("gcs_http_url") or "").strip()
    if not http_u:
        return None
    return _generated_image_meta_with_url(http_u, base)


def _resolve_generated_image_gcs_uri(row: dict[str, Any]) -> str:
    from app.external_services.gcs import gs_uri_from_storage_reference_url

    gcs_uri = str(row.get("gcs_uri") or "").strip()
    if gcs_uri.startswith("gs://"):
        return gcs_uri
    ref = str(row.get("gcs_http_url") or "").strip()
    if not ref:
        return gcs_uri
    mapped = gs_uri_from_storage_reference_url(ref)
    if mapped:
        return mapped
    return gcs_uri


def _generated_image_meta_from_http_fallback(
    row: dict[str, Any], base: dict[str, Any]
) -> dict[str, Any] | None:
    for candidate in (
        str(row.get("gcs_uri") or "").strip(),
        str(row.get("gcs_http_url") or "").strip(),
    ):
        if candidate.startswith("http://") or candidate.startswith("https://"):
            return _generated_image_meta_with_url(candidate, base)
    return None


def generated_image_meta_from_asset_record(
    row: dict[str, Any],
) -> dict[str, Any] | None:
    """Build chat_history ``generated_image`` metadata from one ``generated_images`` index row.

    With **real** GCS, prefers a canonical ``gs://`` URI when present or derivable from
    ``gcs_http_url``. If no ``gs://`` is available, accepts absolute ``http(s)://`` URLs
    (e.g. Fal CDN stored in the row).

    With **fake** GCS (``use_fake_gcs``), ``gcs_uri`` may still look like ``gs://`` but only
    maps to the local fake layout; the fetchable URL is ``gcs_http_url`` (typically
    ``file://...`` from ``Blob.public_url``), which we use as ``image_url`` when set.
    """
    from app.core.config import global_config_loaded_from_config_yaml

    base = _generated_image_dimension_base(row)

    if global_config_loaded_from_config_yaml.gcs.use_fake_gcs:
        return _generated_image_meta_for_fake_gcs_row(row, base)

    gcs_uri = _resolve_generated_image_gcs_uri(row)
    if gcs_uri.startswith("gs://"):
        return _generated_image_meta_with_url(gcs_uri, base)

    return _generated_image_meta_from_http_fallback(row, base)


def generated_image_meta_from_index_slice(
    store: MemoryStore, baseline_index: int
) -> dict[str, Any] | None:
    """Return metadata for the latest new asset rows since ``baseline_index`` (list length offset)."""
    records = list_image_asset_records(store)
    if baseline_index < 0 or baseline_index > len(records):
        return None
    for row in reversed(records[baseline_index:]):
        meta = generated_image_meta_from_asset_record(row)
        if meta is not None:
            return meta
    return None


def _normalize_relative_path_for_index(path: str) -> str:
    return (path or "").strip().replace("\\", "/")


def find_latest_asset_by_local_relative_path(
    store: MemoryStore, relative_path: str
) -> dict[str, Any] | None:
    target = _normalize_relative_path_for_index(relative_path)
    if not target:
        return None
    for row in reversed(list_image_asset_records(store)):
        if (
            _normalize_relative_path_for_index(
                str(row.get("local_path_relative") or "")
            )
            == target
        ):
            return row
    return None


def relative_path_under_workspace(
    store: MemoryStore, absolute_path: Path
) -> str:
    """Map a local absolute path to a scope-relative key segment (basename when not under synthetic root)."""
    return PurePosixPath(absolute_path.resolve().as_posix()).name
