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

from experimental.fal_ai.fal import (
    DEFAULT_GPT_IMAGE_1_5_EDIT_CONFIG,
    DEFAULT_SEEDREAM_V4_5_EDIT_CONFIG,
    IMAGE_SIZE_PORTRAIT_16_9,
    FalAIClient,
    FalTextToImageResult,
    GPTImage1_5EditGenConfig,
    SeedreamV4_5EditGenConfig,
)


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
    gpt_image_1_5_edit_config: GPTImage1_5EditGenConfig | None = None,
    seedream_v4_5_edit_config: SeedreamV4_5EditGenConfig | None = None,
) -> FalTextToImageResult:
    """
    Generate image via fal image-to-image using char and user avatar URLs.
    For gpt-image-1.5/edit uses GPTImage1_5EditGenConfig so image_size is valid (never portrait_16_9).
    For seedream v4.5 edit uses SeedreamV4_5EditGenConfig. Other models (e.g. fal-ai/fast-sdxl) use
    extra_args with image_size/output_format; enable_safety_checker is passed for models that support it.
    Caller is responsible for timing and calling save_result_to_files.
    """
    client = FalAIClient()
    model_lower = model.lower()
    if "gpt-image" in model_lower:
        config = gpt_image_1_5_edit_config or DEFAULT_GPT_IMAGE_1_5_EDIT_CONFIG
        return client.image_to_image(
            model=model,
            image_urls=[char_avatar_url, user_avatar_url],
            prompt=prompt,
            num_images=config.num_images,
            gpt_image_1_5_edit_config=config,
            extra_args={"enable_safety_checker": False},
        )
    if "seedream" in model_lower:
        config = seedream_v4_5_edit_config or SeedreamV4_5EditGenConfig(
            num_images=num_images,
            image_size=image_size,
            output_format=output_format,
        )
        return client.image_to_image(
            model=model,
            image_urls=[char_avatar_url, user_avatar_url],
            prompt=prompt,
            num_images=config.num_images,
            seedream_v4_5_edit_config=config,
        )
    extra: dict[str, Any] = {
        "image_size": image_size,
        "output_format": output_format,
        "enable_safety_checker": False,
    }
    return client.image_to_image(
        model=model,
        image_urls=[char_avatar_url, user_avatar_url],
        prompt=prompt,
        strength=strength,
        num_images=num_images,
        extra_args=extra,
    )


def _model_to_output_subdir(output_dir: str, model: str) -> str:
    """
    Map model name to output subpath: slashes in model become subdirs.
    E.g. "fal-ai/gpt-image-1.5/edit" -> output_dir/fal-ai/gpt-image-1.5/edit
    """
    parts = [output_dir, *model.split("/")]
    return os.path.join(*parts)


def save_result_to_files(
    fal_result: FalTextToImageResult,
    files_prefix: str,
    duration: datetime.timedelta,
    model: str,
    output_dir: str = "tmp",
) -> tuple[str, str]:
    """
    Download first image from fal_result.images[0].url, write JSON with raw + duration + model.
    Both files are saved under output_dir/<model_path>, where model_path is the model name
    with "/" turned into subdirs (e.g. fal-ai/gpt-image-1.5/edit).
    Returns (out_image path, out_json path). The saved JSON includes the fal model name.
    """
    model_dir = _model_to_output_subdir(output_dir, model)
    os.makedirs(model_dir, exist_ok=True)
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    files_stem = f"{files_prefix}_fal_output_{suffix}"
    out_image = os.path.join(model_dir, f"{files_stem}.jpeg")
    out_json = os.path.join(model_dir, f"{files_stem}.json")

    if not fal_result.images:
        raise ValueError("fal_result has no images")
    first_url = fal_result.images[0].url
    req = urllib.request.Request(
        first_url, headers={"User-Agent": "inty-eval-fal/1"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        image_data = resp.read()
    with open(out_image, "wb") as f:
        f.write(image_data)
    print(f"Saved image to {out_image} for files_prefix: {files_prefix}")

    payload: dict[str, Any] = dict(fal_result.raw)
    payload["duration_seconds"] = duration.total_seconds()
    payload["model"] = model
    if fal_result.prompt is not None:
        payload["prompt"] = fal_result.prompt
    if fal_result.seed is not None:
        payload["seed"] = fal_result.seed
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Saved response JSON to {out_json} for files_prefix: {files_prefix}")
    return out_image, out_json
