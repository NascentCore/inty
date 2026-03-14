#!/usr/bin/env python3
"""
List all chat-generated images, preview each locally, and ask Gemini 2.5 Flash Lite
how many characters are in the image (structured output { count: int }); display results.

Usage (from repo root):
    export PYTHONPATH=.
    python scripts/chat_image_gen_fallbacks_only_include_ai_character/check_chat_images_character_count.py --chat-images-json /path/to/studio_results.json
    python scripts/chat_image_gen_fallbacks_only_include_ai_character/check_chat_images_character_count.py --chat-images-json data.json --config devops/config.yaml.dev --limit 2 --no-preview
    python scripts/chat_image_gen_fallbacks_only_include_ai_character/check_chat_images_character_count.py --chat-images-json data.json --output-json results.json

Image list is read from JSON only (array of objects with gcs_uri or image_url, and optionally id, session_id, created_at).
"""

from __future__ import annotations

import asyncio
import io
import json
import shutil
import sys
from pathlib import Path
from typing import Annotated, Optional

import cyclopts
from google.genai import types as gemini_types
from loguru import logger
from PIL import Image
from pydantic import BaseModel

CONFIG_YAML = "config.yaml"


def _repo_root() -> Path:
    """仓库根目录（本脚本在 scripts/chat_image_gen_fallbacks_only_include_ai_character/ 下）。"""
    return Path(__file__).resolve().parent.parent.parent


def _ensure_config(config_path: Optional[str]) -> None:
    """若提供 --config 则复制到 cwd 的 config.yaml；否则要求 cwd 下已存在 config.yaml。"""
    cwd = Path.cwd()
    target = cwd / CONFIG_YAML
    if config_path:
        src = Path(config_path)
        if not src.is_absolute():
            src = _repo_root() / config_path
        if not src.exists():
            print(f"错误: 配置文件不存在: {src}", file=sys.stderr)
            sys.exit(1)
        shutil.copy2(src, target)
        logger.debug("已复制配置到 %s", target)
    else:
        if not target.exists():
            print(
                f"错误: 未指定 --config 且当前目录下不存在 {CONFIG_YAML}，请在仓库根目录运行或使用 --config PATH",
                file=sys.stderr,
            )
            sys.exit(1)


class CharacterCountResponse(BaseModel):
    """Structured output from Gemini: number of characters in the image."""

    count: int


async def _main(
    chat_images_json: Annotated[
        str,
        cyclopts.Parameter(
            name="--chat-images-json",
            help="JSON file path: array of objects with gcs_uri or image_url, and optionally id, session_id, created_at.",
        ),
    ],
    config: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--config",
            help="复制此 YAML 到当前目录 config.yaml 后再导入 app；不指定则要求已存在 config.yaml。",
        ),
    ] = None,
    no_preview: Annotated[
        bool,
        cyclopts.Parameter(
            name="--no-preview",
            help="Skip opening each image for preview; only download and call Gemini.",
        ),
    ] = False,
    limit: Annotated[
        Optional[int],
        cyclopts.Parameter(
            name="--limit",
            help="Process only the first N images (for testing).",
        ),
    ] = None,
    output_json: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--output-json",
            help="Write results to this JSON file.",
        ),
    ] = None,
) -> None:
    """Read image list from JSON, preview each, call Gemini for character count, display results."""
    _ensure_config(config)

    from app.utils.gemini import get_genai_client

    json_path = Path(chat_images_json)
    if not json_path.is_absolute():
        json_path = _repo_root() / chat_images_json
    if not json_path.exists():
        print(f"错误: JSON 文件不存在: {json_path}", file=sys.stderr)
        sys.exit(1)
    with open(json_path, encoding="utf-8") as f:
        items = json.load(f)
    if not isinstance(items, list):
        items = [items]
    rows = []
    for it in items:
        gcs_uri = it.get("gcs_uri") or it.get("image_url")
        if not gcs_uri:
            logger.warning("Entry missing gcs_uri, skip: {}", it.get("id"))
            continue
        rows.append(
            (
                str(it.get("id", "")),
                str(it.get("session_id", "")),
                gcs_uri,
                {},
                it.get("created_at"),
            )
        )
    total = len(rows)

    results: list[dict] = []
    client = get_genai_client()
    prompt_text = "How many characters are in the image?"
    config_gemini = gemini_types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=CharacterCountResponse,
    )

    if limit is not None:
        rows = rows[:limit]
    logger.debug("Found {} chat-generated images, processing {}", total, len(rows))

    for idx, row in enumerate(rows):
        message_id = row[0]
        session_id = row[1]
        image_url_raw = row[2]
        meta_data = row[3] or {}
        created_at = row[4]

        if not image_url_raw:
            logger.warning("Row id={} has empty image_url, skip", message_id)
            continue

        gcs_url = image_url_raw
        if gcs_url.startswith("gs://"):
            https_url = "https://storage.googleapis.com/" + gcs_url.removeprefix(
                "gs://"
            )
        else:
            https_url = gcs_url

        if not no_preview:
            try:
                import subprocess

                filename = (
                    f"image_{message_id}.{https_url.split('/')[-1].split('.')[-1]}"
                )
                subprocess.run(["wget", https_url, "-O", filename])
                image_bytes = open(filename, "rb").read()
                img = Image.open(io.BytesIO(image_bytes))
                img.show()
            except Exception as e:
                logger.warning("Preview failed for message_id={}: {}", message_id, e)

        meta_format = (
            (meta_data.get("generated_image") or {}).get("format")
            if meta_data
            else None
        )
        if not meta_format and gcs_url:
            meta_format = "png" if gcs_url.lower().endswith(".png") else "jpeg"
        mime_type = f"image/{meta_format or 'jpeg'}"

        contents = [
            gemini_types.Content(
                role="user",
                parts=[
                    gemini_types.Part.from_uri(file_uri=https_url, mime_type=mime_type),
                    gemini_types.Part.from_text(text=prompt_text),
                ],
            )
        ]

        response = None
        for attempt in range(3):
            try:
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model="gemini-2.5-flash-lite",
                    contents=contents,
                    config=config_gemini,
                )
                break
            except Exception as e:
                logger.warning(
                    "Gemini call failed for message_id={} (attempt {}/3): {}",
                    message_id,
                    attempt + 1,
                    e,
                )
                if attempt == 2:
                    continue
        if response is None:
            continue

        count_val: Optional[int] = None
        if (
            response.candidates
            and response.candidates[0].content
            and response.candidates[0].content.parts
        ):
            part = response.candidates[0].content.parts[0]
            text_out = getattr(part, "text", None) or ""
            if text_out.strip():
                try:
                    parsed = CharacterCountResponse.model_validate_json(text_out)
                    count_val = parsed.count
                except Exception as e:
                    logger.debug("Parse structured output failed: {}", e)

        if count_val is None:
            count_val = -1
        one_character = count_val == 1

        created_at_iso = (
            (created_at.isoformat() if hasattr(created_at, "isoformat") else created_at)
            if created_at
            else None
        )
        record = {
            "message_id": message_id,
            "session_id": session_id,
            "image_url": https_url,
            "count": count_val,
            "one_character": one_character,
            "created_at": created_at_iso,
        }
        results.append(record)

        print(
            f"[{idx + 1}/{len(rows)}] message_id={message_id} session_id={session_id} https_url={https_url} "
            f"count={count_val} one_character={one_character}"
        )

    if output_json:
        out_path = Path(output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(results)} results to {out_path}")

    print(f"Done. Processed {len(results)} images (total in JSON: {total}).")


def main(
    chat_images_json: Annotated[
        str,
        cyclopts.Parameter(
            name="--chat-images-json",
            help="JSON file path: array of objects with gcs_uri or image_url, and optionally id, session_id, created_at.",
        ),
    ],
    config: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--config",
            help="复制此 YAML 到当前目录 config.yaml 后再导入 app；不指定则要求已存在 config.yaml。",
        ),
    ] = None,
    no_preview: Annotated[
        bool,
        cyclopts.Parameter(
            name="--no-preview",
            help="Skip opening each image for preview; only download and call Gemini.",
        ),
    ] = False,
    limit: Annotated[
        Optional[int],
        cyclopts.Parameter(
            name="--limit",
            help="Process only the first N images (for testing).",
        ),
    ] = None,
    output_json: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--output-json",
            help="Write results to this JSON file.",
        ),
    ] = None,
) -> None:
    """Sync entrypoint: parse args and run async _main."""
    asyncio.run(
        _main(
            chat_images_json=chat_images_json,
            config=config,
            no_preview=no_preview,
            limit=limit,
            output_json=output_json,
        )
    )


if __name__ == "__main__":
    app = cyclopts.App(
        help="List chat-generated images, preview each, ask Gemini 2.5 Flash Lite for character count, display results."
    )
    app.default(main)
    app()
