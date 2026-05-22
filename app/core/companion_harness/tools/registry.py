"""Minimal companion tool registry used before per-tool dispatch.

The companion harness receives tool names from model output, then checks those
names against the advertised tool surface before routing to specialized
dispatchers. This module keeps that allowlist separate from the dispatcher
implementations so unknown tools fail early with a clear boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

ToolHandler = Callable[[dict[str, Any]], str]


@dataclass(frozen=True)
class RegisteredTool:
    """Runtime binding between a companion tool name and its handler."""

    name: str
    handler: ToolHandler


class ToolRegistry:
    """Allowlist and direct-dispatch table for companion tool calls."""

    def __init__(self, allowed_names: tuple[str, ...] = ()) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._allowed_names: set[str] = set(allowed_names)

    def register(self, tool: RegisteredTool) -> None:
        """Register one direct handler for a tool name."""
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool registration: {tool.name!r}")
        self._tools[tool.name] = tool

    def is_allowed(self, name: str) -> bool:
        """Return whether the tool is advertised or has a direct handler."""
        return name in self._allowed_names or name in self._tools

    def dispatch(self, name: str, arguments: dict[str, Any]) -> str | None:
        """Run a direct handler, or return ``None`` for dispatcher-owned tools."""
        tool = self._tools.get(name)
        if tool is None:
            return None
        return tool.handler(arguments)
