"""Harness scope for agent-channel stack: one human user bound to one Inty agent."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.companion_harness.companion.scope import CompanionScope

_AGENT_SCOPE_CHAT_ID_PREFIX = "agent-scope:"


def is_agent_scope_memory_store_chat_id(chat_id: str) -> bool:
    """True when ``chat_id`` is the synthetic MemoryStore key for agent-channel."""
    assert chat_id != ""
    return chat_id.startswith(_AGENT_SCOPE_CHAT_ID_PREFIX)


@dataclass(frozen=True)
class AgentScope:
    """Logical companion scope without legacy ``chats.id``.

    Designed for agentic companion.
    Agentic companion is designed to be bonded to a single user.
    """

    user_id: str
    agent_id: str

    def registry_key(self) -> str:
        assert self.user_id != ""
        assert self.agent_id != ""
        return f"{self.user_id}:{self.agent_id}"

    def memory_store_chat_id(self) -> str:
        """Deterministic MemoryStore key; never collides with UUID chat rows."""
        return f"{_AGENT_SCOPE_CHAT_ID_PREFIX}{self.user_id}:{self.agent_id}"

    def to_companion_scope(self) -> CompanionScope:
        chat_id = self.memory_store_chat_id()
        return CompanionScope(
            user_id=self.user_id,
            companion_id=self.agent_id,
            chat_id=chat_id,
        )
