"""Inbound channel abstraction: merge external messages into LLM chat transcripts."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from .telegram_channel import (
    TelegramBotApi,
    TelegramIncomingMessage,
    format_epoch_for_local_log,
)

logger = logging.getLogger(__name__)


class InboundChannel(Protocol):
    """Pluggable source of user turns that are not yet in the LLM messages list."""

    def drain_into_llm_messages(
        self,
        messages: list[dict[str, Any]],
        *,
        merge_batches: bool,
        poll_timeout_override: int | None = None,
    ) -> int:
        """Poll the channel, append new user content to ``messages``, return inbound count."""
        ...


@dataclass
class TelegramInbox:
    """Telegram long-poll inbox with Telegram offset + application last_applied cursor.

    - ``next_get_updates_offset``: passed to getUpdates so Telegram drops confirmed updates.
    - ``last_applied_update_id``: updates merged into ``messages``; only moves when drain appends.
    - ``drain_into_llm_messages(..., poll_timeout_override=...)``: optional per-call getUpdates
      timeout; use ``0`` for short polling when the caller is only draining queued updates.
    """

    bot_api: TelegramBotApi
    poll_timeout_seconds: int
    bound_chat_id: str | None = None
    next_get_updates_offset: int | None = field(
        default=None, init=False, repr=False
    )
    last_applied_update_id: int = field(default=0, init=False)

    def drain_into_llm_messages(
        self,
        messages: list[dict[str, Any]],
        *,
        merge_batches: bool,
        poll_timeout_override: int | None = None,
    ) -> int:
        poll_timeout = (
            self.poll_timeout_seconds
            if poll_timeout_override is None
            else poll_timeout_override
        )
        offset_before = self.next_get_updates_offset
        t0 = time.monotonic()
        incoming, next_off = self.bot_api.get_text_messages(
            offset=self.next_get_updates_offset,
            timeout_seconds=poll_timeout,
        )
        poll_elapsed_ms = (time.monotonic() - t0) * 1000
        self.next_get_updates_offset = next_off
        logger.info(
            "telegram_get_updates poll_timeout_s=%d elapsed_ms=%.1f "
            "raw_text_messages=%d offset_in=%s offset_out=%s",
            poll_timeout,
            poll_elapsed_ms,
            len(incoming),
            offset_before,
            next_off,
        )

        eligible: list[TelegramIncomingMessage] = []
        for msg in incoming:
            if self.bound_chat_id is None:
                self.bound_chat_id = msg.chat_id
                logger.info(
                    "telegram_inbox bound chat_id=%s", self.bound_chat_id
                )
            if msg.chat_id != self.bound_chat_id:
                continue
            if msg.update_id <= self.last_applied_update_id:
                continue
            eligible.append(msg)

        if not eligible:
            return 0

        eligible.sort(key=lambda m: m.update_id)
        max_id = eligible[-1].update_id

        if merge_batches:
            lines: list[str] = []
            for m in eligible:
                suffix = (
                    f" (telegram_date_unix={m.message_date_unix})"
                    if m.message_date_unix is not None
                    else ""
                )
                lines.append(f"[update_id={m.update_id}]{suffix} {m.text}")
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "New message(s) from the user on Telegram:\n"
                        + "\n".join(lines)
                    ),
                }
            )
        else:
            for m in eligible:
                messages.append({"role": "user", "content": m.text})

        self.last_applied_update_id = max_id
        per_msg = " | ".join(
            (
                f"update_id={m.update_id} "
                f"telegram_message.date_local={format_epoch_for_local_log(m.message_date_unix)} "
                f"local_received_at_local={format_epoch_for_local_log(m.local_received_at)}"
            )
            for m in eligible
        )
        logger.info(
            "telegram_inbox drained update_ids=%s..%s count=%d merge_batches=%s | %s",
            eligible[0].update_id,
            max_id,
            len(eligible),
            merge_batches,
            per_msg,
        )
        return len(eligible)
