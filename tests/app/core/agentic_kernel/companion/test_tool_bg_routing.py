"""tool_bg_routing JSON envelope parsing."""

from __future__ import annotations

from app.core.agentic_kernel.companion.tool_bg_routing import (
    parse_tool_bg_first_round_skip,
    parse_tool_bg_first_round_skip_details,
    parse_tool_bg_routing_content,
)


def test_parse_tool_bg_routing_plain_json() -> None:
    p = parse_tool_bg_routing_content(
        '{"output_to_user": true, "user_visible_text": "hello"}'
    )
    assert p is not None
    assert p.output_to_user is True
    assert p.user_visible_text == "hello"


def test_parse_tool_bg_routing_fence() -> None:
    raw = "```json\n{\"output_to_user\": false, \"user_visible_text\": \"\"}\n```"
    p = parse_tool_bg_routing_content(raw)
    assert p is not None
    assert p.output_to_user is False


def test_parse_tool_bg_routing_invalid_returns_none() -> None:
    assert parse_tool_bg_routing_content("not json") is None
    assert parse_tool_bg_routing_content("") is None


def test_parse_tool_bg_first_round_skip_plain_json() -> None:
    p = parse_tool_bg_first_round_skip('{"skip": true}')
    assert p is not None
    assert p.skip is True
    p2 = parse_tool_bg_first_round_skip('{"skip": false}')
    assert p2 is not None
    assert p2.skip is False


def test_parse_tool_bg_first_round_skip_fence() -> None:
    raw = "```json\n{\"skip\": true}\n```"
    p = parse_tool_bg_first_round_skip(raw)
    assert p is not None
    assert p.skip is True


def test_parse_tool_bg_first_round_skip_invalid_returns_none() -> None:
    assert parse_tool_bg_first_round_skip("not json") is None
    assert parse_tool_bg_first_round_skip("") is None
    assert parse_tool_bg_first_round_skip("{}") is None


def test_parse_tool_bg_first_round_skip_details_success() -> None:
    env, reason = parse_tool_bg_first_round_skip_details('{"skip": true}')
    assert env is not None and env.skip is True
    assert reason is None


def test_parse_tool_bg_first_round_skip_details_failure_reasons() -> None:
    env, reason = parse_tool_bg_first_round_skip_details("")
    assert env is None and reason == "empty_after_strip"

    env2, reason2 = parse_tool_bg_first_round_skip_details("not json")
    assert env2 is None and reason2 is not None and reason2.startswith("json_decode:")

    env3, reason3 = parse_tool_bg_first_round_skip_details("{}")
    assert env3 is None and reason3 is not None and reason3.startswith("validation:")
