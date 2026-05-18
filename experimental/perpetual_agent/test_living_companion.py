from __future__ import annotations

import math

from experimental.perpetual_agent.living_companion import (
    ChannelType,
    CompanionState,
    InMemoryChannelTransport,
    ModelCatalog,
    PerpetualCompanionAgent,
    ScriptedModelExecutor,
)


def _build_agent(
    *, now: float, clock_rate: float = 1.0
) -> PerpetualCompanionAgent:
    state = CompanionState(
        companion_name="Ivy",
        user_name="Alex",
        user_contact="alex@example.com",
        initial_virtual_age_years=2.0,
        clock_rate=clock_rate,
        now=now,
    )
    return PerpetualCompanionAgent(
        state=state,
        model_catalog=ModelCatalog.default(),
        model_executor=ScriptedModelExecutor(),
        channel_transport=InMemoryChannelTransport(),
        proactive_interval_seconds=300.0,
    )


def test_tick_updates_virtual_age_by_clock_rate() -> None:
    agent = _build_agent(now=1000.0, clock_rate=10.0)
    agent.tick(now=4600.0)

    expected_delta = (3600.0 * 10.0) / agent.state.seconds_per_virtual_year
    assert math.isclose(
        agent.state.virtual_age_years, 2.0 + expected_delta, rel_tol=1e-9
    )


def test_user_emotional_cue_updates_expression_and_sends_sms() -> None:
    agent = _build_agent(now=1000.0)
    events = agent.tick(
        now=1010.0, user_message="I feel lonely and sad tonight."
    )

    assert len(events) == 1
    event = events[0]
    assert event.channel == ChannelType.SMS
    assert event.metadata["emotion"] == "sad"
    assert event.metadata["expression"] == "gentle"


def test_voice_request_routes_to_multimodal_model_and_voice_call_channel() -> (
    None
):
    agent = _build_agent(now=1000.0)
    events = agent.tick(
        now=1010.0, user_message="Please call me and talk it through."
    )

    assert len(events) == 1
    event = events[0]
    assert event.channel == ChannelType.VOICE_CALL
    assert event.metadata["model_tier"] == "multimodal"


def test_heartbeat_proactively_sends_message_after_interval() -> None:
    agent = _build_agent(now=1000.0)

    silent_events = agent.tick(now=1200.0)
    proactive_events = agent.tick(now=1401.0)

    assert silent_events == []
    assert len(proactive_events) == 1
    assert proactive_events[0].metadata["proactive"] == "true"


def test_email_channel_can_be_requested_explicitly() -> None:
    agent = _build_agent(now=1000.0)
    events = agent.tick(
        now=1005.0,
        user_message="Email me a summary of how you feel today.",
    )

    assert len(events) == 1
    assert events[0].channel == ChannelType.EMAIL


def test_default_channel_can_be_telegram_for_user_and_heartbeat() -> None:
    agent = _build_agent(now=1000.0)
    agent.state.default_channel = ChannelType.TELEGRAM

    user_events = agent.tick(now=1010.0, user_message="Can we continue here?")
    proactive_events = agent.tick(now=1311.0)

    assert len(user_events) == 1
    assert user_events[0].channel == ChannelType.TELEGRAM
    assert len(proactive_events) == 1
    assert proactive_events[0].channel == ChannelType.TELEGRAM
