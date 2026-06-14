"""Telegram agent-channel uplink → ``UplinkEnvelope`` (``USER_MESSAGE`` only)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.companion_harness.agent_channel.scope import AgentScope
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


def parse_telegram_uplink(
    *,
    scope: AgentScope,
    user_text: str,
    resolved_chat_model: GenAIModel,
    preset_user_msg_uuid: str,
    session_id: str,
    background_output_sink: object | None,
    agentic_loop_channel: object | None,
) -> UplinkEnvelope:
    """Telegram has no ``IMPLICIT_SIGN_ON``; always ``USER_MESSAGE``."""
    assert user_text.strip()
    assert preset_user_msg_uuid.strip()
    synthetic_chat_id = scope.memory_store_chat_id()
    bundle = ImplicitSignalBundle(
        client_time=None,
        user_signed_on=False,
        server_received_at_utc=datetime.now(timezone.utc),
    )
    return UplinkEnvelope(
        trigger=UplinkTriggerKind.USER_MESSAGE,
        user_input=CompanionUserTurnInput(text=user_text.strip()),
        launch_ctx=TurnLaunchContext(
            user_id=scope.user_id,
            agent_id=scope.agent_id,
            chat_id=synthetic_chat_id,
            resolved_chat_model=resolved_chat_model,
            session_id=session_id,
            preset_user_msg_uuid=preset_user_msg_uuid.strip(),
            runtime_channel=CompanionRuntimeChannel.TELEGRAM.value,
            background_output_sink=background_output_sink,
            bootstrap_interim_output_sink=None,
            agentic_loop_channel=agentic_loop_channel,
        ),
        runtime_context=TurnRuntimeContext(
            channel=CompanionRuntimeChannel.TELEGRAM,
            implicit_signal_bundle=bundle,
        ),
    )
