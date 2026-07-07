"""Shared inner-tick poll: proactive and scheduled delivery tracks (WS or Weixin).

Requires signed-on presence coordinates on ``coordinator`` — poll runs on the same ``Coordinator``
as user chat. Scope ``CompanionSession.turn_lock`` (#3272) serializes inner-tick ``try_fire_*``
with user turns on ``(user_id, agent_id, chat_id)``. Prototype assumes one wire per paired
user; multiple tabs are out of scope (``companion_harness`` AGENTS.md).

Each poll wake tries at most one activity, in priority order: proactive → scheduled.

Scope tracks (scheduled when offline, monolog, autonomy, dreaming) run on
``scope_inner_tick_poll`` (#3255, #3689). Offline due scheduled tasks fire from the
scope worker; this poll still handles proactive and scheduled when the user is signed on.

TODO(inner-tick-poll-multi-track): Try every **due** track per wake (e.g. scheduled must not
be skipped when proactive fires) — product decision #3273
https://github.com/NascentCore/inty/issues/3273
"""

from __future__ import annotations

from typing import Optional

from app.services.agentic_companion import inner_tick_fire
from app.services.agentic_companion.inner_tick_delivery import InnerTickDelivery
from app.services.agentic_companion.inner_tick_scope import InnerTickFireInput
from app.services.agentic_companion.session import Coordinator, InnerTickCoords


async def run_inner_tick_poll(
    *,
    delivery: InnerTickDelivery,
    coordinator: Coordinator,
    ws_conn_id: str | None,
    tc_box: list[Optional[dict]] | None,
) -> None:
    """Run one inner-tick cycle when the coordinator still has signed-on coordinates."""
    live_ctx = coordinator.snapshot_inner_tick_coords()
    if live_ctx is None:
        return
    poll_coords = InnerTickCoords.from_context(live_ctx)
    if poll_coords is None:
        return
    ws_id = ws_conn_id if ws_conn_id is not None else "weixin_presence"
    tc = tc_box if tc_box is not None else [None]
    fire_input = InnerTickFireInput(
        delivery=delivery,
        coords=poll_coords,
        coordinator=coordinator,
        ws_conn_id=ws_id,
        tc_box=tc,
    )
    # TODO(inner-tick-poll-multi-track): #3273 — do not early-return; attempt each due track per wake.
    if await inner_tick_fire.try_fire_proactive_chat_inner_tick(fire_input):
        return
    await inner_tick_fire.try_fire_scheduled_inner_tick(fire_input)
