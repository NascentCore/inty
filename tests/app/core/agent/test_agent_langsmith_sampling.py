from types import SimpleNamespace

import pytest

from app.core.agent import agent as agent_module


class _FakeRun:
    def __init__(self, record: dict):
        self._record = record

    def end(self, outputs=None):
        self._record["outputs"] = outputs


class _FakeTraceContext:
    def __init__(self, collector: list[dict], kwargs: dict):
        self._collector = collector
        self._record = {"kwargs": kwargs, "outputs": None, "exception_type": None}

    def __enter__(self):
        self._collector.append(self._record)
        return _FakeRun(self._record)

    def __exit__(self, exc_type, exc, tb):
        self._record["exception_type"] = exc_type.__name__ if exc_type else None
        return False


class _FakeLangSmith:
    def __init__(self):
        self.runs: list[dict] = []

    def trace(self, **kwargs):
        return _FakeTraceContext(self.runs, kwargs)


class _FakeCompletions:
    def __init__(self, *, response=None, error: Exception | None = None):
        self._response = response
        self._error = error

    def create(self, **kwargs):
        if self._error is not None:
            raise self._error
        return self._response


class _FakeClient:
    def __init__(self, completions: _FakeCompletions):
        self.chat = SimpleNamespace(completions=completions)


def _build_agent() -> agent_module.Agent:
    return agent_module.Agent(agent_id="agent-test", name="Agent", model_config={})


def _make_success_response(content: str = "ok"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason="stop",
            )
        ],
        model="test-model",
        usage=SimpleNamespace(
            prompt_tokens=1,
            completion_tokens=2,
            total_tokens=3,
        ),
    )


def _enable_non_test_tracing(monkeypatch, fake_ls: _FakeLangSmith) -> None:
    monkeypatch.setattr(agent_module, "LANGSMITH_AVAILABLE", True)
    monkeypatch.setattr(agent_module, "ls", fake_ls)
    monkeypatch.setattr(
        agent_module.global_config_loaded_from_config_yaml.app,
        "environment",
        agent_module.Environment.DEV,
    )


def test_resolve_text_chat_langsmith_sample_rate_caps_to_ten_percent():
    assert agent_module._resolve_text_chat_langsmith_sample_rate(1.0) == 0.1
    assert agent_module._resolve_text_chat_langsmith_sample_rate(0.08) == 0.08
    assert agent_module._resolve_text_chat_langsmith_sample_rate(-1) == 0.0


def test_should_trace_text_chat_success_invocation_uses_sample_rate(monkeypatch):
    monkeypatch.setattr(
        agent_module,
        "_get_text_chat_langsmith_sample_rate",
        lambda: 0.1,
    )
    assert agent_module._should_trace_text_chat_success_invocation(0.01) is True
    assert agent_module._should_trace_text_chat_success_invocation(0.5) is False


def test_call_openai_api_with_retry_skips_trace_on_unsampled_success(monkeypatch):
    fake_ls = _FakeLangSmith()
    _enable_non_test_tracing(monkeypatch, fake_ls)
    monkeypatch.setattr(
        agent_module,
        "_should_trace_text_chat_success_invocation",
        lambda: False,
    )

    response = _build_agent()._call_openai_api_with_retry(
        client=_FakeClient(_FakeCompletions(response=_make_success_response("hello"))),
        model="openai/gpt-test",
        openai_messages=[{"role": "user", "content": "hello"}],
        temperature=0.7,
        max_tokens=128,
        top_p=1.0,
        extra_body={},
        user_id="user-1",
        max_retries=1,
    )

    assert response.choices[0].message.content == "hello"
    assert fake_ls.runs == []


def test_call_openai_api_with_retry_traces_sampled_success(monkeypatch):
    fake_ls = _FakeLangSmith()
    _enable_non_test_tracing(monkeypatch, fake_ls)
    monkeypatch.setattr(
        agent_module,
        "_should_trace_text_chat_success_invocation",
        lambda: True,
    )

    response = _build_agent()._call_openai_api_with_retry(
        client=_FakeClient(_FakeCompletions(response=_make_success_response("sampled"))),
        model="openai/gpt-test",
        openai_messages=[{"role": "user", "content": "hello"}],
        temperature=0.7,
        max_tokens=128,
        top_p=1.0,
        extra_body={},
        user_id="user-1",
        max_retries=1,
    )

    assert response.choices[0].message.content == "sampled"
    assert len(fake_ls.runs) == 1
    assert fake_ls.runs[0]["kwargs"]["metadata"].get("force_trace_reason") is None
    assert fake_ls.runs[0]["outputs"]["content"] == "sampled"


def test_call_openai_api_with_retry_force_traces_failure_when_unsampled(monkeypatch):
    fake_ls = _FakeLangSmith()
    _enable_non_test_tracing(monkeypatch, fake_ls)
    monkeypatch.setattr(
        agent_module,
        "_should_trace_text_chat_success_invocation",
        lambda: False,
    )

    with pytest.raises(RuntimeError, match="boom"):
        _build_agent()._call_openai_api_with_retry(
            client=_FakeClient(_FakeCompletions(error=RuntimeError("boom"))),
            model="openai/gpt-test",
            openai_messages=[{"role": "user", "content": "hello"}],
            temperature=0.7,
            max_tokens=128,
            top_p=1.0,
            extra_body={},
            user_id="user-1",
            max_retries=1,
        )

    assert len(fake_ls.runs) == 1
    metadata = fake_ls.runs[0]["kwargs"]["metadata"]
    assert metadata["force_trace_reason"] == "failed_llm_invocation"
    assert fake_ls.runs[0]["outputs"]["error_type"] == "RuntimeError"
