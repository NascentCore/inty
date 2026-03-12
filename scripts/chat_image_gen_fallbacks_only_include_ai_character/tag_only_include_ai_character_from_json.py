#!/usr/bin/env python3
"""
Tag existing one-character chat images as fallback candidates by setting
resource_metadata.only_include_ai_character = True on the corresponding Resource rows.

Reads a JSON file (e.g. output of check_chat_images_character_count.py with one_character
field), filters to entries with one_character is True, maps each image_url to GCS URI,
and updates the Resource row if found.

Test with one image: run with --limit 1, then run the manual check in
scripts/chat_image_gen_fallbacks_only_include_ai_character/verify_only_include_ai_character_fallback.py.

Usage (from repo root):
    export PYTHONPATH=.
    python scripts/chat_image_gen_fallbacks_only_include_ai_character/tag_only_include_ai_character_from_json.py --chat-images-json only-include-imate.json --config devops/config.yaml.dev --dry-run
    python scripts/chat_image_gen_fallbacks_only_include_ai_character/tag_only_include_ai_character_from_json.py --chat-images-json only-include-imate.json --config devops/config.yaml.dev --limit 1
    python scripts/chat_image_gen_fallbacks_only_include_ai_character/tag_only_include_ai_character_from_json.py --chat-images-json only-include-imate.json --config devops/config.yaml.dev --yes
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from pathlib import Path
from typing import Annotated, Optional

import cyclopts
from loguru import logger
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.resource import Resource, ResourceType

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


def image_url_to_gcs_uri(image_url: str) -> str:
    """Convert https://storage.googleapis.com/bucket/path to gs://bucket/path."""
    if not image_url:
        return ""
    if image_url.startswith("gs://"):
        return image_url
    prefix = "https://storage.googleapis.com/"
    if image_url.startswith(prefix):
        return "gs://" + image_url[len(prefix) :]
    return ""


async def _run(
    chat_images_json: Annotated[
        str,
        cyclopts.Parameter(
            name="--chat-images-json",
            help="JSON file path: array of objects with image_url and one_character.",
        ),
    ],
    config: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--config",
            help="复制此 YAML 到当前目录 config.yaml 后再导入 app；不指定则要求已存在 config.yaml。",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        cyclopts.Parameter(
            name="--dry-run",
            help="Only log what would be updated; do not commit.",
        ),
    ] = False,
    limit: Annotated[
        Optional[int],
        cyclopts.Parameter(
            name="--limit",
            help="Process only the first N entries with one_character=true.",
        ),
    ] = None,
    yes: Annotated[
        bool,
        cyclopts.Parameter(
            name="--yes",
            help="Skip confirmation prompt when not in dry-run.",
        ),
    ] = False,
) -> None:
    _ensure_config(config)

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

    one_character_entries = [it for it in items if it.get("one_character") is True]
    total = len(one_character_entries)
    if limit is not None:
        one_character_entries = one_character_entries[:limit]
    to_process = len(one_character_entries)

    if total == 0:
        print("No entries with one_character=true in JSON.", file=sys.stderr)
        return

    if not dry_run and not yes:
        print(
            f"About to update up to {to_process} resources (total with one_character=true: {total}). Proceed? [y/N] ",
            end="",
        )
        if input().strip().lower() != "y":
            print("Aborted.")
            return

    stats = {"found": 0, "updated": 0, "not_found": 0, "error": 0}

    async with AsyncSessionLocal() as db:
        for it in one_character_entries:
            image_url = it.get("image_url") or it.get("gcs_uri")
            if not image_url:
                logger.warning(
                    "Entry missing image_url, skip: {}", it.get("message_id")
                )
                continue
            gcs_uri = image_url_to_gcs_uri(image_url)
            if not gcs_uri:
                logger.warning("Could not convert to GCS URI: {}", image_url)
                stats["error"] += 1
                continue

            result = await db.execute(
                select(Resource).where(
                    Resource.url == gcs_uri,
                    Resource.type == ResourceType.IMAGE,
                )
            )
            resource = result.scalar_one_or_none()
            if not resource:
                logger.debug("Resource not found: {}", gcs_uri)
                stats["not_found"] += 1
                continue
            stats["found"] += 1

            meta = dict(resource.resource_metadata or {})
            if meta.get("only_include_ai_character") is True:
                logger.debug("Already tagged: {}", gcs_uri)
                stats["updated"] += 1
                continue
            meta["only_include_ai_character"] = True
            if dry_run:
                logger.debug(
                    "[dry-run] would set only_include_ai_character=True: {}", gcs_uri
                )
                stats["updated"] += 1
                continue
            resource.resource_metadata = meta
            db.add(resource)
            await db.commit()
            logger.debug("Updated: {}", gcs_uri)
            stats["updated"] += 1

    print(
        f"Done. one_character=true in JSON: {total}; processed: {to_process}; "
        f"found: {stats['found']}, updated: {stats['updated']}, not_found: {stats['not_found']}, error: {stats['error']}"
    )
    if dry_run:
        print("(dry-run: no changes committed)")


def run(
    chat_images_json: Annotated[
        str,
        cyclopts.Parameter(
            name="--chat-images-json",
            help="JSON file path: array of objects with image_url and one_character.",
        ),
    ],
    config: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--config",
            help="复制此 YAML 到当前目录 config.yaml 后再导入 app；不指定则要求已存在 config.yaml。",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        cyclopts.Parameter(
            name="--dry-run",
            help="Only log what would be updated; do not commit.",
        ),
    ] = False,
    limit: Annotated[
        Optional[int],
        cyclopts.Parameter(
            name="--limit",
            help="Process only the first N entries with one_character=true.",
        ),
    ] = None,
    yes: Annotated[
        bool,
        cyclopts.Parameter(
            name="--yes",
            help="Skip confirmation prompt when not in dry-run.",
        ),
    ] = False,
) -> None:
    """Sync entrypoint: parse args and run async _run."""
    asyncio.run(
        _run(
            chat_images_json=chat_images_json,
            config=config,
            dry_run=dry_run,
            limit=limit,
            yes=yes,
        )
    )


if __name__ == "__main__":
    app = cyclopts.App(
        help="Tag one-character images in Resource.resource_metadata with only_include_ai_character=True for fallback."
    )
    app.default(run)
    app()
