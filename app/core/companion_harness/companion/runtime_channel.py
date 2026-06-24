"""Runtime communication channel selection for companion prompt assembly.

TODO(rename-channel-to-gateway): Rename interim ``ChannelKind`` → ``GatewayKind``; move enum + — #3548
``TurnRuntimeContext`` to ``agent_channel/gateway.py`` (#3409). Harness traits in
``agent_channel/gateway_traits.py`` (functions/registry, not class hierarchy).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.schemas.implicit_signals import ImplicitSignalBundle


class ChannelKind(StrEnum):
    """Human-facing medium between the companion and the human users.

    This enum is used to identify the channel type for the companion turn.
    Each type of channel ties to a specific Gateway class,
    which orchestrates the communication between the companion and the human users.
    """

    APP_WS = "app_ws"
    WECHAT_WEIXIN = "wechat_weixin"
    TELEGRAM = "telegram"
    SMS = "sms"


def is_im_runtime_channel(channel: ChannelKind) -> bool:
    """True when the turn is delivered on an instant-messaging surface (not the app)."""
    match channel:
        case ChannelKind.WECHAT_WEIXIN | ChannelKind.TELEGRAM:
            return True
        case ChannelKind.APP_WS | ChannelKind.SMS:
            return False


@dataclass(frozen=True)
class TurnRuntimeContext:
    """Runtime facts for one companion turn, separate from prompt documents."""

    channel: ChannelKind
    implicit_signal_bundle: ImplicitSignalBundle | None
