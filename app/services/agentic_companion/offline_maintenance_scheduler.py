"""Presence-less maintenance heartbeat: keep companions evolving while users are offline.

WebSocket/Weixin presence drives maintenance inner-tick only while connected, so an
offline companion freezes. This process-level scheduler scans active companion chats on
a fixed interval and fires one headless maintenance turn per due scope (no user-facing
delivery), throttled by a persisted wall-clock :class:`MaintenanceTickState`. Scopes that
currently have a live presence are skipped so the same MemoryStore is never driven twice.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select

from app.core.companion_harness.companion.inner_tick_schedule import (
    inner_tick_min_transcript_msgs,
    maintenance_due_offline,
    maintenance_transcript_line_count,
)
from app.core.companion_harness.companion.maintenance_tick_state import (
    MaintenanceTickState,
    load_maintenance_tick_state,
    save_maintenance_tick_state,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.config import global_config_loaded_from_config_yaml
from app.core.model_selection import select_chat_model
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services import chat_service, companion_chat_service
from app.services.agentic_companion.active_presence_registry import is_present
from app.services.global_services import subscription_service

_scheduler_task: asyncio.Task[None] | None = None
_scheduler_running = False


def _features():
    return global_config_loaded_from_config_yaml.app.features


async def _maybe_fire_offline_maintenance(scope: CompanionScope) -> None:
    """Run one headless maintenance turn for ``scope`` when it is due and presence-less."""
    if is_present(scope.registry_key()):
        return

    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.id == scope.user_id))
        ).scalar_one_or_none()
        if user is None:
            return
        subscription = await subscription_service.get_user_current_subscription(
            db, scope.user_id
        )
        model_override = select_chat_model(
            user=user, is_subscribed=bool(subscription)
        )

    store = companion_chat_service.companion_memory_store_if_ready(
        user_id=scope.user_id,
        agent_id=scope.companion_id,
        chat_id=scope.chat_id,
        resolved_chat_model=model_override,
    )
    if store is None:
        return

    state = load_maintenance_tick_state(store)
    now_utc = datetime.now(timezone.utc)
    feats = _features()
    if not maintenance_due_offline(
        store,
        now_utc=now_utc,
        last_fired_at_utc=state.last_fired_at_utc if state else None,
        last_transcript_line_count=(
            state.last_transcript_line_count if state else None
        ),
        min_gap_seconds=float(
            feats.companion_ws_maintenance_inner_tick_min_gap_seconds
        ),
        min_transcript_msgs=inner_tick_min_transcript_msgs(),
    ):
        return

    line_count = maintenance_transcript_line_count(store)
    turn = await companion_chat_service.run_companion_inner_tick_maintenance_turn_for_api(
        user_id=scope.user_id,
        agent_id=scope.companion_id,
        chat_id=scope.chat_id,
        resolved_chat_model=model_override,
        defer_memory_update=True,
        session_id=None,
        background_output_sink=None,
        runtime_channel=CompanionRuntimeChannel.APP,
    )

    # Maintenance reorganizes memory via its tool loop in a background thread; wait for
    # it so the persisted tick state reflects completed evolution, not just the foreground.
    if turn.tool_background_started:
        idle_event = (
            companion_chat_service.companion_session_tool_bg_idle_event(
                user_id=scope.user_id,
                agent_id=scope.companion_id,
                chat_id=scope.chat_id,
                resolved_chat_model=model_override,
            )
        )
        await asyncio.to_thread(
            idle_event.wait,
            float(feats.companion_tool_bg_idle_wait_timeout_sec),
        )

    save_maintenance_tick_state(
        store,
        MaintenanceTickState(
            last_fired_at_utc=now_utc,
            last_transcript_line_count=line_count,
        ),
    )
    logger.info(
        "offline_maintenance fired scope={} line_count={} tool_bg={}",
        scope.registry_key(),
        line_count,
        turn.tool_background_started,
    )


async def _run_one_scan() -> None:
    """Scan all active companion scopes once, firing offline maintenance where due."""
    async with AsyncSessionLocal() as db:
        scopes = await chat_service.list_active_companion_scopes(db)
    for scope in scopes:
        try:
            await _maybe_fire_offline_maintenance(scope)
        except Exception:
            logger.exception(
                "offline_maintenance scope failed scope={}",
                scope.registry_key(),
            )


async def start_offline_maintenance_scheduler() -> None:
    """Start the process-level offline maintenance loop (idempotent)."""
    global _scheduler_task, _scheduler_running
    if _scheduler_running:
        return
    _scheduler_running = True

    async def _loop() -> None:
        while _scheduler_running:
            poll_seconds = float(
                _features().companion_ws_proactive_chat_poll_seconds
            )
            try:
                await asyncio.sleep(poll_seconds)
                await _run_one_scan()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("offline_maintenance scan loop error")

    _scheduler_task = asyncio.create_task(_loop(), name="offline_maintenance")
    logger.info("offline_maintenance scheduler started")


async def stop_offline_maintenance_scheduler() -> None:
    """Stop the offline maintenance loop and await cancellation."""
    global _scheduler_task, _scheduler_running
    _scheduler_running = False
    task = _scheduler_task
    if task is not None and (not task.done()):
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    _scheduler_task = None
    logger.info("offline_maintenance scheduler stopped")
