"""Regression for companion generated_images index -> chat ``generated_image`` metadata."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import app.external_services.gcs as gcs_mod
import pytest

from app.core.agentic_kernel.companion.image_gate import (
    append_image_asset_record,
    generated_image_meta_from_asset_record,
    generated_image_meta_from_index_slice,
    list_image_asset_records,
)


def test_generated_image_meta_from_slice_prefers_gs_uri(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    append_image_asset_record(
        root,
        {
            "asset_id": "a1",
            "gcs_uri": "gs://bucket/old/path.jpg",
            "gcs_http_url": "https://storage.googleapis.com/bucket/old/path.jpg",
            "width": 10,
            "height": 20,
        },
    )
    baseline = len(list_image_asset_records(root))
    append_image_asset_record(
        root,
        {
            "asset_id": "a2",
            "gcs_uri": "gs://bucket/new/path.png",
            "gcs_http_url": "https://storage.googleapis.com/bucket/new/path.png",
            "width": 640,
            "height": 480,
        },
    )
    meta = generated_image_meta_from_index_slice(root, baseline)
    assert meta is not None
    assert meta["image_url"] == "gs://bucket/new/path.png"
    assert meta["width"] == 640
    assert meta["height"] == 480


def test_generated_image_meta_omits_when_no_gs_uri(tmp_path: Path) -> None:
    root = tmp_path / "ws2"
    root.mkdir()
    append_image_asset_record(
        root,
        {
            "asset_id": "x",
            "gcs_http_url": None,
            "gcs_uri": None,
        },
    )
    assert generated_image_meta_from_index_slice(root, 0) is None


def test_generated_image_meta_accepts_https_when_no_gs_uri() -> None:
    url = "https://cdn.example.invalid/fal/out.png"
    meta = generated_image_meta_from_asset_record(
        {
            "gcs_uri": url,
            "gcs_http_url": url,
            "width": 512,
            "height": 768,
        }
    )
    assert meta is not None
    assert meta["image_url"] == url
    assert meta["width"] == 512
    assert meta["height"] == 768


def test_generated_image_meta_maps_fake_file_http_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = tmp_path / "fake_store"
    store.mkdir()
    obj_path = store / "mybucket" / "gen" / "out.png"
    obj_path.parent.mkdir(parents=True)
    obj_path.write_bytes(b"\x89PNG")
    file_uri = obj_path.resolve().as_uri()
    monkeypatch.setattr(
        gcs_mod,
        "global_config_loaded_from_config_yaml",
        SimpleNamespace(
            gcs=SimpleNamespace(
                use_fake_gcs=True,
                fake_gcs_base_dir=str(store.resolve()),
            )
        ),
    )
    meta = generated_image_meta_from_asset_record(
        {"gcs_uri": "", "gcs_http_url": file_uri, "width": 3, "height": 4}
    )
    assert meta is not None
    assert meta["image_url"] == "gs://mybucket/gen/out.png"
