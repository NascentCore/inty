"""Companion tools: OpenAI schemas in this module; execution lives in companion_tool_runtime."""

from __future__ import annotations

from typing import Any

from .companion_tool_runtime import (
    MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP,
    REPL_WRITABLE_RELATIVE_PATHS,
    build_openai_repl_tools,
    build_openai_repl_tools_inner_tick,
)

WRITABLE_RELATIVE_PATHS = REPL_WRITABLE_RELATIVE_PATHS


def build_companion_tools(
    *, interactive_bootstrap_active: bool = False
) -> list[dict[str, Any]]:
    return build_openai_repl_tools(
        interactive_bootstrap_active=interactive_bootstrap_active
    )


__all__ = [
    "MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP",
    "WRITABLE_RELATIVE_PATHS",
    "build_companion_tools",
    "build_openai_repl_tools_inner_tick",
]
