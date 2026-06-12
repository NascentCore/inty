"""Tests for ``parse_start_payload``."""

from __future__ import annotations

from backend.ops.telegram_demo.binding import (
    StartPayloadKind,
    parse_start_agent_id,
    parse_start_payload,
)


def test_parse_start_payload_onboard_bare() -> None:
    payload = parse_start_payload("/start")
    assert payload.kind == StartPayloadKind.ONBOARD
    assert payload.agent_id is None


def test_parse_start_payload_onboard_explicit() -> None:
    payload = parse_start_payload("/start onboard")
    assert payload.kind == StartPayloadKind.ONBOARD


def test_parse_start_payload_onboard_with_bot_username() -> None:
    payload = parse_start_payload("/start@MyBot onboard")
    assert payload.kind == StartPayloadKind.ONBOARD


def test_parse_start_payload_agent_id() -> None:
    payload = parse_start_payload("/start agent_abc-123")
    assert payload.kind == StartPayloadKind.AGENT_ID
    assert payload.agent_id == "abc-123"


def test_parse_start_payload_none() -> None:
    payload = parse_start_payload("hello")
    assert payload.kind == StartPayloadKind.NONE


def test_parse_start_agent_id_legacy_helper() -> None:
    assert parse_start_agent_id("/start agent_uuid-here") == "uuid-here"
