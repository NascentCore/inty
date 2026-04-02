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


def test_call_openai_api_with_retry_fallbacks_on_invalid_model_identifier(monkeypatch):
    agent = Agent(
        agent_id="agent_fallback_test",
        name="TraceAgent",
        model_config={"model": "anthropic/claude-3.5-sonnet"},
    )
    monkeypatch.setattr(
        agent_module.global_config.app, "environment", agent_module.Environment.TEST
    )

    call_models: list[str] = []

    class DummyAPI:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            call_models.append(kwargs["model"])
            if self.calls == 1:
                raise RuntimeError(
                    'Error code: 400 - {"error":{"message":"The provided model identifier is invalid."}}'
                )
            return type(
                "Resp",
                (),
                {
                    "choices": [
                        type(
                            "Choice",
                            (),
                            {
                                "message": type("Msg", (), {"content": "ok", "tool_calls": []})(),
                                "finish_reason": "stop",
                            },
                        )()
                    ],
                    "model": kwargs["model"],
                    "usage": None,
                },
            )()

    client = type(
        "Client",
        (),
        {"chat": type("Chat", (), {"completions": DummyAPI()})()},
    )()

    response, trace_id = agent._call_openai_api_with_retry(
        client=client,
        model="anthropic/claude-3.5-sonnet",
        openai_messages=[{"role": "user", "content": "hello"}],
        temperature=0.7,
        max_tokens=128,
        top_p=0.9,
        extra_body={"user": "user-1", "generation_config": {"thinking_budget": 0}},
        user_id="user-1",
        max_retries=3,
        initial_delay=0.0,
        fallback_model="google/gemini-2.5-flash",
    )

    assert response.model == "google/gemini-2.5-flash"
    assert trace_id is None
    assert call_models == ["anthropic/claude-3.5-sonnet", "google/gemini-2.5-flash"]
