"""Reject companion WebSocket when another runtime channel already holds the user.

TODO(telegram-demo-ws-guard): Extend to Weixin bridge and cross-process registry when needed — #3351
"""

from __future__ import annotations

from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.services.agentic_companion.runtime_channel_registry import (
    other_active_channel,
    register_active_channel,
    unregister_active_channel,
)


def ws_reject_reason_if_telegram_active(*, user_id: str) -> str | None:
    """Return close reason when Telegram demo blocks a new App WS session."""
    assert user_id != ""
    conflict = other_active_channel(
        user_id=user_id,
        desired=ChannelKind.APP_WS,
    )
    if conflict == ChannelKind.TELEGRAM:
        return (
            "Companion is active on Telegram demo for this user. "
            "Close Telegram chat before opening the app WebSocket."
        )
    return None


def register_app_ws_channel(*, user_id: str) -> None:
    register_active_channel(user_id=user_id, channel=ChannelKind.APP_WS)


def unregister_app_ws_channel(*, user_id: str) -> None:
    unregister_active_channel(user_id=user_id, channel=ChannelKind.APP_WS)
