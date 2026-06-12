"""Runtime communication channel selection for companion prompt assembly."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.schemas.implicit_signals import ImplicitSignalBundle


class CompanionRuntimeChannel(StrEnum):
    """Human-facing medium carrying this companion turn."""

    APP = "app"
    WECHAT_WEIXIN = "wechat_weixin"
    TELEGRAM = "telegram"


def is_im_runtime_channel(channel: CompanionRuntimeChannel) -> bool:
    """True when the turn is delivered on an instant-messaging surface (not the app)."""
    match channel:
        case (
            CompanionRuntimeChannel.WECHAT_WEIXIN
            | CompanionRuntimeChannel.TELEGRAM
        ):
            return True
        case CompanionRuntimeChannel.APP:
            return False


@dataclass(frozen=True)
class TurnRuntimeContext:
    """Runtime facts for one companion turn, separate from prompt documents."""

    channel: CompanionRuntimeChannel
    implicit_signal_bundle: ImplicitSignalBundle | None
