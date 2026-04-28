"""Persist companion-visible agent status_line (chat header subtitle)."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Optional

from loguru import logger
from sqlalchemy import select

from app import models, schemas
from app.db.session import AsyncSessionLocal
from app.services import agent_service

_tls = threading.local()
_PERSIST_BRIDGE_TIMEOUT_SEC = 30.0


def set_tool_background_db_loop(loop: asyncio.AbstractEventLoop | None) -> None:
    """Used only by ``inty-v2-tool-bg``: persist PG on the server loop, not ``asyncio.run``'s loop."""
    _tls.persist_bridge_loop = loop


def clear_tool_background_db_loop() -> None:
    _tls.persist_bridge_loop = None


def _tool_background_db_loop() -> asyncio.AbstractEventLoop | None:
    return getattr(_tls, "persist_bridge_loop", None)


def agent_id_from_companion_workspace_root(root: Path) -> str:
    """Workspace root is ``.../<user_id>/<agent_id>/<chat_id>``; agent id is parent of chat folder."""
    return root.resolve().parent.name


async def _persist_agent_status_line_body(
    agent_id: str, payload: Optional[str]
) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Agent).where(
                models.Agent.id == agent_id,
                models.Agent.deleted_at.is_(None),
            )
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            logger.warning(
                "persist_agent_status_line skipped: agent not found agent_id={}",
                agent_id,
            )
            return
        await agent_service.update_agent(
            db,
            agent,
            schemas.AgentUpdate(status_line=payload),
        )


async def persist_agent_status_line(agent_id: str, status_line: Optional[str]) -> None:
    """Writes ``agents.status_line``. Empty or whitespace clears the column."""
    normalized = (status_line or "").strip()
    payload = normalized if normalized else None
    bridge = _tool_background_db_loop()
    running = asyncio.get_running_loop()
    if bridge is not None and bridge is not running:
        fut = asyncio.run_coroutine_threadsafe(
            _persist_agent_status_line_body(agent_id, payload),
            bridge,
        )
        try:
            await asyncio.wait_for(
                asyncio.wrap_future(fut),
                timeout=_PERSIST_BRIDGE_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError:
            logger.error(
                "persist_agent_status_line timed out after {:.0f}s (main loop bridge)",
                _PERSIST_BRIDGE_TIMEOUT_SEC,
            )
            raise ValueError(
                "persist_agent_status_line timed out waiting for database on main event loop"
            ) from None
        except Exception as exc:
            logger.exception(
                "persist_agent_status_line bridge failed agent_id={}", agent_id
            )
            raise ValueError(f"persist_agent_status_line failed: {exc}") from exc
        return
    await _persist_agent_status_line_body(agent_id, payload)


async def tool_update_agent_status_line(root: Path, status_line: str) -> str:
    """Companion tool: set short chat-header status line for this agent."""
    agent_id = agent_id_from_companion_workspace_root(root)
    await persist_agent_status_line(agent_id, status_line)
    return "OK updated agent status line"
