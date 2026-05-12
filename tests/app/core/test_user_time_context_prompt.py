"""Tests for tail-user time context suffix formatting."""

from __future__ import annotations

import pytest

from app.core.agent.agent import UserTimeContext
from app.core.user_time_context_prompt import (
    format_utc_offset_minutes,
    suffix_user_text_with_time_context_lines,
)


def test_suffix_disabled_returns_unchanged() -> None:
    ctx: UserTimeContext = {
        "local_time": "2026-05-01T10:00:00",
        "timezone": "Europe/Berlin",
        "utc_offset_minutes": 120,
    }
    assert (
        suffix_user_text_with_time_context_lines("hi", ctx, enabled=False) == "hi"
    )


def test_suffix_enabled_empty_context_returns_unchanged() -> None:
    assert suffix_user_text_with_time_context_lines("hi", None, enabled=True) == "hi"
    assert suffix_user_text_with_time_context_lines("hi", {}, enabled=True) == "hi"


def test_suffix_omits_blank_fields() -> None:
    ctx: UserTimeContext = {"local_time": "  ", "timezone": ""}
    assert suffix_user_text_with_time_context_lines("x", ctx, enabled=True) == "x"


def test_suffix_all_three_lines() -> None:
    ctx: UserTimeContext = {
        "local_time": "2026-05-01T10:00:00",
        "timezone": "Europe/Berlin",
        "utc_offset_minutes": 120,
    }
    out = suffix_user_text_with_time_context_lines("body", ctx, enabled=True)
    assert out.startswith("body\n\n")
    assert "user-time: 2026-05-01T10:00:00" in out
    assert "user-time-zone: Europe/Berlin" in out
    assert "user-time-utc-offset: UTC+02:00" in out


def test_format_utc_offset_minutes_negative() -> None:
    assert format_utc_offset_minutes(-330) == "UTC-05:30"


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
        assert out == "m\n\nuser-time-zone: UTC"
    else:
        assert out == "m"
