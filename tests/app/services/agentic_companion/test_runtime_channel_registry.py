"""Tests for runtime channel exclusivity registry."""

from __future__ import annotations

from app.services.agentic_companion.runtime_channel_registry import (
    ActiveRuntimeChannel,
    clear_all_for_tests,
    other_active_channel,
    register_active_channel,
)


def test_channel_registry_detects_telegram_conflict() -> None:
    clear_all_for_tests()
    user_id = "user-channel-test"
    register_active_channel(
        user_id=user_id,
        channel=ActiveRuntimeChannel.TELEGRAM,
    )
    conflict = other_active_channel(
        user_id=user_id,
        desired=ActiveRuntimeChannel.APP,
    )
    assert conflict == ActiveRuntimeChannel.TELEGRAM
    clear_all_for_tests()
