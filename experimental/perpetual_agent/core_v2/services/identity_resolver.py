from __future__ import annotations

from ..contracts import ChannelType


def resolve_user_id(*, channel: ChannelType, channel_user_id: str) -> str:
    normalized = channel_user_id.strip()
    if not normalized:
        raise ValueError("channel_user_id cannot be empty")
    return f"{channel.value}:{normalized}"
