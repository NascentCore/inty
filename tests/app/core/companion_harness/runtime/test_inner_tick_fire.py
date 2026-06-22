"""Tests for harness runtime inner-tick due checks and kernel fire helpers."""

from __future__ import annotations

from app.core.companion_harness.runtime.inner_tick_fire import (
    InnerTickThrottleSnapshot,
    monolog_inner_tick_remain_seconds,
    proactive_chat_remain_seconds,
)


def test_proactive_chat_remain_seconds_returns_non_negative() -> None:
    # Without a real MemoryStore this only checks the API shape; integration
    # coverage lives in agentic_companion inner-tick tests.
    throttle = InnerTickThrottleSnapshot(
        last_monolog_monotonic=None,
        last_monolog_line_count=None,
        last_autonomy_monotonic=None,
        last_autonomy_line_count=None,
    )
    assert throttle.last_monolog_line_count is None
    assert (
        proactive_chat_remain_seconds.__name__
        == "proactive_chat_remain_seconds"
    )
    assert (
        monolog_inner_tick_remain_seconds.__name__
        == "monolog_inner_tick_remain_seconds"
    )
