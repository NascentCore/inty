from __future__ import annotations

import logging

import pytest

from experimental.perpetual_agent.channel_inbox import TelegramInbox
from experimental.perpetual_agent.telegram_channel import (
    TelegramIncomingMessage,
)


def _msg(
    update_id: int,
    chat_id: str,
    text: str,
    *,
    local_received_at: float = 1.0,
    message_date_unix: int | None = 100,
) -> TelegramIncomingMessage:
    return TelegramIncomingMessage(
        update_id=update_id,
        chat_id=chat_id,
        text=text,
        local_received_at=local_received_at,
        message_date_unix=message_date_unix,
    )


class _FakeBotApi:
    def __init__(self, batches: list[list[TelegramIncomingMessage]]):
        self._batches = batches
        self.calls: list[tuple[int | None, int]] = []

    def get_text_messages(self, *, offset, timeout_seconds):  # noqa: ANN001
        self.calls.append((offset, timeout_seconds))
        batch = self._batches.pop(0)
        next_offset = offset
        if batch:
            next_offset = batch[-1].update_id + 1
        return batch, next_offset


def test_drain_binds_first_chat_and_appends_merged_user_message() -> None:
    api = _FakeBotApi(
        batches=[
            [_msg(10, "99", "hello")],
        ]
    )
    inbox = TelegramInbox(bot_api=api, poll_timeout_seconds=5)  # type: ignore[arg-type]
    messages: list = [{"role": "system", "content": "sys"}]

    n = inbox.drain_into_llm_messages(messages, merge_batches=True)

    assert n == 1
    assert inbox.bound_chat_id == "99"
    assert inbox.last_applied_update_id == 10
    assert inbox.next_get_updates_offset == 11
    assert len(messages) == 2
    assert messages[1]["role"] == "user"
    assert "hello" in messages[1]["content"]
    assert "update_id=10" in messages[1]["content"]


def test_drain_skips_other_chat_but_advances_telegram_offset() -> None:
    api = _FakeBotApi(
        batches=[
            [_msg(1, "other", "x"), _msg(2, "target", "y")],
        ]
    )
    inbox = TelegramInbox(bot_api=api, poll_timeout_seconds=3, bound_chat_id="target")  # type: ignore[arg-type]
    messages: list = []

    n = inbox.drain_into_llm_messages(messages, merge_batches=False)

    assert n == 1
    assert messages[0]["content"] == "y"
    assert inbox.last_applied_update_id == 2
    assert inbox.next_get_updates_offset == 3


def test_drain_second_poll_skips_already_applied_ids() -> None:
    api = _FakeBotApi(
        batches=[
            [_msg(5, "1", "a")],
            [_msg(5, "1", "a")],
        ]
    )
    inbox = TelegramInbox(bot_api=api, poll_timeout_seconds=1, bound_chat_id="1")  # type: ignore[arg-type]
    messages: list = []
    assert inbox.drain_into_llm_messages(messages, merge_batches=True) == 1
    assert inbox.drain_into_llm_messages(messages, merge_batches=True) == 0
    assert len(messages) == 1


def test_drain_merge_multiple_lines_in_one_user_message() -> None:
    api = _FakeBotApi(
        batches=[
            [
                _msg(3, "1", "first"),
                _msg(4, "1", "second"),
            ],
        ]
    )
    inbox = TelegramInbox(bot_api=api, poll_timeout_seconds=1, bound_chat_id="1")  # type: ignore[arg-type]
    messages: list = []
    n = inbox.drain_into_llm_messages(messages, merge_batches=True)
    assert n == 2
    assert messages[0]["role"] == "user"
    assert (
        "first" in messages[0]["content"] and "second" in messages[0]["content"]
    )


@pytest.fixture
def caplog_channel_inbox(
    caplog: pytest.LogCaptureFixture,
) -> pytest.LogCaptureFixture:
    caplog.set_level(
        logging.INFO, logger="experimental.perpetual_agent.channel_inbox"
    )
    return caplog


def test_drain_log_includes_local_timestamps(
    caplog_channel_inbox: pytest.LogCaptureFixture,
) -> None:
    api = _FakeBotApi(
        batches=[
            [
                _msg(
                    10,
                    "99",
                    "hello",
                    local_received_at=1_700_000_000.0,
                    message_date_unix=1_700_000_001,
                )
            ],
        ]
    )
    inbox = TelegramInbox(bot_api=api, poll_timeout_seconds=5)  # type: ignore[arg-type]
    inbox.drain_into_llm_messages([], merge_batches=True)
    text = caplog_channel_inbox.text
    assert "telegram_get_updates poll_timeout_s=5" in text
    assert "elapsed_ms=" in text
    assert "local_received_at_local=" in text
    assert "telegram_message.date_local=" in text
    assert "update_id=10" in text


def test_drain_poll_timeout_override_passed_to_api() -> None:
    api = _FakeBotApi(
        batches=[
            [_msg(1, "42", "x")],
        ]
    )
    inbox = TelegramInbox(bot_api=api, poll_timeout_seconds=99, bound_chat_id="42")  # type: ignore[arg-type]
    inbox.drain_into_llm_messages(
        [], merge_batches=True, poll_timeout_override=0
    )
    assert api.calls == [(None, 0)]
