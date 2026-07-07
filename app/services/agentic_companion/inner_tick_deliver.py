"""Persist visible inner-tick turns and push channel delivery (WS / Weixin / Telegram)."""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.models import (
    user_visible_assistant_text,
)
from app.schemas.chat_websocket import (
    ChatWsCompanionWireMessageMetaData,
    dump_chat_ws_companion_wire_meta,
)
from app.services import chat_history_service
from app.services.agentic_companion.inner_tick_delivery import (
    InnerTickDelivery,
    deliver_inner_tick_assistant,
)
from app.services.agentic_companion.ws_turn_support import (
    companion_ai_meta_from_turn_result,
)


@dataclass(frozen=True)
class InnerTickVisibleDeliverInput:
    """One user-visible inner-tick round after kernel turn completes."""

    delivery: InnerTickDelivery | None
    session_id: str
    chat_row_agent_id: str
    preset_uid: str
    transcript_user_text: str
    companion_turn: CompanionTurnResult
    user_wire_meta: ChatWsCompanionWireMessageMetaData
    companion_scheduled_reminder: bool | None
    scheduled_task_id: str | None
    log_label: str
    skip_user_history: bool


async def deliver_visible_inner_tick_turn(
    deliver_input: InnerTickVisibleDeliverInput,
) -> bool:
    """Write chat_history rows and enqueue outbound assistant payload when non-empty.

    Returns True when user-visible assistant text was delivered on the channel.
    """
    if not deliver_input.skip_user_history:
        user_meta = dump_chat_ws_companion_wire_meta(
            deliver_input.user_wire_meta
        )
        await chat_history_service.add_user_message_async(
            deliver_input.session_id,
            deliver_input.transcript_user_text,
            meta_data=user_meta,
        )

    companion_reply = deliver_input.companion_turn.assistant_text
    reply_stripped = user_visible_assistant_text(
        str(companion_reply) if companion_reply is not None else ""
    )
    if reply_stripped is None:
        return False

    companion_ai_meta = companion_ai_meta_from_turn_result(
        deliver_input.companion_turn,
        companion_scheduled_reminder=deliver_input.companion_scheduled_reminder,
        scheduled_task_id=deliver_input.scheduled_task_id,
    )
    await chat_history_service.add_ai_message_sync_async(
        deliver_input.session_id,
        companion_reply,
        agent_id=deliver_input.chat_row_agent_id,
        meta_data=companion_ai_meta,
    )

    if deliver_input.delivery is None:
        return True

    # AgenticLoop already appended this turn's visible rows to the scope
    # OutputQueue; on IM channels the presence output pump owns delivery of
    # agent-initiated rows, so a direct channel send here would duplicate the
    # message. Keep chat_history persistence above, skip the channel push.
    # TODO(#3543): converge App-WS onto the same pump-owned delivery, then
    # dissolve this direct-send path entirely.
    if deliver_input.companion_turn.output_message_ids:
        logger.info(
            "{} channel send delegated to scope output pump "
            "(output_message_ids={})",
            deliver_input.log_label,
            deliver_input.companion_turn.output_message_ids,
        )
        return True

    has_im_sink = (
        deliver_input.delivery.weixin_assistant_text is not None
        or deliver_input.delivery.telegram_assistant_text is not None
    )
    if not has_im_sink:
        return True

    await deliver_inner_tick_assistant(
        deliver_input.delivery,
        assistant_text=str(companion_reply),
    )
    return True
