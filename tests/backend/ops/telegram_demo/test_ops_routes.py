"""Ops mounts telegram-demo onboard page and debug bindings API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.routing import APIRoute

from backend.ops.main import app


def test_ops_mounts_telegram_demo_page() -> None:
    paths = [
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
    ]
    assert "/telegram-demo" in paths


@pytest.mark.asyncio
async def test_telegram_demo_bindings_api_lists_rows() -> None:
    from backend.ops.api.v1.telegram_demo import telegram_demo_bindings

    fake_row = type(
        "Row",
        (),
        {
            "telegram_chat_id": "123",
            "user_id": "user-1",
            "agent_id": "agent-1",
            "chat_id": "chat-1",
        },
    )()
    with patch(
        "backend.ops.api.v1.telegram_demo.list_bindings",
        new_callable=AsyncMock,
        return_value=[fake_row],
    ):
        resp = await telegram_demo_bindings()
    assert resp.data.count == 1
    assert resp.data.bindings[0].telegram_chat_id == "123"
