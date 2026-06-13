"""Scope inner-tick worker lifecycle (Ops + production inty backend)."""

from __future__ import annotations

import asyncio

from loguru import logger

from app.services.agentic_companion.scope_inner_tick_worker import (
    run_scope_inner_tick_worker_loop,
)

_worker_task: asyncio.Task[None] | None = None
_stop: asyncio.Event | None = None


async def start_scope_inner_tick_worker() -> None:
    """Start process-level scope inner-tick worker (dreaming without presence)."""
    global _worker_task, _stop
    if _worker_task is not None and (not _worker_task.done()):
        logger.warning("scope-inner-tick-worker: already running")
        return
    _stop = asyncio.Event()
    _worker_task = asyncio.create_task(
        run_scope_inner_tick_worker_loop(stop=_stop),
        name="scope_inner_tick_worker",
    )
    logger.info("scope-inner-tick-worker: started")


async def stop_scope_inner_tick_worker() -> None:
    """Stop scope inner-tick worker task."""
    global _worker_task, _stop
    stop_ev = _stop
    task = _worker_task
    _stop = None
    _worker_task = None
    if stop_ev is not None:
        stop_ev.set()
    if task is not None and (not task.done()):
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    logger.info("scope-inner-tick-worker: stopped")
