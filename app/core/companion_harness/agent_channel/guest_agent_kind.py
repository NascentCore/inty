"""Companion guest onboard kind mapped from ``CompanionRuntimeChannel``."""

from __future__ import annotations

from enum import StrEnum

from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)


class CompanionGuestAgentKind(StrEnum):
    """Onboard surface selecting default PRIVATE agent copy."""

    AGENT_CHANNEL = "agent_channel"
    TELEGRAM = "telegram"
    WEIXIN = "weixin"


def companion_guest_agent_kind_for_channel(
    channel: CompanionRuntimeChannel,
) -> CompanionGuestAgentKind:
    """Map runtime channel to default onboard agent copy template."""
    match channel:
        case CompanionRuntimeChannel.TELEGRAM:
            return CompanionGuestAgentKind.TELEGRAM
        case CompanionRuntimeChannel.WECHAT_WEIXIN:
            return CompanionGuestAgentKind.WEIXIN
        case CompanionRuntimeChannel.APP:
            return CompanionGuestAgentKind.AGENT_CHANNEL
        case _:
            raise AssertionError(
                f"unsupported companion runtime channel: {channel!r}"
            )
