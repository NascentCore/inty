from langchain_core.messages import AIMessage, HumanMessage

from app.core.agent import agent as agent_module
from app.core.agent.agent import Agent


def _build_agent() -> Agent:
    return Agent(
        agent_id="agent-compaction-test",
        name="CompactionAgent",
        model_config={},
    )


def test_maybe_compact_history_for_user_tier_triggers_on_overflow(monkeypatch):
    monkeypatch.setattr(
        agent_module.global_config.app.limits,
        "free_user_chat_messages_limit",
        2,
    )
    history_messages = [
        HumanMessage(content="h1"),
        AIMessage(content="a1"),
        HumanMessage(content="h2"),
        AIMessage(content="a2"),
    ]
    captured = {}

    def fake_compact(**kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(
        agent_module,
        "maybe_compact_and_save_overflow_history",
        fake_compact,
    )
    monkeypatch.setattr(agent_module, "get_sync_engine", lambda: object())
    submitted = {}

    class _FakeFuture:
        def add_done_callback(self, callback):
            submitted["callback"] = callback

    class _FakeExecutor:
        def submit(self, fn, **kwargs):
            submitted["fn"] = fn
            submitted["kwargs"] = kwargs
            return _FakeFuture()

    monkeypatch.setattr(
        agent_module, "get_compaction_executor", lambda: _FakeExecutor()
    )

    agent = _build_agent()
    agent._maybe_compact_history_for_user_tier(
        user_id="user-1",
        session_id="session-1",
        history_messages=history_messages,
        is_subscribed=False,
    )

    assert submitted["fn"].__name__ == "_run_messages_compaction_task"
    assert submitted["kwargs"]["user_id"] == "user-1"
    assert submitted["kwargs"]["session_id"] == "session-1"
    assert submitted["kwargs"]["max_messages_limit"] == 2
    assert len(submitted["kwargs"]["history_messages"]) == 4
    assert "callback" in submitted


def test_maybe_compact_history_for_user_tier_skips_when_within_limit(
    monkeypatch,
):
    monkeypatch.setattr(
        agent_module.global_config.app.limits,
        "free_user_chat_messages_limit",
        10,
    )
    history_messages = [
        HumanMessage(content="h1"),
        AIMessage(content="a1"),
    ]

    def fail_if_submit(*_args, **_kwargs):
        raise AssertionError(
            "compaction should not be submitted when history is within limit"
        )

    class _FakeExecutor:
        def submit(self, *_args, **_kwargs):
            return fail_if_submit()

    monkeypatch.setattr(
        agent_module, "get_compaction_executor", lambda: _FakeExecutor()
    )

    agent = _build_agent()
    agent._maybe_compact_history_for_user_tier(
        user_id="user-1",
        session_id="session-1",
        history_messages=history_messages,
        is_subscribed=False,
    )


def test_maybe_compact_history_for_user_tier_returns_quickly_when_background_task_is_slow(
    monkeypatch,
):
    monkeypatch.setattr(
        agent_module.global_config.app.limits,
        "free_user_chat_messages_limit",
        1,
    )
    history_messages = [
        HumanMessage(content="h1"),
        AIMessage(content="a1"),
        HumanMessage(content="h2"),
    ]
    import threading
    import time
    from concurrent.futures import Future

    submitted = {}

    class _AsyncSlowExecutor:
        def submit(self, fn, **kwargs):
            submitted["fn"] = fn
            submitted["kwargs"] = kwargs
            future = Future()

            def run_slow_task():
                time.sleep(6)
                try:
                    future.set_result(fn(**kwargs))
                except (
                    Exception
                ) as error:  # pragma: no cover - defensive for test stability
                    future.set_exception(error)

            threading.Thread(target=run_slow_task, daemon=True).start()
            return future

    monkeypatch.setattr(
        agent_module, "get_compaction_executor", lambda: _AsyncSlowExecutor()
    )
    monkeypatch.setattr(agent_module, "get_sync_engine", lambda: object())

    agent = _build_agent()

    started_at = time.perf_counter()
    agent._maybe_compact_history_for_user_tier(
        user_id="user-1",
        session_id="session-1",
        history_messages=history_messages,
        is_subscribed=False,
    )
    elapsed_seconds = time.perf_counter() - started_at
    assert elapsed_seconds < 5


def test_maybe_compact_history_for_user_tier_returns_quickly_when_get_sync_engine_is_slow(
    monkeypatch,
):
    monkeypatch.setattr(
        agent_module.global_config.app.limits,
        "free_user_chat_messages_limit",
        1,
    )
    history_messages = [
        HumanMessage(content="h1"),
        AIMessage(content="a1"),
        HumanMessage(content="h2"),
    ]
    import threading
    import time
    from concurrent.futures import Future

    class _FastAsyncExecutor:
        def submit(self, fn, **kwargs):
            future = Future()

            def run_task():
                try:
                    future.set_result(fn(**kwargs))
                except (
                    Exception
                ) as error:  # pragma: no cover - defensive for test stability
                    future.set_exception(error)

            threading.Thread(target=run_task, daemon=True).start()
            return future

    def slow_get_sync_engine():
        time.sleep(6)
        return object()

    monkeypatch.setattr(
        agent_module, "get_compaction_executor", lambda: _FastAsyncExecutor()
    )
    monkeypatch.setattr(agent_module, "get_sync_engine", slow_get_sync_engine)
    monkeypatch.setattr(
        agent_module,
        "maybe_compact_and_save_overflow_history",
        lambda **_kwargs: True,
    )

    agent = _build_agent()

    started_at = time.perf_counter()
    agent._maybe_compact_history_for_user_tier(
        user_id="user-1",
        session_id="session-1",
        history_messages=history_messages,
        is_subscribed=False,
    )
    elapsed_seconds = time.perf_counter() - started_at
    assert elapsed_seconds < 5
