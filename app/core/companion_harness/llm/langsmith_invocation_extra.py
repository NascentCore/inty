"""Trace shaping for LangSmith: attach consistent names and metadata to companion LLM calls
so production traces stay readable and easy to slice in the LangSmith UI.

The module separates three observability concerns—foreground user-facing envelope completions,
background tool-model phases, and dreaming memory consolidation—each with naming and tagging
appropriate to how operators and engineers look for them, without mixing semantics across flows.
"""

from __future__ import annotations

from typing import Any

INTY_LLM_SOURCE_METADATA_KEY = "inty_llm_source"
INTY_RUNTIME_CHANNEL_METADATA_KEY = "inty_runtime_channel"
INTY_RUNTIME_CHANNEL_SOURCE_METADATA_KEY = "inty_runtime_channel_source"
INTY_TOOL_CHOICE_ATTEMPT_METADATA_KEY = "inty_tool_choice_attempt"
INTY_TOOL_BG_ROUND_METADATA_KEY = "inty_tool_bg_round"

# Companion foreground chat completion that requests structured JSON envelope + importance_* fields.
# TODO(#3398): Historical dual-LLM user-turn foreground; settled USER_CHAT uses SOURCE_USER_CHAT_IN_TURN_SYNC.
SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE = "foreground_dual_llm_envelope"
SOURCE_BOOTSTRAP_TRACK = "bootstrap_track"
SOURCE_USER_CHAT_IN_TURN_SYNC = "user_chat_in_turn_sync"
SOURCE_IMPLICIT_SIGN_ON_GREETING = "implicit_sign_on_greeting"
SOURCE_SINGLE_COMPLETION = "single_completion"
SOURCE_TOOL_BACKGROUND_INITIAL = "tool_background_initial"
SOURCE_TOOL_BACKGROUND_CONTINUE = "tool_background_continue"
SOURCE_TOOL_BACKGROUND_ROUTING_FALLBACK = "tool_background_routing_fallback"

TOOL_CHOICE_ATTEMPT_REQUIRED = "required"
TOOL_CHOICE_ATTEMPT_AUTO = "auto"

LANGSMITH_RUN_NAME_DREAMING_CONSOLIDATION_BASE = (
    "agentic_companion_dreaming_consolidation"
)


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
    """LangSmith extra for tool-model client: phase as run name, optional metadata only."""
    merged: dict[str, Any] = dict(extra_metadata) if extra_metadata else {}
    return {
        "name": phase_suffix,
        "metadata": merged,
    }


def tool_choice_attempt_metadata(tool_choice: str | None) -> dict[str, Any]:
    """Normalize ``tool_choice`` argument into ``inty_tool_choice_attempt`` metadata."""
    if tool_choice == "required":
        return {
            INTY_TOOL_CHOICE_ATTEMPT_METADATA_KEY: TOOL_CHOICE_ATTEMPT_REQUIRED
        }
    return {INTY_TOOL_CHOICE_ATTEMPT_METADATA_KEY: TOOL_CHOICE_ATTEMPT_AUTO}


def dreaming_consolidation_langsmith_extra(
    *, model_role: str
) -> dict[str, Any]:
    """LangSmith extra for dreaming consolidation curator ``complete_text`` calls."""
    role = (model_role or "memory").strip() or "memory"
    source = f"dreaming_consolidation_{role}"
    return invocation_extra(
        source=source,
        run_name=f"{LANGSMITH_RUN_NAME_DREAMING_CONSOLIDATION_BASE}-{role}",
    )
