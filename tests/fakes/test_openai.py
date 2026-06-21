from __future__ import annotations

import pytest

from app.external_services.fakes.openai import (
    FakeOpenAI,
    FakeOpenAIScriptExhaustedError,
    fake_step_dual_llm_envelope,
    fake_step_text,
    fake_step_tool_call,
)
from app.core.companion_harness.companion.dual_llm_chat_branch_envelope import (
    parse_dual_llm_chat_envelope_json,
)


def test_returns_random_for_unspecified_request():
    client = FakeOpenAI()

    messages = [{"role": "user", "content": "Hello"}]

    res1 = client.chat.completions.create(model="gpt-test", messages=messages)
    res2 = client.chat.completions.create(model="gpt-test", messages=messages)

    # Random responses should differ across calls
    assert res1.choices[0].message.content != res2.choices[0].message.content
    assert res1.model == "gpt-test"
    assert res1.object == "chat.completion"
    assert res1.choices[0].message.role == "assistant"
    assert (
        res1.usage.total_tokens
        == res1.usage.prompt_tokens + res1.usage.completion_tokens
    )


def test_returns_registered_response_for_specific_request():
    client = FakeOpenAI()

    messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Tell me a joke"},
    ]

    client.register_response(
        messages=messages, content="Knock knock", model="gpt-x"
    )

    res = client.chat.completions.create(model="gpt-x", messages=messages)

    assert res.choices[0].message.content == "Knock knock"
    assert res.model == "gpt-x"


def test_request_key_includes_message_name_and_list_content_support():
    client = FakeOpenAI()

    # Different name should make key different
    messages_a = [{"role": "user", "content": "Hi", "name": "alice"}]
    messages_b = [{"role": "user", "content": "Hi", "name": "bob"}]

    client.register_response(messages=messages_a, content="A")
    client.register_response(messages=messages_b, content="B")

    res_a = client.chat.completions.create(messages=messages_a)
    res_b = client.chat.completions.create(messages=messages_b)

    assert res_a.choices[0].message.content == "A"
    assert res_b.choices[0].message.content == "B"

    # List content (multimodal-like) should be normalized consistently
    messages_list = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello"},
                {"type": "image_url", "image_url": {"url": "http://x"}},
            ],
        }
    ]
    client.register_response(messages=messages_list, content="C", model="m1")
    res_list = client.chat.completions.create(
        messages=messages_list, model="m1"
    )
    assert res_list.choices[0].message.content == "C"


def test_stream_not_supported():
    client = FakeOpenAI()

    try:
        client.chat.completions.create(
            messages=[{"role": "user", "content": "x"}], stream=True
        )
        assert False, "Expected NotImplementedError"
    except NotImplementedError:
        pass


def test_script_returns_steps_in_order():
    script = (
        fake_step_text("first"),
        fake_step_text("second"),
    )
    client = FakeOpenAI(script=script)
    messages = [{"role": "user", "content": "hi"}]

    res1 = client.chat.completions.create(messages=messages)
    res2 = client.chat.completions.create(messages=messages)

    assert res1.choices[0].message.content == "first"
    assert res2.choices[0].message.content == "second"
    assert client.script_index == 2


def test_script_tool_calls_shape():
    script = (
        fake_step_tool_call(
            "memory_store_list_paths",
            '{"relative_path": ""}',
            tool_call_id="call_abc",
        ),
    )
    client = FakeOpenAI(script=script)
    res = client.chat.completions.create(
        messages=[{"role": "user", "content": "list files"}]
    )
    msg = res.choices[0].message
    assert msg.content == ""
    assert len(msg.tool_calls) == 1
    tc = msg.tool_calls[0]
    assert tc.id == "call_abc"
    assert tc.function.name == "memory_store_list_paths"
    assert tc.function.arguments == '{"relative_path": ""}'
    assert res.choices[0].finish_reason == "tool_calls"


def test_script_exhaustion_raises():
    client = FakeOpenAI(script=(fake_step_text("only"),))
    client.chat.completions.create(messages=[{"role": "user", "content": "x"}])
    with pytest.raises(FakeOpenAIScriptExhaustedError):
        client.chat.completions.create(messages=[{"role": "user", "content": "y"}])


@pytest.mark.asyncio
async def test_async_create_uses_same_script():
    client = FakeOpenAI(script=(fake_step_text("async-reply"),))
    res = await client.async_client.chat.completions.create(
        messages=[{"role": "user", "content": "hello"}]
    )
    assert res.choices[0].message.content == "async-reply"
    assert client.script_index == 1


def test_fake_step_dual_llm_envelope_produces_valid_json():
    step = fake_step_dual_llm_envelope(
        user_facing_reply="done",
        output_to_user=False,
        importance_round=5,
        importance_user_message=4,
        importance_assistant_message=6,
        turn_recall="",
    )
    env = parse_dual_llm_chat_envelope_json(step.content)
    assert env is not None
    assert env.user_facing_reply == "done"
    assert env.output_to_user is False

    client = FakeOpenAI(script=(step,))
    res = client.chat.completions.create(messages=[{"role": "user", "content": "x"}])
    assert res.choices[0].message.content == step.content
