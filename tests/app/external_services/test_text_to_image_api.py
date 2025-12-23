from __future__ import annotations

import pytest

from app.external_services.text_to_image_api import (
    TextToImageGenerationRequest,
    TextToImageProvider,
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
    def __init__(self, generated_images: list[_FakeGoogleGeneratedImage]) -> None:
        self.generated_images = generated_images


class _FakeGoogleModels:
    def generate_images(self, *, model: str, prompt: str, config):  # noqa: ARG002
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


def test_text_to_image_google_prefix_dispatch() -> None:
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
    assert all(img.provider == TextToImageProvider.GOOGLE for img in result.images)
    assert all(img.gcs_uri and img.gcs_uri.startswith("gs://") for img in result.images)
    assert all(
        img.public_url and img.public_url.startswith("https://storage.googleapis.com/")
        for img in result.images
    )


def test_text_to_image_falai_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_subscribe(model: str, arguments: dict, with_logs: bool = False):  # noqa: ARG001
        assert model == "fal-ai/z-image/turbo"
        assert arguments["prompt"] == "A cute cat sitting on a sofa"
        assert arguments["num_images"] == 2
        return {
            "images": [
                {
                    "url": "https://fal.example/1.png",
                    "width": 1024,
                    "height": 768,
                    "content_type": "image/png",
                },
                {
                    "url": "https://fal.example/2.png",
                    "width": 1024,
                    "height": 768,
                    "content_type": "image/png",
                },
            ],
            "seed": 42,
            "prompt": arguments["prompt"],
            "has_nsfw_concepts": [False, False],
        }

    monkeypatch.setattr("app.external_services.fal_ai.fal_client.subscribe", fake_subscribe)

    result = generate_text_to_image(
        TextToImageGenerationRequest(
            model="fal-ai/z-image/turbo",
            prompt="A cute cat sitting on a sofa",
            num_images=2,
            seed=42,
            provider_args={"image_size": "landscape_4_3", "output_format": "png"},
        )
    )

    assert result.provider == TextToImageProvider.FALAI
    assert result.model == "fal-ai/z-image/turbo"
    assert len(result.images) == 2
    assert all(img.provider == TextToImageProvider.FALAI for img in result.images)
    assert [img.url for img in result.images] == [
        "https://fal.example/1.png",
        "https://fal.example/2.png",
    ]

