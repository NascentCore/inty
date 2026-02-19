"""
For each prompt file under tmp/scene_prompt_*.txt, read content and generate images via fal.
Use --model for fal model; use --image-url or --image-path for image-to-image (otherwise text-to-image).
If --image-path is set, the file is uploaded to fal CDN and the returned URL is used for generation.
Run from repo root so tmp/ is correct.
"""

from __future__ import annotations

import datetime
import glob
from typing import Annotated

import cyclopts
import fal_client

from dotenv import load_dotenv

load_dotenv()

from experimental.eval_nana_banana.fal.lib import generate, save_result_to_files

DEFAULT_MODEL = "fal-ai/flux-1.1-pro"


def main(
    model: Annotated[
        str,
        cyclopts.Parameter(help="fal model, e.g. fal-ai/flux-1.1-pro or fal-ai/gpt-image-1.5/edit"),
    ] = DEFAULT_MODEL,
    image_url: Annotated[
        str | None,
        cyclopts.Parameter(help="If set, use this URL for image-to-image (ignored if --image-path is set)"),
    ] = None,
    image_path: Annotated[
        str | None,
        cyclopts.Parameter(help="Local image path to upload to fal CDN and use for image-to-image (e.g. tests/files/nurse_char_full_body.jpeg)"),
    ] = None,
    output_dir: Annotated[
        str,
        cyclopts.Parameter(help="Output directory for images and JSON"),
    ] = "tmp",
) -> None:
    ref_url: str | None = image_url
    if image_path is not None:
        ref_url = fal_client.sync_client.upload_file(image_path)
        print(f"Uploaded {image_path} to fal CDN: {ref_url}")
    prompt_files = glob.glob("tmp/scene_prompt_*.txt")
    for prompt_file in prompt_files:
        files_prefix = prompt_file.split("/")[-1].split(".")[0]
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read()
        start_time = datetime.datetime.now()
        result = generate(prompt, model=model, image_url=ref_url)
        duration = datetime.datetime.now() - start_time
        save_result_to_files(result, files_prefix, duration, output_dir=output_dir)


if __name__ == "__main__":
    cyclopts.run(main)
