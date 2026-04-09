"""Companion workspace tools: full REPL schemas; execution lives in repl_workspace_tools."""

from __future__ import annotations

from typing import Any

from .repl_workspace_tools import (
    REPL_WRITABLE_RELATIVE_PATHS,
    build_openai_repl_tools,
    build_openai_repl_tools_inner_tick,
)

WORKSPACE_READ_FILE_MAX_CHARS_CAP: int = 120_000
WRITABLE_RELATIVE_PATHS = REPL_WRITABLE_RELATIVE_PATHS


def build_companion_tools() -> list[dict[str, Any]]:
    return build_openai_repl_tools()


__all__ = [
    "WORKSPACE_READ_FILE_MAX_CHARS_CAP",
    "WRITABLE_RELATIVE_PATHS",
    "build_companion_tools",
    "build_openai_repl_tools_inner_tick",
]
