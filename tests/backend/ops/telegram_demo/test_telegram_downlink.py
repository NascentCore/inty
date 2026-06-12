"""Tests for TelegramDownlink sendMessage routing."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.agentic_companion.downlink import (
    Downlink,
    DownlinkKind,
)
from backend.ops.telegram_demo.telegram_downlink import TelegramDownlink


@pytest.mark.asyncio
async def test_telegram_downlink_send_assistant_text_targets_bound_chat() -> None:
    api = MagicMock()
    downlink = TelegramDownlink(
        api=api,
        chat_id_resolver=lambda: "5078060274",
    )
    await downlink.send_assistant_text("hello teammate")
    api.send_message.assert_called_once_with(
        chat_id="5078060274",
        text="hello teammate",
    )


@pytest.mark.asyncio
async def test_telegram_downlink_deliver_proactive() -> None:
    api = MagicMock()
    downlink = TelegramDownlink(
        api=api,
        chat_id_resolver=lambda: "111",
    )
    await downlink.deliver(
        Downlink(
            kind=DownlinkKind.PROACTIVE,
            assistant_text=" proactive ",
            turn=None,
            tool_output=None,
            bootstrap_interim=None,
            scheduled_task_id=None,
            transcript_user_text=None,
        )
    )
    api.send_message.assert_called_once_with(
        chat_id="111",
        text="proactive",
    )
