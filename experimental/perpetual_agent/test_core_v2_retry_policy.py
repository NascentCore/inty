from __future__ import annotations

import urllib.error

import pytest

from experimental.perpetual_agent.core_v2.services.retry_policy import (
    RetryPolicy,
    RetryableError,
    TerminalError,
)


def test_retry_policy_retries_transient_then_success(monkeypatch) -> None:
    policy = RetryPolicy(max_attempts=3, base_delay_seconds=0.01)
    sleep_calls: list[float] = []
    monkeypatch.setattr(
        "experimental.perpetual_agent.core_v2.services.retry_policy.time.sleep",
        lambda seconds: sleep_calls.append(seconds),
    )

    state = {"n": 0}

    def _func() -> str:
        state["n"] += 1
        if state["n"] < 3:
            raise TimeoutError("temporary timeout")
        return "ok"

    assert policy.execute(_func) == "ok"
    assert state["n"] == 3
    assert sleep_calls == [0.01, 0.02]


def test_retry_policy_raises_after_exhausted(monkeypatch) -> None:
    policy = RetryPolicy(max_attempts=2, base_delay_seconds=0.01)
    monkeypatch.setattr(
        "experimental.perpetual_agent.core_v2.services.retry_policy.time.sleep",
        lambda _seconds: None,
    )

    def _func() -> str:
        raise urllib.error.URLError("network down")

    with pytest.raises(RetryableError, match="exceeded retries"):
        policy.execute(_func)


def test_retry_policy_terminal_error_no_retry() -> None:
    policy = RetryPolicy(max_attempts=5, base_delay_seconds=0.01)
    calls = {"n": 0}

    def _func() -> str:
        calls["n"] += 1
        raise TerminalError("bad request")

    with pytest.raises(TerminalError, match="bad request"):
        policy.execute(_func)
    assert calls["n"] == 1
