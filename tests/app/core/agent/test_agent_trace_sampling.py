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

    assert agent_module._should_trace(user_email=" Internal-Dev@Example.com ") is True


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
