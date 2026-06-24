"""Per-user active gateway registry (prototype: in-process only).

TODO(cross-channel-same-user-association): #3491 — associate gateways for the same
canonical user across devices; today exclusivity is per-process user_id only.
TODO(telegram-demo-ws-guard): Extend registry across Ops replicas — #3351
"""

from __future__ import annotations

from app.core.companion_harness.agent_channel.gateway import GatewayKind

_active_by_user_id: dict[str, GatewayKind] = {}


def register_active_gateway(
    *,
    user_id: str,
    gateway: GatewayKind,
) -> GatewayKind | None:
    """Record ``gateway`` for ``user_id``; return prior gateway if different."""
    assert user_id != ""
    prior = _active_by_user_id.get(user_id)
    _active_by_user_id[user_id] = gateway
    if prior is not None and prior != gateway:
        return prior
    return None


def unregister_active_gateway(
    *,
    user_id: str,
    gateway: GatewayKind,
) -> None:
    assert user_id != ""
    current = _active_by_user_id.get(user_id)
    if current == gateway:
        _active_by_user_id.pop(user_id, None)


def active_gateway_for_user(user_id: str) -> GatewayKind | None:
    assert user_id != ""
    return _active_by_user_id.get(user_id)


def other_active_gateway(
    *,
    user_id: str,
    desired: GatewayKind,
) -> GatewayKind | None:
    """Return conflicting gateway when another medium is already active."""
    assert user_id != ""
    current = _active_by_user_id.get(user_id)
    if current is None or current == desired:
        return None
    return current


def clear_all_for_tests() -> None:
    _active_by_user_id.clear()
