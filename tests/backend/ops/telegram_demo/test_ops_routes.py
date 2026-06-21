"""Ops mounts telegram onboard page and debug bindings API."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import APIRouter
from fastapi.routing import APIRoute

from app.api.constants import API_V1_PREFIX
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from backend.ops.api.telegram_web import _TELEGRAM_ONBOARD_HTML
from backend.ops.api.v1 import telegram, telegram_demo
from backend.ops.main import app


def _telegram_api_paths(*, debug: bool) -> list[str]:
    router = APIRouter(prefix=API_V1_PREFIX)
    router.include_router(telegram.router)
    if debug:
        router.include_router(telegram_demo.router)
    return [route.path for route in router.routes if isinstance(route, APIRoute)]


def test_ops_mounts_telegram_onboard_page() -> None:
    paths = [route.path for route in app.routes if isinstance(route, APIRoute)]
    assert "/telegram" in paths


def test_telegram_product_api_paths() -> None:
    paths = _telegram_api_paths(debug=False)
    assert "/api/v1/telegram/bot-info" in paths
    assert "/api/v1/telegram-demo/bindings" not in paths


def test_telegram_debug_bindings_only_when_debug() -> None:
    debug_paths = _telegram_api_paths(debug=True)
    prod_paths = _telegram_api_paths(debug=False)
    assert "/api/v1/telegram-demo/bindings" in debug_paths
    assert "/api/v1/telegram-demo/bindings" not in prod_paths
    assert "/api/v1/telegram/bot-info" in prod_paths


def test_telegram_onboard_html_uses_product_api() -> None:
    assert "/api/v1/telegram" in _TELEGRAM_ONBOARD_HTML
    assert "telegram-demo" not in _TELEGRAM_ONBOARD_HTML
    assert "Demo" not in _TELEGRAM_ONBOARD_HTML


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
