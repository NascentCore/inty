"""Reject companion WebSocket when another channel already holds the user."""

from __future__ import annotations

from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.services.agentic_companion.runtime_channel_registry import (
    other_active_channel,
    register_active_channel,
    unregister_active_channel,
)


def ws_reject_reason_if_other_channel_active(*, user_id: str) -> str | None:
    """Return close reason when a non-App channel blocks a new App WS session."""
    assert user_id != ""
    conflict = other_active_channel(
        user_id=user_id,
        desired=ChannelKind.APP_WS,
    )
    if conflict is None:
        return None
    return (
        f"Companion is active on {conflict.value} for this user. "
        "Close that channel before opening the app WebSocket."
    )


def register_app_ws_channel(*, user_id: str) -> None:
    register_active_channel(user_id=user_id, channel=ChannelKind.APP_WS)


def unregister_app_ws_channel(*, user_id: str) -> None:
    unregister_active_channel(user_id=user_id, channel=ChannelKind.APP_WS)
