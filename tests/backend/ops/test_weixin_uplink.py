"""Weixin demo-bridge uplink parser tests."""

from __future__ import annotations

from app.core.companion_harness.companion.runtime_channel import CompanionRuntimeChannel
from app.services.agentic_companion.uplink import UplinkTriggerKind
from app.utils.models_catalog import CHAT_TEXT_MODELS
from backend.ops.weixin_channel.weixin_uplink import parse_weixin_uplink


def test_parse_weixin_uplink_trigger() -> None:
    model = CHAT_TEXT_MODELS[0]
    envelope = parse_weixin_uplink(
        user_id="u1",
        agent_id="a1",
        chat_id="wx-chat",
        user_text="hello wx",
        resolved_chat_model=model,
        session_id="sess",
        preset_user_msg_uuid="mid-wx",
        background_output_sink=None,
        agentic_loop_channel=None,
    )
    assert envelope.trigger == UplinkTriggerKind.USER_MESSAGE
    assert envelope.user_text() == "hello wx"
    assert envelope.runtime_context.channel == CompanionRuntimeChannel.WECHAT_WEIXIN
