"""Scope-level inner-tick poll: autonomous tracks without signed-on presence (#3255).

Orchestration only — Postgres reads go through ``scope_inner_tick_persistence``;
track execution goes through ``scope_inner_tick_fire``.
"""

from __future__ import annotations

import asyncio

from loguru import logger

from app.core.companion_harness.companion.scope import CompanionScope
from app.services.agentic_companion.inner_tick_scope import (
    InnerTickChatResolveMode,
)
from app.services.agentic_companion.scope_inner_tick_fire import (
    try_fire_autonomy_for_scope,
    try_fire_dreaming_for_scope,
    try_fire_maintenance_for_scope,
)
from app.services.agentic_companion.scope_inner_tick_persistence import (
    fetch_initialized_companion_scopes,
)
from app.services.agentic_companion.session import InnerTickCoords

_SCOPE_WORKER_POLL_SOURCE = "scope_inner_tick_worker"

# TODO(dreaming-cluster-lock): Postgres advisory lock per scope (#3271).


async def run_scope_inner_tick_poll_for_scope(
    *,
    scope: CompanionScope,
) -> bool:
    """Run one scope poll wake: maintenance → autonomy → dreaming (#3255)."""
    coords = InnerTickCoords(
        user_id=scope.user_id,
        agent_id=scope.companion_id,
        chat_id=scope.chat_id,
    )
    common = {
        "coords": coords,
        "poll_source": _SCOPE_WORKER_POLL_SOURCE,
        "chat_resolve_mode": InnerTickChatResolveMode.READ_ONLY,
        "implicit_signal_bundle": None,
    }
    if await try_fire_maintenance_for_scope(**common):
        return True
    if await try_fire_autonomy_for_scope(**common):
        return True
    return await try_fire_dreaming_for_scope(
        coords=coords,
        poll_source=_SCOPE_WORKER_POLL_SOURCE,
    )


async def run_scope_inner_tick_poll_cycle(
    *,
    stop: asyncio.Event,
) -> None:
    """Enumerate Postgres scopes and attempt one scope track per scope per wake."""
    scopes = await fetch_initialized_companion_scopes()
    for scope in scopes:
        if stop.is_set():
            return
        try:
            await run_scope_inner_tick_poll_for_scope(scope=scope)
        except Exception as exc:
            logger.warning(
                "scope_inner_tick_poll scope={} failed: {}",
                scope.registry_key(),
                exc,
            )
