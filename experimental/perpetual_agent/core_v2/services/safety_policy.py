from __future__ import annotations

from datetime import datetime

from ..contracts import ChannelType


def is_quiet_hours(
    *,
    now_local: datetime,
    start_hour_local: int,
    end_hour_local: int,
) -> bool:
    if not (0 <= start_hour_local <= 23 and 0 <= end_hour_local <= 23):
        raise ValueError("quiet hour bounds must be in [0, 23]")
    hour = now_local.hour
    if start_hour_local == end_hour_local:
        return True
    if start_hour_local < end_hour_local:
        return start_hour_local <= hour < end_hour_local
    return hour >= start_hour_local or hour < end_hour_local


def allow_send_in_quiet_hours(*, channel: ChannelType) -> bool:
    return channel in {ChannelType.SMS, ChannelType.TELEGRAM}
