"""Stable LangSmith ``langsmith_extra`` payloads for Inty LLM call sites.

Maps companion dual-LLM and tool_background phases to ``metadata`` keys so traces
can be filtered without relying on run order. Optional per-invocation ``name``
overrides the wrapped span title when clarity matters (e.g. routing fallback).
"""

from __future__ import annotations

from typing import Any

INTY_LLM_SOURCE_METADATA_KEY = "inty_llm_source"
INTY_TOOL_CHOICE_ATTEMPT_METADATA_KEY = "inty_tool_choice_attempt"
INTY_TOOL_BG_ROUND_METADATA_KEY = "inty_tool_bg_round"

SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE = "foreground_dual_llm_envelope"
SOURCE_TOOL_BACKGROUND_INITIAL = "tool_background_initial"
SOURCE_TOOL_BACKGROUND_CONTINUE = "tool_background_continue"
SOURCE_TOOL_BACKGROUND_ROUTING_FALLBACK = "tool_background_routing_fallback"

TOOL_CHOICE_ATTEMPT_REQUIRED = "required"
TOOL_CHOICE_ATTEMPT_AUTO = "auto"

LANGSMITH_RUN_NAME_TOOL_BG_ROUTING = "agentic_companion_tool_bg_routing"


def invocation_extra(
    *,
    source: str,
    run_name: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a ``langsmith_extra`` dict for ``chat.completions.create`` (wrapped client)."""
    meta: dict[str, Any] = {INTY_LLM_SOURCE_METADATA_KEY: source}
    if extra_metadata:
        meta.update(extra_metadata)
    out: dict[str, Any] = {"metadata": meta}
    if run_name:
        out["name"] = run_name
    return out


def tool_choice_attempt_metadata(tool_choice: str | None) -> dict[str, Any]:
    """Normalize ``tool_choice`` argument into ``inty_tool_choice_attempt`` metadata."""
    if tool_choice == "required":
        return {INTY_TOOL_CHOICE_ATTEMPT_METADATA_KEY: TOOL_CHOICE_ATTEMPT_REQUIRED}
    return {INTY_TOOL_CHOICE_ATTEMPT_METADATA_KEY: TOOL_CHOICE_ATTEMPT_AUTO}
