"""Ops mounts telegram-demo onboard page and debug bindings API."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.routing import APIRoute

from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from backend.ops.main import app


def test_ops_mounts_telegram_demo_page() -> None:
    paths = [
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
    ]
    assert "/telegram-demo" in paths


@dataclass(frozen=True)
class _FakeEndpoint:
    user_id: str
    agent_id: str
    channel: CompanionRuntimeChannel
    channel_address: str
    channel_user_id: str


@pytest.mark.asyncio
async def test_telegram_demo_bindings_api_lists_rows() -> None:
    from backend.ops.api.v1.telegram_demo import telegram_demo_bindings

    fake_row = _FakeEndpoint(
        channel_address="123",
        channel_user_id="456",
        user_id="user-1",
        agent_id="agent-1",
        channel=CompanionRuntimeChannel.TELEGRAM,
    )
    with patch(
        "backend.ops.api.v1.telegram_demo.list_endpoints_for_channel",
        new_callable=AsyncMock,
        return_value=[fake_row],
    ):
        resp = await telegram_demo_bindings()
    assert resp.data.count == 1
    assert resp.data.bindings[0].channel_address == "123"
