from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from ..contracts import ChannelType, MemoryItem, MemoryStatus, MemoryType


def build_preference_memory_from_event(
    *,
    user_id: str,
    event_id: str,
    event_content: str,
    now: datetime,
) -> MemoryItem | None:
    normalized = event_content.lower()
    if "sms" in normalized and (
        "prefer" in normalized or "priority" in normalized
    ):
        key = "preferred_channel"
        value = ChannelType.SMS.value
    elif "telegram" in normalized and (
        "prefer" in normalized or "priority" in normalized
    ):
        key = "preferred_channel"
        value = ChannelType.TELEGRAM.value
    else:
        return None

    memory_hash = sha256(
        f"{user_id}:{key}:{value}".encode("utf-8")
    ).hexdigest()[:24]
    return MemoryItem(
        memory_id=f"mem_{memory_hash}",
        user_id=user_id,
        memory_type=MemoryType.PREFERENCE,
        key=key,
        value=value,
        confidence=0.8,
        evidence_event_ids=[event_id],
        status=MemoryStatus.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
    )
