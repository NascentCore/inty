"""Tests for in-memory telegram-demo session store."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.ops.telegram_demo.binding import TelegramDemoBinding
from backend.ops.telegram_demo.session_store import (
    clear_all_for_tests,
    get_binding,
    put_binding,
    remove_binding,
)


@pytest.mark.asyncio
async def test_session_store_put_get_remove() -> None:
    clear_all_for_tests()
    binding = TelegramDemoBinding(
        telegram_chat_id="12345",
        user_id="user-1",
        agent_id="agent-1",
        chat_id="chat-1",
    )
    with patch(
        "backend.ops.telegram_demo.session_store.persist_binding_row",
        new_callable=AsyncMock,
    ):
        await put_binding(binding)
    assert get_binding("12345") == binding
    remove_binding("12345")
    assert get_binding("12345") is None
    clear_all_for_tests()
