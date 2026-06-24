"""Reject companion WebSocket when another gateway already holds the user."""

from __future__ import annotations

from app.core.companion_harness.agent_channel.gateway import GatewayKind
from app.services.agentic_companion.active_gateway_registry import (
    other_active_gateway,
    register_active_gateway,
    unregister_active_gateway,
)


def ws_reject_reason_if_other_gateway_active(*, user_id: str) -> str | None:
    """Return close reason when a non-App gateway blocks a new App WS session."""
    assert user_id != ""
    conflict = other_active_gateway(
        user_id=user_id,
        desired=GatewayKind.APP_WS,
    )
    if conflict is None:
        return None
    return (
        f"Companion is active on {conflict.value} for this user. "
        "Close that channel before opening the app WebSocket."
    )


def register_app_ws_gateway(*, user_id: str) -> None:
    register_active_gateway(user_id=user_id, gateway=GatewayKind.APP_WS)


def unregister_app_ws_gateway(*, user_id: str) -> None:
    unregister_active_gateway(user_id=user_id, gateway=GatewayKind.APP_WS)
