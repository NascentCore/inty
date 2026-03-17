from __future__ import annotations

import json
from types import SimpleNamespace

from experimental.perpetual_agent import main


def _tool_call(call_id: str, seconds: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name="pulse", arguments=json.dumps({"seconds": seconds})),
    )


def _tool_response(call_id: str, seconds: int) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="", tool_calls=[_tool_call(call_id, seconds)])
            )
        ]
    )


class _FakeCompletions:
    def __init__(self, responses: list[SimpleNamespace], seen_system_messages: list[str]):
        self._responses = responses
        self._seen_system_messages = seen_system_messages

    def create(self, *, model, messages, tools, tool_choice):  # noqa: ANN001
        self._seen_system_messages.append(messages[0]["content"])
        return self._responses.pop(0)


class _FakeClient:
    def __init__(self, responses: list[SimpleNamespace]):
        self.seen_system_messages: list[str] = []
        self.chat = SimpleNamespace(
            completions=_FakeCompletions(
                responses=responses, seen_system_messages=self.seen_system_messages
            )
        )


def test_pulse_sleeps_and_counter_updates_system_message(monkeypatch):
    responses = [_tool_response("pulse-call-1", 2), _tool_response("pulse-call-2", 1)]
    fake_client = _FakeClient(responses=responses)
    sleep_calls: list[int] = []

    monkeypatch.setattr(main.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    main.run_perpetual_agent(
        user_prompt="Run forever and use pulse.",
        model="demo-model",
        max_steps=2,
        client=fake_client,
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
    )

    assert sleep_calls == [2, 1]
    assert "Current pulse counter: 0" in fake_client.seen_system_messages[0]
    assert "Current pulse counter: 1" in fake_client.seen_system_messages[1]
