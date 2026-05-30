"""Shared inner-tick poll: scheduled, proactive, maintenance (WS or Weixin delivery).

Requires signed-on presence coordinates in ``ctx`` — poll runs on the same ``Coordinator``
as user chat, so **one ``turn_lock`` per wire** serializes scheduled → proactive → maintenance
when each ``try_fire_*`` runs (they do not overlap in time on that connection).

While scope dreaming is active (``activity_gate``), the whole poll cycle is skipped — inner
ticks do not compete with background consolidation on the scope layer. Three lock layers
(presence / scope / cluster): see ``session.Coordinator`` module docstring.

Planned: add ``InnerTickActivity.DREAMING`` here; drop ``CompanionDreamingScheduler`` and gate;
mutually exclusive activities per poll wake. Offline scopes: #3255.
"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger
from sqlalchemy import select

from app.core.model_selection import select_chat_model
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services import chat_service, companion_chat_service
from app.services.agentic_companion import inner_tick_fire
from app.services.agentic_companion.inner_tick_delivery import InnerTickDelivery
from app.services.agentic_companion.session import Coordinator
from app.services.subscription_service import SubscriptionService


async def _inner_tick_poll_skipped_by_dreaming(
    *,
    ctx: dict[str, Any],
    subscription_svc: SubscriptionService,
    ws_conn_id: str,
) -> bool:
    """Return whether this poll cycle should skip all companion-initiated inner ticks."""
    user_id = str(ctx.get("user_id") or "").strip()
    agent_id = str(ctx.get("agent_id") or "").strip()
    chat_id_raw = ctx.get("chat_id")
    if not user_id or not agent_id or chat_id_raw is None:
        return False

    async with AsyncSessionLocal() as pre_db:
        r_user = await pre_db.execute(select(User).where(User.id == user_id))
        current_user = r_user.scalar_one_or_none()
        if current_user is None:
            return False

        chat = await chat_service.get_or_create_chat_by_agent(
            db=pre_db,
            user_id=user_id,
            agent_id=agent_id,
        )
        if str(chat.id) != str(chat_id_raw):
            return False

        subscription = await subscription_svc.get_user_current_subscription(
            pre_db,
            user_id,
        )
        is_subscribed = bool(subscription)
        model_override = select_chat_model(
            user=current_user,
            is_subscribed=is_subscribed,
        )
        if not companion_chat_service.companion_session_dreaming_active(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat.id,
            resolved_chat_model=model_override,
        ):
            return False

    logger.info(
        "companion_inner_tick_poll skipped dreaming_active ws_conn_id={} user={} agent={} chat={}",
        ws_conn_id,
        user_id,
        agent_id,
        chat.id,
    )
    return True


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

    if await _inner_tick_poll_skipped_by_dreaming(
        ctx=ctx,
        subscription_svc=subscription_svc,
        ws_conn_id=ws_id,
    ):
        return

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
