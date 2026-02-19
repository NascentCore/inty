"""
Minimal fal.ai evaluation lib: generate (text-to-image or image-to-image) and save results to files.

Uses app.external_services.fal.FalAIClient. Auth via FAL_KEY or explicit api_key.
"""

from __future__ import annotations

import datetime
import json
import os
import urllib.request
from typing import Any

from app.external_services.fal import IMAGE_SIZE_PORTRAIT_16_9, FalAIClient, FalTextToImageResult

def generate(
    prompt: str,
    model: str,
    char_avatar_url: str,
    user_avatar_url: str,
    *,
    strength: float = 0.75,
    num_images: int = 1,
    image_size: str = IMAGE_SIZE_PORTRAIT_16_9,
    output_format: str = "jpeg",
) -> FalTextToImageResult:
    """
    Generate image via fal image-to-image using char and user avatar URLs.
    Caller is responsible for timing and calling save_result_to_files.
    """
    client = FalAIClient()
    extra = {"image_size": image_size, "output_format": output_format}
    return client.image_to_image(
        model=model,
        image_urls=[char_avatar_url, user_avatar_url],
        prompt=prompt,
        strength=strength,
        num_images=num_images,
        extra_args=extra,
    )


def save_result_to_files(
    fal_result: FalTextToImageResult,
    files_prefix: str,
    duration: datetime.timedelta,
    output_dir: str = "tmp",
) -> tuple[str, str]:
    """
    Download first image from fal_result.images[0].url to output_dir, write JSON with raw + duration.
    Returns (out_image path, out_json path).
    """
    os.makedirs(output_dir, exist_ok=True)
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    files_stem = f"{files_prefix}_fal_output_{suffix}"
    out_image = os.path.join(output_dir, f"{files_stem}.jpeg")
    out_json = os.path.join(output_dir, f"{files_stem}.json")

    if not fal_result.images:
        raise ValueError("fal_result has no images")
    first_url = fal_result.images[0].url
    req = urllib.request.Request(first_url, headers={"User-Agent": "inty-eval-fal/1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        image_data = resp.read()
    with open(out_image, "wb") as f:
        f.write(image_data)
    print(f"Saved image to {out_image} for files_prefix: {files_prefix}")

    payload: dict[str, Any] = dict(fal_result.raw)
    payload["duration_seconds"] = duration.total_seconds()
    if fal_result.prompt is not None:
        payload["prompt"] = fal_result.prompt
    if fal_result.seed is not None:
        payload["seed"] = fal_result.seed
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Saved response JSON to {out_json} for files_prefix: {files_prefix}")
    return out_image, out_json
