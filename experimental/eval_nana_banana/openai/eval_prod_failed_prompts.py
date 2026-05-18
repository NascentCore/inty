"""
For each prompt file under tmp/scene_prompt_*.txt, read content and generate images via OpenAI Images Edit (gpt-image-1.5).
Uses default char/user avatar files (local paths). Use --model to choose model.
On OpenAI API error: print response, save full error JSON, then continue.
Run from repo root so tmp/ and tests/files/ paths are correct.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
from typing import Annotated, Any

import cyclopts
from dotenv import load_dotenv
from openai import APIError, APIConnectionError, APITimeoutError

load_dotenv()

from experimental.eval_nana_banana.openai.lib import (
    _model_to_output_subdir,
    generate,
    save_result_to_files,
)

DEFAULT_MODEL = "gpt-image-1.5"
PROMPT_PREVIEW_MAX_CHARS = 1000

DEFAULT_CHAR_AVATAR_PATH = "tests/files/nurse_char.jpg"
DEFAULT_USER_AVATAR_PATH = "tests/files/zunlong.jpg"


def _json_safe(val: Any) -> Any:
    """Recursively make value JSON-serializable (e.g. exception args)."""
    if val is None or isinstance(val, (bool, int, float, str)):
        return val
    if isinstance(val, (list, tuple)):
        return [_json_safe(x) for x in val]
    if isinstance(val, dict):
        return {str(k): _json_safe(v) for k, v in val.items()}
    return str(val)


def _save_error_json(
    output_dir: str,
    model: str,
    files_prefix: str,
    error_payload: dict,
) -> str:
    """Write error payload under output_dir/openai/<model>/{files_prefix}_openai_output_{suffix}_error.json. Returns path."""
    model_dir = _model_to_output_subdir(output_dir, model)
    os.makedirs(model_dir, exist_ok=True)
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    stem = f"{files_prefix}_openai_output_{suffix}_error"
    path = os.path.join(model_dir, f"{stem}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_json_safe(error_payload), f, indent=2, ensure_ascii=False)
    return path


def main(
    model: Annotated[
        str,
        cyclopts.Parameter(help="OpenAI image model, e.g. gpt-image-1.5"),
    ] = DEFAULT_MODEL,
    output_dir: Annotated[
        str,
        cyclopts.Parameter(help="Output directory for images and JSON"),
    ] = "tmp",
    char_avatar_path: Annotated[
        str,
        cyclopts.Parameter(help="Path to character avatar image"),
    ] = DEFAULT_CHAR_AVATAR_PATH,
    user_avatar_path: Annotated[
        str,
        cyclopts.Parameter(help="Path to user avatar image"),
    ] = DEFAULT_USER_AVATAR_PATH,
) -> None:
    prompt_files = sorted(glob.glob("tmp/scene_prompt_*.txt"))
    for prompt_file in prompt_files:
        files_prefix = os.path.splitext(os.path.basename(prompt_file))[0]
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read()
        start_time = datetime.datetime.now()
        try:
            result = generate(
                prompt,
                model=model,
                char_avatar_path=char_avatar_path,
                user_avatar_path=user_avatar_path,
            )
            duration = datetime.datetime.now() - start_time
            save_result_to_files(
                result,
                files_prefix,
                duration,
                model=model,
                output_dir=output_dir,
                prompt_preview=(
                    prompt[:PROMPT_PREVIEW_MAX_CHARS] if prompt else None
                ),
            )
            print(f"Saved image and JSON for {files_prefix}")
        except (APIError, APIConnectionError, APITimeoutError, ValueError) as e:
            duration = datetime.datetime.now() - start_time
            error_payload = {
                "error": True,
                "exception_type": type(e).__name__,
                "message": str(e),
                "args": _json_safe(list(e.args)),
                "prompt_file": prompt_file,
                "files_prefix": files_prefix,
                "duration_seconds": duration.total_seconds(),
                "prompt_preview": (
                    prompt[:PROMPT_PREVIEW_MAX_CHARS] if prompt else None
                ),
            }
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_payload["response_json"] = (
                        e.response.json()
                        if hasattr(e.response, "json")
                        else str(e.response)
                    )
                except (ValueError, TypeError, AttributeError, OSError):
                    error_payload["response_raw"] = str(e.response)
            if hasattr(e, "body"):
                error_payload["body"] = e.body
            print(repr(e))
            out_path = _save_error_json(
                output_dir, model, files_prefix, error_payload
            )
            print(
                f"Saved error JSON to {out_path} for {files_prefix}, continuing."
            )


if __name__ == "__main__":
    cyclopts.run(main)
