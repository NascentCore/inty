"""Tests for SMS channel kind and guest agent naming."""

from __future__ import annotations

from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.services.agentic_channel.companion_guest_provision import (
    companion_guest_agent_name,
)
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.companion.prompt_stack import (
    output_format_prompt_slice_for_runtime_channel,
)


def test_companion_guest_agent_name_sms() -> None:
    assert companion_guest_agent_name(
        channel=ChannelKind.SMS,
        tag="abc123",
    ) == "sms-abc123"


def test_output_format_slice_sms_is_empty() -> None:
    bundle = PromptBundle(
        identity="id",
        soul="soul",
        user_md="user",
        memory_md="memory",
        output_format_im_dm_md="use markdown",
    )
    assert (
        output_format_prompt_slice_for_runtime_channel(
            bundle=bundle,
            runtime_channel=ChannelKind.SMS,
        )
        == ""
    )
