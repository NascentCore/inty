"""Tests for active gateway exclusivity registry."""

from __future__ import annotations

from app.core.companion_harness.agent_channel.channel_kind import ChannelKind
from app.services.agentic_companion.active_channel_registry import (
    clear_all_for_tests,
    other_active_channel,
    register_active_channel,
)


def test_active_channel_registry_detects_telegram_conflict() -> None:
    clear_all_for_tests()
    user_id = "user-gateway-test"
    register_active_channel(user_id=user_id, channel=ChannelKind.TELEGRAM,
    )
    conflict = other_active_channel(
        user_id=user_id,
        desired=ChannelKind.APP_WS,
    )
    assert conflict == ChannelKind.TELEGRAM
    clear_all_for_tests()


def test_active_channel_registry_detects_sms_conflict() -> None:
    clear_all_for_tests()
    user_id = "user-gateway-sms-test"
    register_active_channel(user_id=user_id, channel=ChannelKind.SMS,
    )
    conflict = other_active_channel(
        user_id=user_id,
        desired=ChannelKind.APP_WS,
    )
    assert conflict == ChannelKind.SMS
    clear_all_for_tests()
