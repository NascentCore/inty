"""Canonical gateway kinds for human-facing companion media.

Generated entirely by Cursor agent.

``GatewayKind`` is the single wire-stable enum for every human-facing medium.
Adapters declare ``GatewayKind``; do not introduce parallel channel enums.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.schemas.implicit_signals import ImplicitSignalBundle


class GatewayKind(StrEnum):
    """Human-facing medium between the companion and the human user."""

    APP_WS = "app_ws"
    WECHAT_WEIXIN = "wechat_weixin"
    TELEGRAM = "telegram"
    SMS = "sms"


def is_im_gateway(gateway: GatewayKind) -> bool:
    """True when the turn is delivered on an instant-messaging surface (not the app)."""
    match gateway:
        case GatewayKind.WECHAT_WEIXIN | GatewayKind.TELEGRAM:
            return True
        case GatewayKind.APP_WS | GatewayKind.SMS:
            return False


@dataclass(frozen=True)
class TurnRuntimeContext:
    """Runtime facts for one companion turn, separate from prompt documents."""

    gateway: GatewayKind
    implicit_signal_bundle: ImplicitSignalBundle | None
