"""Tail user message shaping for one companion turn.

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.companion_harness.agentic_companion.types import (
    AgenticLoopInputBatch,
)
from app.core.companion_harness.loop.config import (
    BatchUserMessagesLlmCallMode,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from .implicit_signal_messages import USER_SIGNED_ON_TRIGGER_USER_TEXT
from .transcript_user_row import (
    TranscriptUserRowBuildInput,
    append_transcript_user_row,
)
from .utc import transcript_message_content_for_llm_at


@dataclass(frozen=True)
class TurnTailUserMessage:
    """One user utterance shared by LLM prompt tail and transcript persistence."""

    message_id: str
    text: str
    received_at_utc: datetime

    def __post_init__(self) -> None:
        assert self.message_id != ""
        assert self.text != ""


def _single_tail_user_message(
    *,
    user_text: str,
    ts_user: datetime,
    user_msg_uuid: str,
) -> TurnTailUserMessage:
    assert user_text != ""
    assert user_msg_uuid != ""
    return TurnTailUserMessage(
        message_id=user_msg_uuid,
        text=user_text,
        received_at_utc=ts_user,
    )


def _joined_input_batch_text(input_batch: AgenticLoopInputBatch) -> str:
    parts = [msg.text for msg in input_batch.messages]
    assert parts
    if len(parts) == 1:
        return parts[0]
    return "\n".join(parts)


def resolve_turn_tail_user_messages(
    *,
    mode: BatchUserMessagesLlmCallMode,
    input_batch: AgenticLoopInputBatch | None,
    user_text: str,
    ts_user: datetime,
    user_msg_uuid: str,
    implicit_sign_on_turn: bool,
) -> tuple[TurnTailUserMessage, ...]:
    """Resolve how the current turn's user batch appears to LLM and transcript.

    ``CompanionTurnResult.transcript_user_content`` uses ``"\\n".join`` of row
    texts when this turn persists multiple user rows; JSONL rows stay per-message.

    Implicit sign-on turns always expose exactly one tail user message.
    """
    if input_batch is None:
        tail = (
            _single_tail_user_message(
                user_text=user_text,
                ts_user=ts_user,
                user_msg_uuid=user_msg_uuid,
            ),
        )
    elif mode == BatchUserMessagesLlmCallMode.JOIN_TO_ONE_USER_MESSAGE:
        tail = (
            TurnTailUserMessage(
                message_id=input_batch.primary_user_msg_uuid,
                text=_joined_input_batch_text(input_batch),
                received_at_utc=input_batch.messages[-1].received_at_utc,
            ),
        )
    else:
        tail = tuple(
            TurnTailUserMessage(
                message_id=msg.message_id,
                text=msg.text,
                received_at_utc=msg.received_at_utc,
            )
            for msg in input_batch.messages
        )

    if implicit_sign_on_turn:
        assert len(tail) == 1
    return tail


def tail_user_message_contents_for_llm(
    *,
    tail_user_messages: tuple[TurnTailUserMessage, ...],
    implicit_sign_on_turn: bool,
) -> tuple[str, ...]:
    """Build timestamp-prefixed LLM user contents for this turn's tail."""
    assert tail_user_messages
    if implicit_sign_on_turn:
        assert len(tail_user_messages) == 1
    return tuple(
        transcript_message_content_for_llm_at(
            content=(
                USER_SIGNED_ON_TRIGGER_USER_TEXT
                if implicit_sign_on_turn
                else message.text
            ),
            at=message.received_at_utc,
        )
        for message in tail_user_messages
    )


def append_tail_user_messages_for_llm(
    messages: list[dict[str, Any]],
    *,
    tail_user_messages: tuple[TurnTailUserMessage, ...],
    implicit_sign_on_turn: bool,
) -> None:
    """Append this turn's tail user messages to an OpenAI-style message stack."""
    for content in tail_user_message_contents_for_llm(
        tail_user_messages=tail_user_messages,
        implicit_sign_on_turn=implicit_sign_on_turn,
    ):
        messages.append({"role": "user", "content": content})


def append_tail_user_transcript_rows(
    store: MemoryStore,
    transcript_relative_path: str,
    *,
    tail_user_messages: tuple[TurnTailUserMessage, ...],
    trace_id: str,
) -> None:
    """Persist this turn's tail user rows in the same order the LLM sees them."""
    assert transcript_relative_path != ""
    assert tail_user_messages
    assert trace_id != ""
    for message in tail_user_messages:
        append_transcript_user_row(
            store,
            transcript_relative_path,
            TranscriptUserRowBuildInput(
                content=message.text,
                uuid=message.message_id,
                trace_id=trace_id,
            ),
            ts=message.received_at_utc.isoformat(),
        )
