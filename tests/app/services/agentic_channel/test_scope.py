"""Tests for AgentScope synthetic MemoryStore chat id."""

from app.core.companion_harness.agent_channel.scope import (
    AgentScope,
    is_agent_scope_memory_store_chat_id,
)


def test_memory_store_chat_id_stable_and_namespaced() -> None:
    scope = AgentScope(user_id="user-a", agent_id="agent-b")
    assert scope.memory_store_chat_id() == "agent-scope:user-a:agent-b"
    assert scope.registry_key() == "user-a:agent-b"
    assert not scope.memory_store_chat_id().startswith(
        "00000000"
    )


def test_to_companion_scope_uses_synthetic_chat_id() -> None:
    scope = AgentScope(user_id="u1", agent_id="a1")
    companion_scope = scope.to_companion_scope()
    assert companion_scope.chat_id == scope.memory_store_chat_id()
    assert companion_scope.companion_id == "a1"


def test_is_agent_scope_memory_store_chat_id() -> None:
    scope = AgentScope(user_id="u1", agent_id="a1")
    assert is_agent_scope_memory_store_chat_id(scope.memory_store_chat_id()) is True
    assert is_agent_scope_memory_store_chat_id("550e8400-e29b-41d4-a716-446655440000") is False
