from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from ...telegram_channel import TelegramBotApi, TelegramIncomingMessage
from ..contracts import ChannelType, EventDirection, InteractionEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramInboundEnvelope:
    update_id: int
    chat_id: str
    text: str
    message_date_unix: int | None


def envelope_from_incoming(
    message: TelegramIncomingMessage,
) -> TelegramInboundEnvelope:
    return TelegramInboundEnvelope(
        update_id=message.update_id,
        chat_id=message.chat_id,
        text=message.text,
        message_date_unix=message.message_date_unix,
    )


def build_inbound_event(
    *,
    user_id: str,
    envelope: TelegramInboundEnvelope,
) -> InteractionEvent:
    if envelope.message_date_unix is not None:
        timestamp = datetime.fromtimestamp(
            envelope.message_date_unix,
            tz=timezone.utc,
        )
    else:
        timestamp = datetime.now(timezone.utc)
    return InteractionEvent(
        event_id=f"telegram_update_{envelope.update_id}",
        user_id=user_id,
        channel=ChannelType.TELEGRAM,
        direction=EventDirection.INBOUND,
        content=envelope.text,
        timestamp=timestamp,
        channel_message_id=str(envelope.update_id),
        metadata={
            "chat_id": envelope.chat_id,
            "update_id": envelope.update_id,
        },
    )


class TelegramAdapter:
    def __init__(
        self, bot_api: TelegramBotApi, poll_timeout_seconds: int
    ) -> None:
        self._bot_api = bot_api
        self._poll_timeout_seconds = poll_timeout_seconds

    def poll_updates(
        self, *, offset: int | None
    ) -> tuple[list[TelegramInboundEnvelope], int | None]:
        incoming, next_offset = self._bot_api.get_text_messages(
            offset=offset,
            timeout_seconds=self._poll_timeout_seconds,
        )
        envelopes = [envelope_from_incoming(message) for message in incoming]
        return envelopes, next_offset

    def send_text(self, *, chat_id: str, text: str) -> dict:
        logger.info("telegram_adapter sending chat_id=%s", chat_id)
        return self._bot_api.send_message(chat_id=chat_id, text=text)
