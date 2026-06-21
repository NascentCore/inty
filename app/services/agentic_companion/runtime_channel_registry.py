"""Per-user active runtime channel registry (prototype: in-process only).

TODO(rename-channel-to-gateway): Rename registry/types to Gateway; key by ``GatewayKind`` — #3548
from ``agent_channel/gateway.py``.
TODO(telegram-demo-channel-multiplex): Unify with Weixin bridge and WS presence in one registry — #3350
"""

from __future__ import annotations

from enum import StrEnum

from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)


class ActiveRuntimeChannel(StrEnum):
    APP = ChannelKind.APP_WS.value
    WECHAT_WEIXIN = ChannelKind.WECHAT_WEIXIN.value
    TELEGRAM = ChannelKind.TELEGRAM.value


_active_by_user_id: dict[str, ActiveRuntimeChannel] = {}


def register_active_channel(
    *,
    user_id: str,
    channel: ActiveRuntimeChannel,
) -> ActiveRuntimeChannel | None:
    """Record ``channel`` for ``user_id``; return prior channel if different."""
    assert user_id != ""
    prior = _active_by_user_id.get(user_id)
    _active_by_user_id[user_id] = channel
    if prior is not None and prior != channel:
        return prior
    return None


def unregister_active_channel(
    *,
    user_id: str,
    channel: ActiveRuntimeChannel,
) -> None:
    assert user_id != ""
    current = _active_by_user_id.get(user_id)
    if current == channel:
        _active_by_user_id.pop(user_id, None)


def active_channel_for_user(user_id: str) -> ActiveRuntimeChannel | None:
    assert user_id != ""
    return _active_by_user_id.get(user_id)


def other_active_channel(
    *,
    user_id: str,
    desired: ActiveRuntimeChannel,
) -> ActiveRuntimeChannel | None:
    """Return conflicting channel when another medium is already active."""
    assert user_id != ""
    current = _active_by_user_id.get(user_id)
    if current is None or current == desired:
        return None
    return current


def clear_all_for_tests() -> None:
    _active_by_user_id.clear()
