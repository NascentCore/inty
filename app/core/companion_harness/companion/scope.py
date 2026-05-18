"""Logical companion session scope (replaces implicit Path semantics for registry keys)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanionScope:
    """Logical companion session scope.

    Everything associated with the same companion scope is considered on the same companion session.
    They are all logically tied to the same "companionship".

    chat_id is for convenience, it's never changed after creation.
    But such a chat ID makes it easy to query.
    """
    user_id: str

    # Agent is for the entity. It could be a companion, an Inty.
    agent_id: str
    chat_id: str

    def registry_key(self) -> str:
        return f"{self.user_id}:{self.agent_id}:{self.chat_id}"
