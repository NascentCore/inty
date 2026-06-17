"""Tool-name allowlist used before companion tool dispatch."""

from __future__ import annotations


class ToolRegistry:
    """Membership guard for OpenAI tool names declared in companion tool definitions."""

    def __init__(self, allowed_names: tuple[str, ...]) -> None:
        self._allowed_names = frozenset(allowed_names)

    def is_allowed(self, name: str) -> bool:
        """Return true when the model-requested tool name is part of the declared schema set."""
        return name in self._allowed_names
