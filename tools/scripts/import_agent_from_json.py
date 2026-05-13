#!/usr/bin/env python3
"""
Import a single agent from a JSON file (as produced by export_agent_to_json.py) into the database.

Preserves agent id for fixture/restore. Use when the same id does not already exist.

Usage (from repo root with config.yaml):
    PYTHONPATH=. python tools/scripts/import_agent_from_json.py --input tests/Isabelle_Martin_imate_info.json
    PYTHONPATH=. python tools/scripts/import_agent_from_json.py --input path/to/agent.json --no-dry-run --yes
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import cyclopts
from loguru import logger
from sqlalchemy import inspect, select

from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.user import User


def _load_agent_data(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and "agents" in raw:
        agents = raw["agents"]
        if not agents:
            raise SystemExit("JSON has empty 'agents' array")
        return agents[0]
    if isinstance(raw, dict) and "id" in raw:
        return raw
    raise SystemExit('JSON must be a single agent object or { "agents": [ {...} ] }')


def _json_to_orm_kwargs(
    data: dict[str, Any], creator_id_override: str | None
) -> dict[str, Any]:
    """Build kwargs for models.Agent from export JSON. Converts timestamps and renames energy_points."""
    # Move llm_config into settings (same as create_agent)
    if "llm_config" in data:
        llm = data.pop("llm_config")
        if data.get("settings") is None:
            data["settings"] = {}
        if isinstance(data["settings"], dict):
            data["settings"]["llm_config"] = llm

    creator_id = (
        creator_id_override
        if creator_id_override is not None
        else data.get("creator_id")
    )
    if not creator_id:
        raise ValueError("creator_id is required (in JSON or --creator-id)")

    col_keys = {c.key for c in inspect(Agent).mapper.column_attrs}
    kwargs: dict[str, Any] = {}

    for key, value in data.items():
        if key not in col_keys:
            continue
        if key == "energy_points":
            kwargs["points"] = value if value is not None else 0
            continue
        if key in ("created_at", "updated_at", "deleted_at") and isinstance(value, int):
            kwargs[key] = (
                datetime.fromtimestamp(value, tz=timezone.utc) if value else None
            )
            continue
        if key == "creator_id":
            kwargs[key] = creator_id
            continue
        kwargs[key] = value

    if "points" not in kwargs and "energy_points" in data:
        kwargs["points"] = data.get("energy_points") or 0
    if "id" not in kwargs and "id" in data:
        kwargs["id"] = data["id"]
    if "readable_id" not in kwargs and data.get("readable_id") is not None:
        kwargs["readable_id"] = data["readable_id"]
    elif "readable_id" not in kwargs:
        kwargs["readable_id"] = ""

    return kwargs


async def _check_creator_exists(db, creator_id: str) -> bool:
    result = await db.execute(select(User.id).where(User.id == creator_id))
    return result.scalar_one_or_none() is not None


async def _import_agent(
    input_path: Path,
    creator_id_override: str | None,
    dry_run: bool,
    yes: bool,
) -> None:
    data = _load_agent_data(input_path)
    agent_id = data.get("id")
    if not agent_id:
        raise SystemExit("JSON must contain 'id'")

    kwargs = _json_to_orm_kwargs(data, creator_id_override)
    creator_id = kwargs.get("creator_id")

    async with AsyncSessionLocal() as db:
        if not await _check_creator_exists(db, creator_id):
            raise SystemExit(f"creator_id '{creator_id}' not found in users table")

        existing = await db.execute(
            select(Agent.id).where(Agent.id == agent_id, Agent.deleted_at.is_(None))
        )
        if existing.scalar_one_or_none() is not None:
            raise SystemExit(
                f"Agent id={agent_id} already exists; delete or use another fixture"
            )

        if dry_run:
            logger.info(
                "DRY-RUN: would insert agent id={} name={} creator_id={}",
                agent_id,
                kwargs.get("name"),
                creator_id,
            )
            logger.debug("kwargs keys: {}", list(kwargs.keys()))
            return

        if not yes:
            print(
                f"\nInsert agent id={agent_id} name={kwargs.get('name')}? (y/N): ",
                end="",
            )
            if input().strip().lower() != "y":
                logger.info("Aborted")
                return

        agent = Agent(**kwargs)
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        logger.info("Inserted agent id=%s name=%s", agent.id, agent.name)


def main(
    input_path: Annotated[
        str,
        cyclopts.Parameter(
            name="input", help="Path to agent JSON file (export format)"
        ),
    ],
    creator_id: Annotated[
        str | None,
        cyclopts.Parameter(name="--creator-id", help="Override creator_id from JSON"),
    ] = None,
    dry_run: Annotated[
        bool,
        cyclopts.Parameter(
            name="--dry-run",
            help="Only validate and log; do not insert (default)",
        ),
    ] = True,
    no_dry_run: Annotated[
        bool,
        cyclopts.Parameter(
            name="--no-dry-run",
            help="Perform insert (use with --yes to skip confirmation)",
        ),
    ] = False,
    yes: Annotated[
        bool,
        cyclopts.Parameter(
            name="--yes",
            help="Skip confirmation when not dry-run",
        ),
    ] = False,
) -> None:
    path = Path(input_path)
    if not path.is_file():
        logger.error("Not a file: %s", path)
        sys.exit(1)
    if no_dry_run:
        dry_run = False
    asyncio.run(_import_agent(path, creator_id, dry_run, yes))


if __name__ == "__main__":
    cyclopts.run(main)
