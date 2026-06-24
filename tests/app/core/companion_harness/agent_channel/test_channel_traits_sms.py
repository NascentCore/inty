"""Tests for SMS gateway traits."""

from __future__ import annotations

from app.core.companion_harness.agent_channel.channel_kind import ChannelKind
from app.core.companion_harness.agent_channel.channel_traits import (
    guest_agent_name_for_channel,
    harness_output_format_slice,
)
from app.core.companion_harness.prompting.bundle import PromptBundle


def test_guest_agent_name_for_sms_gateway() -> None:
    assert guest_agent_name_for_channel(channel=ChannelKind.SMS,
        tag="abc123",
    ) == "sms-abc123"


def test_harness_output_format_slice_sms_is_empty() -> None:
    bundle = PromptBundle(
        identity="id",
        soul="soul",
        user_md="user",
        memory_md="memory",
        output_format_im_dm_md="use markdown",
    )
    assert (
        harness_output_format_slice(
            bundle=bundle,
            channel=ChannelKind.SMS,
        )
        == ""
    )
