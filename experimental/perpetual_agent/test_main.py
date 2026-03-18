from __future__ import annotations

import json
import urllib.parse
from types import SimpleNamespace

from experimental.perpetual_agent import main


def _tool_call(
    call_id: str, name: str, arguments: dict[str, object]
) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


def _tool_response(call: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[call]))
        ]
    )


class _FakeCompletions:
    def __init__(
        self,
        responses: list[SimpleNamespace],
        seen_system_messages: list[str],
        seen_tool_choices: list[str | dict[str, object]],
    ):
        self._responses = responses
        self._seen_system_messages = seen_system_messages
        self._seen_tool_choices = seen_tool_choices

    def create(self, *, model, messages, tools, tool_choice):  # noqa: ANN001
        self._seen_system_messages.append(messages[0]["content"])
        self._seen_tool_choices.append(tool_choice)
        return self._responses.pop(0)


class _FakeClient:
    def __init__(self, responses: list[SimpleNamespace]):
        self.seen_system_messages: list[str] = []
        self.seen_tool_choices: list[str | dict[str, object]] = []
        self.chat = SimpleNamespace(
            completions=_FakeCompletions(
                responses=responses,
                seen_system_messages=self.seen_system_messages,
                seen_tool_choices=self.seen_tool_choices,
            )
        )


def test_pulse_sleeps_and_counter_updates_system_message(monkeypatch):
    responses = [
        _tool_response(_tool_call("pulse-call-1", "pulse", {"seconds": 2})),
        _tool_response(_tool_call("pulse-call-2", "pulse", {"seconds": 1})),
    ]
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
    assert fake_client.seen_tool_choices == ["auto", "auto"]


def test_call_prompt_forces_call_user_tool_choice(monkeypatch):
    fake_client = _FakeClient(
        responses=[
            _tool_response(
                _tool_call(
                    "call-1",
                    "call_user",
                    {
                        "phone_number": "+14155550123",
                        "reason": "User requested a call.",
                    },
                )
            )
        ]
    )
    monkeypatch.setattr(
        main,
        "_execute_call_user_tool",
        lambda *, phone_number, reason: {
            "to_number": phone_number,
            "reason": reason,
            "twilio_call_sid": "CA_TEST",
            "twilio_status": "queued",
        },
    )

    main.run_perpetual_agent(
        user_prompt="Please call me at +1 415 555 0123",
        model="demo-model",
        max_steps=1,
        client=fake_client,
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
    )

    assert fake_client.seen_tool_choices == [
        {"type": "function", "function": {"name": "call_user"}}
    ]


def test_execute_call_user_tool_uses_twilio_and_returns_sid(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "auth")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15005550006")
    monkeypatch.setenv("GEMINI_LIVE_BRIDGE_WS_URL", "wss://bridge.example/ws")
    monkeypatch.setenv("GEMINI_LIVE_CALL_SYSTEM_PROMPT", "You are Inty voice.")

    def _fake_create_call(*, to_number, reason, config):  # noqa: ANN001
        assert to_number == "+14155550123"
        assert reason == "Check in with user"
        assert config.account_sid == "AC123"
        assert config.gemini_live_bridge_ws_url == "wss://bridge.example/ws"
        return {"sid": "CA123", "status": "queued"}

    output = main._execute_call_user_tool(
        phone_number="+14155550123",
        reason="Check in with user",
        create_call=_fake_create_call,
    )

    assert output == {
        "to_number": "+14155550123",
        "reason": "Check in with user",
        "twilio_call_sid": "CA123",
        "twilio_status": "queued",
    }


def test_create_twilio_call_posts_expected_form_data():
    captured: dict[str, object] = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def read(self):
            return json.dumps({"sid": "CA111", "status": "queued"}).encode("utf-8")

    def _fake_urlopen(request, timeout):  # noqa: ANN001
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["headers"] = dict(request.header_items())
        captured["body"] = request.data.decode("utf-8")
        captured["timeout"] = timeout
        return _FakeResponse()

    config = main.TwilioCallConfig(
        account_sid="AC999",
        auth_token="secret",
        from_number="+15005550006",
        gemini_live_bridge_ws_url="wss://bridge.example/ws",
        bridge_system_prompt="Be concise.",
    )
    result = main._create_twilio_call(
        to_number="+14155550123",
        reason="Call requested by user",
        config=config,
        urlopen=_fake_urlopen,
    )
    encoded = urllib.parse.parse_qs(captured["body"])

    assert result == {"sid": "CA111", "status": "queued"}
    assert captured["url"].endswith("/Accounts/AC999/Calls.json")
    assert captured["method"] == "POST"
    assert captured["timeout"] == 30
    assert encoded["From"] == ["+15005550006"]
    assert encoded["To"] == ["+14155550123"]
    assert '<Stream url="wss://bridge.example/ws">' in encoded["Twiml"][0]
    assert "Call requested by user" in encoded["Twiml"][0]
