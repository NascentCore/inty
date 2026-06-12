"""Tests for telegram demo in-memory scope cache."""

from backend.ops.telegram_demo import session_store
from app.core.companion_harness.agent_channel.scope import AgentScope


def test_remember_scope_by_address() -> None:
    session_store.clear_all_for_tests()
    scope = AgentScope(user_id="u1", agent_id="a1")
    session_store.remember_scope(channel_address="12345", scope=scope)
    assert session_store.get_scope_for_telegram_address("12345") == scope
    session_store.clear_all_for_tests()
