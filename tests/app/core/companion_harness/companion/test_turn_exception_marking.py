"""Regression tests for companion turn exception ownership markers."""

from __future__ import annotations

from app.core.companion_harness.companion.turn import (
    CompanionToolBackgroundStartedError,
)


def test_tool_background_started_marker_lives_on_wrapper_exception() -> None:
    original = RuntimeError("foreground failed after tool_background start")

    wrapped = CompanionToolBackgroundStartedError(original)

    assert wrapped.companion_tool_background_started is True
    assert wrapped.original_exception is original
    assert str(wrapped) == "foreground failed after tool_background start"
    assert not hasattr(original, "companion_tool_background_started")
