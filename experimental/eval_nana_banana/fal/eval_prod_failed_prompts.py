"""
For each prompt file under tmp/scene_prompt_*.txt, read content and generate images via fal (image-to-image).
Uses default char/user avatar files (uploaded to fal CDN). Use --model to choose fal model.
On fal error (e.g. 422 content_policy_violation): print response, save full error JSON, then continue.
Run from repo root so tmp/ and tests/files/ paths are correct.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
from typing import Annotated, Any

import cyclopts
import fal_client
from fal_client.client import FalClientHTTPError

from dotenv import load_dotenv

load_dotenv()

from experimental.eval_nana_banana.fal.lib import (
    _model_to_output_subdir,
    generate,
    save_result_to_files,
)

DEFAULT_MODEL = "fal-ai/flux-1.1-pro"
PROMPT_PREVIEW_MAX_CHARS = 1000


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
    """Write error payload under output_dir/<model_subdir>/{files_prefix}_fal_output_{suffix}_error.json. Returns path."""
    model_dir = _model_to_output_subdir(output_dir, model)
    os.makedirs(model_dir, exist_ok=True)
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    stem = f"{files_prefix}_fal_output_{suffix}_error"
    path = os.path.join(model_dir, f"{stem}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_json_safe(error_payload), f, indent=2, ensure_ascii=False)
    return path


# DEFAULT_CHAR_AVATAR_PATH = "tests/files/nurse_char_full_body.jpg"
DEFAULT_CHAR_AVATAR_PATH = "tests/files/nurse_char.jpg"
DEFAULT_USER_AVATAR_PATH = "tests/files/zunlong.jpg"


def upload_file(path: str) -> str:
    return fal_client.sync_client.upload_file(path)


def main(
    model: Annotated[
        str,
        cyclopts.Parameter(
            help="fal model, e.g. fal-ai/flux-1.1-pro or fal-ai/gpt-image-1.5/edit"
        ),
    ] = DEFAULT_MODEL,
    output_dir: Annotated[
        str,
        cyclopts.Parameter(help="Output directory for images and JSON"),
    ] = "tmp",
) -> None:
    char_avatar_url = upload_file(DEFAULT_CHAR_AVATAR_PATH)
    user_avatar_url = upload_file(DEFAULT_USER_AVATAR_PATH)
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
                char_avatar_url=char_avatar_url,
                user_avatar_url=user_avatar_url,
            )
            duration = datetime.datetime.now() - start_time
            save_result_to_files(
                result,
                files_prefix,
                duration,
                model=model,
                output_dir=output_dir,
            )
        except (FalClientHTTPError, ValueError) as e:
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
            if hasattr(e, "body"):
                error_payload["body"] = e.body
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_payload["response_json"] = (
                        e.response.json()
                        if hasattr(e.response, "json")
                        else str(e.response)
                    )
                except (ValueError, TypeError, AttributeError, OSError):
                    error_payload["response_raw"] = str(e.response)
            print(repr(e))
            out_path = _save_error_json(
                output_dir, model, files_prefix, error_payload
            )
            print(
                f"Saved error JSON to {out_path} for {files_prefix}, continuing."
            )
            continue


if __name__ == "__main__":
    cyclopts.run(main)
