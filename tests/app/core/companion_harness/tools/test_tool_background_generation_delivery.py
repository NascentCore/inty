"""Tests for tool_background image GENERATION deliver."""

from __future__ import annotations

from app.core.companion_harness.tools.tool_background import (
    _generation_tool_execution_deliver,
)


def test_generation_deliver_true_when_image_paths_present() -> None:
    appended = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "tc1",
                    "function": {"name": "generate_image"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "tc1",
            "content": "OK local_path=/tmp/out.png",
        },
    ]
    assert _generation_tool_execution_deliver(
        appended,
        ["generate_image"],
        ["/tmp/out.png"],
    )
