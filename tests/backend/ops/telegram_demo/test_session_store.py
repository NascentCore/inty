"""Tests for in-memory telegram-demo session store."""

from __future__ import annotations

import pytest

from backend.ops.telegram_demo.binding import TelegramDemoBinding
from backend.ops.telegram_demo import session_store
from backend.ops.telegram_demo.session_store import (
    clear_all_for_tests,
    get_binding,
    remove_binding,
)


@pytest.fixture(autouse=True)
def _reset_store() -> None:
    clear_all_for_tests()
    yield
    clear_all_for_tests()


@pytest.mark.asyncio
async def test_session_store_put_get_remove() -> None:
    binding = TelegramDemoBinding(
        telegram_chat_id="12345",
        user_id="user-1",
        agent_id="agent-1",
        chat_id="chat-1",
    )
    session_store._bindings_by_chat_id[binding.telegram_chat_id] = binding
    assert get_binding("12345") == binding
    remove_binding("12345")
    assert get_binding("12345") is None
