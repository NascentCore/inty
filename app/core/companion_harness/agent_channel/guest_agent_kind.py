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
    SMS = "sms"


def companion_guest_agent_kind_for_channel(
    channel: ChannelKind,
) -> CompanionGuestAgentKind:
    """Map runtime channel to default onboard agent copy template."""
    from app.core.companion_harness.agent_channel.gateway import GatewayKind
    from app.core.companion_harness.agent_channel.gateway_traits import (
        guest_agent_kind_for_gateway,
    )

    return guest_agent_kind_for_gateway(GatewayKind(channel.value))
