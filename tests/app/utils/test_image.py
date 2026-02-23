"""Tests for app.utils.image."""

import base64
from pathlib import Path

import pytest

from app.utils.image import save_image_data_to_file

_TEST_JPG_PATH = Path("tests/files/test.jpg")


def test_save_image_data_to_file_roundtrip_identical_to_source():
    """Read test.jpg, build data URI, save via save_image_data_to_file, assert saved bytes equal original."""
    original_bytes = _TEST_JPG_PATH.read_bytes()
    b64 = base64.b64encode(original_bytes).decode("ascii")
    data_uri = f"data:image/jpeg;base64,{b64}"

    path = save_image_data_to_file(data_uri)

    saved_bytes = Path(path).read_bytes()
    assert saved_bytes == original_bytes
