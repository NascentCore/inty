#!/usr/bin/env python3
"""
List agents that have at least one fallback image (Resource with type=IMAGE and
resource_metadata.only_include_ai_character == true).

Usage (from repo root):
    export PYTHONPATH=.
    python scripts/list_agents_with_fallback_images.py --config devops/config.yaml.dev
    python scripts/list_agents_with_fallback_images.py --config devops/config.yaml.dev --output agents_with_fallback.json
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
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.resource import Resource, ResourceType

CONFIG_YAML = "config.yaml"


def _repo_root() -> Path:
    """仓库根目录（scripts 的上一级）。"""
    return Path(__file__).resolve().parent.parent


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


async def run(
    config: Optional[str] = None,
    output: Optional[str] = None,
) -> None:
    _ensure_config(config)

    query = (
        select(
            Agent.id.label("agent_id"),
            Agent.name.label("agent_name"),
            func.count(Resource.url).label("fallback_count"),
        )
        .select_from(Resource)
        .join(Agent, Resource.agent_id == Agent.id)
        .where(
            Resource.type == ResourceType.IMAGE,
            Resource.agent_id.isnot(None),
            Resource.resource_metadata.op("->>")("only_include_ai_character")
            == "true",
        )
        .group_by(Agent.id, Agent.name)
        .order_by(func.count(Resource.url).desc())
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(query)
        rows = result.all()

    items = [
        {
            "agent_id": row.agent_id,
            "agent_name": row.agent_name,
            "fallback_count": row.fallback_count,
        }
        for row in rows
    ]

    if output is not None:
        out_path = Path(output)
        if not out_path.is_absolute():
            out_path = _repo_root() / output
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        print(f"Wrote {len(items)} agents to {out_path}", file=sys.stderr)
    else:
        for it in items:
            print(f"{it['agent_id']}\t{it['agent_name']}\t{it['fallback_count']}")


def main(
    config: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--config",
            help="复制此 YAML 到当前目录 config.yaml 后再导入 app；不指定则要求已存在 config.yaml。",
        ),
    ] = None,
    output: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--output",
            help="输出 JSON 文件路径；不指定则打印到 stdout。",
        ),
    ] = None,
) -> None:
    """Sync entrypoint for cyclopts; runs async run()."""
    asyncio.run(run(config=config, output=output))


if __name__ == "__main__":
    app = cyclopts.App(
        help="List agents that have at least one fallback image (only_include_ai_character=true)."
    )
    app.default(main)
    app()
