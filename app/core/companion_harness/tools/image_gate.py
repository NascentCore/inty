"""Generated image index access and chat_history generated_image helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from app.core.companion_harness.memory.memory_store import MemoryStore

_IMAGE_ASSET_INDEX_REL = "generated_images/index.jsonl"


def _read_profile_doc(store: MemoryStore, relative_path: str) -> str:
    body = store.read_document_if_exists(relative_path)
    if body is not None:
        return body
    return ""


def _core_profile_payload(store: MemoryStore) -> dict[str, str]:
    return {
        "IDENTITY.md": _read_profile_doc(store, "IDENTITY.md"),
        "SOUL.md": _read_profile_doc(store, "SOUL.md"),
        "USER.md": _read_profile_doc(store, "USER.md"),
    }


def compute_persona_revision_id(store: MemoryStore) -> str:
    payload = _core_profile_payload(store)
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def current_persona_revision_id(store: MemoryStore) -> str:
    return compute_persona_revision_id(store)


def append_image_asset_record(store: MemoryStore, record: dict[str, Any]) -> None:
    store.append_jsonl_record(_IMAGE_ASSET_INDEX_REL, record)


def list_image_asset_records(store: MemoryStore) -> list[dict[str, Any]]:
    body = store.read_document_if_exists(_IMAGE_ASSET_INDEX_REL)
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
    from app.external_services.gcs import gs_uri_from_storage_reference_url

    w = row.get("width")
    h = row.get("height")
    base = {
        "width": w,
        "height": h,
        "format": "png",
    }

    if global_config_loaded_from_config_yaml.gcs.use_fake_gcs:
        http_u = str(row.get("gcs_http_url") or "").strip()
        if http_u:
            return {"image_url": http_u, **base}

    gcs_uri = str(row.get("gcs_uri") or "").strip()
    if not gcs_uri.startswith("gs://"):
        ref = str(row.get("gcs_http_url") or "").strip()
        if ref:
            mapped = gs_uri_from_storage_reference_url(ref)
            if mapped:
                gcs_uri = mapped

    if gcs_uri.startswith("gs://"):
        return {"image_url": gcs_uri, **base}

    for candidate in (
        str(row.get("gcs_uri") or "").strip(),
        str(row.get("gcs_http_url") or "").strip(),
    ):
        if candidate.startswith("http://") or candidate.startswith("https://"):
            return {"image_url": candidate, **base}
    return None


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


def relative_path_under_workspace(store: MemoryStore, absolute_path: Path) -> str:
    """Map a local absolute path to a scope-relative key segment (basename when not under synthetic root)."""
    return PurePosixPath(absolute_path.resolve().as_posix()).name
