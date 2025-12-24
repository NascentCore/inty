"""
fal.ai text-to-image client wrapper.

This module is intentionally NOT integrated into Inty backend flows yet.

CREATED_BY_AGENT
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

import fal_client


FAL_API_KEY_ENV_VAR = "FAL_KEY"


@dataclass(frozen=True, slots=True)
class FalGeneratedImage:
    url: str
    width: int | None = None
    height: int | None = None
    content_type: str | None = None


@dataclass(frozen=True, slots=True)
class FalTextToImageResult:
    images: list[FalGeneratedImage]
    seed: int | None
    prompt: str | None
    has_nsfw_concepts: list[bool] | None
    raw: dict[str, Any]


class FalAIClient:
    """
    Minimal fal.ai client wrapper using the official `fal_client` package.

    Auth is typically supplied via `FAL_KEY` env var as in fal.ai docs. You may also
    pass `api_key` explicitly which will be set to the env var for this process.
    """

    def __init__(self, *, api_key: Optional[str] = None) -> None:
        if api_key:
            os.environ[FAL_API_KEY_ENV_VAR] = api_key

    def text_to_image(
        self,
        *,
        model: str,
        arguments: dict[str, Any],
        with_logs: bool = False,
    ) -> FalTextToImageResult:
        result = fal_client.subscribe(model, arguments=arguments, with_logs=with_logs)
        return _parse_fal_text_to_image_result(result)


def _parse_fal_text_to_image_result(result: dict[str, Any]) -> FalTextToImageResult:
    images: list[FalGeneratedImage] = []
    for img in result.get("images", []) or []:
        if not isinstance(img, dict) or "url" not in img:
            continue
        images.append(
            FalGeneratedImage(
                url=str(img["url"]),
                width=img.get("width"),
                height=img.get("height"),
                content_type=img.get("content_type"),
            )
        )

    seed = result.get("seed")
    prompt = result.get("prompt")
    has_nsfw_concepts = result.get("has_nsfw_concepts")
    if has_nsfw_concepts is not None and not isinstance(has_nsfw_concepts, list):
        has_nsfw_concepts = None

    return FalTextToImageResult(
        images=images,
        seed=seed if isinstance(seed, int) else None,
        prompt=prompt if isinstance(prompt, str) else None,
        has_nsfw_concepts=has_nsfw_concepts,
        raw=result,
    )


__all__ = [
    "FAL_API_KEY_ENV_VAR",
    "FalAIClient",
    "FalGeneratedImage",
    "FalTextToImageResult",
]
