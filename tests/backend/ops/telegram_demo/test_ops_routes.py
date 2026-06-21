"""Ops mounts telegram onboard page and debug bindings API."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.config import global_config_loaded_from_config_yaml
from backend.ops.api.telegram_web import _TELEGRAM_ONBOARD_HTML
from backend.ops.api.v1.router import api_router
from backend.ops.main import app


def _telegram_paths_on_api_router() -> list[str]:
    return [
        route.path
        for route in api_router.routes
        if isinstance(route, APIRoute) and "telegram" in route.path
    ]


def test_ops_mounts_telegram_onboard_page() -> None:
    paths = [route.path for route in app.routes if isinstance(route, APIRoute)]
    assert "/telegram" in paths
    assert "/api/v1/telegram/bot-info" in paths


def test_api_router_telegram_product_route_always_mounted() -> None:
    paths = _telegram_paths_on_api_router()
    assert "/api/v1/telegram/bot-info" in paths


def test_api_router_debug_bindings_follows_config() -> None:
    paths = _telegram_paths_on_api_router()
    if global_config_loaded_from_config_yaml.app.debug:
        assert "/api/v1/telegram-demo/bindings" in paths
    else:
        assert "/api/v1/telegram-demo/bindings" not in paths


def test_telegram_onboard_html_uses_product_api() -> None:
    assert "/api/v1/telegram" in _TELEGRAM_ONBOARD_HTML
    assert "telegram-demo" not in _TELEGRAM_ONBOARD_HTML
    assert "Demo" not in _TELEGRAM_ONBOARD_HTML


def test_telegram_bot_info_http_route_exists() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/telegram/bot-info")
    assert response.status_code in (200, 502, 503)


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
