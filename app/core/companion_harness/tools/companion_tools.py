"""Companion tools: OpenAI schemas in this module; execution lives in companion_tool_runtime.

TODO(cleanup): This file can be removed, names referenced here can be replaced by sources.
"""

from __future__ import annotations

from typing import Any

from .companion_tool_runtime import (
    MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    build_openai_bootstrap_track_tools,
    build_openai_repl_tools,
    build_openai_repl_tools_inner_tick,
    build_openai_repl_tools_inner_tick_autonomy,
)


def build_companion_tools(
    *, interactive_bootstrap_active: bool = False
) -> list[dict[str, Any]]:
    return build_openai_repl_tools(
        interactive_bootstrap_active=interactive_bootstrap_active
    )


__all__ = [
    "MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP",
    "MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST",
    "build_companion_tools",
    "build_openai_bootstrap_track_tools",
    "build_openai_repl_tools_inner_tick",
    "build_openai_repl_tools_inner_tick_autonomy",
]
