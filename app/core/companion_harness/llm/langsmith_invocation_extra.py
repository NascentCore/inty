"""LangSmith ``langsmith_extra`` builders for Inty OpenAI-wrapped chat completions.

Foreground dual-LLM **chat envelope** (JSON with ``user_facing_reply`` + importance scores) uses
``invocation_extra`` with ``SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE`` (``inty_llm_source`` in metadata).
Background
tool paths use ``tool_call_langsmith_extra``: run **name**
``agentic_companion_tool_call-<phase>`` plus optional auxiliary metadata (no
``inty_llm_source`` on those spans).
"""

from __future__ import annotations

from typing import Any

INTY_LLM_SOURCE_METADATA_KEY = "inty_llm_source"
INTY_TOOL_CHOICE_ATTEMPT_METADATA_KEY = "inty_tool_choice_attempt"
INTY_TOOL_BG_ROUND_METADATA_KEY = "inty_tool_bg_round"

# Companion foreground chat completion that requests structured JSON envelope + importance_* fields.
SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE = "foreground_dual_llm_envelope"
SOURCE_TOOL_BACKGROUND_INITIAL = "tool_background_initial"
SOURCE_TOOL_BACKGROUND_CONTINUE = "tool_background_continue"
SOURCE_TOOL_BACKGROUND_ROUTING_FALLBACK = "tool_background_routing_fallback"

TOOL_CHOICE_ATTEMPT_REQUIRED = "required"
TOOL_CHOICE_ATTEMPT_AUTO = "auto"

LANGSMITH_RUN_NAME_TOOL_CALL_BASE = "agentic_companion_tool_call"


def invocation_extra(
    *,
    source: str,
    run_name: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build ``langsmith_extra`` for foreground envelope (sets ``inty_llm_source``)."""
    meta: dict[str, Any] = {INTY_LLM_SOURCE_METADATA_KEY: source}
    if extra_metadata:
        meta.update(extra_metadata)
    out: dict[str, Any] = {"metadata": meta}
    if run_name:
        out["name"] = run_name
    return out


def tool_call_langsmith_extra(
    *,
    phase_suffix: str,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """LangSmith extra for tool-model client: suffixed run name, optional metadata only."""
    merged: dict[str, Any] = dict(extra_metadata) if extra_metadata else {}
    return {
        "name": f"{LANGSMITH_RUN_NAME_TOOL_CALL_BASE}-{phase_suffix}",
        "metadata": merged,
    }


def tool_choice_attempt_metadata(tool_choice: str | None) -> dict[str, Any]:
    """Normalize ``tool_choice`` argument into ``inty_tool_choice_attempt`` metadata."""
    if tool_choice == "required":
        return {INTY_TOOL_CHOICE_ATTEMPT_METADATA_KEY: TOOL_CHOICE_ATTEMPT_REQUIRED}
    return {INTY_TOOL_CHOICE_ATTEMPT_METADATA_KEY: TOOL_CHOICE_ATTEMPT_AUTO}
