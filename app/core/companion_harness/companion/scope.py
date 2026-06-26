"""Logical companion session scope (replaces implicit Path semantics for registry keys).

TODO(world-engine-agent-scope): Generalize MemoryStore scope to ``agent_id``
(companion + sub-agent each own a scope) — #3704 (epic #3700).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanionScope:
    user_id: str
    companion_id: str
    chat_id: str

    def registry_key(self) -> str:
        return f"{self.user_id}:{self.companion_id}:{self.chat_id}"
