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


@dataclass(frozen=True)
class TurnRuntimeContext:
    """Runtime facts for one companion turn, separate from prompt documents."""

    channel: CompanionRuntimeChannel
    implicit_signal_bundle: ImplicitSignalBundle | None
