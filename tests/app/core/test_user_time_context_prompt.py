"""Tests for tail-user time context suffix formatting."""

from __future__ import annotations

import pytest

from app.core.agent.agent import UserTimeContext
from app.core.user_time_context_prompt import suffix_user_text_with_time_context_lines


def test_suffix_disabled_returns_unchanged() -> None:
    ctx: UserTimeContext = {
        "local_time": "2026-05-01T10:00:00",
        "timezone": "Europe/Berlin",
        "utc_offset_minutes": 120,
    }
    assert suffix_user_text_with_time_context_lines("hi", ctx, enabled=False) == "hi"


def test_suffix_enabled_empty_context_returns_unchanged() -> None:
    assert suffix_user_text_with_time_context_lines("hi", None, enabled=True) == "hi"
    assert suffix_user_text_with_time_context_lines("hi", {}, enabled=True) == "hi"


def test_suffix_omits_blank_fields() -> None:
    ctx: UserTimeContext = {"local_time": "  ", "timezone": ""}
    assert suffix_user_text_with_time_context_lines("x", ctx, enabled=True) == "x"


def test_suffix_user_time_and_time_zone_lines() -> None:
    ctx: UserTimeContext = {
        "local_time": "2026-05-01T10:00:00",
        "timezone": "Europe/Berlin",
        "utc_offset_minutes": 120,
    }
    out = suffix_user_text_with_time_context_lines("body", ctx, enabled=True)
    assert out.startswith("body\n\n")
    assert "User's time: 2026/05/01 10:00" in out
    assert "Time zone: Europe/Berlin" in out
    assert "user-time-utc-offset" not in out


@pytest.mark.parametrize(
    ("enabled", "expect_suffix"),
    [
        (True, True),
        (False, False),
    ],
)
def test_suffix_partial_fields(enabled: bool, expect_suffix: bool) -> None:
    ctx: UserTimeContext = {"timezone": "UTC"}
    out = suffix_user_text_with_time_context_lines("m", ctx, enabled=enabled)
    if expect_suffix:
        assert out == "m\n\nTime zone: UTC"
    else:
        assert out == "m"
