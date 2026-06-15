"""Tests for agent-channel transport reply suppression after agentic loop."""

from __future__ import annotations

from app.services.agentic_channel.transport_reply import (
    agentic_loop_suppresses_transport_reply,
)


def test_suppresses_settled_user_chat_when_loop_downlink_wired() -> None:
    assert agentic_loop_suppresses_transport_reply(
        agentic_loop_channel_wired=True,
        interactive_bootstrap_active=False,
        assistant_reply="嗯？笑什么呀。",
    )


def test_keeps_bootstrap_terminal_for_transport() -> None:
    assert not agentic_loop_suppresses_transport_reply(
        agentic_loop_channel_wired=True,
        interactive_bootstrap_active=True,
        assistant_reply="bootstrap terminal",
    )


def test_no_suppression_without_loop_channel() -> None:
    assert not agentic_loop_suppresses_transport_reply(
        agentic_loop_channel_wired=False,
        interactive_bootstrap_active=False,
        assistant_reply="legacy path",
    )


def test_no_suppression_on_empty_reply() -> None:
    assert not agentic_loop_suppresses_transport_reply(
        agentic_loop_channel_wired=True,
        interactive_bootstrap_active=False,
        assistant_reply="   ",
    )
