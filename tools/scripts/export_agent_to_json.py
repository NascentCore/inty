#!/usr/bin/env python3
"""
Export a single agent by ID to a JSON file (complete row for fixture/restore).

Usage (from repo root with config.yaml or devops/config.yaml.local):
    PYTHONPATH=. python tools/scripts/export_agent_to_json.py --agent-id <uuid> [--output path]
    PYTHONPATH=. python tools/scripts/export_agent_to_json.py --agent-id 1d2814b4-76dc-49de-83ac-d183baca1a87 --output tests/Isabelle_Martin_imate_info.json
"""

import asyncio
import json
from pathlib import Path
from typing import Annotated

import cyclopts
from loguru import logger
from sqlalchemy import inspect, select

from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.schemas import agent as schemas_agent


async def _export_agent(agent_id: str, output_path: Path) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.deleted_at.is_(None),
            )
        )
        agent_orm = result.scalar_one_or_none()
        if not agent_orm:
            raise SystemExit(f"Agent not found: {agent_id}")

        # Build dict from ORM columns only (AgentInDB expects "points", aliased as energy_points)
        col_keys = [c.key for c in inspect(Agent).mapper.column_attrs]
        data = {k: getattr(agent_orm, k) for k in col_keys}
        if data.get("readable_id") is None:
            data["readable_id"] = ""

        payload = schemas_agent.AgentInDB.model_validate(data).model_dump(
            mode="json"
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        logger.info(
            "Exported agent id={} name={} -> {}",
            agent_id,
            agent_orm.name,
            output_path,
        )


def main(
    agent_id: Annotated[
        str,
        cyclopts.Parameter(help="Agent UUID to export"),
    ],
    output: Annotated[
        str,
        cyclopts.Parameter(help="Output JSON file path"),
    ] = "tests/Isabelle_Martin_imate_info.json",
) -> None:
    asyncio.run(_export_agent(agent_id, Path(output)))


if __name__ == "__main__":
    cyclopts.run(main)
