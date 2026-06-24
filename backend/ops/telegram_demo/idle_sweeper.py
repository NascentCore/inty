"""Ops Telegram idle runtime pause sweeper for launch cost control."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.models import (
    TranscriptProjection,
    load_transcript_projection_from_store,
)
from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.transcript_anchor import (
    last_real_user_transcript_anchor,
)
from app.core.companion_harness.memory.companion_scope_listing import (
    list_companion_memory_scopes,
)
from app.core.companion_harness.memory.memory_registry import (
    get_memory_store,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal
from app.models.agent_channel_endpoint import AgentChannelEndpoint
from app.models.companion_bond import CompanionBond
from app.services.agentic_channel.channel_runtime import (
    get_scope_channel_registry,
    turn_channel_down,
)
from app.services.agentic_channel.companion_bonds import (
    get_companion_bond_for_scope,
    list_active_companion_agent_scope_keys,
    pause_companion_bond_runtime,
)
from app.services.agentic_channel.presence import stop_presence

_IDLE_SWEEP_INTERVAL_SECONDS = 3600.0
_sweeper_task: asyncio.Task[None] | None = None
_stop: asyncio.Event | None = None


def _agent_scope(scope: CompanionScope) -> AgentScope:
    return AgentScope(user_id=scope.user_id, agent_id=scope.companion_id)


def _now_utc() -> datetime:
    return datetime.now(UTC)


async def _telegram_endpoint_created_at(
    db: AsyncSession,
    scope: AgentScope,
) -> datetime | None:
    result = await db.execute(
        select(AgentChannelEndpoint.created_at)
        .where(
            AgentChannelEndpoint.user_id == scope.user_id,
            AgentChannelEndpoint.agent_id == scope.agent_id,
            AgentChannelEndpoint.channel == ChannelKind.TELEGRAM.value,
        )
        .order_by(AgentChannelEndpoint.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def idle_activity_anchor_at(
    db: AsyncSession,
    scope: CompanionScope,
    bond: CompanionBond,
) -> datetime:
    """Return the latest user-activity or runtime-resume anchor for idle pause."""
    store = get_memory_store(
        scope,
        dsn=global_config_loaded_from_config_yaml.database.url,
    )
    transcript = load_transcript_projection_from_store(
        store,
        "transcript.jsonl",
        TranscriptProjection.FULL,
    )
    real_user_anchor = last_real_user_transcript_anchor(transcript).ts
    endpoint_created_at = await _telegram_endpoint_created_at(
        db,
        _agent_scope(scope),
    )
    candidates = [
        dt
        for dt in (
            real_user_anchor,
            endpoint_created_at,
            bond.last_resumed_at,
            bond.created_at,
        )
        if dt is not None
    ]
    return max(candidates) if candidates else bond.created_at


async def pause_companion_runtime(
    scope: AgentScope,
    reason: str,
    threshold_minutes: int,
) -> None:
    """Pause one ACTIVE companion runtime while keeping its bond ACTIVE."""
    assert reason != ""
    assert threshold_minutes >= 1
    async with AsyncSessionLocal() as db:
        paused = await pause_companion_bond_runtime(db, scope)
        if not paused:
            return
        await db.commit()
    async with AsyncSessionLocal() as db:
        bond = await get_companion_bond_for_scope(db, scope)
        if bond is None or bond.runtime_paused_at is None:
            return

    registry = get_scope_channel_registry(scope)
    active_channel = registry.active_channel()
    await stop_presence(scope)
    if active_channel is not None:
        await turn_channel_down(scope, active_channel, reason=reason)
    logger.info(
        "runtime_pause scope={} reason={} threshold_minutes={}",
        scope.registry_key(),
        reason,
        threshold_minutes,
    )


async def run_idle_sweeper_cycle() -> None:
    """Pause Telegram companion runtimes whose idle anchor exceeds config threshold."""
    timeout_minutes = (
        global_config_loaded_from_config_yaml.agent.companion_harness.agent_scope_idle_timeout_minutes
    )
    threshold = timedelta(minutes=timeout_minutes)
    now = _now_utc()
    async with AsyncSessionLocal() as db:
        memory_scopes = await list_companion_memory_scopes(db)
        active_keys = await list_active_companion_agent_scope_keys(db)
        candidate_scopes = [
            scope
            for scope in memory_scopes
            if (scope.user_id, scope.companion_id) in active_keys
        ]
        stale_scopes: list[AgentScope] = []
        for scope in candidate_scopes:
            agent_scope = _agent_scope(scope)
            bond = await get_companion_bond_for_scope(db, agent_scope)
            if bond is None:
                continue
            anchor_at = await idle_activity_anchor_at(db, scope, bond)
            if now - anchor_at <= threshold:
                continue
            stale_scopes.append(agent_scope)

    for scope in stale_scopes:
        try:
            await pause_companion_runtime(
                scope,
                reason="idle_timeout",
                threshold_minutes=timeout_minutes,
            )
        except Exception:
            logger.exception(
                "idle_sweeper pause failed scope={}",
                scope.registry_key(),
            )


async def _run_idle_sweeper_loop(stop: asyncio.Event) -> None:
    logger.info(
        "idle_sweeper started interval_seconds={}",
        _IDLE_SWEEP_INTERVAL_SECONDS,
    )
    while not stop.is_set():
        try:
            await run_idle_sweeper_cycle()
        except Exception:
            logger.exception("idle_sweeper cycle failed")
        if stop.is_set():
            break
        try:
            await asyncio.wait_for(
                stop.wait(),
                timeout=_IDLE_SWEEP_INTERVAL_SECONDS,
            )
        except asyncio.TimeoutError:
            pass
    logger.info("idle_sweeper stopped")


async def start_idle_sweeper() -> None:
    """Start Ops-owned Telegram idle pause sweeper."""
    global _sweeper_task, _stop
    if _sweeper_task is not None and (not _sweeper_task.done()):
        logger.warning("idle_sweeper: already running")
        return
    _stop = asyncio.Event()
    _sweeper_task = asyncio.create_task(
        _run_idle_sweeper_loop(_stop),
        name="telegram_idle_sweeper",
    )


async def stop_idle_sweeper() -> None:
    """Stop Ops-owned Telegram idle pause sweeper."""
    global _sweeper_task, _stop
    stop_ev = _stop
    task = _sweeper_task
    _stop = None
    _sweeper_task = None
    if stop_ev is not None:
        stop_ev.set()
    if task is not None and (not task.done()):
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
