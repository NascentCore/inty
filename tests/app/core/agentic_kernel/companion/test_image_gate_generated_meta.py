"""Regression for companion generated_images index -> chat ``generated_image`` metadata."""

from __future__ import annotations

from pathlib import Path

from app.core.agentic_kernel.companion.image_gate import (
    append_image_asset_record,
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
