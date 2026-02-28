#!/usr/bin/env python3
"""
Manual check (not on CI): after tagging one Resource with only_include_ai_character=True
via tag_only_include_ai_character_from_json.py --limit 1, run this script with that
Resource's GCS URI or agent_id to confirm get_generated_images_for_agent(..., only_include_ai_character=True)
returns it.

Usage (from repo root):
    export PYTHONPATH=.
    python scripts/verify_only_include_ai_character_fallback.py --gcs-uri "gs://inty-static/chat_images/AGENT_ID/filename.jpg" --config devops/config.yaml.dev
    python scripts/verify_only_include_ai_character_fallback.py --agent-id AGENT_ID --config devops/config.yaml.dev
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Annotated, Optional

import cyclopts
from loguru import logger
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.resource import Resource, ResourceType
from app.services import image_generation_service

CONFIG_YAML = "config.yaml"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _ensure_config(config_path: Optional[str]) -> None:
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
                f"错误: 未指定 --config 且当前目录下不存在 {CONFIG_YAML}",
                file=sys.stderr,
            )
            sys.exit(1)


def _normalize_gcs_uri(uri: str) -> str:
    if not uri:
        return ""
    if uri.startswith("gs://"):
        return uri
    prefix = "https://storage.googleapis.com/"
    if uri.startswith(prefix):
        return "gs://" + uri[len(prefix) :]
    return ""


async def _run(
    gcs_uri: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--gcs-uri",
            help="GCS URI of the Resource to verify (e.g. gs://inty-static/chat_images/...).",
        ),
    ] = None,
    agent_id: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--agent-id",
            help="Agent ID; then all fallback candidates for this agent are listed (no single-URI check).",
        ),
    ] = None,
    config: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--config",
            help="复制此 YAML 到当前目录 config.yaml 后再导入 app。",
        ),
    ] = None,
) -> None:
    _ensure_config(config)
    if not gcs_uri and not agent_id:
        print("Provide either --gcs-uri or --agent-id.", file=sys.stderr)
        sys.exit(1)
    if gcs_uri and agent_id:
        print("Provide only one of --gcs-uri or --agent-id.", file=sys.stderr)
        sys.exit(1)

    gcs_uri_normalized = _normalize_gcs_uri(gcs_uri) if gcs_uri else None

    async with AsyncSessionLocal() as db:
        if gcs_uri_normalized:
            result = await db.execute(
                select(Resource).where(
                    Resource.url == gcs_uri_normalized,
                    Resource.type == ResourceType.IMAGE,
                )
            )
            resource = result.scalar_one_or_none()
            if not resource:
                print(f"Resource not found: {gcs_uri_normalized}", file=sys.stderr)
                sys.exit(1)
            agent_id = resource.agent_id
            if not agent_id:
                print("Resource has no agent_id.", file=sys.stderr)
                sys.exit(1)

        images = await image_generation_service.get_generated_images_for_agent(
            db, agent_id, only_include_ai_character=True
        )
        image_ids = [img["image_id"] for img in images]

        if gcs_uri_normalized:
            if gcs_uri_normalized in image_ids:
                print(f"OK: {gcs_uri_normalized} is in get_generated_images_for_agent(..., only_include_ai_character=True)")
            else:
                print(
                    f"FAIL: {gcs_uri_normalized} is NOT in fallback list (agent_id={agent_id}, count={len(images)})",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            print(f"Agent {agent_id}: {len(images)} fallback image(s):")
            for img in images:
                print(f"  {img['image_id']}")


if __name__ == "__main__":
    import asyncio

    app = cyclopts.App(
        help="Verify a tagged Resource appears in get_generated_images_for_agent(..., only_include_ai_character=True)."
    )
    app.default(_run)
    app()
