"""Runtime communication channel selection for companion prompt assembly.

TODO(rename-channel-to-gateway): Move ``TurnRuntimeContext`` to ``agent_channel/gateway.py`` — #3548
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.companion_harness.agent_channel.gateway import GatewayKind
from app.schemas.implicit_signals import ImplicitSignalBundle

ChannelKind = GatewayKind


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
