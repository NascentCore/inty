"""Reject companion WebSocket when telegram-demo already holds the user's channel.

TODO(telegram-demo-ws-guard): Extend to Weixin bridge and cross-process registry when needed.
"""

from __future__ import annotations

from backend.ops.telegram_demo.channel_registry import (
    ActiveRuntimeChannel,
    other_active_channel,
)


def ws_reject_reason_if_telegram_active(*, user_id: str) -> str | None:
    """Return close reason when Telegram demo blocks a new App WS session."""
    assert user_id != ""
    conflict = other_active_channel(
        user_id=user_id,
        desired=ActiveRuntimeChannel.APP,
    )
    if conflict == ActiveRuntimeChannel.TELEGRAM:
        return (
            "Companion is active on Telegram demo for this user. "
            "Close Telegram chat before opening the app WebSocket."
        )
    return None


def register_app_ws_channel(*, user_id: str) -> None:
    from backend.ops.telegram_demo.channel_registry import register_active_channel

    register_active_channel(user_id=user_id, channel=ActiveRuntimeChannel.APP)


def unregister_app_ws_channel(*, user_id: str) -> None:
    from backend.ops.telegram_demo.channel_registry import unregister_active_channel

    unregister_active_channel(user_id=user_id, channel=ActiveRuntimeChannel.APP)
