"""Persist companion-visible agent status_line (chat header subtitle)."""

from __future__ import annotations

import asyncio
import threading
from typing import Optional

from loguru import logger
from sqlalchemy import select

from app.models.agent import Agent
from app.core.agentic_kernel.companion.memory_store import MemoryStore
from app.db.session import AsyncSessionLocal
from app.services import agent_service
from app.schemas.agent import AgentUpdate

_tls = threading.local()
_PERSIST_BRIDGE_TIMEOUT_SEC = 30.0


def set_tool_background_db_loop(loop: asyncio.AbstractEventLoop | None) -> None:
    """Used only by ``inty-v2-tool-bg``: persist PG on the server loop, not ``asyncio.run``'s loop."""
    _tls.persist_bridge_loop = loop


def clear_tool_background_db_loop() -> None:
    _tls.persist_bridge_loop = None


def _tool_background_db_loop() -> asyncio.AbstractEventLoop | None:
    return getattr(_tls, "persist_bridge_loop", None)


def agent_id_from_companion_memory_store(store: MemoryStore) -> str:
    """Agent id is the companion id in ``CompanionScope``."""
    return store.scope.companion_id


async def _persist_agent_status_line_body(
    agent_id: str, payload: Optional[str]
) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.deleted_at.is_(None),
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
            AgentUpdate(status_line=payload),
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


_STATUS_LINE_TOOL_PREVIEW_MAX_CHARS = 280


def _status_line_tool_result_quoted_fragment(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return escaped


async def tool_update_agent_status_line(store: MemoryStore, status_line: str) -> str:
    """Companion tool: set short chat-header status line for this agent."""
    agent_id = agent_id_from_companion_memory_store(store)
    await persist_agent_status_line(agent_id, status_line)
    normalized = (status_line or "").strip()
    if not normalized:
        return "status line cleared"
    preview = normalized
    if len(preview) > _STATUS_LINE_TOOL_PREVIEW_MAX_CHARS:
        preview = preview[:_STATUS_LINE_TOOL_PREVIEW_MAX_CHARS] + "..."
    inner = _status_line_tool_result_quoted_fragment(preview)
    return f'status line updated to "{inner}"'
