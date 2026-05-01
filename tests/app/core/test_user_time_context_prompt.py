"""unit tests for shared user time context markdown."""

from __future__ import annotations

from app.core.agent.agent import UserTimeContext, _build_user_time_context_prompt
from app.core.user_time_context_prompt import build_user_time_context_markdown


def test_build_user_time_context_markdown_matches_agent_wrapper() -> None:
    ctx: UserTimeContext = {
        "local_time": "2026-05-01T10:00:00",
        "timezone": "Europe/Berlin",
        "utc_offset_minutes": 120,
    }
    assert _build_user_time_context_prompt(ctx) == build_user_time_context_markdown(ctx)


def test_build_user_time_context_markdown_empty_mapping() -> None:
    assert build_user_time_context_markdown({}) is None
    assert build_user_time_context_markdown(None) is None
