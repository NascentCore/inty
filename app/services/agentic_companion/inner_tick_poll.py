"""Shared inner-tick poll: proactive, scheduled, autonomy, maintenance, dreaming (WS or Weixin delivery).

Requires signed-on presence coordinates on ``coordinator`` — poll runs on the same ``Coordinator``
as user chat. Scope ``CompanionSession.turn_lock`` (#3272) serializes inner-tick ``try_fire_*``
with user turns on ``(user_id, agent_id, chat_id)``. Prototype assumes one wire per paired
user; multiple tabs are out of scope (``companion_harness`` AGENTS.md).

Each poll wake tries at most one activity, in priority order:
proactive → scheduled → autonomy → maintenance → dreaming.

TODO(inner-tick-poll-multi-track): Try every **due** track per wake (e.g. scheduled must not
be skipped when proactive fires) — product decision #3273
https://github.com/NascentCore/inty/issues/3273

TODO(scope-inner-tick-worker): Inner-tick is autonomous agent behavior and should not
require the user on any channel (#3255 — https://github.com/NascentCore/inty/issues/3255).
Split **scope** activities (dreaming, maintenance/autonomy — no user-visible delivery)
from **presence** activities (proactive, scheduled — need ``InnerTickDelivery`` or
undelivered queue). Run scope poll from a process worker keyed by
``(user_id, agent_id, chat_id)`` with scope-level ``turn_lock`` on ``CompanionSession``;
keep this presence poll only for delivery tracks until #3255 lands. See ``dreaming.py``,
``session.Coordinator`` module docstring.
"""

from __future__ import annotations

from typing import Any, Optional

from app.services.agentic_companion import inner_tick_fire
from app.services.agentic_companion.inner_tick_delivery import InnerTickDelivery
from app.services.agentic_companion.inner_tick_fire import InnerTickFireInput
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
    if await inner_tick_fire.try_fire_scheduled_inner_tick(fire_input):
        return
    if await inner_tick_fire.try_fire_autonomy_inner_tick(fire_input):
        return
    if await inner_tick_fire.try_fire_maintenance_inner_tick(fire_input):
        return
    await inner_tick_fire.try_fire_dreaming_inner_tick(fire_input)
