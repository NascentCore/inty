"""Regression tests for OpenRouter chat completion when the API returns zero choices."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.agent import agent as agent_module
from app.core.agent.agent import Agent
from app.core.config import Environment


def test_call_openai_retries_when_choices_empty(monkeypatch):
    agent = Agent(agent_id="empty-choice-agent", name="N", model_config={})
    client = MagicMock()
    empty = SimpleNamespace(choices=[])
    ok_inner = SimpleNamespace(
        content="hi",
        tool_calls=None,
        finish_reason="stop",
    )
    ok = SimpleNamespace(
        choices=[SimpleNamespace(message=ok_inner, finish_reason="stop")]
    )

    calls = {"n": 0}

    def fake_create(**kwargs):
        calls["n"] += 1
        return empty if calls["n"] == 1 else ok

    client.chat.completions.create = fake_create
    monkeypatch.setattr(agent_module.global_config.app, "environment", Environment.TEST)

    resp, _tid = agent._call_openai_api_with_retry(
        client=client,
        model="x",
        openai_messages=[{"role": "user", "content": "h"}],
        temperature=0.1,
        max_tokens=10,
        top_p=1.0,
        extra_body={},
        user_id="u1",
        max_retries=3,
        initial_delay=0.0,
    )
    assert calls["n"] == 2
    assert resp.choices[0].message.content == "hi"


def test_call_openai_raises_when_choices_stay_empty(monkeypatch):
    agent = Agent(agent_id="empty-choice-agent-2", name="N", model_config={})
    client = MagicMock()
    client.chat.completions.create = lambda **kwargs: SimpleNamespace(choices=[])
    monkeypatch.setattr(agent_module.global_config.app, "environment", Environment.TEST)

    with pytest.raises(ValueError, match="LLM returned no choices"):
        agent._call_openai_api_with_retry(
            client=client,
            model="x",
            openai_messages=[{"role": "user", "content": "h"}],
            temperature=0.1,
            max_tokens=10,
            top_p=1.0,
            extra_body={},
            user_id="u1",
            max_retries=2,
            initial_delay=0.0,
        )
