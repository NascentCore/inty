"""Regression: tool_background transcript body merges NL routing with tool digest."""

from __future__ import annotations

from app.core.agentic_kernel.companion.tool_background import (
    TOOL_RESULTS_TRANSCRIPT_MARKER,
    build_tool_background_transcript_body,
)


def test_build_tool_background_transcript_body_merges_nl_and_digest() -> None:
    appended = [
        {
            "role": "assistant",
            "tool_calls": [{"id": "c1", "function": {"name": "demo"}}],
        },
        {"role": "tool", "tool_call_id": "c1", "content": "demo_tool_ok"},
    ]
    body = build_tool_background_transcript_body(
        display_text="Routing line for user.",
        appended_turn_msgs=appended,
        total_tool_calls=1,
    )
    assert "Routing line for user." in body
    assert TOOL_RESULTS_TRANSCRIPT_MARKER in body
    assert "demo_tool_ok" in body


def test_build_tool_background_transcript_body_digest_only_when_nl_empty() -> None:
    appended = [
        {"role": "tool", "tool_call_id": "c1", "content": "only_tool"},
    ]
    body = build_tool_background_transcript_body(
        display_text="",
        appended_turn_msgs=appended,
        total_tool_calls=1,
    )
    assert body.startswith(TOOL_RESULTS_TRANSCRIPT_MARKER)
    assert "only_tool" in body
