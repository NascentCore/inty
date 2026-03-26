from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


ToolHandler = Callable[[dict[str, Any]], str]


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: RegisteredTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool registration: {tool.name!r}")
        self._tools[tool.name] = tool

    def dispatch(self, name: str, arguments: dict[str, Any]) -> str | None:
        tool = self._tools.get(name)
        if tool is None:
            return None
        return tool.handler(arguments)
