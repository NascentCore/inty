"""TelegramTransport routes inbound text by telegram chat_id."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.external_services.telegram_bot_api import TelegramIncomingMessage
from backend.ops.telegram_demo.binding import TelegramDemoBinding
from backend.ops.telegram_demo.session_store import clear_all_for_tests, put_binding
from backend.ops.telegram_demo.transport import TelegramTransport


@pytest.mark.asyncio
async def test_handle_inbound_routes_text_to_binding_chat_id() -> None:
    clear_all_for_tests()
    api = MagicMock()
    transport = TelegramTransport(api=api)
    binding = TelegramDemoBinding(
        telegram_chat_id="5078060274",
        user_id="user-a",
        agent_id="agent-a",
        chat_id="chat-a",
    )
    with patch(
        "backend.ops.telegram_demo.session_store.persist_binding_row",
        new_callable=AsyncMock,
    ):
        await put_binding(binding)

    presence = MagicMock()
    presence.handle_user_text = AsyncMock(return_value="reply-from-a")
    with patch(
        "backend.ops.telegram_demo.transport.get_or_create_presence",
        return_value=presence,
    ):
        inbound = TelegramIncomingMessage(
            update_id=1,
            chat_id="5078060274",
            text="你好",
            local_received_at=time.time(),
        )
        reply = await transport._handle_inbound(inbound)

    presence.handle_user_text.assert_awaited_once_with("你好")
    assert reply == "reply-from-a"
    clear_all_for_tests()


@pytest.mark.asyncio
async def test_handle_inbound_unknown_chat_prompts_onboard() -> None:
    clear_all_for_tests()
    transport = TelegramTransport(api=MagicMock())
    inbound = TelegramIncomingMessage(
        update_id=2,
        chat_id="999",
        text="hello",
        local_received_at=time.time(),
    )
    reply = await transport._handle_inbound(inbound)
    assert "onboard" in reply
    clear_all_for_tests()
