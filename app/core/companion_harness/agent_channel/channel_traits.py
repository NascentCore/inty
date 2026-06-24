"""Per-channel harness traits registered in one place.

New channels add rows here instead of scattering match arms across companion modules.
TODO(cross-channel-consistent-identity): #3491 — route onboard traits through shared identity service.
"""

from __future__ import annotations

from app.core.companion_harness.agent_channel.channel_kind import (
    ChannelKind,
    is_im_channel,
)
from app.core.companion_harness.prompting.bundle import PromptBundle


def guest_agent_name_for_channel(*, channel: ChannelKind, tag: str) -> str:
    """Channel-specific PRIVATE agent display name."""
    assert tag != ""
    match channel:
        case ChannelKind.APP_WS:
            return f"agent-channel-{tag}"
        case ChannelKind.TELEGRAM:
            return f"telegram-{tag}"
        case ChannelKind.WECHAT_WEIXIN:
            return f"weixin-companion-{tag}"
        case ChannelKind.SMS:
            return f"sms-{tag}"
        case _:
            raise AssertionError(f"unsupported channel: {channel!r}")


def harness_output_format_slice(
    *,
    bundle: PromptBundle,
    channel: ChannelKind,
) -> str:
    """Resolve harness output-format system slice for one channel turn."""
    match channel:
        case ChannelKind.SMS | ChannelKind.APP_WS:
            return ""
        case ch if is_im_channel(ch):
            return bundle.output_format_im_dm_md
        case _:
            return ""
