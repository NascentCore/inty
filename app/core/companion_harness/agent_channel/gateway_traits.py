"""Per-gateway harness traits registered in one place.

Generated entirely by Cursor agent.

New gateways add rows here instead of scattering match arms across companion modules.
TODO(cross-channel-consistent-identity): #3491 — route onboard traits through shared identity service.
"""

from __future__ import annotations

from app.core.companion_harness.agent_channel.gateway import (
    GatewayKind,
    is_im_gateway,
)
from app.core.companion_harness.prompting.bundle import PromptBundle


def guest_agent_name_for_gateway(*, gateway: GatewayKind, tag: str) -> str:
    """Gateway-specific PRIVATE agent display name."""
    assert tag != ""
    match gateway:
        case GatewayKind.APP_WS:
            return f"agent-channel-{tag}"
        case GatewayKind.TELEGRAM:
            return f"telegram-{tag}"
        case GatewayKind.WECHAT_WEIXIN:
            return f"weixin-companion-{tag}"
        case GatewayKind.SMS:
            return f"sms-{tag}"
        case _:
            raise AssertionError(f"unsupported gateway: {gateway!r}")


def harness_output_format_slice(
    *,
    bundle: PromptBundle,
    gateway: GatewayKind,
) -> str:
    """Resolve harness output-format system slice for one gateway turn."""
    match gateway:
        case GatewayKind.SMS | GatewayKind.APP_WS:
            return ""
        case gateway if is_im_gateway(gateway):
            return bundle.output_format_im_dm_md
        case _:
            return ""
