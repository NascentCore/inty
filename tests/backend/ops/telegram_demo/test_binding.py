"""Tests for Telegram ``/start`` payload parsing."""

from __future__ import annotations

from backend.ops.telegram_demo.binding import parse_start_agent_id


def test_parse_start_agent_id_plain() -> None:
    assert parse_start_agent_id("/start agent_abc-123") == "abc-123"


def test_parse_start_agent_id_with_bot_username() -> None:
    assert (
        parse_start_agent_id("/start@MyBot agent_uuid-here") == "uuid-here"
    )


def test_parse_start_agent_id_rejects_missing_agent_prefix() -> None:
    assert parse_start_agent_id("/start hello") is None


def test_parse_start_agent_id_rejects_non_start() -> None:
    assert parse_start_agent_id("hello") is None
