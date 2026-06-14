"""Dispatch ``UplinkEnvelope`` to companion harness entry points."""

from __future__ import annotations

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.runtime_channel import CompanionRuntimeChannel
from app.core.companion_harness.companion.turn_routes import BackgroundToolEventSink
from app.services.agentic_companion.uplink import UplinkEnvelope, UplinkTriggerKind
from app.services import companion_chat_service


async def dispatch_uplink_envelope(
    envelope: UplinkEnvelope,
) -> CompanionTurnResult:
    """Run one user-turn from a channel-agnostic uplink envelope."""
    ctx = envelope.launch_ctx
    channel = CompanionRuntimeChannel(ctx.runtime_channel)
    bg_sink: BackgroundToolEventSink | None = ctx.background_output_sink
    interim_sink = ctx.bootstrap_interim_output_sink
    match envelope.trigger:
        case UplinkTriggerKind.IMPLICIT_SIGN_ON:
            return await companion_chat_service.run_companion_implicit_sign_on_greeting_turn_for_api(
                user_id=ctx.user_id,
                agent_id=ctx.agent_id,
                chat_id=ctx.chat_id,
                user_text="",
                resolved_chat_model=ctx.resolved_chat_model,
                session_id=ctx.session_id,
                preset_user_msg_uuid=ctx.preset_user_msg_uuid,
                runtime_channel=channel,
                implicit_signal_bundle=envelope.runtime_context.implicit_signal_bundle,
                agentic_loop_channel=ctx.agentic_loop_channel,
            )
        case UplinkTriggerKind.USER_MESSAGE:
            return await companion_chat_service.run_user_chat(
                user_id=ctx.user_id,
                agent_id=ctx.agent_id,
                chat_id=ctx.chat_id,
                user_text=envelope.user_text(),
                resolved_chat_model=ctx.resolved_chat_model,
                session_id=ctx.session_id,
                background_output_sink=bg_sink,
                preset_user_msg_uuid=ctx.preset_user_msg_uuid,
                implicit_signal_bundle=envelope.runtime_context.implicit_signal_bundle,
                runtime_channel=channel,
                bootstrap_interim_output_sink=interim_sink,
                agentic_loop_channel=ctx.agentic_loop_channel,
            )
        case _:
            raise AssertionError(f"unknown uplink trigger: {envelope.trigger}")
