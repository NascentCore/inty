"""Tests for ``parse_start_payload``."""

from __future__ import annotations

from backend.ops.telegram_demo.binding import StartPayloadKind, parse_start_payload


def test_parse_start_payload_bare_start() -> None:
    payload = parse_start_payload("/start")
    assert payload.kind == StartPayloadKind.ONBOARD


def test_parse_start_payload_bare_start_with_bot_username() -> None:
    payload = parse_start_payload("/start@MyBot")
    assert payload.kind == StartPayloadKind.ONBOARD


def test_parse_start_payload_start_with_payload_is_none() -> None:
    payload = parse_start_payload("/start onboard")
    assert payload.kind == StartPayloadKind.NONE


def test_parse_start_payload_start_with_bot_username_and_payload_is_none() -> None:
    payload = parse_start_payload("/start@MyBot onboard")
    assert payload.kind == StartPayloadKind.NONE


def test_parse_start_payload_unknown_start_token_is_none() -> None:
    payload = parse_start_payload("/start agent_abc-123")
    assert payload.kind == StartPayloadKind.NONE


def test_parse_start_payload_none() -> None:
    payload = parse_start_payload("hello")
    assert payload.kind == StartPayloadKind.NONE
