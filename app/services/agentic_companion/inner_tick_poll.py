"""Shared inner-tick poll: scheduled, proactive, maintenance (WS or Weixin delivery)."""

from __future__ import annotations

from typing import Any, Optional

from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.implicit_signals import HumanChannel
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
    human_channel: HumanChannel,
) -> None:
    """Run one inner-tick cycle when ``ctx`` has signed-on coordinates."""
    assert human_channel is not None
    ws_id = ws_conn_id if ws_conn_id is not None else "weixin_presence"
    tc = tc_box if tc_box is not None else [None]

    await inner_tick_fire.try_fire_scheduled_inner_tick(
        delivery=delivery,
        ctx=ctx,
        subscription_svc=subscription_svc,
        coordinator=coordinator,
        ws_conn_id=ws_id,
        tc_box=tc,
        human_channel=human_channel,
    )
    await inner_tick_fire.try_fire_proactive_chat_inner_tick(
        delivery=delivery,
        ctx=ctx,
        subscription_svc=subscription_svc,
        coordinator=coordinator,
        ws_conn_id=ws_id,
        tc_box=tc,
        human_channel=human_channel,
    )
    feats = global_config_loaded_from_config_yaml.app.features
    if bool(feats.companion_ws_maintenance_inner_tick_enabled):
        await inner_tick_fire.try_fire_maintenance_inner_tick(
            delivery=delivery,
            ctx=ctx,
            subscription_svc=subscription_svc,
            coordinator=coordinator,
            ws_conn_id=ws_id,
            tc_box=tc,
            human_channel=human_channel,
        )
