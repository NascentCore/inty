"""Per-gateway harness traits registered in one place.

Generated entirely by Cursor agent.

New gateways add rows here instead of scattering match arms across companion modules.
"""

from __future__ import annotations

from app.core.companion_harness.agent_channel.gateway import GatewayKind
from app.core.companion_harness.agent_channel.guest_agent_kind import (
    CompanionGuestAgentKind,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    is_im_runtime_channel,
)
from app.core.companion_harness.prompting.bundle import PromptBundle


def guest_agent_kind_for_gateway(gateway: GatewayKind) -> CompanionGuestAgentKind:
    """Map gateway to default onboard agent copy template."""
    match gateway:
        case GatewayKind.TELEGRAM:
            return CompanionGuestAgentKind.TELEGRAM
        case GatewayKind.WECHAT_WEIXIN:
            return CompanionGuestAgentKind.WEIXIN
        case GatewayKind.SMS:
            return CompanionGuestAgentKind.SMS
        case GatewayKind.APP_WS:
            return CompanionGuestAgentKind.AGENT_CHANNEL
        case _:
            raise AssertionError(f"unsupported gateway: {gateway!r}")


def guest_agent_name_for_gateway(*, gateway: GatewayKind, tag: str) -> str:
    """Channel-specific PRIVATE agent display name."""
    assert tag != ""
    match gateway:
        case GatewayKind.AGENT_CHANNEL:
            return f"agent-channel-{tag}"
        case GatewayKind.TELEGRAM:
            return f"telegram-{tag}"
        case GatewayKind.WECHAT_WEIXIN:
            return f"weixin-companion-{tag}"
        case GatewayKind.SMS:
            return f"sms-{tag}"


def harness_output_format_slice(
    *,
    bundle: PromptBundle,
    runtime_channel: ChannelKind,
) -> str:
    """Resolve harness output-format system slice for one gateway turn."""
    match runtime_channel:
        case ChannelKind.SMS | ChannelKind.APP_WS:
            return ""
        case channel if is_im_runtime_channel(channel):
            return bundle.output_format_im_dm_md
        case _:
            return ""
