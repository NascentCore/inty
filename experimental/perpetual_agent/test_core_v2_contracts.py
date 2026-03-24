from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from experimental.perpetual_agent.core_v2.contracts import (
    ActionStatus,
    ChannelType,
    EventDirection,
    InteractionEvent,
    MemoryItem,
    MemoryStatus,
    MemoryType,
    PlanAction,
)


def test_interaction_event_roundtrip() -> None:
    event = InteractionEvent(
        event_id="evt_1",
        user_id="telegram:123",
        channel=ChannelType.TELEGRAM,
        direction=EventDirection.INBOUND,
        content="hello",
        timestamp=datetime(2026, 3, 24, tzinfo=timezone.utc),
        channel_message_id="42",
        metadata={"k": "v"},
    )

    payload = event.model_dump(mode="json")
    rebuilt = InteractionEvent.model_validate(payload)
    assert rebuilt == event


def test_memory_item_confidence_validation() -> None:
    with pytest.raises(ValidationError):
        MemoryItem(
            memory_id="m1",
            user_id="u1",
            memory_type=MemoryType.PREFERENCE,
            key="preferred_channel",
            value="telegram",
            confidence=1.1,
            evidence_event_ids=["evt_1"],
            status=MemoryStatus.ACTIVE,
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )


def test_plan_action_minimal() -> None:
    action = PlanAction(
        action_id="act_1",
        user_id="u1",
        goal="follow_up_checkin",
        scheduled_at=datetime.now(timezone.utc),
        preferred_channel=ChannelType.SMS,
        message_strategy="gentle_checkin",
        constraints={"source": "test"},
        status=ActionStatus.PENDING,
        result_event_id=None,
    )
    assert action.preferred_channel is ChannelType.SMS
