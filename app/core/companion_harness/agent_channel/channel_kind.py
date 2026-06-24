"""Canonical channel kinds for human-facing companion media.

``ChannelKind`` is the single wire-stable enum for every human-facing medium.
Adapters declare ``ChannelKind``; do not introduce parallel channel enums.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.schemas.implicit_signals import ImplicitSignalBundle


class ChannelKind(StrEnum):
    """Human-facing medium between the companion and the human user."""

    APP_WS = "app_ws"
    WECHAT_WEIXIN = "wechat_weixin"
    TELEGRAM = "telegram"
    SMS = "sms"


def is_im_channel(channel: ChannelKind) -> bool:
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
