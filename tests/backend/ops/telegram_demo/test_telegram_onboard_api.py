"""Tests for product Telegram onboard API (GET /api/v1/telegram/bot-info)."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from backend.ops.api.v1.telegram import telegram_bot_info


@dataclass(frozen=True)
class _FakeMe:
    bot_id: int
    username: str


@pytest.mark.asyncio
async def test_telegram_bot_info_returns_username() -> None:
    with (
        patch(
            "backend.ops.api.v1.telegram.resolved_telegram_bot_token",
            return_value="test-token",
        ),
        patch("backend.ops.api.v1.telegram.TelegramBotApi") as mock_api_cls,
    ):
        mock_api_cls.return_value.get_me.return_value = _FakeMe(
            bot_id=42,
            username="inty_bot",
        )
        resp = await telegram_bot_info()
    assert resp.data.bot_id == 42
    assert resp.data.bot_username == "inty_bot"


@pytest.mark.asyncio
async def test_telegram_bot_info_503_when_token_missing() -> None:
    with patch(
        "backend.ops.api.v1.telegram.resolved_telegram_bot_token",
        return_value="",
    ):
        with pytest.raises(HTTPException) as exc_info:
            await telegram_bot_info()
    assert exc_info.value.status_code == 503
