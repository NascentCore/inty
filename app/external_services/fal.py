"""
fal.ai unified client wrapper (image / tts / video).

说明：
- 该模块封装官方 `fal_client`，并提供尽量“宽松”的结果解析，以兼容不同模型的返回结构差异。
- 上层可以直接传入 fal 的 `model`（如 "fal-ai/xxx"）与 `arguments` 字典。
- Auth 通常通过环境变量 `FAL_KEY` 注入（与 fal 官方一致）。

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


@dataclass(frozen=True, slots=True)
class FalGeneratedAudio:
    url: str
    content_type: str | None = None


@dataclass(frozen=True, slots=True)
class FalTextToSpeechResult:
    audio: FalGeneratedAudio | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FalGeneratedVideo:
    url: str
    content_type: str | None = None


@dataclass(frozen=True, slots=True)
class FalTextToVideoResult:
    videos: list[FalGeneratedVideo]
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

    def subscribe(
        self, *, model: str, arguments: dict[str, Any], with_logs: bool = False
    ) -> dict[str, Any]:
        result = fal_client.subscribe(model, arguments=arguments, with_logs=with_logs)
        if not isinstance(result, dict):
            raise TypeError(f"fal_client.subscribe returned non-dict: {type(result)}")
        return result

    def text_to_image(
        self,
        *,
        model: str,
        arguments: dict[str, Any],
        with_logs: bool = False,
    ) -> FalTextToImageResult:
        return _parse_fal_text_to_image_result(
            self.subscribe(model=model, arguments=arguments, with_logs=with_logs)
        )

    def text_to_speech(
        self,
        *,
        model: str,
        arguments: dict[str, Any],
        with_logs: bool = False,
    ) -> FalTextToSpeechResult:
        return _parse_fal_text_to_speech_result(
            self.subscribe(model=model, arguments=arguments, with_logs=with_logs)
        )

    def text_to_video(
        self,
        *,
        model: str,
        arguments: dict[str, Any],
        with_logs: bool = False,
    ) -> FalTextToVideoResult:
        return _parse_fal_text_to_video_result(
            self.subscribe(model=model, arguments=arguments, with_logs=with_logs)
        )


def is_fal_model(model: Optional[str]) -> bool:
    if not model:
        return False
    normalized = model.strip().lower()
    return normalized.startswith("fal-ai/") or normalized.startswith("fal/")


def _parse_fal_text_to_image_result(result: dict[str, Any]) -> FalTextToImageResult:
    images: list[FalGeneratedImage] = []
    for img in (result.get("images", []) or []) if isinstance(result, dict) else []:
        if not isinstance(img, dict) or "url" not in img:
            continue
        images.append(
            FalGeneratedImage(
                url=str(img["url"]),
                width=img.get("width") if isinstance(img.get("width"), int) else None,
                height=img.get("height") if isinstance(img.get("height"), int) else None,
                content_type=img.get("content_type")
                if isinstance(img.get("content_type"), str)
                else None,
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


def _parse_fal_text_to_speech_result(result: dict[str, Any]) -> FalTextToSpeechResult:
    audio_url: Optional[str] = None
    content_type: Optional[str] = None

    # Common shapes:
    # - {"audio_url": "..."}
    # - {"audio": {"url": "...", "content_type": "audio/wav"}}
    # - {"url": "...", "content_type": "..."}  (rare, but be defensive)
    if isinstance(result.get("audio_url"), str):
        audio_url = result["audio_url"]
    elif isinstance(result.get("audio"), dict):
        audio = result["audio"]
        if isinstance(audio.get("url"), str):
            audio_url = audio["url"]
        if isinstance(audio.get("content_type"), str):
            content_type = audio["content_type"]
    elif isinstance(result.get("url"), str):
        audio_url = result["url"]
        if isinstance(result.get("content_type"), str):
            content_type = result["content_type"]

    audio = (
        FalGeneratedAudio(url=audio_url, content_type=content_type)
        if audio_url
        else None
    )
    return FalTextToSpeechResult(audio=audio, raw=result)


def _parse_fal_text_to_video_result(result: dict[str, Any]) -> FalTextToVideoResult:
    videos: list[FalGeneratedVideo] = []

    # Common shapes:
    # - {"video": {"url": "..."}}
    # - {"videos": [{"url": "..."}, ...]}
    if isinstance(result.get("videos"), list):
        for item in result["videos"]:
            if not isinstance(item, dict) or not isinstance(item.get("url"), str):
                continue
            videos.append(
                FalGeneratedVideo(
                    url=item["url"],
                    content_type=item.get("content_type")
                    if isinstance(item.get("content_type"), str)
                    else None,
                )
            )
    elif isinstance(result.get("video"), dict):
        item = result["video"]
        if isinstance(item.get("url"), str):
            videos.append(
                FalGeneratedVideo(
                    url=item["url"],
                    content_type=item.get("content_type")
                    if isinstance(item.get("content_type"), str)
                    else None,
                )
            )
        elif isinstance(item.get("uri"), str):
            videos.append(FalGeneratedVideo(url=item["uri"], content_type=None))

    return FalTextToVideoResult(videos=videos, raw=result)


__all__ = [
    "FAL_API_KEY_ENV_VAR",
    "FalAIClient",
    "FalGeneratedAudio",
    "FalGeneratedImage",
    "FalGeneratedVideo",
    "FalTextToImageResult",
    "FalTextToSpeechResult",
    "FalTextToVideoResult",
    "is_fal_model",
]

