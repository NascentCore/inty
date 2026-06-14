"""Weixin demo-bridge uplink → ``UplinkEnvelope`` (``USER_MESSAGE`` only)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.user_turn_input import CompanionUserTurnInput
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_companion.uplink import (
    TurnLaunchContext,
    UplinkEnvelope,
    UplinkTriggerKind,
)
from app.utils.models_catalog import GenAIModel


def parse_weixin_uplink(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    user_text: str,
    resolved_chat_model: GenAIModel,
    session_id: str | None,
    preset_user_msg_uuid: str | None,
    background_output_sink: object | None,
    agentic_loop_channel: object | None,
) -> UplinkEnvelope:
    """Weixin has no sign-on greeting uplink."""
    assert user_text.strip()
    bundle = ImplicitSignalBundle(
        client_time=None,
        user_signed_on=False,
        server_received_at_utc=datetime.now(timezone.utc),
    )
    return UplinkEnvelope(
        trigger=UplinkTriggerKind.USER_MESSAGE,
        user_input=CompanionUserTurnInput(text=user_text.strip()),
        launch_ctx=TurnLaunchContext(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
            resolved_chat_model=resolved_chat_model,
            session_id=session_id,
            preset_user_msg_uuid=preset_user_msg_uuid,
            runtime_channel=CompanionRuntimeChannel.WECHAT_WEIXIN.value,
            background_output_sink=background_output_sink,
            bootstrap_interim_output_sink=None,
            agentic_loop_channel=agentic_loop_channel,
        ),
        runtime_context=TurnRuntimeContext(
            channel=CompanionRuntimeChannel.WECHAT_WEIXIN,
            implicit_signal_bundle=bundle,
        ),
    )
