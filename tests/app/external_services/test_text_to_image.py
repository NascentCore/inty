from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.external_services.fakes.openai import FakeOpenAI
from app.external_services.text_to_image import (
    TextToImageGenerationRequest,
    TextToImageProvider,
    _resolve_provider_and_model,
    generate_text_to_image,
)


class _FakeGoogleImage:
    def __init__(self, gcs_uri: str) -> None:
        self.gcs_uri = gcs_uri


class _FakeGoogleGeneratedImage:
    def __init__(self, gcs_uri: str) -> None:
        self.image = _FakeGoogleImage(gcs_uri=gcs_uri)
        self.rai_filtered_reason = None
        self.enhanced_prompt = ""


class _FakeGoogleGenerateImagesResponse:
    def __init__(
        self, generated_images: list[_FakeGoogleGeneratedImage]
    ) -> None:
        self.generated_images = generated_images


class _FakeGoogleModels:
    def generate_images(
        self, *, model: str, prompt: str, config
    ):  # noqa: ARG002
        assert model == "imagen-4.0-fast-generate-001"
        assert prompt == "A friendly companion smiling at the camera"
        assert getattr(config, "number_of_images") == 2
        assert getattr(config, "output_gcs_uri") == "gs://fake-bucket/generated"
        return _FakeGoogleGenerateImagesResponse(
            generated_images=[
                _FakeGoogleGeneratedImage("gs://fake-bucket/generated/1.jpg"),
                _FakeGoogleGeneratedImage("gs://fake-bucket/generated/2.jpg"),
            ]
        )


class _FakeGoogleClient:
    def __init__(self) -> None:
        self.models = _FakeGoogleModels()


class _FakeFalClient:
    def subscribe(
        self, model: str, arguments: dict[str, object], with_logs: bool = False
    ):  # noqa: ARG002
        assert model == "fal-ai/z-image/turbo"
        assert (
            arguments["prompt"] == "A friendly companion smiling at the camera"
        )
        assert arguments["num_images"] == 2
        assert arguments["image_size"] == "portrait_4_3"
        assert arguments["output_format"] == "png"
        assert arguments["sync_mode"] is False
        return {
            "images": [
                {
                    "url": "https://fal.example/generated/1.png",
                    "width": 1024,
                    "height": 1365,
                    "content_type": "image/png",
                },
                {
                    "url": "https://fal.example/generated/2.png",
                    "width": 1024,
                    "height": 1365,
                    "content_type": "image/png",
                },
            ],
            "prompt": "A friendly companion smiling at the camera",
        }


def test_text_to_image_google_prefix_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config as app_config

    monkeypatch.setattr(
        app_config,
        "global_config_loaded_from_config_yaml",
        SimpleNamespace(gcs=SimpleNamespace(use_fake_gcs=False)),
    )

    fake_client = _FakeGoogleClient()

    result = generate_text_to_image(
        TextToImageGenerationRequest(
            model="google/imagen-4.0-fast-generate-001",
            prompt="A friendly companion smiling at the camera",
            num_images=2,
            provider_args={
                "client": fake_client,
                "aspect_ratio": "9:16",
                "output_gcs_uri": "gs://fake-bucket/generated",
                "output_mime_type": "image/jpeg",
            },
        )
    )

    assert result.provider == TextToImageProvider.GOOGLE
    assert result.model == "google/imagen-4.0-fast-generate-001"
    assert len(result.images) == 2
    assert all(
        img.provider == TextToImageProvider.GOOGLE for img in result.images
    )
    assert all(
        img.gcs_uri and img.gcs_uri.startswith("gs://") for img in result.images
    )
    assert all(
        img.public_url
        and img.public_url.startswith("https://storage.googleapis.com/")
        for img in result.images
    )


def test_resolve_provider_and_model_google_strips_org_prefix() -> None:
    provider, provider_model = _resolve_provider_and_model(
        "google/imagen-4.0-fast-generate-001"
    )
    assert provider == TextToImageProvider.GOOGLE
    assert provider_model == "imagen-4.0-fast-generate-001"


def test_resolve_provider_and_model_openai_keeps_org_prefix() -> None:
    provider, provider_model = _resolve_provider_and_model("openai/gpt-image-1")
    assert provider == TextToImageProvider.OPENAI
    assert provider_model == "openai/gpt-image-1"


def test_resolve_provider_and_model_falai_keeps_org_prefix() -> None:
    provider, provider_model = _resolve_provider_and_model(
        "fal-ai/z-image/turbo"
    )
    assert provider == TextToImageProvider.FALAI
    assert provider_model == "fal-ai/z-image/turbo"


def test_resolve_provider_and_model_falai_alias_normalized() -> None:
    provider, provider_model = _resolve_provider_and_model("FAL/Z-IMAGE/TURBO")
    assert provider == TextToImageProvider.FALAI
    assert provider_model == "fal-ai/z-image/turbo"


@pytest.mark.parametrize(
    "model",
    ["", "google/", "openai/", "fal-ai/", "fal/", "unknown/x"],
)
def test_resolve_provider_and_model_invalid_raises(model: str) -> None:
    with pytest.raises(ValueError):
        _resolve_provider_and_model(model)


def test_resolve_provider_and_model_bare_model_raises() -> None:
    """Bare model id without explicit provider prefix should raise."""
    with pytest.raises(
        ValueError, match="Model id must use google/, openai/, or fal-ai/"
    ):
        _resolve_provider_and_model("some-bare-model")


def test_text_to_image_openai_returns_png_bytes() -> None:
    fake = FakeOpenAI(seed=123)
    result = generate_text_to_image(
        TextToImageGenerationRequest(
            model="openai/gpt-image-1",
            prompt="a simple test image",
            num_images=2,
            provider_args={
                "openai_client": fake,
                "output": "bytes",
            },
        )
    )

    assert result.provider == TextToImageProvider.OPENAI
    assert result.model == "openai/gpt-image-1"
    assert len(result.images) == 2
    for img in result.images:
        assert img.provider == TextToImageProvider.OPENAI
        assert img.image_bytes and isinstance(
            img.image_bytes, (bytes, bytearray)
        )
        assert img.width == 64
        assert img.height == 64
        assert img.format == "png"
        assert img.gcs_uri is None


def test_text_to_image_falai_prefix_dispatch_z_image_turbo() -> None:
    fake_fal_client = _FakeFalClient()
    result = generate_text_to_image(
        TextToImageGenerationRequest(
            model="fal-ai/z-image/turbo",
            prompt="A friendly companion smiling at the camera",
            num_images=2,
            provider_args={
                "fal_client": fake_fal_client,
                "image_size": "portrait_4_3",
                "output_format": "png",
                "sync_mode": False,
            },
        )
    )

    assert result.provider == TextToImageProvider.FALAI
    assert result.model == "fal-ai/z-image/turbo"
    assert len(result.images) == 2
    for image in result.images:
        assert image.provider == TextToImageProvider.FALAI
        assert image.url and image.url.startswith(
            "https://fal.example/generated/"
        )
        assert image.width == 1024
        assert image.height == 1365
        assert image.mime_type == "image/png"


def test_gcs_uri_to_public_url_fake_filesystem_vs_https(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.core import config as app_config

    from app.external_services.text_to_image import _gcs_uri_to_public_url

    base = tmp_path / "fb"
    base.mkdir()
    local_file = base / "bk" / "o.jpg"
    local_file.parent.mkdir(parents=True)
    local_file.write_bytes(b"x")

    monkeypatch.setattr(
        app_config,
        "global_config_loaded_from_config_yaml",
        SimpleNamespace(
            gcs=SimpleNamespace(
                use_fake_gcs=True,
                fake_gcs_base_dir=str(base.resolve()),
            )
        ),
    )
    assert (
        _gcs_uri_to_public_url("gs://bk/o.jpg") == local_file.resolve().as_uri()
    )

    monkeypatch.setattr(
        app_config,
        "global_config_loaded_from_config_yaml",
        SimpleNamespace(gcs=SimpleNamespace(use_fake_gcs=False)),
    )
    assert (
        _gcs_uri_to_public_url("gs://bk/o.jpg")
        == "https://storage.googleapis.com/bk/o.jpg"
    )
