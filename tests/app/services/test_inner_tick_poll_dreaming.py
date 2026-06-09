from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.runtime.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.services.agentic_companion import inner_tick_poll
from app.services.agentic_companion.inner_tick_delivery import InnerTickDelivery


def _poll_delivery() -> InnerTickDelivery:
    return InnerTickDelivery(
        ws_outbound_queue=asyncio.Queue(),
        weixin_assistant_text=None,
        runtime_channel=CompanionRuntimeChannel.APP,
    )


@pytest.mark.asyncio
async def test_run_inner_tick_poll_stops_after_first_fire() -> None:
    live_ctx = {"user_id": "u", "agent_id": "a", "chat_id": "c"}
    coordinator = MagicMock()
    coordinator.snapshot_inner_tick_coords.return_value = live_ctx

    with (
        patch.object(
            inner_tick_poll.inner_tick_fire,
            "try_fire_proactive_chat_inner_tick",
            new_callable=AsyncMock,
            return_value=True,
        ) as proactive,
        patch.object(
            inner_tick_poll.inner_tick_fire,
            "try_fire_scheduled_inner_tick",
            new_callable=AsyncMock,
        ) as scheduled,
        patch.object(
            inner_tick_poll.inner_tick_fire,
            "try_fire_maintenance_inner_tick",
            new_callable=AsyncMock,
        ) as maintenance,
        patch.object(
            inner_tick_poll.inner_tick_fire,
            "try_fire_dreaming_inner_tick",
            new_callable=AsyncMock,
        ) as dreaming,
    ):
        await inner_tick_poll.run_inner_tick_poll(
            delivery=_poll_delivery(),
            coordinator=coordinator,
            ws_conn_id="ws",
            tc_box=[None],
        )

    proactive.assert_awaited_once()
    scheduled.assert_not_awaited()
    maintenance.assert_not_awaited()
    dreaming.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_inner_tick_poll_skips_when_coords_disarmed() -> None:
    coordinator = MagicMock()
    coordinator.snapshot_inner_tick_coords.return_value = None

    with (
        patch.object(
            inner_tick_poll.inner_tick_fire,
            "try_fire_proactive_chat_inner_tick",
            new_callable=AsyncMock,
        ) as proactive,
        patch.object(
            inner_tick_poll.inner_tick_fire,
            "try_fire_scheduled_inner_tick",
            new_callable=AsyncMock,
        ) as scheduled,
    ):
        await inner_tick_poll.run_inner_tick_poll(
            delivery=_poll_delivery(),
            coordinator=coordinator,
            ws_conn_id="ws",
            tc_box=[None],
        )

    proactive.assert_not_awaited()
    scheduled.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_inner_tick_poll_falls_through_to_dreaming() -> None:
    live_ctx = {"user_id": "u", "agent_id": "a", "chat_id": "c"}
    coordinator = MagicMock()
    coordinator.snapshot_inner_tick_coords.return_value = live_ctx

    with (
        patch.object(
            inner_tick_poll.inner_tick_fire,
            "try_fire_proactive_chat_inner_tick",
            new_callable=AsyncMock,
            return_value=False,
        ) as proactive,
        patch.object(
            inner_tick_poll.inner_tick_fire,
            "try_fire_scheduled_inner_tick",
            new_callable=AsyncMock,
            return_value=False,
        ) as scheduled,
        patch.object(
            inner_tick_poll.inner_tick_fire,
            "try_fire_maintenance_inner_tick",
            new_callable=AsyncMock,
            return_value=False,
        ) as maintenance,
        patch.object(
            inner_tick_poll.inner_tick_fire,
            "try_fire_dreaming_inner_tick",
            new_callable=AsyncMock,
            return_value=True,
        ) as dreaming,
    ):
        await inner_tick_poll.run_inner_tick_poll(
            delivery=_poll_delivery(),
            coordinator=coordinator,
            ws_conn_id="ws",
            tc_box=[None],
        )

    proactive.assert_awaited_once()
    scheduled.assert_awaited_once()
    maintenance.assert_awaited_once()
    dreaming.assert_awaited_once()
