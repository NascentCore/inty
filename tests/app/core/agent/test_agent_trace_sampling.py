from types import SimpleNamespace

import pytest

from app.core.agent import agent as agent_module
from app.core.agent.agent import Agent


def test_should_trace_forces_trace_when_user_email_in_allowlist(monkeypatch):
    monkeypatch.setattr(
        agent_module.global_config.agent,
        "langsmith_text_chat_always_trace_user_emails",
        ["internal-dev@example.com"],
    )
    monkeypatch.setattr(
        agent_module.global_config.agent,
        "langsmith_text_chat_sample_rate",
        0.0,
    )
    monkeypatch.setattr(agent_module.random, "random", lambda: 0.9999)

    assert (
        agent_module._should_trace(user_email=" Internal-Dev@Example.com ")
        is True
    )


def test_should_trace_falls_back_to_sample_rate_when_email_not_in_allowlist(
    monkeypatch,
):
    monkeypatch.setattr(
        agent_module.global_config.agent,
        "langsmith_text_chat_always_trace_user_emails",
        ["other@example.com"],
    )
    monkeypatch.setattr(
        agent_module.global_config.agent,
        "langsmith_text_chat_sample_rate",
        0.2,
    )

    monkeypatch.setattr(agent_module.random, "random", lambda: 0.1)
    assert agent_module._should_trace(user_email="dev@example.com") is True

    monkeypatch.setattr(agent_module.random, "random", lambda: 0.9)
    assert agent_module._should_trace(user_email="dev@example.com") is False


def test_get_user_email_for_trace_prefers_cached_auth_snapshot(monkeypatch):
    agent = Agent(agent_id="agent_trace_test", name="TraceAgent", model_config={})
    monkeypatch.setattr(
        agent_module.cache_service,
        "get_user_auth_snapshot",
        lambda user_id: {"email": " Dev@Example.com "},
    )

    assert agent._get_user_email_for_trace("user-1") == "dev@example.com"


def _response_with_choices(content: str):
    choice = SimpleNamespace(
        message=SimpleNamespace(content=content, tool_calls=None),
        finish_reason="stop",
    )
    return SimpleNamespace(choices=[choice], model="test-model", usage=None)


def _response_without_choices():
    return SimpleNamespace(choices=[], model="test-model", usage=None)


class _FakeCompletions:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def create(self, **kwargs):
        response = self._responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return response


def _build_fake_client(responses):
    completions = _FakeCompletions(responses)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return client, completions


def test_call_openai_api_with_retry_retries_when_llm_returns_no_choices(monkeypatch):
    monkeypatch.setattr(
        agent_module.global_config.app,
        "environment",
        agent_module.Environment.TEST,
    )
    monkeypatch.setattr(agent_module.time, "sleep", lambda _seconds: None)

    agent = Agent(agent_id="agent_retry_test", name="RetryAgent", model_config={})
    success_response = _response_with_choices("ok after retry")
    client, completions = _build_fake_client(
        [_response_without_choices(), success_response]
    )

    response, trace_id = agent._call_openai_api_with_retry(
        client=client,
        model="google/gemini-2.5-flash-lite",
        openai_messages=[{"role": "user", "content": "hello"}],
        temperature=0.7,
        max_tokens=128,
        top_p=0.9,
        extra_body={"user": "user-1"},
        user_id="user-1",
        max_retries=3,
        initial_delay=1.0,
    )

    assert response is success_response
    assert trace_id is None
    assert completions.calls == 2


def test_call_openai_api_with_retry_raises_after_all_no_choices(monkeypatch):
    monkeypatch.setattr(
        agent_module.global_config.app,
        "environment",
        agent_module.Environment.TEST,
    )
    monkeypatch.setattr(agent_module.time, "sleep", lambda _seconds: None)

    agent = Agent(agent_id="agent_retry_fail_test", name="RetryAgent", model_config={})
    client, completions = _build_fake_client(
        [
            _response_without_choices(),
            _response_without_choices(),
            _response_without_choices(),
        ]
    )

    with pytest.raises(agent_module.LLMNoChoicesError):
        agent._call_openai_api_with_retry(
            client=client,
            model="google/gemini-2.5-flash-lite",
            openai_messages=[{"role": "user", "content": "hello"}],
            temperature=0.7,
            max_tokens=128,
            top_p=0.9,
            extra_body={"user": "user-1"},
            user_id="user-1",
            max_retries=3,
            initial_delay=1.0,
        )

    assert completions.calls == 3
