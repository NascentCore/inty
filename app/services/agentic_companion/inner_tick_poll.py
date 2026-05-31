"""Shared inner-tick poll: scheduled, proactive, maintenance (WS or Weixin delivery)."""

from __future__ import annotations

from typing import Any, Optional

from app.services.agentic_companion import inner_tick_fire
from app.services.agentic_companion.inner_tick_delivery import InnerTickDelivery
from app.services.agentic_companion.session import Coordinator
from app.services.subscription_service import SubscriptionService


async def run_inner_tick_poll(
    *,
    ctx: dict[str, Any],
    delivery: InnerTickDelivery,
    subscription_svc: SubscriptionService,
    coordinator: Coordinator,
    ws_conn_id: str | None,
    tc_box: list[Optional[dict]] | None,
) -> None:
    """Run one inner-tick cycle when ``ctx`` has signed-on coordinates."""
    ws_id = ws_conn_id if ws_conn_id is not None else "weixin_presence"
    tc = tc_box if tc_box is not None else [None]

    await inner_tick_fire.try_fire_scheduled_inner_tick(
        delivery=delivery,
        ctx=ctx,
        subscription_svc=subscription_svc,
        coordinator=coordinator,
        ws_conn_id=ws_id,
        tc_box=tc,
    )
    await inner_tick_fire.try_fire_proactive_chat_inner_tick(
        delivery=delivery,
        ctx=ctx,
        subscription_svc=subscription_svc,
        coordinator=coordinator,
        ws_conn_id=ws_id,
        tc_box=tc,
    )
    await inner_tick_fire.try_fire_maintenance_inner_tick(
        delivery=delivery,
        ctx=ctx,
        subscription_svc=subscription_svc,
        coordinator=coordinator,
        ws_conn_id=ws_id,
        tc_box=tc,
    )
