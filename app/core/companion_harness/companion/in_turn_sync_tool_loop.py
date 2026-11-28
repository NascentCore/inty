"""Shared result type and round budget for the single-LLM in-turn tool loop.

The single-LLM user turn is executed inline by ``AgenticLoop`` (see
``loop/agentic_loop.py`` ``_run_prompt_plan_tool_loop``) over a ``PromptPlan``.
This module only carries the value types shared between that loop and its callers:
``InTurnSyncToolLoopResult`` (the per-turn outcome) and the bootstrap round budget.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

BOOTSTRAP_SYNC_MAX_TOOL_ROUNDS = 24


@dataclass(frozen=True)
class InTurnSyncToolLoopResult:
    """Outputs from one in-turn sync tool loop."""

    assistant_text: str
    langsmith_trace_id: str
    langsmith_run_id: str
    skip_final_transcript_assistant_row: bool
    last_interim_assistant_msg_uuid: str | None
    significance_meta: dict[str, Any] | None = None
    """Moment-level significance perception from a structured envelope, when produced."""
    turn_recall: str | None = None
    """Ephemeral per-turn memory depth from a structured envelope, when produced."""
