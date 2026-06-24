"""Canonical gateway kinds for human-facing companion media.

Generated entirely by Cursor agent.

Adapters declare ``GatewayKind``; transport code must not define parallel enums.
"""

from __future__ import annotations

from enum import StrEnum


class GatewayKind(StrEnum):
    """Human-facing medium between the companion and the human user."""

    APP_WS = "app_ws"
    WECHAT_WEIXIN = "wechat_weixin"
    TELEGRAM = "telegram"
    SMS = "sms"
