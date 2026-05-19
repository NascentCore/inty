from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from experimental.perpetual_agent.channel_inbox import TelegramInbox
from experimental.perpetual_agent.telegram_agentic_loop import (
    PULSE_TOOL_DEFINITION,
    run_telegram_agentic_completion_loop,
    run_telegram_llm_session,
)
from experimental.perpetual_agent.telegram_channel import (
    TelegramIncomingMessage,
)


def _incoming(
    update_id: int,
    chat_id: str,
    text: str,
) -> TelegramIncomingMessage:
    return TelegramIncomingMessage(
        update_id=update_id,
        chat_id=chat_id,
        text=text,
        local_received_at=0.0,
        message_date_unix=None,
    )


class _FakeBotApi:
    def __init__(self, batches: list[list[TelegramIncomingMessage]]):
        self._batches = batches
        self.sent: list[tuple[str, str]] = []
        self.get_text_calls: list[tuple[int | None, int]] = []

    def get_text_messages(self, *, offset, timeout_seconds):  # noqa: ANN001
        self.get_text_calls.append((offset, timeout_seconds))
        batch = self._batches.pop(0)
        next_offset = offset
        if batch:
            next_offset = batch[-1].update_id + 1
        return batch, next_offset

    def send_message(self, *, chat_id: str, text: str) -> dict:
        self.sent.append((chat_id, text))
        return {"ok": True, "result": {}}


class _FakeCompletions:
    def __init__(self, owner: "_FakeClient"):
        self._owner = owner

    def create(self, **kwargs):  # noqa: ANN003
        return self._owner._pop_response(**kwargs)


class _FakeChat:
    def __init__(self, owner: "_FakeClient"):
        self.completions = _FakeCompletions(owner)


class _FakeClient:
    def __init__(self, responses: list):
        self._responses = responses
        self.chat = _FakeChat(self)
        self.completion_calls: list[dict] = []

    def _pop_response(self, **kwargs):  # noqa: ANN003
        self.completion_calls.append(kwargs)
        return self._responses.pop(0)


def test_completion_loop_drains_before_each_api_call() -> None:
    bot = _FakeBotApi(
        batches=[
            [_incoming(1, "7", "hi")],
            [],
        ]
    )
    inbox = TelegramInbox(bot_api=bot, poll_timeout_seconds=1, bound_chat_id="7")  # type: ignore[arg-type]

    resp = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="hello there", tool_calls=None)
            )
        ]
    )
    client = _FakeClient([resp])
    messages: list = [{"role": "system", "content": "sys"}]

    out = run_telegram_agentic_completion_loop(
        client=client,
        model="m1",
        messages=messages,
        inbox=inbox,
        bot_api=bot,  # type: ignore[arg-type]
        merge_batches=True,
        tools=None,
    )

    assert out == "hello there"
    assert bot.sent == [("7", "hello there")]
    assert len(messages) == 3
    assert messages[-1]["role"] == "assistant"
    assert bot.get_text_calls == [(None, 0)]


def test_completion_loop_second_round_includes_telegram_during_tool_gap() -> (
    None
):
    """After first drain, a second poll (before next completion) pulls new user text."""
    bot = _FakeBotApi(
        batches=[
            [],
            [_incoming(2, "1", "follow-up")],
        ]
    )
    inbox = TelegramInbox(bot_api=bot, poll_timeout_seconds=1, bound_chat_id="1")  # type: ignore[arg-type]
    messages: list = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "initial"},
    ]

    tc = SimpleNamespace(
        id="c1",
        type="function",
        function=SimpleNamespace(
            name="pulse", arguments=json.dumps({"seconds": 0})
        ),
    )
    resp_tool = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="", tool_calls=[tc])
            )
        ]
    )
    resp_final = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="done", tool_calls=None)
            )
        ]
    )
    client = _FakeClient([resp_tool, resp_final])

    with patch(
        "experimental.perpetual_agent.telegram_agentic_loop._execute_pulse_tool",
        return_value={"slept_seconds": 0},
    ):
        run_telegram_agentic_completion_loop(
            client=client,
            model="m",
            messages=messages,
            inbox=inbox,
            bot_api=bot,  # type: ignore[arg-type]
            merge_batches=True,
            tools=[PULSE_TOOL_DEFINITION],
        )

    user_contents = [m["content"] for m in messages if m.get("role") == "user"]
    assert any("follow-up" in c for c in user_contents)
    assert bot.sent[-1] == ("1", "done")
    assert [c[1] for c in bot.get_text_calls] == [0, 0]


def test_run_telegram_llm_session_processes_two_inbound_batches() -> None:
    bot = _FakeBotApi(
        [
            [_incoming(1, "9", "first")],
            [],
            [_incoming(2, "9", "second")],
            [],
        ]
    )
    r1 = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="R1", tool_calls=None)
            )
        ]
    )
    r2 = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="R2", tool_calls=None)
            )
        ]
    )
    client = _FakeClient([r1, r2])

    def factory(api):  # noqa: ANN001
        return TelegramInbox(
            bot_api=api, poll_timeout_seconds=1, bound_chat_id="9"
        )

    run_telegram_llm_session(
        model="m",
        api_key_env="UNUSED",
        base_url="http://test",
        telegram_bot_token="t",
        telegram_chat_id="9",
        telegram_poll_timeout_seconds=1,
        max_user_turns=2,
        merge_telegram_batches=True,
        client=client,
        bot_api=bot,  # type: ignore[arg-type]
        inbox_factory=factory,
    )

    assert bot.sent == [("9", "R1"), ("9", "R2")]
    assert [c[1] for c in bot.get_text_calls] == [1, 0, 1, 0]


@pytest.fixture
def caplog_telegram_llm(
    caplog: pytest.LogCaptureFixture,
) -> pytest.LogCaptureFixture:
    caplog.set_level(
        logging.INFO,
        logger="experimental.perpetual_agent.telegram_agentic_loop",
    )
    return caplog


def test_completion_loop_logs_llm_request_and_response_info(
    caplog_telegram_llm: pytest.LogCaptureFixture,
) -> None:
    bot = _FakeBotApi(
        batches=[
            [_incoming(1, "7", "hi")],
            [],
        ]
    )
    inbox = TelegramInbox(bot_api=bot, poll_timeout_seconds=1, bound_chat_id="7")  # type: ignore[arg-type]
    resp = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="hello there", tool_calls=None),
                finish_reason="stop",
            )
        ],
        usage=None,
    )
    client = _FakeClient([resp])
    messages: list = [{"role": "system", "content": "sys"}]

    run_telegram_agentic_completion_loop(
        client=client,
        model="m1",
        messages=messages,
        inbox=inbox,
        bot_api=bot,  # type: ignore[arg-type]
        merge_batches=True,
        tools=None,
    )

    text = caplog_telegram_llm.text
    assert "telegram_llm completion_request step=1" in text
    assert "telegram_llm completion_response step=1" in text
    assert "telegram_llm phase_timing step=1" in text
    assert "send_message_ms=" in text
    assert "finish_reason=stop" in text
    assert "hello there" in text
