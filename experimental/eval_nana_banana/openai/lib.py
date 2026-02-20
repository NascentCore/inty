"""
Minimal OpenAI Images Edit evaluation lib: generate (prompt + char/user avatar files) and save results.

Uses official OpenAI Python SDK client.images.edit() with multiple input images.
Auth via OPENAI_API_KEY (e.g. from .env).
"""

from __future__ import annotations

import base64
import datetime
import json
import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


def _get_client() -> OpenAI:
    """Return OpenAI client using OPENAI_API_KEY from environment (e.g. set by load_dotenv from .env)."""
    return OpenAI()


@dataclass
class OpenAIImageEditResult:
    """Result from a single images.edit call."""

    image_b64: str
    raw: Any


def _model_to_output_subdir(output_dir: str, model: str) -> str:
    """
    Map model name to output subpath. Use openai/<model> so outputs don't clash with Fal.
    E.g. "gpt-image-1.5" -> output_dir/openai/gpt-image-1.5
    """
    safe_model = model.replace("/", "_")
    return os.path.join(output_dir, "openai", safe_model)


def generate(
    prompt: str,
    model: str,
    char_avatar_path: str,
    user_avatar_path: str,
    *,
    size: str = "auto",
    n: int = 1,
    response_format: str = "b64_json",
) -> OpenAIImageEditResult:
    """
    Call OpenAI Images Edit with two reference images (char, user).
    SDK accepts image= as a list of file objects (up to 16 for GPT image models).
    Caller is responsible for timing and save_result_to_files.
    Note: openai 1.82.1 images.edit() does not support input_fidelity or output_format;
    use response_format='b64_json' to get base64 image data (we write as .jpeg).
    """
    client = _get_client()
    with open(char_avatar_path, "rb") as f1, open(user_avatar_path, "rb") as f2:
        response = client.images.edit(
            image=[f1, f2],
            prompt=prompt,
            model=model,
            n=n,
            size=size,
            response_format=response_format,
        )
    # GPT image models return base64 in data[0].b64_json
    data_list = getattr(response, "data", []) or []
    if not data_list:
        raise ValueError("OpenAI images.edit returned no data")
    first = data_list[0]
    b64_json = getattr(first, "b64_json", None)
    if not b64_json:
        raise ValueError("OpenAI response data[0] has no b64_json")
    return OpenAIImageEditResult(image_b64=b64_json, raw=response)


def save_result_to_files(
    result: OpenAIImageEditResult,
    files_prefix: str,
    duration: datetime.timedelta,
    model: str,
    output_dir: str = "tmp",
    *,
    prompt_preview: str | None = None,
) -> tuple[str, str]:
    """
    Decode result.image_b64, write image and JSON under output_dir/openai/<model>/.
    Returns (out_image path, out_json path).
    """
    model_dir = _model_to_output_subdir(output_dir, model)
    os.makedirs(model_dir, exist_ok=True)
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    stem = f"{files_prefix}_openai_output_{suffix}"
    out_image = os.path.join(model_dir, f"{stem}.jpeg")
    out_json = os.path.join(model_dir, f"{stem}.json")

    image_bytes = base64.standard_b64decode(result.image_b64)
    with open(out_image, "wb") as f:
        f.write(image_bytes)

    payload: dict[str, Any] = {
        "duration_seconds": duration.total_seconds(),
        "model": model,
    }
    if hasattr(result.raw, "model_dump"):
        try:
            payload["raw"] = result.raw.model_dump()
        except (TypeError, ValueError):
            payload["raw"] = str(result.raw)
    else:
        payload["raw"] = str(result.raw)
    if prompt_preview is not None:
        payload["prompt_preview"] = prompt_preview
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return out_image, out_json
