# CREATED_BY_AGENT: cursor-gpt-5.2 (2025-12-23)

from __future__ import annotations

import pytest

from app.external_services.fakes.openai import FakeOpenAI
from app.utils.image_generation_wrapper import (
    ImageProvider,
    generate_images,
    resolve_image_model,
)


def test_resolve_image_model_google_strips_org_prefix():
    resolved = resolve_image_model("google/imagen-4.0-fast-generate-001")
    assert resolved.provider == ImageProvider.GOOGLE
    assert resolved.provider_model == "imagen-4.0-fast-generate-001"
    assert resolved.model == "google/imagen-4.0-fast-generate-001"


def test_resolve_image_model_openai_keeps_org_prefix():
    resolved = resolve_image_model("openai/gpt-image-1")
    assert resolved.provider == ImageProvider.OPENAI
    assert resolved.provider_model == "openai/gpt-image-1"
    assert resolved.model == "openai/gpt-image-1"


@pytest.mark.parametrize("model", ["", "imagen-4.0-fast-generate-001", "google/", "unknown/x"])
def test_resolve_image_model_invalid_raises(model: str):
    with pytest.raises(ValueError):
        resolve_image_model(model)


def test_generate_images_openai_branch_returns_png_bytes():
    fake = FakeOpenAI(seed=123)
    results = generate_images(
        model="openai/gpt-image-1",
        prompt="a simple test image",
        count=2,
        output="bytes",
        openai_client=fake,
    )

    assert len(results) == 2
    for r in results:
        assert r.provider == ImageProvider.OPENAI
        assert r.model == "openai/gpt-image-1"
        assert r.image_bytes and isinstance(r.image_bytes, (bytes, bytearray))
        assert r.size is not None
        assert r.size.width == 64
        assert r.size.height == 64
        assert r.gcs_uri is None

