"""Scope-level inner-tick poll: autonomous tracks without signed-on presence (#3255)."""

from __future__ import annotations

import asyncio

from loguru import logger

from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.companion_scope_listing import (
    list_companion_memory_scopes,
)
from app.db.session import AsyncSessionLocal
from app.services.agentic_companion import inner_tick_fire
from app.services.agentic_companion.inner_tick_delivery import InnerTickDelivery
from app.services.agentic_companion.inner_tick_fire import InnerTickFireInput
from app.services.agentic_companion.session import Coordinator, InnerTickCoords

_SCOPE_WORKER_POLL_SOURCE = "scope_inner_tick_worker"


def _scope_worker_fire_input(
    *,
    coords: InnerTickCoords,
) -> InnerTickFireInput:
    """Build ``InnerTickFireInput`` for scope worker (dreaming does not use delivery/coordinator)."""
    return InnerTickFireInput(
        delivery=InnerTickDelivery(
            ws_outbound_queue=asyncio.Queue(),
            weixin_assistant_text=None,
            telegram_assistant_text=None,
            runtime_channel=CompanionRuntimeChannel.APP,
        ),
        coords=coords,
        coordinator=Coordinator.for_current_loop(),
        ws_conn_id=_SCOPE_WORKER_POLL_SOURCE,
        tc_box=[None],
    )


async def run_scope_inner_tick_poll_for_scope(
    *,
    scope: CompanionScope,
) -> bool:
    """Run one scope poll wake (dreaming only until maintenance/autonomy throttle moves off presence)."""
    coords = InnerTickCoords(
        user_id=scope.user_id,
        agent_id=scope.companion_id,
        chat_id=scope.chat_id,
    )
    fire_input = _scope_worker_fire_input(coords=coords)
    return await inner_tick_fire.try_fire_dreaming_inner_tick(fire_input)


async def run_scope_inner_tick_poll_cycle() -> None:
    """Enumerate Postgres scopes and attempt dreaming for each initialized scope."""
    async with AsyncSessionLocal() as db:
        scopes = await list_companion_memory_scopes(db)
    for scope in scopes:
        try:
            await run_scope_inner_tick_poll_for_scope(scope=scope)
        except Exception as exc:
            logger.warning(
                "scope_inner_tick_poll scope={} failed: {}",
                scope.registry_key(),
                exc,
            )
