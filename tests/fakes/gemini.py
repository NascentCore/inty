from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from PIL import Image


@dataclass
class _FakeGeneratedImageResponse:
    generated_images: List["_FakeGeneratedImage"]


@dataclass
class _FakeGeneratedImage:
    image: "_FakeGeneratedImageContent"
    rai_filtered_reason: Optional[str]
    enhanced_prompt: str


@dataclass
class _FakeGeneratedImageContent:
    gcs_uri: str


class _FakeGeminiModels:
    def __init__(self, client: "FakeGeminiClient") -> None:
        self._client = client

    def generate_images(self, *, model: str, prompt: str, config):
        return self._client._generate_images(model=model, prompt=prompt, config=config)


class FakeGeminiClient:
    """
    A lightweight fake of the Gemini image generation client for tests.

    It mimics the subset of the google.genai client interface that our code
    relies on:
      * client.models.generate_images(...)
      * GeneratedImage objects exposing .image.gcs_uri, .rai_filtered_reason,
        and .enhanced_prompt

    The fake stores generated image bytes in-memory so that callers patched
    through download_from_gcs() can retrieve them via download_image().
    """

    def __init__(self) -> None:
        self.models = _FakeGeminiModels(self)
        self._generated_bytes: Dict[str, bytes] = {}
        self._call_index = 0

    def _generate_images(self, *, model: str, prompt: str, config):
        gcs_base = getattr(config, "output_gcs_uri", "gs://fake-bucket/generated")
        count = int(getattr(config, "number_of_images", 1) or 1)
        generated_images: List[_FakeGeneratedImage] = []

        for index in range(count):
            gcs_uri = self._build_gcs_uri(gcs_base, index)
            https_uri = self._convert_to_https(gcs_uri)
            self._generated_bytes[https_uri] = self._make_image_bytes(index)
            generated_images.append(
                _FakeGeneratedImage(
                    image=_FakeGeneratedImageContent(gcs_uri=gcs_uri),
                    rai_filtered_reason=None,
                    enhanced_prompt=prompt,
                )
            )

        self._call_index += 1
        return _FakeGeneratedImageResponse(generated_images=generated_images)

    def download_image(self, url: str) -> bytes:
        """
        Return the fake image bytes for the provided URL.
        """
        if url not in self._generated_bytes:
            raise KeyError(f"No fake image registered for URL: {url}")
        return self._generated_bytes[url]

    def _build_gcs_uri(self, base: str, index: int) -> str:
        normalized = base.rstrip("/")
        uid = uuid.uuid4().hex
        return f"{normalized}/fake_image_{self._call_index}_{index}_{uid}.jpeg"

    @staticmethod
    def _convert_to_https(gcs_uri: str) -> str:
        if gcs_uri.startswith("gs://"):
            path = gcs_uri[5:]
            return f"https://storage.googleapis.com/{path}"
        return gcs_uri

    @staticmethod
    def _make_image_bytes(index: int) -> bytes:
        image = Image.new(
            "RGB",
            (64, 64),
            color=((index * 40) % 255, (index * 70) % 255, (index * 110) % 255),
        )
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        return buffer.getvalue()


__all__ = ["FakeGeminiClient"]
