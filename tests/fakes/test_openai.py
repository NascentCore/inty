from __future__ import annotations

from app.external_services.fakes.openai import FakeOpenAI


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

    client.register_response(messages=messages, content="Knock knock", model="gpt-x")

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
    res_list = client.chat.completions.create(messages=messages_list, model="m1")
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
