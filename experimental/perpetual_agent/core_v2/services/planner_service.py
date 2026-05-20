from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import sha256

from ..contracts import ActionStatus, ChannelType, MemoryItem, PlanAction


def build_followup_action(
    *,
    user_id: str,
    trigger_event_id: str,
    now: datetime,
    followup_delay_minutes: int,
    preferred_channel_from_memory: ChannelType | None,
) -> PlanAction:
    if followup_delay_minutes <= 0:
        raise ValueError("followup_delay_minutes must be > 0")

    preferred_channel = preferred_channel_from_memory or ChannelType.TELEGRAM
    action_hash = sha256(
        f"{user_id}:{trigger_event_id}:{preferred_channel.value}".encode(
            "utf-8"
        )
    ).hexdigest()[:24]
    return PlanAction(
        action_id=f"act_{action_hash}",
        user_id=user_id,
        goal="follow_up_checkin",
        scheduled_at=now + timedelta(minutes=followup_delay_minutes),
        preferred_channel=preferred_channel,
        message_strategy="gentle_checkin",
        constraints={"trigger_event_id": trigger_event_id},
        status=ActionStatus.PENDING,
        result_event_id=None,
    )


def pick_preferred_channel_from_memories(
    memories: list[MemoryItem],
) -> ChannelType | None:
    for memory in memories:
        if memory.key != "preferred_channel":
            continue
        if memory.value == ChannelType.SMS.value:
            return ChannelType.SMS
        if memory.value == ChannelType.TELEGRAM.value:
            return ChannelType.TELEGRAM
    return None
