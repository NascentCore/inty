"""Companion guest onboard kind mapped from ``ChannelKind``.

TODO(rename-channel-to-gateway): Move ``companion_guest_agent_kind_for_channel`` to — #3548
``agent_channel/gateway_traits.py`` when ``gateway.py`` lands (#3409).
"""

from __future__ import annotations

from enum import StrEnum

from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)


class CompanionGuestAgentKind(StrEnum):
    """Onboard surface selecting default PRIVATE agent copy."""

    AGENT_CHANNEL = "agent_channel"
    TELEGRAM = "telegram"
    WEIXIN = "weixin"


def companion_guest_agent_kind_for_channel(
    channel: ChannelKind,
) -> CompanionGuestAgentKind:
    """Map runtime channel to default onboard agent copy template."""
    match channel:
        case ChannelKind.TELEGRAM:
            return CompanionGuestAgentKind.TELEGRAM
        case ChannelKind.WECHAT_WEIXIN:
            return CompanionGuestAgentKind.WEIXIN
        case ChannelKind.APP_WS:
            return CompanionGuestAgentKind.AGENT_CHANNEL
        case _:
            raise AssertionError(
                f"unsupported companion runtime channel: {channel!r}"
            )
