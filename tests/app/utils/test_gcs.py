"""Tests for GCS URL parsing and path helpers."""

from pathlib import Path
from types import SimpleNamespace

import pytest

import app.external_services.gcs as gcs_mod
from app.external_services.gcs import (
    append_filename_suffix,
    get_bucket_and_path_from_gcs_url,
    is_valid_gcs_url,
)


def test_get_bucket_and_path_from_gcs_url():
    assert get_bucket_and_path_from_gcs_url("gs://test-bucket/test-path") == (
        "test-bucket",
        "test-path",
    )
    assert get_bucket_and_path_from_gcs_url(
        "https://storage.googleapis.com/test-bucket/test-path/test-path2"
    ) == (
        "test-bucket",
        "test-path/test-path2",
    )
    assert get_bucket_and_path_from_gcs_url(
        "https://storage.cloud.google.com/test-bucket/test-path/test-path2"
    ) == (
        "test-bucket",
        "test-path/test-path2",
    )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://example.com/test-bucket/test-path",
        "gs://test-bucket",
        "https://storage.googleapis.com/test-bucket",
    ],
)
def test_get_bucket_and_path_from_gcs_url_rejects_invalid_url(url):
    with pytest.raises(ValueError, match="Invalid GCS URL"):
        get_bucket_and_path_from_gcs_url(url)


def test_append_filename_suffix():
    assert append_filename_suffix("a/b.c", "suffix") == "a/bsuffix.c"
    assert append_filename_suffix("a/b", "suffix") == "a/bsuffix"
    assert append_filename_suffix("b.c", "-suffix") == "b-suffix.c"
    assert append_filename_suffix("b", "-suffix") == "b-suffix"


def test_get_bucket_from_file_uri_under_fake_base(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    base = tmp_path / "fgcs"
    base.mkdir()
    local_file = base / "mybucket" / "p" / "x.bin"
    local_file.parent.mkdir(parents=True)
    local_file.write_bytes(b"z")
    uri = local_file.resolve().as_uri()
    monkeypatch.setattr(
        gcs_mod,
        "global_config_loaded_from_config_yaml",
        SimpleNamespace(
            gcs=SimpleNamespace(
                use_fake_gcs=True, fake_gcs_base_dir=str(base.resolve())
            )
        ),
    )
    assert get_bucket_and_path_from_gcs_url(uri) == ("mybucket", "p/x.bin")


def test_is_valid_gcs_url_accepts_fake_file_uri(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    base = tmp_path / "fgcs2"
    base.mkdir()
    local_file = base / "bkt" / "obj.txt"
    local_file.parent.mkdir(parents=True)
    local_file.write_bytes(b"a")
    uri = local_file.resolve().as_uri()
    monkeypatch.setattr(
        gcs_mod,
        "global_config_loaded_from_config_yaml",
        SimpleNamespace(
            gcs=SimpleNamespace(
                use_fake_gcs=True, fake_gcs_base_dir=str(base.resolve())
            )
        ),
    )
    assert is_valid_gcs_url(uri) is True
