"""Runtime communication channel selection for companion prompt assembly."""

from __future__ import annotations

from enum import StrEnum


class CompanionRuntimeChannel(StrEnum):
    """Human-facing medium carrying this companion turn."""

    APP = "app"
    WECHAT_WEIXIN = "wechat_weixin"
