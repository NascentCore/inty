"""Tests for tool_background image GENERATION deliver."""

from __future__ import annotations

from app.core.companion_harness.companion.models import InnerTickActivity
from app.core.companion_harness.tools.tool_background import (
    _generation_tool_execution_deliver,
    tool_background_should_deliver_to_user,
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


def test_autonomy_inner_tick_never_delivers_despite_generation_deliver() -> (
    None
):
    assert not tool_background_should_deliver_to_user(
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.AUTONOMY,
        generation_deliver=True,
        output_to_user=True,
    )


def test_maintenance_inner_tick_still_delivers_on_generation_deliver() -> None:
    assert tool_background_should_deliver_to_user(
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        generation_deliver=True,
        output_to_user=False,
    )
