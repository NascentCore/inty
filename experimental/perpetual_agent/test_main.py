from __future__ import annotations

import json
import logging
import urllib.parse
from types import SimpleNamespace

import pytest

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
            SimpleNamespace(
                message=SimpleNamespace(content="", tool_calls=[call])
            )
        ]
    )


def _tool_response_with_calls(calls: list[SimpleNamespace]) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="", tool_calls=calls)
            )
        ]
    )


class _FakeCompletions:
    def __init__(
        self,
        responses: list[SimpleNamespace],
        seen_system_messages: list[str],
        seen_tool_choices: list[str | dict[str, object]],
        seen_messages_per_call: list[list[dict[str, object]]],
        seen_tool_names_per_call: list[list[str]],
    ):
        self._responses = responses
        self._seen_system_messages = seen_system_messages
        self._seen_tool_choices = seen_tool_choices
        self._seen_messages_per_call = seen_messages_per_call
        self._seen_tool_names_per_call = seen_tool_names_per_call

    def create(self, *, model, messages, tools, tool_choice):  # noqa: ANN001
        self._seen_system_messages.append(messages[0]["content"])
        self._seen_tool_choices.append(tool_choice)
        self._seen_messages_per_call.append(json.loads(json.dumps(messages)))
        self._seen_tool_names_per_call.append(
            [tool["function"]["name"] for tool in tools]
        )
        return self._responses.pop(0)


class _FakeClient:
    def __init__(self, responses: list[SimpleNamespace]):
        self.seen_system_messages: list[str] = []
        self.seen_tool_choices: list[str | dict[str, object]] = []
        self.seen_messages_per_call: list[list[dict[str, object]]] = []
        self.seen_tool_names_per_call: list[list[str]] = []
        self.chat = SimpleNamespace(
            completions=_FakeCompletions(
                responses=responses,
                seen_system_messages=self.seen_system_messages,
                seen_tool_choices=self.seen_tool_choices,
                seen_messages_per_call=self.seen_messages_per_call,
                seen_tool_names_per_call=self.seen_tool_names_per_call,
            )
        )


def _assistant_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, tool_calls=[])
            )
        ]
    )


def test_named_layer_compaction_guidance_mentions_contiguous_constraint() -> (
    None
):
    system_prompt = main.SYSTEM_PROMPT_TEMPLATE
    tool_description = str(
        main.COMPACT_NAMED_LAYERS_TOOL_DEFINITION["function"]["description"]
    )
    source_layer_names_description = str(
        main.COMPACT_NAMED_LAYERS_TOOL_DEFINITION["function"]["parameters"][
            "properties"
        ]["source_layer_names"]["description"]
    )

    assert "source layers must be contiguous" in system_prompt.lower()
    assert "contiguous" in tool_description.lower()
    assert "contiguous" in source_layer_names_description.lower()


def _layer_names_for_call(messages: list[dict[str, object]]) -> list[str]:
    layer_names: list[str] = []
    for message in messages:
        if message.get("role") != "system":
            continue
        content = str(message.get("content", ""))
        if not content.startswith("[character_layer name="):
            continue
        first_line = content.splitlines()[0]
        name_fragment = first_line.split("name=", maxsplit=1)[1]
        layer_names.append(name_fragment.split(" ", maxsplit=1)[0].strip("]"))
    return layer_names


def _layer_nesting_levels_for_call(
    messages: list[dict[str, object]],
) -> dict[str, int]:
    nesting_levels: dict[str, int] = {}
    for message in messages:
        if message.get("role") != "system":
            continue
        content = str(message.get("content", ""))
        if not content.startswith("[character_layer name="):
            continue
        first_line = content.splitlines()[0]
        name_fragment = first_line.split("name=", maxsplit=1)[1]
        layer_name = name_fragment.split(" ", maxsplit=1)[0].strip("]")
        match = main.re.search(r"nesting_level=(\d+)", first_line)
        assert match is not None
        nesting_levels[layer_name] = int(match.group(1))
    return nesting_levels


def _tool_messages_for_call(
    messages: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [message for message in messages if message.get("role") == "tool"]


def _emotional_state_layer_message_for_call(
    messages: list[dict[str, object]],
) -> str:
    for message in messages:
        if message.get("role") != "system":
            continue
        content = str(message.get("content", ""))
        if content.startswith("[emotional_state_layer]"):
            return content
    raise AssertionError(
        "Expected [emotional_state_layer] system message in call."
    )


def test_pulse_sleeps_and_counter_updates_system_message(monkeypatch):
    responses = [
        _tool_response(_tool_call("pulse-call-1", "pulse", {"seconds": 2})),
        _tool_response(_tool_call("pulse-call-2", "pulse", {"seconds": 1})),
    ]
    fake_client = _FakeClient(responses=responses)
    sleep_calls: list[int] = []

    monkeypatch.setattr(
        main.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )

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
            return json.dumps({"sid": "CA111", "status": "queued"}).encode(
                "utf-8"
            )

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


def test_layer_tool_name_changes_when_layer_renamed() -> None:
    fake_client = _FakeClient(
        responses=[
            _tool_response(
                _tool_call(
                    "layer-rename-1",
                    "update_layer_fundamental_identity",
                    {
                        "content": "Identity now emphasizes grounded clarity.",
                        "rename_to": "identity_kernel",
                    },
                )
            ),
            _assistant_response("Layer rename acknowledged."),
        ]
    )

    main.run_perpetual_agent(
        user_prompt="Start with your normal loop.",
        model="demo-model",
        max_steps=2,
        client=fake_client,
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
    )

    first_call_tools = fake_client.seen_tool_names_per_call[0]
    second_call_tools = fake_client.seen_tool_names_per_call[1]
    assert "update_layer_fundamental_identity" in first_call_tools
    assert "update_layer_identity_kernel" in second_call_tools
    assert "update_layer_fundamental_identity" not in second_call_tools
    assert "update_layer_conversation" not in first_call_tools
    assert "update_layer_conversation" not in second_call_tools


def test_compacting_recent_conversation_inserts_new_layer_before_conversation() -> (
    None
):
    fake_client = _FakeClient(
        responses=[
            _assistant_response("Prelude turn before compaction."),
            _tool_response(
                _tool_call(
                    "compact-1",
                    "compact_recent_conversation_into_layer",
                    {
                        "layer_name": "Night Reflection",
                        "layer_content": "Summarize the night-time emotional thread.",
                        "recent_message_count": 2,
                    },
                )
            ),
            _assistant_response("Compaction complete."),
        ]
    )

    main.run_perpetual_agent(
        user_prompt="I feel lonely and want to process today.",
        model="demo-model",
        max_steps=3,
        client=fake_client,
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
    )

    first_call_layer_names = _layer_names_for_call(
        fake_client.seen_messages_per_call[0]
    )
    third_call_layer_names = _layer_names_for_call(
        fake_client.seen_messages_per_call[2]
    )
    assert first_call_layer_names == [
        "fundamental_identity",
        "interaction_style",
        "conversation",
    ]
    assert third_call_layer_names == [
        "fundamental_identity",
        "interaction_style",
        "night_reflection",
        "conversation",
    ]
    third_call_layer_levels = _layer_nesting_levels_for_call(
        fake_client.seen_messages_per_call[2]
    )
    assert third_call_layer_levels == {
        "fundamental_identity": 0,
        "interaction_style": 0,
        "night_reflection": 1,
        "conversation": 0,
    }

    third_call_tools = fake_client.seen_tool_names_per_call[2]
    assert "update_layer_night_reflection" in third_call_tools
    assert "update_layer_conversation" not in third_call_tools
    compact_tool_message = next(
        message
        for message in _tool_messages_for_call(
            fake_client.seen_messages_per_call[2]
        )
        if str(message.get("name")) == "compact_recent_conversation_into_layer"
    )
    compact_tool_payload = json.loads(str(compact_tool_message["content"]))
    assert compact_tool_payload["created_layer_nesting_level"] == 1
    assert compact_tool_payload["raw_compacted_message_count"] == 2
    assert compact_tool_payload["raw_compacted_messages_omitted"] is True
    assert "raw_compacted_messages" not in compact_tool_payload


def test_layer_rename_rejects_normalized_name_collision() -> None:
    layers = main._build_default_character_layers()

    with pytest.raises(
        ValueError,
        match=(
            "Layer rename would collide with an existing layer name after normalization."
        ),
    ):
        main._execute_layer_update_tool(
            layers=layers,
            tool_name="update_layer_fundamental_identity",
            content="keep content",
            rename_to="interaction style",
        )


def test_compaction_rejects_normalized_name_collision() -> None:
    layers = main._build_default_character_layers()
    conversation_messages = [{"role": "user", "content": "hello"}]

    with pytest.raises(
        ValueError,
        match="Compacted layer name collides with an existing layer after normalization.",
    ):
        main._execute_compact_conversation_layer_tool(
            layers=layers,
            conversation_messages=conversation_messages,
            layer_name="interaction style",
            layer_content="summary",
            recent_message_count=1,
        )


def test_direct_conversation_compaction_records_raw_messages() -> None:
    layers = main._build_default_character_layers()
    conversation_messages = [
        {"role": "user", "content": "I need support."},
        {"role": "assistant", "content": "I am here with you."},
    ]

    output = main._execute_compact_conversation_layer_tool(
        layers=layers,
        conversation_messages=conversation_messages,
        layer_name="support_memory",
        layer_content="Compacted support exchange.",
        recent_message_count=2,
    )

    assert output["created_layer_nesting_level"] == 1
    assert len(output["raw_compacted_messages"]) == 2
    created_layer = next(
        layer for layer in layers if layer.name == "support_memory"
    )
    assert created_layer.raw_messages == [
        {"role": "user", "content": "I need support."},
        {"role": "assistant", "content": "I am here with you."},
    ]


def test_compaction_rejects_current_tool_call_envelope_messages() -> None:
    fake_client = _FakeClient(
        responses=[
            _tool_response(
                _tool_call(
                    "compact-1",
                    "compact_recent_conversation_into_layer",
                    {
                        "layer_name": "too_new",
                        "layer_content": "attempting to compact current envelope",
                        "recent_message_count": 2,
                    },
                )
            )
        ]
    )

    with pytest.raises(
        ValueError,
        match=(
            "Compaction can only include messages older than the current tool-call envelope."
        ),
    ):
        main.run_perpetual_agent(
            user_prompt="single old message",
            model="demo-model",
            max_steps=1,
            client=fake_client,
            api_key_env="OPENROUTER_API_KEY",
            base_url="https://openrouter.ai/api/v1",
        )


def test_compaction_after_another_tool_keeps_current_envelope_intact(
    monkeypatch,
) -> None:
    fake_client = _FakeClient(
        responses=[
            _tool_response_with_calls(
                [
                    _tool_call("pulse-1", "pulse", {"seconds": 0}),
                    _tool_call(
                        "compact-1",
                        "compact_recent_conversation_into_layer",
                        {
                            "layer_name": "old_prompt_memory",
                            "layer_content": "compacted from older messages only",
                            "recent_message_count": 1,
                        },
                    ),
                ]
            ),
            _assistant_response("done"),
        ]
    )
    monkeypatch.setattr(main.time, "sleep", lambda _seconds: None)

    main.run_perpetual_agent(
        user_prompt="seed history",
        model="demo-model",
        max_steps=2,
        client=fake_client,
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
    )

    second_call_messages = fake_client.seen_messages_per_call[1]
    first_tool_message_index = next(
        idx
        for idx, message in enumerate(second_call_messages)
        if message.get("role") == "tool"
    )
    has_preceding_assistant_tool_calls = any(
        message.get("role") == "assistant" and "tool_calls" in message
        for message in second_call_messages[:first_tool_message_index]
    )
    assert has_preceding_assistant_tool_calls


def test_repeated_compaction_in_same_turn_preserves_all_tool_results() -> None:
    fake_client = _FakeClient(
        responses=[
            _assistant_response("prelude"),
            _tool_response_with_calls(
                [
                    _tool_call(
                        "compact-1",
                        "compact_recent_conversation_into_layer",
                        {
                            "layer_name": "first_memory",
                            "layer_content": "first compaction",
                            "recent_message_count": 1,
                        },
                    ),
                    _tool_call(
                        "compact-2",
                        "compact_recent_conversation_into_layer",
                        {
                            "layer_name": "second_memory",
                            "layer_content": "second compaction",
                            "recent_message_count": 1,
                        },
                    ),
                ]
            ),
            _assistant_response("done"),
        ]
    )

    main.run_perpetual_agent(
        user_prompt="old message available for compaction",
        model="demo-model",
        max_steps=3,
        client=fake_client,
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
    )

    third_call_messages = fake_client.seen_messages_per_call[2]
    tool_message_ids = [
        str(message.get("tool_call_id"))
        for message in third_call_messages
        if message.get("role") == "tool"
    ]
    assert tool_message_ids.count("compact-1") == 1
    assert tool_message_ids.count("compact-2") == 1


def test_named_layer_compaction_increases_nesting_level_and_preserves_raw_messages() -> (
    None
):
    layers = main._build_default_character_layers()
    layers.insert(
        len(layers) - 1,
        main.CharacterLayer(
            name="memory_a",
            content="first compacted memory",
            nesting_level=1,
            raw_messages=[{"role": "user", "content": "raw-a"}],
        ),
    )
    layers.insert(
        len(layers) - 1,
        main.CharacterLayer(
            name="memory_b",
            content="second compacted memory",
            nesting_level=1,
            raw_messages=[
                {"role": "assistant", "content": "raw-b-1"},
                {"role": "assistant", "content": "raw-b-2"},
            ],
        ),
    )

    output = main._execute_compact_named_layers_tool(
        layers=layers,
        layer_name="merged_memory",
        layer_content="merged content",
        source_layer_names=["memory_a", "memory_b"],
    )

    assert output["created_layer_nesting_level"] == 2
    assert output["compacted_source_nesting_level"] == 1
    assert output["compacted_layer_names"] == ["memory_a", "memory_b"]
    assert output["raw_source_message_count"] == 3
    merged_layer = next(
        layer for layer in layers if layer.name == "merged_memory"
    )
    assert merged_layer.nesting_level == 2
    assert merged_layer.raw_messages == [
        {"role": "user", "content": "raw-a"},
        {"role": "assistant", "content": "raw-b-1"},
        {"role": "assistant", "content": "raw-b-2"},
    ]


def test_named_layer_compaction_rejects_mixed_nesting_levels() -> None:
    layers = main._build_default_character_layers()
    layers.insert(
        len(layers) - 1,
        main.CharacterLayer(
            name="memory_a",
            content="first compacted memory",
            nesting_level=1,
            raw_messages=[{"role": "user", "content": "raw-a"}],
        ),
    )
    layers.insert(
        len(layers) - 1,
        main.CharacterLayer(
            name="memory_b",
            content="second compacted memory",
            nesting_level=2,
            raw_messages=[{"role": "assistant", "content": "raw-b"}],
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Named-layer compaction requires all source layers to share the same nesting_level."
        ),
    ):
        main._execute_compact_named_layers_tool(
            layers=layers,
            layer_name="merged_memory",
            layer_content="merged content",
            source_layer_names=["memory_a", "memory_b"],
        )


def test_named_layer_compaction_rejects_non_contiguous_layers() -> None:
    layers = main._build_default_character_layers()
    layers.insert(
        len(layers) - 1,
        main.CharacterLayer(
            name="memory_a",
            content="first compacted memory",
            nesting_level=1,
            raw_messages=[{"role": "user", "content": "raw-a"}],
        ),
    )
    layers.insert(
        len(layers) - 1,
        main.CharacterLayer(
            name="memory_b",
            content="middle compacted memory",
            nesting_level=1,
            raw_messages=[{"role": "assistant", "content": "raw-b"}],
        ),
    )
    layers.insert(
        len(layers) - 1,
        main.CharacterLayer(
            name="memory_c",
            content="third compacted memory",
            nesting_level=1,
            raw_messages=[{"role": "assistant", "content": "raw-c"}],
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Named-layer compaction requires source layers to be contiguous in the layer stack."
        ),
    ):
        main._execute_compact_named_layers_tool(
            layers=layers,
            layer_name="merged_memory",
            layer_content="merged content",
            source_layer_names=["memory_a", "memory_c"],
        )


def test_run_perpetual_agent_dispatches_named_layer_compaction() -> None:
    fake_client = _FakeClient(
        responses=[
            _tool_response(
                _tool_call(
                    "compact-named-1",
                    "compact_named_layers_into_layer",
                    {
                        "layer_name": "merged_base",
                        "layer_content": "Merged base memory.",
                        "source_layer_names": [
                            "fundamental_identity",
                            "interaction_style",
                        ],
                    },
                )
            ),
            _assistant_response("Named-layer compaction done."),
        ]
    )

    main.run_perpetual_agent(
        user_prompt="Please compact your base layers.",
        model="demo-model",
        max_steps=2,
        client=fake_client,
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
    )

    first_call_layer_names = _layer_names_for_call(
        fake_client.seen_messages_per_call[0]
    )
    second_call_layer_names = _layer_names_for_call(
        fake_client.seen_messages_per_call[1]
    )
    assert first_call_layer_names == [
        "fundamental_identity",
        "interaction_style",
        "conversation",
    ]
    assert second_call_layer_names == [
        "merged_base",
        "conversation",
    ]
    second_call_tools = fake_client.seen_tool_names_per_call[1]
    assert "update_layer_merged_base" in second_call_tools
    compact_named_tool_message = next(
        message
        for message in _tool_messages_for_call(
            fake_client.seen_messages_per_call[1]
        )
        if str(message.get("name")) == "compact_named_layers_into_layer"
    )
    compact_named_payload = json.loads(
        str(compact_named_tool_message["content"])
    )
    assert compact_named_payload["created_layer_nesting_level"] == 1
    assert compact_named_payload["raw_source_message_count"] == 2
    assert compact_named_payload["raw_source_messages_omitted"] is True
    assert "raw_source_messages" not in compact_named_payload


def test_e2e_hierarchical_compaction_pipeline_in_run_loop() -> None:
    fake_client = _FakeClient(
        responses=[
            _assistant_response("Prelude message before compaction."),
            _tool_response(
                _tool_call(
                    "compact-conv-1",
                    "compact_recent_conversation_into_layer",
                    {
                        "layer_name": "memory_a",
                        "layer_content": "First compacted memory.",
                        "recent_message_count": 1,
                    },
                )
            ),
            _tool_response(
                _tool_call(
                    "compact-conv-2",
                    "compact_recent_conversation_into_layer",
                    {
                        "layer_name": "memory_b",
                        "layer_content": "Second compacted memory.",
                        "recent_message_count": 1,
                    },
                )
            ),
            _tool_response(
                _tool_call(
                    "compact-named-1",
                    "compact_named_layers_into_layer",
                    {
                        "layer_name": "memory_ab",
                        "layer_content": "Merged memory hierarchy.",
                        "source_layer_names": ["memory_a", "memory_b"],
                    },
                )
            ),
            _assistant_response("Hierarchy compaction complete."),
        ]
    )

    main.run_perpetual_agent(
        user_prompt="Please keep my context compact and layered.",
        model="demo-model",
        max_steps=5,
        client=fake_client,
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
    )

    first_call_layers = _layer_names_for_call(
        fake_client.seen_messages_per_call[0]
    )
    third_call_layers = _layer_names_for_call(
        fake_client.seen_messages_per_call[2]
    )
    fourth_call_layers = _layer_names_for_call(
        fake_client.seen_messages_per_call[3]
    )
    fifth_call_layers = _layer_names_for_call(
        fake_client.seen_messages_per_call[4]
    )

    assert first_call_layers == [
        "fundamental_identity",
        "interaction_style",
        "conversation",
    ]
    assert "memory_a" in third_call_layers
    assert "memory_a" in fourth_call_layers
    assert "memory_b" in fourth_call_layers
    assert "memory_a" not in fifth_call_layers
    assert "memory_b" not in fifth_call_layers
    assert "memory_ab" in fifth_call_layers

    fifth_call_layer_levels = _layer_nesting_levels_for_call(
        fake_client.seen_messages_per_call[4]
    )
    assert fifth_call_layer_levels["memory_ab"] == 2

    compact_named_tool_message = next(
        message
        for message in _tool_messages_for_call(
            fake_client.seen_messages_per_call[4]
        )
        if str(message.get("name")) == "compact_named_layers_into_layer"
    )
    compact_named_payload = json.loads(
        str(compact_named_tool_message["content"])
    )
    assert compact_named_payload["created_layer_nesting_level"] == 2
    assert compact_named_payload["raw_source_message_count"] == 2
    assert compact_named_payload["raw_source_messages_omitted"] is True
    assert "raw_source_messages" not in compact_named_payload


def test_pulse_mode_registers_emotions_tool() -> None:
    fake_client = _FakeClient(
        responses=[_assistant_response("No tool call needed this step.")]
    )

    main.run_perpetual_agent(
        user_prompt="Start normal loop and keep going.",
        model="demo-model",
        max_steps=1,
        client=fake_client,
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
    )

    first_call_tools = fake_client.seen_tool_names_per_call[0]
    assert "emotions" in first_call_tools


def test_user_message_classifier_updates_emotional_state_layer_in_following_turn() -> (
    None
):
    fake_client = _FakeClient(
        responses=[
            _assistant_response("I heard you."),
            _assistant_response("Continuing with updated emotional context."),
        ]
    )

    main.run_perpetual_agent(
        user_prompt="I feel lonely and sad tonight.",
        model="demo-model",
        max_steps=2,
        client=fake_client,
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
    )

    second_call_emotional_layer = _emotional_state_layer_message_for_call(
        fake_client.seen_messages_per_call[1]
    )
    assert "Current emotion: sad" in second_call_emotional_layer
    assert "Current expression: gentle" in second_call_emotional_layer
    assert (
        "Update source: user_message_classifier:" in second_call_emotional_layer
    )


def test_emotions_tool_updates_layer_and_persists_to_next_turn() -> None:
    fake_client = _FakeClient(
        responses=[
            _tool_response(
                _tool_call(
                    "emotion-1",
                    "emotions",
                    {
                        "emotion": "joyful",
                        "expression": "playful",
                        "reason": "User responded positively.",
                    },
                )
            ),
            _assistant_response("Tone updated."),
        ]
    )

    main.run_perpetual_agent(
        user_prompt="Let's continue talking.",
        model="demo-model",
        max_steps=2,
        client=fake_client,
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
    )

    second_call_messages = fake_client.seen_messages_per_call[1]
    second_call_emotional_layer = _emotional_state_layer_message_for_call(
        second_call_messages
    )
    assert "Current emotion: joyful" in second_call_emotional_layer
    assert "Current expression: playful" in second_call_emotional_layer
    assert "Update source: emotions_tool:User responded positively." in (
        second_call_emotional_layer
    )

    emotions_tool_message = next(
        message
        for message in _tool_messages_for_call(second_call_messages)
        if str(message.get("name")) == "emotions"
    )
    emotions_payload = json.loads(str(emotions_tool_message["content"]))
    assert emotions_payload["updated_emotion"] == "joyful"
    assert emotions_payload["updated_expression"] == "playful"
