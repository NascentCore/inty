"""tool_bg_routing JSON envelope parsing."""

from __future__ import annotations

from app.core.agentic_kernel.companion.tool_bg_routing import (
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
