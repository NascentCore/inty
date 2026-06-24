"""Tests for SMS gateway traits."""

from __future__ import annotations

from app.core.companion_harness.agent_channel.gateway import GatewayKind
from app.core.companion_harness.agent_channel.gateway_traits import (
    guest_agent_kind_for_gateway,
    harness_output_format_slice,
)
from app.core.companion_harness.agent_channel.guest_agent_kind import (
    CompanionGuestAgentKind,
)
from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.core.companion_harness.prompting.bundle import PromptBundle


def test_guest_agent_kind_for_sms_gateway() -> None:
    assert guest_agent_kind_for_gateway(GatewayKind.SMS) == CompanionGuestAgentKind.SMS


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
            runtime_channel=ChannelKind.SMS,
        )
        == ""
    )
