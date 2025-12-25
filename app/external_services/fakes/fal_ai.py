"""
Fake fal.ai client for tests.

CREATED_BY_AGENT
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


DEFAULT_CONTENT_TYPE = "image/png"
DEFAULT_WIDTH = 64
DEFAULT_HEIGHT = 64


@dataclass(frozen=True, slots=True)
class FakeFalGeneratedImage:
    url: str
    width: int
    height: int
    content_type: str


@dataclass(frozen=True, slots=True)
class FakeFalTextToImageResult:
    images: list[FakeFalGeneratedImage]
    seed: int
    prompt: str
    raw: dict[str, Any]


class FakeFalAIClient:
    """
    A lightweight in-memory fake for `FalAIClient`.

    It returns deterministic, local-looking URLs that are suitable for unit tests.
    """

    def __init__(self, *, seed: int = 0) -> None:
        self._seed = seed

    def text_to_image(
        self,
        *,
        model: str,
        arguments: dict[str, Any],
        with_logs: bool = False,  # noqa: ARG002 - kept for signature compatibility
    ) -> FakeFalTextToImageResult:
        prompt = str(arguments.get("prompt") or "")
        num_images = int(arguments.get("num_images") or 1)

        images: list[FakeFalGeneratedImage] = []
        for _ in range(num_images):
            images.append(
                FakeFalGeneratedImage(
                    url=f"https://fal.fake/{model}/{uuid.uuid4().hex}.png",
                    width=int(arguments.get("width") or DEFAULT_WIDTH),
                    height=int(arguments.get("height") or DEFAULT_HEIGHT),
                    content_type=str(
                        arguments.get("content_type") or DEFAULT_CONTENT_TYPE
                    ),
                )
            )

        raw = {
            "images": [
                {
                    "url": image.url,
                    "width": image.width,
                    "height": image.height,
                    "content_type": image.content_type,
                }
                for image in images
            ],
            "seed": self._seed,
            "prompt": prompt,
        }
        return FakeFalTextToImageResult(
            images=images, seed=self._seed, prompt=prompt, raw=raw
        )


__all__ = [
    "FakeFalAIClient",
    "FakeFalGeneratedImage",
    "FakeFalTextToImageResult",
]
